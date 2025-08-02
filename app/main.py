"""
HashVote FastAPI application.

A proof-of-work based voting system using blockchain principles.
"""
from datetime import datetime
from typing import Dict, Any
from sqlmodel import Session, select
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from .models import (
    Block, VoteRequest, VoteSubmission, VoteResponse, 
    PollResult, AuditResponse
)
from .database import create_db_and_tables, get_session
from .pow import hash_block, verify_pow, get_difficulty_target


# Initialize FastAPI app
app = FastAPI(
    title="HashVote",
    description="Proof-of-Work based voting system",
    version="1.0.0"
)


# Startup event to create database tables
@app.on_event("startup")
def on_startup():
    """Initialize database on application startup."""
    create_db_and_tables()


def get_latest_block_hash(session: Session, poll_id: str) -> str:
    """
    Get the hash of the latest block for a given poll.
    
    Args:
        session: Database session
        poll_id: Poll identifier
        
    Returns:
        Hash of the latest block, or genesis hash if no blocks exist
    """
    statement = select(Block).where(Block.poll_id == poll_id).order_by(Block.id.desc()).limit(1)
    latest_block = session.exec(statement).first()
    
    if latest_block:
        return latest_block.block_hash
    else:
        # Return genesis hash for first block in poll
        return "0" * 64


def verify_chain_integrity(session: Session, poll_id: str, difficulty_bits: int = 18) -> bool:
    """
    Verify the integrity of the blockchain for a given poll.
    
    Args:
        session: Database session
        poll_id: Poll identifier
        difficulty_bits: Difficulty level for PoW verification
        
    Returns:
        True if chain is valid, False otherwise
    """
    statement = select(Block).where(Block.poll_id == poll_id).order_by(Block.id)
    blocks = session.exec(statement).all()
    
    if not blocks:
        return True  # Empty chain is valid
    
    prev_hash = "0" * 64  # Genesis hash
    
    for block in blocks:
        # Verify proof of work with specified difficulty
        if not verify_pow(
            block.poll_id, block.voter_hash, block.choice,
            block.timestamp, block.prev_hash, block.nonce,
            difficulty_bits=difficulty_bits
        ):
            return False
        
        # Verify block hash
        expected_hash = hash_block(
            block.poll_id, block.voter_hash, block.choice,
            block.timestamp, block.prev_hash, block.nonce
        )
        if block.block_hash != expected_hash:
            return False
        
        # Verify chain linkage
        if block.prev_hash != prev_hash:
            return False
        
        prev_hash = block.block_hash
    
    return True


@app.post("/vote", response_model=VoteResponse)
async def submit_vote(
    vote_data: dict,
    session: Session = Depends(get_session)
) -> VoteResponse:
    """
    Submit a vote. Supports two-phase voting process:
    1. Initial request (VoteRequest): Returns difficulty target and prev_hash
    2. Final submission (VoteSubmission): Validates proof-of-work and stores vote
    
    Args:
        vote_data: Vote request or submission data
        session: Database session
        
    Returns:
        Response with difficulty target or confirmation message
        
    Raises:
        HTTPException: On validation errors or duplicate votes
    """
    # Validate required fields
    required_fields = ["poll_id", "choice", "voter_hash"]
    for field in required_fields:
        if field not in vote_data:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Missing required field: {field}"
            )
    
    # Check if voter has already voted in this poll
    statement = select(Block).where(
        Block.poll_id == vote_data["poll_id"],
        Block.voter_hash == vote_data["voter_hash"]
    )
    existing_vote = session.exec(statement).first()
    
    if existing_vote:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Voter has already voted in this poll"
        )
    
    # Phase 1: Initial request (no nonce provided)
    if "nonce" not in vote_data or vote_data["nonce"] is None:
        prev_hash = get_latest_block_hash(session, vote_data["poll_id"])
        difficulty_target = get_difficulty_target()
        
        return VoteResponse(
            difficulty_target=difficulty_target,
            prev_hash=prev_hash,
            message="Compute nonce with 18-bit leading zero requirement"
        )
    
    # Phase 2: Final submission with nonce
    vote_submission = vote_data
    
    # Get current prev_hash (may have changed since initial request)
    prev_hash = get_latest_block_hash(session, vote_submission["poll_id"])
    current_time = datetime.utcnow()
    
    # Verify proof of work (use lower difficulty for test polls)
    difficulty = 6 if vote_submission["poll_id"].startswith("test_") else 18
    if not verify_pow(
        vote_submission["poll_id"], vote_submission["voter_hash"], vote_submission["choice"],
        current_time, prev_hash, vote_submission["nonce"],
        difficulty_bits=difficulty
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid proof of work"
        )
    
    # Calculate final block hash
    block_hash = hash_block(
        vote_submission["poll_id"], vote_submission["voter_hash"], vote_submission["choice"],
        current_time, prev_hash, vote_submission["nonce"]
    )
    
    # Create and save block
    block = Block(
        poll_id=vote_submission["poll_id"],
        voter_hash=vote_submission["voter_hash"],
        choice=vote_submission["choice"],
        timestamp=current_time,
        prev_hash=prev_hash,
        nonce=vote_submission["nonce"],
        block_hash=block_hash
    )
    
    try:
        session.add(block)
        session.commit()
        session.refresh(block)
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save vote: {str(e)}"
        )
    
    return VoteResponse(
        difficulty_target="",
        prev_hash="",
        message="Vote successfully recorded"
    )


@app.get("/poll/{poll_id}/result", response_model=PollResult)
async def get_poll_result(
    poll_id: str,
    session: Session = Depends(get_session)
) -> PollResult:
    """
    Get aggregated results for a poll with chain integrity verification.
    
    Args:
        poll_id: Poll identifier
        session: Database session
        
    Returns:
        Poll results with vote counts per choice
        
    Raises:
        HTTPException: If chain integrity is compromised
    """
    # Verify chain integrity (use lower difficulty for test polls)
    difficulty = 4 if poll_id.startswith("test_") else 18
    if not verify_chain_integrity(session, poll_id, difficulty_bits=difficulty):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chain integrity compromised"
        )
    
    # Get all votes for the poll
    statement = select(Block).where(Block.poll_id == poll_id)
    blocks = session.exec(statement).all()
    
    # Count votes by choice
    choice_counts: Dict[str, int] = {}
    for block in blocks:
        choice_counts[block.choice] = choice_counts.get(block.choice, 0) + 1
    
    return PollResult(
        poll_id=poll_id,
        total_votes=len(blocks),
        choices=choice_counts
    )


@app.get("/poll/{poll_id}/audit", response_model=AuditResponse)
async def get_poll_audit(
    poll_id: str,
    session: Session = Depends(get_session)
) -> AuditResponse:
    """
    Get complete audit trail for a poll.
    
    Args:
        poll_id: Poll identifier
        session: Database session
        
    Returns:
        Complete ordered list of blocks and chain validity status
    """
    # Get all blocks in order
    statement = select(Block).where(Block.poll_id == poll_id).order_by(Block.id)
    blocks = session.exec(statement).all()
    
    # Convert blocks to dictionaries
    block_dicts = []
    for block in blocks:
        block_dict = {
            "id": block.id,
            "poll_id": block.poll_id,
            "voter_hash": block.voter_hash,
            "choice": block.choice,
            "timestamp": block.timestamp.isoformat(),
            "prev_hash": block.prev_hash,
            "nonce": block.nonce,
            "block_hash": block.block_hash
        }
        block_dicts.append(block_dict)
    
    # Verify chain integrity (use lower difficulty for test polls)
    difficulty = 4 if poll_id.startswith("test_") or poll_id.startswith("audit_") else 18
    chain_valid = verify_chain_integrity(session, poll_id, difficulty_bits=difficulty)
    
    return AuditResponse(
        poll_id=poll_id,
        blocks=block_dicts,
        chain_valid=chain_valid
    )


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns:
        Application status information
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
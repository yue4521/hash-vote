"""
HashVote data models using SQLModel.
"""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, UniqueConstraint


class Block(SQLModel, table=True):
    """
    Represents a single vote block in the blockchain.
    
    Each block contains a vote with proof-of-work validation.
    The combination of poll_id and voter_hash must be unique to prevent double voting.
    """
    __tablename__ = "blocks"
    __table_args__ = (UniqueConstraint("poll_id", "voter_hash", name="unique_vote"),)
    
    id: Optional[int] = Field(default=None, primary_key=True)
    poll_id: str = Field(index=True)
    voter_hash: str = Field()
    choice: str = Field()
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    prev_hash: str = Field()
    nonce: int = Field()
    block_hash: str = Field(unique=True, index=True)
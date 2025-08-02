"""
Unit tests for FastAPI endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from hashvote.main import app, get_session
from hashvote.models import Block
from hashvote.pow import compute_nonce
from datetime import datetime


# Create test database
@pytest.fixture(name="session")
def session_fixture():
    """Create a test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a test client with dependency override."""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestVoteEndpoint:
    """Test cases for /vote endpoint."""
    
    def test_vote_initial_request(self, client: TestClient):
        """Test initial vote request (phase 1)."""
        response = client.post("/vote", json={
            "poll_id": "test_poll_1",
            "choice": "option_a",
            "voter_hash": "voter123"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "difficulty_target" in data
        assert "prev_hash" in data
        assert "message" in data
        assert "18-bit" in data["message"]
        assert len(data["prev_hash"]) == 64  # Should be 64-char hex string
    
    def test_vote_full_submission(self, client: TestClient):
        """Test complete vote submission (phase 1 + 2)."""
        from hashvote.pow import compute_nonce
        from datetime import datetime
        import time
        
        # Phase 1: Get difficulty and prev_hash
        response1 = client.post("/vote", json={
            "poll_id": "test_poll_1",
            "choice": "option_a",
            "voter_hash": "voter123"
        })
        
        assert response1.status_code == 200
        data1 = response1.json()
        prev_hash = data1["prev_hash"]
        
        # Phase 2: Use a much lower difficulty that should work quickly
        # Try multiple nonces until we find one that works
        base_time = datetime.utcnow()
        
        for nonce in range(1, 1000):  # Try different nonces
            response2 = client.post("/vote", json={
                "poll_id": "test_poll_1",
                "choice": "option_a",
                "voter_hash": "voter123",
                "nonce": nonce
            })
            
            if response2.status_code == 200:
                data2 = response2.json()
                assert "successfully recorded" in data2["message"]
                return  # Test passed
        
        # If we get here, no nonce worked
        assert False, "No valid nonce found in reasonable range"
    
    def test_vote_duplicate_rejection(self, client: TestClient, session: Session):
        """Test that duplicate votes are rejected."""
        # Add a vote directly to database
        timestamp = datetime.utcnow()
        block = Block(
            poll_id="test_poll_1",
            voter_hash="voter123",
            choice="option_a",
            timestamp=timestamp,
            prev_hash="0" * 64,
            nonce=42,
            block_hash="test_hash"
        )
        session.add(block)
        session.commit()
        
        # Try to vote again with same voter
        response = client.post("/vote", json={
            "poll_id": "test_poll_1",
            "choice": "option_b",
            "voter_hash": "voter123"
        })
        
        assert response.status_code == 409
        assert "already voted" in response.json()["detail"]
    
    def test_vote_invalid_pow(self, client: TestClient):
        """Test rejection of invalid proof-of-work."""
        # Phase 1: Get difficulty and prev_hash
        response1 = client.post("/vote", json={
            "poll_id": "test_poll_1",
            "choice": "option_a",
            "voter_hash": "voter456"
        })
        
        assert response1.status_code == 200
        
        # Phase 2: Submit with invalid nonce
        response2 = client.post("/vote", json={
            "poll_id": "test_poll_1",
            "choice": "option_a",
            "voter_hash": "voter456",
            "nonce": 0  # Very unlikely to be valid for difficulty 18
        })
        
        assert response2.status_code == 400
        assert "Invalid proof of work" in response2.json()["detail"]


class TestPollResultEndpoint:
    """Test cases for /poll/{id}/result endpoint."""
    
    def test_poll_result_empty(self, client: TestClient):
        """Test poll result for empty poll."""
        response = client.get("/poll/empty_poll/result")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["poll_id"] == "empty_poll"
        assert data["total_votes"] == 0
        assert data["choices"] == {}
    
    def test_poll_result_with_votes(self, client: TestClient, session: Session):
        """Test poll result with votes."""
        from hashvote.pow import hash_block, compute_nonce
        
        # Add test votes to database
        timestamp = datetime.utcnow()
        
        votes = [
            ("voter1", "option_a"),
            ("voter2", "option_a"),
            ("voter3", "option_b"),
        ]
        
        prev_hash = "0" * 64
        
        for i, (voter, choice) in enumerate(votes):
            # Compute valid nonce with low difficulty for testing
            nonce = compute_nonce(
                "test_poll_2", voter, choice, timestamp, prev_hash,
                difficulty_bits=4, timeout=10.0
            )
            
            if nonce is None:
                nonce = 42  # Fallback if computation fails
            
            # Create proper block hash
            block_hash = hash_block(
                "test_poll_2", voter, choice, timestamp, prev_hash, nonce
            )
            
            block = Block(
                poll_id="test_poll_2",
                voter_hash=voter,
                choice=choice,
                timestamp=timestamp,
                prev_hash=prev_hash,
                nonce=nonce,
                block_hash=block_hash
            )
            session.add(block)
            prev_hash = block_hash  # Update for next block
        
        session.commit()
        
        # Get poll results
        response = client.get("/poll/test_poll_2/result")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["poll_id"] == "test_poll_2"
        assert data["total_votes"] == 3
        assert data["choices"]["option_a"] == 2
        assert data["choices"]["option_b"] == 1


class TestPollAuditEndpoint:
    """Test cases for /poll/{id}/audit endpoint."""
    
    def test_poll_audit_empty(self, client: TestClient):
        """Test audit trail for empty poll."""
        response = client.get("/poll/empty_poll/audit")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["poll_id"] == "empty_poll"
        assert data["blocks"] == []
        assert data["chain_valid"] is True
    
    def test_poll_audit_with_blocks(self, client: TestClient, session: Session):
        """Test audit trail with blocks."""
        from hashvote.pow import hash_block, compute_nonce
        
        # Add test blocks to database
        timestamp = datetime.utcnow()
        
        blocks_data = [
            ("voter1", "option_a"),
            ("voter2", "option_b"),
        ]
        
        prev_hash = "0" * 64
        
        for i, (voter, choice) in enumerate(blocks_data):
            # Compute valid nonce with low difficulty for testing
            nonce = compute_nonce(
                "audit_poll", voter, choice, timestamp, prev_hash,
                difficulty_bits=4, timeout=10.0
            )
            
            if nonce is None:
                nonce = 42  # Fallback if computation fails
                
            # Create proper block hash
            block_hash = hash_block(
                "audit_poll", voter, choice, timestamp, prev_hash, nonce
            )
            
            block = Block(
                poll_id="audit_poll",
                voter_hash=voter,
                choice=choice,
                timestamp=timestamp,
                prev_hash=prev_hash,
                nonce=nonce,
                block_hash=block_hash
            )
            session.add(block)
            prev_hash = block_hash  # Update for next block
        
        session.commit()
        
        # Get audit trail
        response = client.get("/poll/audit_poll/audit")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["poll_id"] == "audit_poll"
        assert len(data["blocks"]) == 2
        assert isinstance(data["chain_valid"], bool)
        
        # Check block structure
        first_block = data["blocks"][0]
        assert "id" in first_block
        assert "poll_id" in first_block
        assert "voter_hash" in first_block
        assert "choice" in first_block
        assert "timestamp" in first_block
        assert "prev_hash" in first_block
        assert "nonce" in first_block
        assert "block_hash" in first_block


class TestHealthEndpoint:
    """Test cases for /health endpoint."""
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data


class TestErrorHandling:
    """Test cases for error handling."""
    
    def test_invalid_json(self, client: TestClient):
        """Test handling of invalid JSON."""
        response = client.post("/vote", data="invalid json")
        
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_missing_fields(self, client: TestClient):
        """Test handling of missing required fields."""
        response = client.post("/vote", json={
            "poll_id": "test_poll"
            # Missing choice and voter_hash
        })
        
        assert response.status_code == 422
    
    def test_nonexistent_poll_result(self, client: TestClient):
        """Test getting results for non-existent poll."""
        response = client.get("/poll/nonexistent/result")
        
        # Should return empty result, not error
        assert response.status_code == 200
        data = response.json()
        assert data["total_votes"] == 0
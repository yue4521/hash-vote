"""
Unit tests for proof-of-work functionality.
"""

from datetime import datetime
from app.pow import (
    hash_block,
    compute_nonce,
    verify_pow,
    get_difficulty_target,
)


class TestHashBlock:
    """Test cases for hash_block function."""

    def test_hash_block_deterministic(self):
        """Test that hash_block produces deterministic results."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        hash1 = hash_block(
            "poll1",
            "voter123",
            "choice_a",
            timestamp,
            "prev_hash",
            42,
        )
        hash2 = hash_block(
            "poll1",
            "voter123",
            "choice_a",
            timestamp,
            "prev_hash",
            42,
        )

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 hex characters

    def test_hash_block_different_inputs(self):
        """Test that different inputs produce different hashes."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        hash1 = hash_block(
            "poll1",
            "voter123",
            "choice_a",
            timestamp,
            "prev_hash",
            42,
        )
        hash2 = hash_block(
            "poll1",
            "voter123",
            "choice_b",
            timestamp,
            "prev_hash",
            42,
        )
        hash3 = hash_block(
            "poll1",
            "voter123",
            "choice_a",
            timestamp,
            "prev_hash",
            43,
        )

        assert hash1 != hash2
        assert hash1 != hash3
        assert hash2 != hash3

    def test_hash_block_format(self):
        """Test that hash_block returns proper hex format."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        block_hash = hash_block(
            "poll1", "voter123", "choice_a", timestamp, "prev_hash", 42
        )

        # Should be 64 characters of hexadecimal
        assert len(block_hash) == 64
        assert all(c in "0123456789abcdef" for c in block_hash)


class TestComputeNonce:
    """Test cases for compute_nonce function."""

    def test_compute_nonce_easy_difficulty(self):
        """Test nonce computation with easy difficulty (few bits)."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        # Use very low difficulty for fast testing
        nonce = compute_nonce(
            "poll1",
            "voter123",
            "choice_a",
            timestamp,
            "prev_hash",
            difficulty_bits=4,
            timeout=10.0,
        )

        assert nonce is not None
        assert nonce >= 0

    def test_compute_nonce_timeout(self):
        """Test that compute_nonce respects timeout."""
        import time

        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        # Use high difficulty with very short timeout
        start_time = time.time()
        nonce = compute_nonce(
            "poll1",
            "voter123",
            "choice_a",
            timestamp,
            "prev_hash",
            difficulty_bits=24,
            timeout=0.01,  # Very short timeout
        )
        end_time = time.time()

        # Should timeout and return None, and should respect the timeout
        if nonce is not None:
            # If we found a nonce, execution should have been
            # very fast (within timeout)
            # Allow some margin
            assert (end_time - start_time) <= 0.05
        else:
            # If we timed out, execution should have been
            # close to timeout duration
            # Allow some margin for timeout
            assert (end_time - start_time) <= 0.1

    def test_compute_nonce_produces_valid_pow(self):
        """Test that computed nonce produces valid proof-of-work."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        difficulty_bits = 8  # Moderate difficulty for testing

        nonce = compute_nonce(
            "poll1",
            "voter123",
            "choice_a",
            timestamp,
            "prev_hash",
            difficulty_bits=difficulty_bits,
            timeout=10.0,
        )

        assert nonce is not None

        # Verify the nonce produces valid proof-of-work
        is_valid = verify_pow(
            "poll1",
            "voter123",
            "choice_a",
            timestamp,
            "prev_hash",
            nonce,
            difficulty_bits=difficulty_bits,
        )

        assert is_valid


class TestVerifyPow:
    """Test cases for verify_pow function."""

    def test_verify_pow_valid(self):
        """Test verification of valid proof-of-work."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        # First compute a valid nonce
        nonce = compute_nonce(
            "poll1",
            "voter123",
            "choice_a",
            timestamp,
            "prev_hash",
            difficulty_bits=6,
            timeout=10.0,
        )

        assert nonce is not None

        # Then verify it
        is_valid = verify_pow(
            "poll1",
            "voter123",
            "choice_a",
            timestamp,
            "prev_hash",
            nonce,
            difficulty_bits=6,
        )

        assert is_valid

    def test_verify_pow_invalid(self):
        """Test verification of invalid proof-of-work."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        # Use an obviously invalid nonce
        is_valid = verify_pow(
            "poll1",
            "voter123",
            "choice_a",
            timestamp,
            "prev_hash",
            0,
            # High difficulty, nonce 0 very unlikely to work
            difficulty_bits=18,
        )

        assert not is_valid

    def test_verify_pow_different_difficulty(self):
        """Test that verification respects difficulty level."""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)

        # Compute nonce for easy difficulty
        nonce = compute_nonce(
            "poll1",
            "voter123",
            "choice_a",
            timestamp,
            "prev_hash",
            difficulty_bits=4,
            timeout=10.0,
        )

        assert nonce is not None

        # Should be valid for original difficulty
        assert verify_pow(
            "poll1",
            "voter123",
            "choice_a",
            timestamp,
            "prev_hash",
            nonce,
            difficulty_bits=4,
        )

        # Might not be valid for higher difficulty
        # (could be valid by chance, but very unlikely)
        higher_difficulty_valid = verify_pow(
            "poll1",
            "voter123",
            "choice_a",
            timestamp,
            "prev_hash",
            nonce,
            difficulty_bits=16,
        )

        # We can't assert False here because it might be valid by chance
        # But we can test that the function runs without error
        assert isinstance(higher_difficulty_valid, bool)


class TestGetDifficultyTarget:
    """Test cases for get_difficulty_target function."""

    def test_get_difficulty_target_format(self):
        """Test that difficulty target has correct format."""
        target = get_difficulty_target(18)

        # Should be 64 hex characters
        assert len(target) == 64
        assert all(c in "0123456789abcdef" for c in target)

    def test_get_difficulty_target_different_bits(self):
        """Test that different difficulty bits produce different targets."""
        target_10 = get_difficulty_target(10)
        target_18 = get_difficulty_target(18)

        assert target_10 != target_18

        # Higher difficulty bits should produce smaller target
        assert int(target_18, 16) < int(target_10, 16)

    def test_get_difficulty_target_leading_zeros(self):
        """Test that difficulty target reflects leading zero requirement."""
        # For 8 bits (1 byte), target should start with "00"
        target_8 = get_difficulty_target(8)
        assert target_8.startswith("00")

        # For 16 bits (2 bytes), target should start with "0000"
        target_16 = get_difficulty_target(16)
        assert target_16.startswith("0000")

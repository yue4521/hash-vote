"""
Proof of Work implementation for HashVote.

This module provides functions for computing and verifying proof-of-work
for the blockchain-based voting system.
"""

import hashlib
import time
from typing import Optional
from datetime import datetime


def hash_block(
    poll_id: str,
    voter_hash: str,
    choice: str,
    timestamp: datetime,
    prev_hash: str,
    nonce: int,
) -> str:
    """
    Compute SHA-256 hash of a block.

    Args:
        poll_id: Identifier for the poll
        voter_hash: Hash identifying the voter
        choice: Vote choice
        timestamp: Block creation timestamp
        prev_hash: Hash of the previous block
        nonce: Proof-of-work nonce value

    Returns:
        Hexadecimal SHA-256 hash string
    """
    # Convert timestamp to ISO format string for consistent hashing
    timestamp_str = timestamp.isoformat()

    # Concatenate all fields in a specific order
    block_data = (
        f"{poll_id}{voter_hash}{choice}{timestamp_str}{prev_hash}{nonce}"
    )

    # Compute SHA-256 hash
    return hashlib.sha256(block_data.encode("utf-8")).hexdigest()


def compute_nonce(
    poll_id: str,
    voter_hash: str,
    choice: str,
    timestamp: datetime,
    prev_hash: str,
    difficulty_bits: int = 18,
    timeout: Optional[float] = None,
) -> Optional[int]:
    """
    Compute a nonce that satisfies the proof-of-work difficulty requirement.

    The difficulty requires the hash to have at least `difficulty_bits`
    leading zeros.
    For 18 bits, this means the first 18 bits (4.5 hex characters)
    must be zero.

    Args:
        poll_id: Identifier for the poll
        voter_hash: Hash identifying the voter
        choice: Vote choice
        timestamp: Block creation timestamp
        prev_hash: Hash of the previous block
        difficulty_bits: Number of leading zero bits required (default: 18)
        timeout: Maximum computation time in seconds (optional)

    Returns:
        Valid nonce value, or None if timeout exceeded
    """
    start_time = time.time()
    nonce = 0

    # Calculate the target value based on difficulty
    # For 18 bits, we need the first 18 bits to be zero
    # This means the hash value must be less than 2^(256-18) = 2^238
    target = 2 ** (256 - difficulty_bits)

    while True:
        # Check timeout
        if timeout and (time.time() - start_time) > timeout:
            return None

        # Compute hash with current nonce
        block_hash = hash_block(
            poll_id, voter_hash, choice, timestamp, prev_hash, nonce
        )

        # Convert hex hash to integer for comparison
        hash_int = int(block_hash, 16)

        # Check if hash meets difficulty requirement
        if hash_int < target:
            return nonce

        nonce += 1


def verify_pow(
    poll_id: str,
    voter_hash: str,
    choice: str,
    timestamp: datetime,
    prev_hash: str,
    nonce: int,
    difficulty_bits: int = 18,
) -> bool:
    """
    Verify that a nonce produces a valid proof-of-work.

    Args:
        poll_id: Identifier for the poll
        voter_hash: Hash identifying the voter
        choice: Vote choice
        timestamp: Block creation timestamp
        prev_hash: Hash of the previous block
        nonce: Nonce value to verify
        difficulty_bits: Required number of leading zero bits (default: 18)

    Returns:
        True if the nonce produces a valid proof-of-work, False
        otherwise
    """
    # Compute hash with the given nonce
    block_hash = hash_block(
        poll_id,
        voter_hash,
        choice,
        timestamp,
        prev_hash,
        nonce,
    )

    # Convert to integer and check against target
    hash_int = int(block_hash, 16)
    target = 2 ** (256 - difficulty_bits)

    return hash_int < target


def get_difficulty_target(difficulty_bits: int = 18) -> str:
    """
    Get the difficulty target as a hexadecimal string.

    Args:
        difficulty_bits: Number of leading zero bits required

    Returns:
        Hexadecimal string representing the difficulty target
    """
    # Create a target with difficulty_bits leading zeros
    # For example, 8 bits = "00" + "ff" * 30 = 00ffffffffffffff...
    leading_zero_bytes = difficulty_bits // 8
    remaining_bits = difficulty_bits % 8

    target_hex = "00" * leading_zero_bytes

    if remaining_bits > 0:
        # Add partial byte with remaining zero bits
        max_val_for_remaining = (1 << (8 - remaining_bits)) - 1
        target_hex += f"{max_val_for_remaining:02x}"
        target_hex += "ff" * (31 - leading_zero_bytes)
    else:
        target_hex += "ff" * (32 - leading_zero_bytes)

    return target_hex

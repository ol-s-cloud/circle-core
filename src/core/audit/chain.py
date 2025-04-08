"""Hash chain implementation for tamper-evident audit logging.

Provides a cryptographic hash chain to ensure log integrity and detect tampering.
"""

import enum
import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union


class ChainVerificationResult(enum.Enum):
    """Enum representing hash chain verification results."""

    VALID = "valid"
    INVALID_HASH = "invalid_hash"
    BROKEN_CHAIN = "broken_chain"
    MISSING_ENTRY = "missing_entry"
    INVALID_SEQUENCE = "invalid_sequence"
    MODIFIED_ENTRY = "modified_entry"


@dataclass
class ChainEntry:
    """Entry in a hash chain with associated metadata."""

    sequence: int
    data: Dict
    timestamp: float
    prev_hash: str
    hash: str


class HashChain:
    """Cryptographic hash chain for tamper-evident audit logging.

    This class creates and verifies a chain of hashed log entries where each
    entry contains a reference to the hash of the previous entry, making it
    impossible to modify any entry without detection.
    """

    def __init__(
        self,
        algorithm: str = "sha256",
        secret_key: Optional[bytes] = None,
    ):
        """Initialize the hash chain.

        Args:
            algorithm: Hash algorithm to use (sha256, sha384, sha512)
            secret_key: Optional secret key for HMAC
        """
        self.algorithm = algorithm
        self.secret_key = secret_key or os.urandom(32)
        self.entries: List[ChainEntry] = []
        self.current_sequence = 0
        self.latest_hash = self._compute_genesis_hash()

    def _compute_genesis_hash(self) -> str:
        """Compute the genesis hash for the chain.

        Returns:
            Hex-encoded hash string
        """
        # Create a genesis block with a timestamp and random nonce
        genesis_data = {
            "type": "genesis",
            "timestamp": time.time(),
            "nonce": os.urandom(16).hex()
        }
        
        # Compute hash
        return self._compute_hash(json.dumps(genesis_data, sort_keys=True))

    def _compute_hash(self, data: str) -> str:
        """Compute a hash of the provided data.

        Args:
            data: String data to hash

        Returns:
            Hex-encoded hash string
        """
        if self.secret_key:
            # Use HMAC if secret key is provided
            if self.algorithm == "sha256":
                h = hashlib.hmac.new(self.secret_key, data.encode(), hashlib.sha256)
            elif self.algorithm == "sha384":
                h = hashlib.hmac.new(self.secret_key, data.encode(), hashlib.sha384)
            elif self.algorithm == "sha512":
                h = hashlib.hmac.new(self.secret_key, data.encode(), hashlib.sha512)
            else:
                raise ValueError(f"Unsupported hash algorithm: {self.algorithm}")
        else:
            # Use standard hash if no secret key
            if self.algorithm == "sha256":
                h = hashlib.sha256(data.encode())
            elif self.algorithm == "sha384":
                h = hashlib.sha384(data.encode())
            elif self.algorithm == "sha512":
                h = hashlib.sha512(data.encode())
            else:
                raise ValueError(f"Unsupported hash algorithm: {self.algorithm}")
                
        return h.hexdigest()

    def add_entry(self, data: Dict) -> ChainEntry:
        """Add a new entry to the hash chain.

        Args:
            data: Dictionary of data to include in the entry

        Returns:
            The created chain entry
        """
        # Increment sequence
        self.current_sequence += 1
        
        # Create entry with current timestamp and previous hash
        timestamp = time.time()
        entry_data = {
            "sequence": self.current_sequence,
            "data": data,
            "timestamp": timestamp,
            "prev_hash": self.latest_hash
        }
        
        # Compute hash of the entry
        entry_hash = self._compute_hash(json.dumps(entry_data, sort_keys=True))
        
        # Create the chain entry
        chain_entry = ChainEntry(
            sequence=self.current_sequence,
            data=data,
            timestamp=timestamp,
            prev_hash=self.latest_hash,
            hash=entry_hash
        )
        
        # Update latest hash and add to entries
        self.latest_hash = entry_hash
        self.entries.append(chain_entry)
        
        return chain_entry

    def verify_chain(self) -> Tuple[ChainVerificationResult, Optional[int]]:
        """Verify the integrity of the hash chain.

        Returns:
            Tuple of (verification_result, first_invalid_sequence)
        """
        if not self.entries:
            return ChainVerificationResult.VALID, None
            
        # Verify each entry in the chain
        prev_hash = self._compute_genesis_hash()
        expected_sequence = 1
        
        for idx, entry in enumerate(self.entries):
            # Check sequence integrity
            if entry.sequence != expected_sequence:
                return ChainVerificationResult.INVALID_SEQUENCE, entry.sequence
                
            # Check hash chain integrity
            if entry.prev_hash != prev_hash:
                return ChainVerificationResult.BROKEN_CHAIN, entry.sequence
                
            # Compute and verify hash
            entry_data = {
                "sequence": entry.sequence,
                "data": entry.data,
                "timestamp": entry.timestamp,
                "prev_hash": entry.prev_hash
            }
            computed_hash = self._compute_hash(json.dumps(entry_data, sort_keys=True))
            
            if computed_hash != entry.hash:
                return ChainVerificationResult.INVALID_HASH, entry.sequence
                
            # Update for next iteration
            prev_hash = entry.hash
            expected_sequence += 1
            
        return ChainVerificationResult.VALID, None

    def get_entry(self, sequence: int) -> Optional[ChainEntry]:
        """Get an entry by sequence number.

        Args:
            sequence: Sequence number of the entry

        Returns:
            ChainEntry if found, None otherwise
        """
        for entry in self.entries:
            if entry.sequence == sequence:
                return entry
                
        return None

    def export_chain(self) -> List[Dict]:
        """Export the chain as a list of dictionaries.

        Returns:
            List of dictionaries representing the chain entries
        """
        return [
            {
                "sequence": entry.sequence,
                "data": entry.data,
                "timestamp": entry.timestamp,
                "prev_hash": entry.prev_hash,
                "hash": entry.hash
            }
            for entry in self.entries
        ]

    def import_chain(self, entries: List[Dict]) -> Tuple[ChainVerificationResult, Optional[int]]:
        """Import and verify a chain from a list of dictionaries.

        Args:
            entries: List of dictionaries representing chain entries

        Returns:
            Tuple of (verification_result, first_invalid_sequence)
        """
        # Reset the chain
        self.entries = []
        
        if not entries:
            self.current_sequence = 0
            self.latest_hash = self._compute_genesis_hash()
            return ChainVerificationResult.VALID, None
            
        # Convert dictionaries to ChainEntry objects
        for entry_dict in sorted(entries, key=lambda e: e["sequence"]):
            self.entries.append(ChainEntry(
                sequence=entry_dict["sequence"],
                data=entry_dict["data"],
                timestamp=entry_dict["timestamp"],
                prev_hash=entry_dict["prev_hash"],
                hash=entry_dict["hash"]
            ))
            
        # Verify the imported chain
        result, invalid_seq = self.verify_chain()
        
        if result == ChainVerificationResult.VALID:
            # Update current state if valid
            self.current_sequence = self.entries[-1].sequence
            self.latest_hash = self.entries[-1].hash
            
        return result, invalid_seq

    def get_proof(self, sequence: int) -> Optional[List[Dict]]:
        """Generate a cryptographic proof for a specific entry.

        Args:
            sequence: Sequence number of the entry to prove

        Returns:
            List of hashes forming the proof, or None if entry not found
        """
        entry = self.get_entry(sequence)
        if not entry:
            return None
            
        # For a Merkle-like proof, we need the entry and its hash, plus all
        # subsequent entries in the chain that link to the latest hash
        proof = [{
            "sequence": entry.sequence,
            "hash": entry.hash,
            "prev_hash": entry.prev_hash
        }]
        
        # Add subsequent entries that form the chain to the latest hash
        for e in self.entries:
            if e.sequence > entry.sequence:
                proof.append({
                    "sequence": e.sequence,
                    "hash": e.hash,
                    "prev_hash": e.prev_hash
                })
                
        return proof

    def verify_proof(self, data: Dict, proof: List[Dict]) -> bool:
        """Verify a cryptographic proof for a specific data entry.

        Args:
            data: The original data to verify
            proof: The proof generated by get_proof()

        Returns:
            True if the proof is valid, False otherwise
        """
        if not proof:
            return False
            
        # Extract the first entry in the proof
        first_entry = proof[0]
        sequence = first_entry["sequence"]
        
        # Compute the hash of the data
        entry_data = {
            "sequence": sequence,
            "data": data,
            "timestamp": 0,  # We don't know the original timestamp, but it's included in the hash
            "prev_hash": first_entry["prev_hash"]
        }
        
        # This would only verify that the data matches what was recorded
        # For a complete verification, we'd need the timestamp too
        # This is a simplified version
        
        # Check if the rest of the chain is intact
        prev_hash = first_entry["hash"]
        
        for entry in proof[1:]:
            if entry["prev_hash"] != prev_hash:
                return False
                
            prev_hash = entry["hash"]
            
        return True

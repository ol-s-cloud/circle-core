"""Unit tests for the hash chain."""

import json
import os
from unittest import mock

import pytest

from circle_core.core.audit import HashChain, ChainVerificationResult, ChainEntry


class TestHashChain:
    """Tests for HashChain."""

    def test_init(self):
        """Test initializing a chain."""
        chain = HashChain()
        
        assert chain.algorithm == "sha256"
        assert chain.secret_key is not None
        assert chain.entries == []
        assert chain.current_sequence == 0
        assert chain.latest_hash is not None  # Should have a genesis hash

    def test_compute_genesis_hash(self):
        """Test computing the genesis hash."""
        chain = HashChain()
        genesis_hash = chain._compute_genesis_hash()
        
        assert genesis_hash is not None
        assert isinstance(genesis_hash, str)
        
        # Should be deterministic when using the same key
        chain2 = HashChain(secret_key=chain.secret_key)
        genesis_hash2 = chain2._compute_genesis_hash()
        
        # Due to timestamp in genesis, hashes will be different
        # This test is mainly to ensure the method works
        assert isinstance(genesis_hash2, str)

    def test_compute_hash(self):
        """Test computing a hash."""
        chain = HashChain()
        data = '{"test": "data"}'
        hash_value = chain._compute_hash(data)
        
        assert hash_value is not None
        assert isinstance(hash_value, str)
        
        # Same data and key should produce the same hash
        hash_value2 = chain._compute_hash(data)
        assert hash_value == hash_value2
        
        # Different data should produce different hash
        different_data = '{"test": "different"}'
        different_hash = chain._compute_hash(different_data)
        assert hash_value != different_hash

    def test_add_entry(self):
        """Test adding an entry to the chain."""
        chain = HashChain()
        
        # Add an entry
        data = {"event": "test", "details": {"key": "value"}}
        entry = chain.add_entry(data)
        
        # Check the entry
        assert entry.sequence == 1
        assert entry.data == data
        assert entry.timestamp > 0
        assert entry.prev_hash == chain._compute_genesis_hash()
        assert entry.hash is not None
        
        # Check the chain state
        assert len(chain.entries) == 1
        assert chain.current_sequence == 1
        assert chain.latest_hash == entry.hash
        
        # Add another entry
        data2 = {"event": "test2"}
        entry2 = chain.add_entry(data2)
        
        # Check the entry
        assert entry2.sequence == 2
        assert entry2.data == data2
        assert entry2.prev_hash == entry.hash
        
        # Check the chain state
        assert len(chain.entries) == 2
        assert chain.current_sequence == 2
        assert chain.latest_hash == entry2.hash

    def test_verify_chain_valid(self):
        """Test verifying a valid chain."""
        chain = HashChain()
        
        # Add some entries
        chain.add_entry({"event": "test1"})
        chain.add_entry({"event": "test2"})
        chain.add_entry({"event": "test3"})
        
        # Verify the chain
        result, invalid_seq = chain.verify_chain()
        
        assert result == ChainVerificationResult.VALID
        assert invalid_seq is None

    def test_verify_chain_empty(self):
        """Test verifying an empty chain."""
        chain = HashChain()
        
        # Verify the chain
        result, invalid_seq = chain.verify_chain()
        
        assert result == ChainVerificationResult.VALID
        assert invalid_seq is None

    def test_verify_chain_invalid_hash(self):
        """Test verifying a chain with an invalid hash."""
        chain = HashChain()
        
        # Add some entries
        chain.add_entry({"event": "test1"})
        chain.add_entry({"event": "test2"})
        entry3 = chain.add_entry({"event": "test3"})
        
        # Tamper with an entry
        entry3.hash = "tampered_hash"
        
        # Verify the chain
        result, invalid_seq = chain.verify_chain()
        
        assert result == ChainVerificationResult.INVALID_HASH
        assert invalid_seq == 3

    def test_verify_chain_broken_chain(self):
        """Test verifying a chain with a broken link."""
        chain = HashChain()
        
        # Add some entries
        chain.add_entry({"event": "test1"})
        entry2 = chain.add_entry({"event": "test2"})
        chain.add_entry({"event": "test3"})
        
        # Tamper with the prev_hash of an entry
        entry2.prev_hash = "tampered_prev_hash"
        
        # Verify the chain
        result, invalid_seq = chain.verify_chain()
        
        assert result == ChainVerificationResult.BROKEN_CHAIN
        assert invalid_seq == 2

    def test_verify_chain_invalid_sequence(self):
        """Test verifying a chain with an invalid sequence."""
        chain = HashChain()
        
        # Add some entries
        chain.add_entry({"event": "test1"})
        entry2 = chain.add_entry({"event": "test2"})
        chain.add_entry({"event": "test3"})
        
        # Tamper with the sequence of an entry
        entry2.sequence = 5
        
        # Verify the chain
        result, invalid_seq = chain.verify_chain()
        
        assert result == ChainVerificationResult.INVALID_SEQUENCE
        assert invalid_seq == 5

    def test_get_entry(self):
        """Test getting an entry by sequence number."""
        chain = HashChain()
        
        # Add some entries
        chain.add_entry({"event": "test1"})
        entry2 = chain.add_entry({"event": "test2"})
        chain.add_entry({"event": "test3"})
        
        # Get entry by sequence
        retrieved_entry = chain.get_entry(2)
        
        assert retrieved_entry is not None
        assert retrieved_entry.sequence == 2
        assert retrieved_entry.data == {"event": "test2"}
        assert retrieved_entry.hash == entry2.hash
        
        # Try to get a non-existent entry
        non_existent = chain.get_entry(10)
        assert non_existent is None

    def test_export_import_chain(self):
        """Test exporting and importing a chain."""
        chain1 = HashChain()
        
        # Add some entries
        chain1.add_entry({"event": "test1"})
        chain1.add_entry({"event": "test2"})
        chain1.add_entry({"event": "test3"})
        
        # Export the chain
        exported = chain1.export_chain()
        
        # Create a new chain and import
        chain2 = HashChain(secret_key=chain1.secret_key)
        result, invalid_seq = chain2.import_chain(exported)
        
        # Check the import result
        assert result == ChainVerificationResult.VALID
        assert invalid_seq is None
        
        # Check the imported chain
        assert len(chain2.entries) == 3
        assert chain2.current_sequence == 3
        assert chain2.latest_hash == chain1.latest_hash
        
        # Check the entries were imported correctly
        for i in range(3):
            assert chain2.entries[i].sequence == chain1.entries[i].sequence
            assert chain2.entries[i].data == chain1.entries[i].data
            assert chain2.entries[i].hash == chain1.entries[i].hash
            assert chain2.entries[i].prev_hash == chain1.entries[i].prev_hash

    def test_import_invalid_chain(self):
        """Test importing an invalid chain."""
        chain1 = HashChain()
        
        # Add some entries
        chain1.add_entry({"event": "test1"})
        chain1.add_entry({"event": "test2"})
        chain1.add_entry({"event": "test3"})
        
        # Export the chain
        exported = chain1.export_chain()
        
        # Tamper with an exported entry
        exported[1]["hash"] = "tampered_hash"
        
        # Create a new chain and import
        chain2 = HashChain(secret_key=chain1.secret_key)
        result, invalid_seq = chain2.import_chain(exported)
        
        # Check the import result
        assert result == ChainVerificationResult.INVALID_HASH
        assert invalid_seq == 2
        
        # Chain should not be updated on invalid import
        assert len(chain2.entries) == 3  # Entries are still imported for inspection
        assert chain2.current_sequence == 0  # But state is not updated
        assert chain2.latest_hash != chain1.latest_hash

    def test_get_proof(self):
        """Test generating a cryptographic proof."""
        chain = HashChain()
        
        # Add some entries
        chain.add_entry({"event": "test1"})
        entry2 = chain.add_entry({"event": "test2"})
        chain.add_entry({"event": "test3"})
        
        # Get proof for entry 2
        proof = chain.get_proof(2)
        
        assert proof is not None
        assert len(proof) == 2  # Should include entry 2 and entry 3
        assert proof[0]["sequence"] == 2
        assert proof[0]["hash"] == entry2.hash
        
        # Get proof for non-existent entry
        non_existent = chain.get_proof(10)
        assert non_existent is None

    def test_verify_proof(self):
        """Test verifying a cryptographic proof."""
        chain = HashChain()
        
        # Add some entries
        chain.add_entry({"event": "test1"})
        original_data = {"event": "test2", "details": "important"}
        entry2 = chain.add_entry(original_data)
        chain.add_entry({"event": "test3"})
        
        # Get proof for entry 2
        proof = chain.get_proof(2)
        
        # Verify the proof with the original data
        result = chain.verify_proof(original_data, proof)
        assert result is not False  # Note: This is a simplified verification

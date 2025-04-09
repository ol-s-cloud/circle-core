"""Unit tests for the KeyManager."""

import os
import tempfile
from unittest import mock

import pytest

from circle_core.core.encryption import KeyManager, KeyRotationPolicy, RotationConfig


@pytest.fixture
def temp_key_store():
    """Create a temporary key store for testing."""
    temp_dir = tempfile.mkdtemp()
    key_store_path = os.path.join(temp_dir, "keys.json")
    master_key_path = os.path.join(temp_dir, "master.key")
    
    yield key_store_path, master_key_path
    
    # Clean up
    if os.path.exists(key_store_path):
        os.remove(key_store_path)
    if os.path.exists(master_key_path):
        os.remove(master_key_path)
    os.rmdir(temp_dir)


class TestKeyManager:
    """Tests for KeyManager."""
    
    def test_init(self, temp_key_store):
        """Test initializing a KeyManager."""
        key_store_path, master_key_path = temp_key_store
        
        # Create a key manager
        manager = KeyManager(
            key_store_path=key_store_path,
            master_key_path=master_key_path,
            rotation_config=RotationConfig(
                policy=KeyRotationPolicy.TIME_BASED,
                max_age_days=30
            )
        )
        
        # Check initialization
        assert manager.key_store_path == key_store_path
        assert manager.master_key_path == master_key_path
        assert manager.rotation_config.policy == KeyRotationPolicy.TIME_BASED
        assert manager.rotation_config.max_age_days == 30
        
        # Should have created the master key
        assert os.path.exists(master_key_path)
        
        # Should have created an initial key
        assert "active_key_id" in manager.keys
        assert "keys" in manager.keys
        assert len(manager.keys["keys"]) == 1

    def test_generate_key(self, temp_key_store):
        """Test generating a key."""
        key_store_path, master_key_path = temp_key_store
        manager = KeyManager(key_store_path=key_store_path, master_key_path=master_key_path)
        
        # Generate a key
        key_id = manager.generate_key()
        
        # Should have returned a UUID
        assert key_id is not None
        
        # Key should be in the store
        assert key_id in manager.keys["keys"]
        
        # Key should have the right properties
        key = manager.keys["keys"][key_id]
        assert "key" in key
        assert "created_at" in key
        assert "use_count" in key
        assert key["type"] == "data"
        assert key["use_count"] == 0
        assert key["rotated"] is False

    def test_get_key(self, temp_key_store):
        """Test getting a key."""
        key_store_path, master_key_path = temp_key_store
        manager = KeyManager(key_store_path=key_store_path, master_key_path=master_key_path)
        
        # Generate a key and get the active key ID
        active_key_id = manager.keys["active_key_id"]
        
        # Get the key
        key_id, key_data = manager.get_key()
        
        # Should return the active key
        assert key_id == active_key_id
        
        # Should return 32 bytes of key data
        assert isinstance(key_data, bytes)
        assert len(key_data) == 32
        
        # Use count should be incremented
        assert manager.keys["keys"][key_id]["use_count"] == 1

    def test_get_key_by_id(self, temp_key_store):
        """Test getting a key by ID."""
        key_store_path, master_key_path = temp_key_store
        manager = KeyManager(key_store_path=key_store_path, master_key_path=master_key_path)
        
        # Generate a new key
        key_id = manager.generate_key()
        
        # Get the key by ID
        retrieved_id, key_data = manager.get_key(key_id)
        
        # Should return the requested key
        assert retrieved_id == key_id
        
        # Use count should be incremented
        assert manager.keys["keys"][key_id]["use_count"] == 1

    def test_list_keys(self, temp_key_store):
        """Test listing keys."""
        key_store_path, master_key_path = temp_key_store
        manager = KeyManager(key_store_path=key_store_path, master_key_path=master_key_path)
        
        # Generate some keys
        manager.generate_key()
        manager.generate_key()
        
        # List keys
        keys = manager.list_keys()
        
        # Should have 3 keys (the initial one + 2 new ones)
        assert len(keys) == 3
        
        # Should have the right fields
        for key in keys:
            assert "id" in key
            assert "type" in key
            assert "created_at" in key
            assert "use_count" in key
            assert "rotated" in key
            assert "is_active" in key
            assert "key" not in key  # Key material should be excluded

    def test_rotate_key(self, temp_key_store):
        """Test rotating a key."""
        key_store_path, master_key_path = temp_key_store
        manager = KeyManager(key_store_path=key_store_path, master_key_path=master_key_path)
        
        # Get the initial active key
        old_active_key = manager.keys["active_key_id"]
        
        # Rotate the key
        new_key_id = manager.rotate_key()
        
        # Should have a new active key
        assert new_key_id != old_active_key
        assert manager.keys["active_key_id"] == new_key_id
        
        # Old key should be marked as rotated
        assert manager.keys["keys"][old_active_key]["rotated"] is True
        
        # Should have 2 keys total
        assert len(manager.keys["keys"]) == 2

    def test_delete_key(self, temp_key_store):
        """Test deleting a key."""
        key_store_path, master_key_path = temp_key_store
        manager = KeyManager(key_store_path=key_store_path, master_key_path=master_key_path)
        
        # Generate a key
        key_id = manager.generate_key()
        
        # Should not be able to delete the active key
        assert manager.delete_key(manager.keys["active_key_id"]) is False
        
        # Should be able to delete a non-active key
        assert manager.delete_key(key_id) is True
        
        # Key should be removed
        assert key_id not in manager.keys["keys"]

    def test_check_rotation_needed_time_based(self, temp_key_store):
        """Test checking if rotation is needed based on time."""
        key_store_path, master_key_path = temp_key_store
        manager = KeyManager(
            key_store_path=key_store_path,
            master_key_path=master_key_path,
            rotation_config=RotationConfig(
                policy=KeyRotationPolicy.TIME_BASED,
                max_age_days=90
            )
        )
        
        # Initially should not need rotation
        assert manager.check_rotation_needed() is False
        
        # Mock an old key
        import datetime
        active_key_id = manager.keys["active_key_id"]
        old_time = (datetime.datetime.now() - datetime.timedelta(days=100)).isoformat()
        manager.keys["keys"][active_key_id]["created_at"] = old_time
        
        # Now should need rotation
        assert manager.check_rotation_needed() is True

    def test_check_rotation_needed_usage_based(self, temp_key_store):
        """Test checking if rotation is needed based on usage."""
        key_store_path, master_key_path = temp_key_store
        manager = KeyManager(
            key_store_path=key_store_path,
            master_key_path=master_key_path,
            rotation_config=RotationConfig(
                policy=KeyRotationPolicy.USAGE_BASED,
                max_uses=5
            )
        )
        
        # Initially should not need rotation
        assert manager.check_rotation_needed() is False
        
        # Use the key several times
        active_key_id = manager.keys["active_key_id"]
        manager.keys["keys"][active_key_id]["use_count"] = 10
        
        # Now should need rotation
        assert manager.check_rotation_needed() is True

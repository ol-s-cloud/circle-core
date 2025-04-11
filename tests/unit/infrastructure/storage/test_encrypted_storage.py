"""Unit tests for encrypted storage wrapper."""

import os
import tempfile
from unittest import mock

import pytest

from circle_core.core.encryption import EncryptionService, EncryptionAlgorithm, KeyManager
from circle_core.infrastructure.storage import (
    FileSystemStorage,
    EncryptedStorageWrapper,
    StorageObject,
    StorageMetadata,
    StorageVisibility
)


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


@pytest.fixture
def encryption_service(temp_key_store):
    """Create an encryption service for testing."""
    key_store_path, master_key_path = temp_key_store
    key_manager = KeyManager(
        key_store_path=key_store_path,
        master_key_path=master_key_path
    )
    return EncryptionService(
        algorithm=EncryptionAlgorithm.AES_GCM,
        key_manager=key_manager
    )


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    
    # Clean up
    for root, dirs, files in os.walk(temp_dir, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(temp_dir)


@pytest.fixture
def base_storage(temp_storage_dir):
    """Create a file system storage backend."""
    return FileSystemStorage(
        base_path=temp_storage_dir,
        create_if_missing=True
    )


@pytest.fixture
def encrypted_storage(base_storage, encryption_service):
    """Create an encrypted storage wrapper."""
    return EncryptedStorageWrapper(
        backend=base_storage,
        encryption_service=encryption_service,
        encrypt_metadata=False,
        encrypted_suffix=".encrypted",
        algorithm=EncryptionAlgorithm.AES_GCM
    )


class TestEncryptedStorageWrapper:
    """Tests for EncryptedStorageWrapper."""
    
    def test_init(self, base_storage, encryption_service):
        """Test initializing encrypted storage."""
        storage = EncryptedStorageWrapper(
            backend=base_storage,
            encryption_service=encryption_service
        )
        
        assert storage.backend == base_storage
        assert storage.encryption_service == encryption_service
        assert storage.encrypted_suffix == ".encrypted"
        assert storage.algorithm == EncryptionAlgorithm.AES_GCM
    
    def test_put_get_object(self, encrypted_storage, base_storage):
        """Test putting and getting an encrypted object."""
        # Put an object
        metadata = encrypted_storage.put_object(
            key="test.txt",
            data="Hello, World!",
            content_type="text/plain",
            metadata={"key1": "value1", "key2": "value2"},
            visibility=StorageVisibility.PRIVATE
        )
        
        # Check metadata
        assert metadata.key == "test.txt"
        assert metadata.content_type == "text/plain"
        assert metadata.visibility == StorageVisibility.PRIVATE
        assert metadata.custom_metadata == {"key1": "value1", "key2": "value2"}
        
        # Original key should not exist in backend
        assert not base_storage.exists("test.txt")
        
        # Encrypted key should exist in backend
        assert base_storage.exists("test.txt.encrypted")
        
        # Get the object
        obj = encrypted_storage.get_object("test.txt")
        
        # Check object data (should be decrypted)
        assert obj.data == b"Hello, World!"
        assert obj.metadata.key == "test.txt"
        assert obj.metadata.content_type == "text/plain"
        
        # Test with non-existent object
        with pytest.raises(KeyError):
            encrypted_storage.get_object("non_existent.txt")
    
    def test_encrypt_metadata(self, base_storage, encryption_service):
        """Test encrypting metadata."""
        # Create storage with metadata encryption
        storage = EncryptedStorageWrapper(
            backend=base_storage,
            encryption_service=encryption_service,
            encrypt_metadata=True
        )
        
        # Put an object with metadata
        metadata = storage.put_object(
            key="test.txt",
            data="Content",
            metadata={"secret": "sensitive-data", "public": "public-data"}
        )
        
        # Get the encrypted metadata from backend
        encrypted_metadata = base_storage.get_object_metadata("test.txt.encrypted")
        
        # Metadata should be encrypted
        assert "encrypted" in encrypted_metadata.custom_metadata
        assert encrypted_metadata.custom_metadata.get("encrypted") == "true"
        assert "algorithm" in encrypted_metadata.custom_metadata
        assert "key_id" in encrypted_metadata.custom_metadata
        assert "data" in encrypted_metadata.custom_metadata
        
        # Get the object from encrypted storage
        obj = storage.get_object("test.txt")
        
        # Metadata should be decrypted
        assert obj.metadata.custom_metadata == {"secret": "sensitive-data", "public": "public-data"}
    
    def test_delete_object(self, encrypted_storage, base_storage):
        """Test deleting an encrypted object."""
        # Put an object
        encrypted_storage.put_object(key="test.txt", data="Content")
        
        # Encrypted key should exist in backend
        assert base_storage.exists("test.txt.encrypted")
        
        # Delete the object
        result = encrypted_storage.delete_object("test.txt")
        assert result is True
        
        # Encrypted key should be gone
        assert not base_storage.exists("test.txt.encrypted")
        
        # Test deleting non-existent object
        result = encrypted_storage.delete_object("non_existent.txt")
        assert result is False
    
    def test_list_objects(self, encrypted_storage):
        """Test listing encrypted objects."""
        # Put some objects
        encrypted_storage.put_object(key="file1.txt", data="Content 1")
        encrypted_storage.put_object(key="file2.txt", data="Content 2")
        encrypted_storage.put_object(key="dir/file3.txt", data="Content 3")
        
        # List all objects
        objects = encrypted_storage.list_objects()
        
        # Check keys (should be original, not encrypted)
        keys = {obj.key for obj in objects}
        assert "file1.txt" in keys
        assert "file2.txt" in keys
        assert "dir/file3.txt" in keys
        
        # List with prefix
        objects = encrypted_storage.list_objects(prefix="dir")
        keys = {obj.key for obj in objects}
        assert len(keys) == 1
        assert "dir/file3.txt" in keys
    
    def test_exists(self, encrypted_storage):
        """Test checking if an encrypted object exists."""
        # Put an object
        encrypted_storage.put_object(key="test.txt", data="Content")
        
        # Check it exists
        assert encrypted_storage.exists("test.txt")
        
        # Check non-existent object
        assert not encrypted_storage.exists("non_existent.txt")
    
    def test_copy_object(self, encrypted_storage, base_storage):
        """Test copying an encrypted object."""
        # Put an object
        encrypted_storage.put_object(key="source.txt", data="Source content")
        
        # Copy the object
        metadata = encrypted_storage.copy_object(
            source_key="source.txt",
            destination_key="dest.txt"
        )
        
        # Check the copy
        assert metadata.key == "dest.txt"
        
        # Both encrypted keys should exist in backend
        assert base_storage.exists("source.txt.encrypted")
        assert base_storage.exists("dest.txt.encrypted")
        
        # Get the copied object
        obj = encrypted_storage.get_object("dest.txt")
        assert obj.data == b"Source content"
    
    def test_move_object(self, encrypted_storage, base_storage):
        """Test moving an encrypted object."""
        # Put an object
        encrypted_storage.put_object(key="source.txt", data="Source content")
        
        # Move the object
        metadata = encrypted_storage.move_object(
            source_key="source.txt",
            destination_key="dest.txt"
        )
        
        # Check the moved object
        assert metadata.key == "dest.txt"
        
        # Source encrypted key should be gone
        assert not base_storage.exists("source.txt.encrypted")
        
        # Destination encrypted key should exist
        assert base_storage.exists("dest.txt.encrypted")
        
        # Get the moved object
        obj = encrypted_storage.get_object("dest.txt")
        assert obj.data == b"Source content"
    
    def test_get_signed_url(self, encrypted_storage):
        """Test generating a signed URL for encrypted storage."""
        # Put an object
        encrypted_storage.put_object(key="test.txt", data="Content")
        
        # Get a signed URL (should not be supported)
        url = encrypted_storage.get_signed_url(key="test.txt")
        assert url is None
    
    def test_stream_object(self, encrypted_storage):
        """Test streaming an encrypted object."""
        # Put a large object
        large_data = b"x" * 10000
        encrypted_storage.put_object(key="large.dat", data=large_data)
        
        # Stream the object
        chunks = list(encrypted_storage.stream_object(key="large.dat", chunk_size=1000))
        
        # Check all chunks
        assert len(chunks) == 10
        assert b"".join(chunks) == large_data
        
        # Test streaming non-existent object
        with pytest.raises(KeyError):
            list(encrypted_storage.stream_object("non_existent.txt"))
    
    def test_update_metadata(self, encrypted_storage):
        """Test updating metadata for an encrypted object."""
        # Put an object with metadata
        encrypted_storage.put_object(
            key="test.txt",
            data="Content",
            metadata={"key1": "value1", "key2": "value2"}
        )
        
        # Update metadata
        metadata = encrypted_storage.update_metadata(
            key="test.txt",
            metadata={"key2": "new_value", "key3": "value3"},
            merge=True
        )
        
        # Check updated metadata
        assert metadata.custom_metadata == {
            "key1": "value1",
            "key2": "new_value",
            "key3": "value3"
        }
        
        # Get the object
        obj = encrypted_storage.get_object("test.txt")
        
        # Check metadata
        assert obj.metadata.custom_metadata == {
            "key1": "value1",
            "key2": "new_value",
            "key3": "value3"
        }

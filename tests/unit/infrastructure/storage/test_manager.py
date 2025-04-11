"""Unit tests for storage manager."""

import os
import tempfile
from unittest import mock

import pytest

from circle_core.core.encryption import EncryptionService, KeyManager
from circle_core.infrastructure.storage import (
    StorageManager,
    FileSystemStorage,
    EncryptedStorageWrapper,
    StorageVisibility
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
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
def storage_manager(temp_dir):
    """Create a storage manager."""
    return StorageManager(
        default_backend=FileSystemStorage(os.path.join(temp_dir, "default")),
        enable_encryption=False
    )


class TestStorageManager:
    """Tests for StorageManager."""
    
    def test_init_default(self, temp_dir):
        """Test initializing with default backend."""
        # Create with default backend
        manager = StorageManager(
            default_backend=FileSystemStorage(os.path.join(temp_dir, "custom"))
        )
        
        # Should have a default backend
        assert "default" in manager.backends
        assert isinstance(manager.backends["default"], FileSystemStorage)
        
        # Create without default backend
        manager = StorageManager()
        
        # Should still have a default backend (auto-created)
        assert "default" in manager.backends
        assert isinstance(manager.backends["default"], FileSystemStorage)
    
    def test_register_backend(self, storage_manager, temp_dir):
        """Test registering backends."""
        # Create a backend
        backend = FileSystemStorage(os.path.join(temp_dir, "backend1"))
        
        # Register it
        storage_manager.register_backend("backend1", backend)
        
        # Should be registered
        assert "backend1" in storage_manager.backends
        assert storage_manager.backends["backend1"] == backend
        
        # Register with encryption wrapper
        storage_manager.encryption_service = mock.Mock()
        storage_manager.enable_encryption = True
        
        backend2 = FileSystemStorage(os.path.join(temp_dir, "backend2"))
        storage_manager.register_backend("backend2", backend2)
        
        # Should be wrapped with encryption
        assert "backend2" in storage_manager.backends
        assert isinstance(storage_manager.backends["backend2"], EncryptedStorageWrapper)
    
    def test_get_backend(self, storage_manager, temp_dir):
        """Test getting backends."""
        # Register some backends
        backend1 = FileSystemStorage(os.path.join(temp_dir, "backend1"))
        backend2 = FileSystemStorage(os.path.join(temp_dir, "backend2"))
        
        storage_manager.register_backend("backend1", backend1)
        storage_manager.register_backend("backend2", backend2)
        
        # Get backends
        assert storage_manager.get_backend("default") == storage_manager.backends["default"]
        assert storage_manager.get_backend("backend1") == backend1
        assert storage_manager.get_backend("backend2") == backend2
        
        # Test non-existent backend
        with pytest.raises(KeyError):
            storage_manager.get_backend("non_existent")
    
    def test_create_file_system_backend(self, storage_manager, temp_dir):
        """Test creating a file system backend."""
        # Create a backend
        backend = storage_manager.create_file_system_backend(
            name="fs1",
            base_path=os.path.join(temp_dir, "fs1"),
            encrypt=False
        )
        
        # Should be registered
        assert "fs1" in storage_manager.backends
        assert storage_manager.backends["fs1"] == backend
        assert isinstance(backend, FileSystemStorage)
        
        # Create with encryption
        storage_manager.encryption_service = mock.Mock()
        
        backend = storage_manager.create_file_system_backend(
            name="fs2",
            base_path=os.path.join(temp_dir, "fs2"),
            encrypt=True
        )
        
        # Should be wrapped with encryption
        assert "fs2" in storage_manager.backends
        assert storage_manager.backends["fs2"] == backend
        assert isinstance(backend, EncryptedStorageWrapper)
    
    def test_put_get_object(self, storage_manager):
        """Test putting and getting an object."""
        # Put an object
        metadata = storage_manager.put_object(
            key="test.txt",
            data="Hello, World!",
            content_type="text/plain",
            metadata={"key1": "value1"}
        )
        
        # Check metadata
        assert metadata.key == "test.txt"
        assert metadata.content_type == "text/plain"
        
        # Get the object
        obj = storage_manager.get_object("test.txt")
        
        # Check data
        assert obj.data == b"Hello, World!"
        assert obj.metadata.key == "test.txt"
        
        # Test with another backend
        storage_manager.create_file_system_backend(
            name="another",
            base_path=tempfile.mkdtemp()
        )
        
        # Put in another backend
        storage_manager.put_object(
            key="another.txt",
            data="Another backend",
            backend="another"
        )
        
        # Should exist in the other backend
        obj = storage_manager.get_object("another.txt", backend="another")
        assert obj.data == b"Another backend"
        
        # But not in the default backend
        with pytest.raises(KeyError):
            storage_manager.get_object("another.txt")
    
    def test_object_metadata(self, storage_manager):
        """Test getting object metadata."""
        # Put an object
        storage_manager.put_object(
            key="test.txt",
            data="Content",
            metadata={"key1": "value1"}
        )
        
        # Get metadata
        metadata = storage_manager.get_object_metadata("test.txt")
        
        # Check metadata
        assert metadata.key == "test.txt"
        assert metadata.custom_metadata == {"key1": "value1"}
        
        # Test with non-existent object
        with pytest.raises(KeyError):
            storage_manager.get_object_metadata("non_existent.txt")
    
    def test_delete_object(self, storage_manager):
        """Test deleting an object."""
        # Put an object
        storage_manager.put_object(key="test.txt", data="Content")
        
        # Delete it
        result = storage_manager.delete_object("test.txt")
        assert result is True
        
        # Should be gone
        with pytest.raises(KeyError):
            storage_manager.get_object("test.txt")
    
    def test_list_objects(self, storage_manager):
        """Test listing objects."""
        # Put some objects
        storage_manager.put_object(key="file1.txt", data="Content 1")
        storage_manager.put_object(key="file2.txt", data="Content 2")
        storage_manager.put_object(key="dir/file3.txt", data="Content 3")
        
        # List all objects
        objects = storage_manager.list_objects()
        assert len(objects) == 3
        
        # List with prefix
        objects = storage_manager.list_objects(prefix="dir")
        assert len(objects) == 1
        assert objects[0].key == "dir/file3.txt"
    
    def test_exists(self, storage_manager):
        """Test checking if an object exists."""
        # Put an object
        storage_manager.put_object(key="test.txt", data="Content")
        
        # Check it exists
        assert storage_manager.exists("test.txt") is True
        
        # Check non-existent object
        assert storage_manager.exists("non_existent.txt") is False
    
    def test_copy_object_same_backend(self, storage_manager):
        """Test copying an object within the same backend."""
        # Put an object
        storage_manager.put_object(
            key="source.txt",
            data="Source content",
            metadata={"key1": "value1"}
        )
        
        # Copy the object
        metadata = storage_manager.copy_object(
            source_key="source.txt",
            destination_key="dest.txt",
            metadata={"key2": "value2"}
        )
        
        # Check metadata
        assert metadata.key == "dest.txt"
        assert "key2" in metadata.custom_metadata
        
        # Get the copied object
        obj = storage_manager.get_object("dest.txt")
        assert obj.data == b"Source content"
        
        # Original should still exist
        obj = storage_manager.get_object("source.txt")
        assert obj.data == b"Source content"
    
    def test_copy_object_different_backends(self, storage_manager, temp_dir):
        """Test copying an object between different backends."""
        # Create another backend
        storage_manager.create_file_system_backend(
            name="another",
            base_path=os.path.join(temp_dir, "another")
        )
        
        # Put an object in the default backend
        storage_manager.put_object(
            key="source.txt",
            data="Source content",
            metadata={"key1": "value1"}
        )
        
        # Copy to the other backend
        metadata = storage_manager.copy_object(
            source_key="source.txt",
            destination_key="dest.txt",
            metadata={"key2": "value2"},
            source_backend="default",
            destination_backend="another"
        )
        
        # Check metadata
        assert metadata.key == "dest.txt"
        assert "key2" in metadata.custom_metadata
        
        # Get the copied object from the other backend
        obj = storage_manager.get_object("dest.txt", backend="another")
        assert obj.data == b"Source content"
        
        # Original should still exist in default backend
        obj = storage_manager.get_object("source.txt")
        assert obj.data == b"Source content"
        
        # But copied object should not exist in default backend
        with pytest.raises(KeyError):
            storage_manager.get_object("dest.txt")
    
    def test_move_object(self, storage_manager):
        """Test moving an object."""
        # Put an object
        storage_manager.put_object(key="source.txt", data="Source content")
        
        # Move the object
        metadata = storage_manager.move_object(
            source_key="source.txt",
            destination_key="dest.txt"
        )
        
        # Check metadata
        assert metadata.key == "dest.txt"
        
        # Get the moved object
        obj = storage_manager.get_object("dest.txt")
        assert obj.data == b"Source content"
        
        # Original should be gone
        with pytest.raises(KeyError):
            storage_manager.get_object("source.txt")
    
    def test_get_signed_url(self, storage_manager):
        """Test getting a signed URL."""
        # Mock the backend's get_signed_url method
        backend = storage_manager.get_backend("default")
        original_method = backend.get_signed_url
        backend.get_signed_url = mock.Mock(return_value="https://example.com/signed")
        
        try:
            # Put an object
            storage_manager.put_object(key="test.txt", data="Content")
            
            # Get signed URL
            url = storage_manager.get_signed_url(
                key="test.txt",
                expires_in=3600,
                method="GET"
            )
            
            # Check URL
            assert url == "https://example.com/signed"
            
            # Check method was called with correct parameters
            backend.get_signed_url.assert_called_once_with(
                key="test.txt",
                expires_in=3600,
                method="GET"
            )
        finally:
            # Restore original method
            backend.get_signed_url = original_method
    
    def test_stream_object(self, storage_manager):
        """Test streaming an object."""
        # Put a large object
        large_data = b"x" * 10000
        storage_manager.put_object(key="large.dat", data=large_data)
        
        # Stream the object
        chunks = list(storage_manager.stream_object(key="large.dat", chunk_size=1000))
        
        # Check all chunks
        assert len(chunks) == 10
        assert b"".join(chunks) == large_data
    
    def test_update_metadata(self, storage_manager):
        """Test updating object metadata."""
        # Put an object with metadata
        storage_manager.put_object(
            key="test.txt",
            data="Content",
            metadata={"key1": "value1", "key2": "value2"}
        )
        
        # Update metadata
        metadata = storage_manager.update_metadata(
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
        
        # Get the object metadata
        obj_metadata = storage_manager.get_object_metadata("test.txt")
        
        # Check metadata was actually updated
        assert obj_metadata.custom_metadata == {
            "key1": "value1",
            "key2": "new_value",
            "key3": "value3"
        }

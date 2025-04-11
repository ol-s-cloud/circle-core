"""Unit tests for file system storage backend."""

import datetime
import os
import tempfile
from unittest import mock
import pytest

from circle_core.infrastructure.storage import (
    FileSystemStorage,
    StorageObject,
    StorageMetadata,
    StorageVisibility
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
def storage(temp_storage_dir):
    """Create a file system storage backend."""
    return FileSystemStorage(
        base_path=temp_storage_dir,
        create_if_missing=True
    )


class TestFileSystemStorage:
    """Tests for FileSystemStorage."""
    
    def test_init(self, temp_storage_dir):
        """Test initializing storage."""
        # Test with existing directory
        storage = FileSystemStorage(temp_storage_dir)
        assert storage.base_path == os.path.abspath(temp_storage_dir)
        
        # Test with non-existent directory (create_if_missing=True)
        non_existent = os.path.join(temp_storage_dir, "non_existent")
        storage = FileSystemStorage(non_existent, create_if_missing=True)
        assert os.path.exists(non_existent)
        
        # Test with non-existent directory (create_if_missing=False)
        non_existent2 = os.path.join(temp_storage_dir, "non_existent2")
        with pytest.raises(ValueError):
            FileSystemStorage(non_existent2, create_if_missing=False)
    
    def test_put_get_object(self, storage):
        """Test putting and getting an object."""
        # Put an object (string)
        metadata = storage.put_object(
            key="test.txt",
            data="Hello, World!",
            content_type="text/plain",
            metadata={"key1": "value1", "key2": "value2"},
            visibility=StorageVisibility.PRIVATE
        )
        
        # Check metadata
        assert metadata.key == "test.txt"
        assert metadata.size == len("Hello, World!")
        assert metadata.content_type == "text/plain"
        assert metadata.visibility == StorageVisibility.PRIVATE
        assert metadata.custom_metadata == {"key1": "value1", "key2": "value2"}
        
        # Get the object
        obj = storage.get_object("test.txt")
        
        # Check object data
        assert obj.data == b"Hello, World!"
        assert obj.metadata.key == "test.txt"
        assert obj.metadata.content_type == "text/plain"
        
        # Put an object (bytes)
        storage.put_object(
            key="binary.dat",
            data=b"\x00\x01\x02\x03",
            content_type="application/octet-stream"
        )
        
        # Get the object
        obj = storage.get_object("binary.dat")
        assert obj.data == b"\x00\x01\x02\x03"
        
        # Put an object (file-like)
        from io import BytesIO
        file_obj = BytesIO(b"File content")
        storage.put_object(
            key="file.txt",
            data=file_obj
        )
        
        # Get the object
        obj = storage.get_object("file.txt")
        assert obj.data == b"File content"
    
    def test_get_object_metadata(self, storage):
        """Test getting object metadata."""
        # Put an object
        storage.put_object(
            key="test.txt",
            data="Hello, World!",
            content_type="text/plain",
            metadata={"key1": "value1"}
        )
        
        # Get metadata
        metadata = storage.get_object_metadata("test.txt")
        
        # Check metadata
        assert metadata.key == "test.txt"
        assert metadata.size == len("Hello, World!")
        assert metadata.content_type == "text/plain"
        assert metadata.custom_metadata == {"key1": "value1"}
        
        # Test non-existent object
        with pytest.raises(KeyError):
            storage.get_object_metadata("non_existent.txt")
    
    def test_delete_object(self, storage):
        """Test deleting an object."""
        # Put an object
        storage.put_object(
            key="test.txt",
            data="Hello, World!"
        )
        
        # Check it exists
        assert storage.exists("test.txt")
        
        # Delete it
        result = storage.delete_object("test.txt")
        assert result is True
        
        # Check it's gone
        assert not storage.exists("test.txt")
        
        # Delete non-existent object
        result = storage.delete_object("non_existent.txt")
        assert result is False
    
    def test_list_objects(self, storage):
        """Test listing objects."""
        # Put some objects
        storage.put_object(key="file1.txt", data="Content 1")
        storage.put_object(key="file2.txt", data="Content 2")
        storage.put_object(key="dir/file3.txt", data="Content 3")
        storage.put_object(key="dir/subdir/file4.txt", data="Content 4")
        
        # List all objects
        objects = storage.list_objects()
        assert len(objects) == 4
        
        # Check keys
        keys = {obj.key for obj in objects}
        assert keys == {"file1.txt", "file2.txt", "dir/file3.txt", "dir/subdir/file4.txt"}
        
        # List with prefix
        objects = storage.list_objects(prefix="dir")
        assert len(objects) == 2
        keys = {obj.key for obj in objects}
        assert keys == {"dir/file3.txt", "dir/subdir/file4.txt"}
        
        # List with max results
        objects = storage.list_objects(max_results=2)
        assert len(objects) <= 2
    
    def test_exists(self, storage):
        """Test checking if an object exists."""
        # Put an object
        storage.put_object(key="test.txt", data="Content")
        
        # Check it exists
        assert storage.exists("test.txt")
        
        # Check non-existent object
        assert not storage.exists("non_existent.txt")
    
    def test_copy_object(self, storage):
        """Test copying an object."""
        # Put an object
        storage.put_object(
            key="source.txt",
            data="Source content",
            metadata={"key1": "value1"},
            visibility=StorageVisibility.PRIVATE
        )
        
        # Copy the object
        metadata = storage.copy_object(
            source_key="source.txt",
            destination_key="dest.txt",
            metadata={"key2": "value2"},
            visibility=StorageVisibility.PUBLIC
        )
        
        # Check the copy
        assert metadata.key == "dest.txt"
        assert metadata.visibility == StorageVisibility.PUBLIC
        assert "key2" in metadata.custom_metadata
        
        # Get the copied object
        obj = storage.get_object("dest.txt")
        assert obj.data == b"Source content"
        
        # Original should still exist
        assert storage.exists("source.txt")
        
        # Test copying non-existent object
        with pytest.raises(KeyError):
            storage.copy_object("non_existent.txt", "dest2.txt")
    
    def test_move_object(self, storage):
        """Test moving an object."""
        # Put an object
        storage.put_object(key="source.txt", data="Source content")
        
        # Move the object
        metadata = storage.move_object(
            source_key="source.txt",
            destination_key="dest.txt"
        )
        
        # Check the moved object
        assert metadata.key == "dest.txt"
        assert storage.exists("dest.txt")
        
        # Original should be gone
        assert not storage.exists("source.txt")
        
        # Test moving non-existent object
        with pytest.raises(KeyError):
            storage.move_object("non_existent.txt", "dest2.txt")
    
    def test_get_signed_url(self, storage):
        """Test generating a signed URL."""
        # Put an object
        storage.put_object(key="test.txt", data="Content")
        
        # Get a signed URL
        url = storage.get_signed_url(key="test.txt")
        
        # For file system storage, we get a file:// URL
        assert url.startswith("file://")
        
        # Test with non-existent object
        url = storage.get_signed_url(key="non_existent.txt")
        assert url is None
    
    def test_stream_object(self, storage):
        """Test streaming an object."""
        # Put a large object
        large_data = b"x" * 10000
        storage.put_object(key="large.dat", data=large_data)
        
        # Stream the object
        chunks = list(storage.stream_object(key="large.dat", chunk_size=1000))
        
        # Check all chunks
        assert len(chunks) == 10
        assert b"".join(chunks) == large_data
        
        # Test streaming non-existent object
        with pytest.raises(KeyError):
            list(storage.stream_object("non_existent.txt"))
    
    def test_update_metadata(self, storage):
        """Test updating object metadata."""
        # Put an object with metadata
        storage.put_object(
            key="test.txt",
            data="Content",
            metadata={"key1": "value1", "key2": "value2"}
        )
        
        # Update metadata (merge)
        metadata = storage.update_metadata(
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
        
        # Update metadata (replace)
        metadata = storage.update_metadata(
            key="test.txt",
            metadata={"key4": "value4"},
            merge=False
        )
        
        # Check updated metadata
        assert metadata.custom_metadata == {"key4": "value4"}
        
        # Test updating non-existent object
        with pytest.raises(KeyError):
            storage.update_metadata("non_existent.txt", {})
    
    def test_path_traversal_prevention(self, storage):
        """Test prevention of path traversal attacks."""
        # Attempt path traversal
        with pytest.raises(ValueError):
            storage.put_object(key="../traversal.txt", data="Evil content")
        
        with pytest.raises(ValueError):
            storage.put_object(key="../../etc/passwd", data="Evil content")

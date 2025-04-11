"""Storage interface definitions.

Provides the abstract base classes and data structures for the storage system.
"""

import abc
import datetime
import io
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union, BinaryIO, Tuple, Iterator


class StorageVisibility(Enum):
    """Enum representing storage object visibility."""
    
    PRIVATE = "private"  # Only accessible with proper authentication
    PUBLIC = "public"    # Publicly accessible (e.g., with URL)
    SHARED = "shared"    # Shared with specific users/groups


@dataclass
class StorageMetadata:
    """Metadata for a storage object."""
    
    key: str  # Object path/key in the storage
    size: int  # Size in bytes
    last_modified: datetime.datetime  # Last modified timestamp
    etag: Optional[str] = None  # Entity tag for change detection
    content_type: Optional[str] = None  # MIME type
    visibility: StorageVisibility = StorageVisibility.PRIVATE
    checksum: Optional[str] = None  # Checksum (e.g., MD5, SHA-256)
    custom_metadata: Dict[str, str] = field(default_factory=dict)  # Custom user metadata


@dataclass
class StorageObject:
    """A storage object containing data and metadata."""
    
    data: Union[bytes, BinaryIO]  # Object data or file-like object
    metadata: StorageMetadata  # Object metadata


class StorageBackend(abc.ABC):
    """Abstract base class for storage backends.
    
    This defines the interface that all storage backends must implement.
    """
    
    @abc.abstractmethod
    def put_object(
        self, 
        key: str, 
        data: Union[bytes, BinaryIO, str],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        visibility: StorageVisibility = StorageVisibility.PRIVATE
    ) -> StorageMetadata:
        """Store an object.
        
        Args:
            key: Object key/path
            data: Object data (bytes, file-like object, or string)
            content_type: Optional MIME type
            metadata: Optional custom metadata
            visibility: Object visibility/permissions
            
        Returns:
            Object metadata
        """
        pass
    
    @abc.abstractmethod
    def get_object(self, key: str) -> StorageObject:
        """Retrieve an object.
        
        Args:
            key: Object key/path
            
        Returns:
            Storage object (data + metadata)
            
        Raises:
            KeyError: If the object does not exist
        """
        pass
    
    @abc.abstractmethod
    def get_object_metadata(self, key: str) -> StorageMetadata:
        """Get object metadata without retrieving the object data.
        
        Args:
            key: Object key/path
            
        Returns:
            Object metadata
            
        Raises:
            KeyError: If the object does not exist
        """
        pass
    
    @abc.abstractmethod
    def delete_object(self, key: str) -> bool:
        """Delete an object.
        
        Args:
            key: Object key/path
            
        Returns:
            True if object was deleted, False if it didn't exist
        """
        pass
    
    @abc.abstractmethod
    def list_objects(
        self, 
        prefix: Optional[str] = None,
        max_results: Optional[int] = None
    ) -> List[StorageMetadata]:
        """List objects in the storage.
        
        Args:
            prefix: Optional key prefix to filter objects
            max_results: Maximum number of results to return
            
        Returns:
            List of object metadata
        """
        pass
    
    @abc.abstractmethod
    def exists(self, key: str) -> bool:
        """Check if an object exists.
        
        Args:
            key: Object key/path
            
        Returns:
            True if the object exists, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def copy_object(
        self, 
        source_key: str, 
        destination_key: str,
        metadata: Optional[Dict[str, str]] = None,
        visibility: Optional[StorageVisibility] = None
    ) -> StorageMetadata:
        """Copy an object within the same storage.
        
        Args:
            source_key: Source object key
            destination_key: Destination object key
            metadata: Optional new metadata (None to keep original)
            visibility: Optional new visibility (None to keep original)
            
        Returns:
            Metadata of the copied object
            
        Raises:
            KeyError: If source object doesn't exist
        """
        pass
    
    @abc.abstractmethod
    def move_object(
        self,
        source_key: str,
        destination_key: str
    ) -> StorageMetadata:
        """Move/rename an object.
        
        Args:
            source_key: Source object key
            destination_key: Destination object key
            
        Returns:
            Metadata of the moved object
            
        Raises:
            KeyError: If source object doesn't exist
        """
        pass
    
    @abc.abstractmethod
    def get_signed_url(
        self,
        key: str,
        expires_in: int = 3600,
        method: str = "GET"
    ) -> Optional[str]:
        """Generate a signed URL for temporary access.
        
        Args:
            key: Object key
            expires_in: Expiration time in seconds (default: 1 hour)
            method: HTTP method to allow ("GET", "PUT", etc.)
            
        Returns:
            Signed URL string or None if not supported
        """
        pass
    
    @abc.abstractmethod
    def stream_object(self, key: str, chunk_size: int = 8192) -> Iterator[bytes]:
        """Stream an object in chunks.
        
        Args:
            key: Object key
            chunk_size: Size of chunks in bytes
            
        Yields:
            Object data in chunks
            
        Raises:
            KeyError: If the object doesn't exist
        """
        pass
    
    @abc.abstractmethod
    def update_metadata(
        self,
        key: str,
        metadata: Dict[str, str],
        merge: bool = True
    ) -> StorageMetadata:
        """Update object metadata.
        
        Args:
            key: Object key
            metadata: New metadata
            merge: If True, merge with existing metadata; if False, replace
            
        Returns:
            Updated metadata
            
        Raises:
            KeyError: If the object doesn't exist
        """
        pass

"""Storage manager.

Provides a unified interface for storage operations across multiple backends.
"""

import os
from enum import Enum
from typing import Any, Dict, List, Optional, Union, BinaryIO, Iterator

from ...core.encryption import EncryptionService
from .interface import StorageBackend, StorageMetadata, StorageObject, StorageVisibility
from .file_storage import FileSystemStorage
from .encryption import EncryptedStorageWrapper


class BackendType(Enum):
    """Enum representing storage backend types."""
    
    FILE_SYSTEM = "file_system"
    OBJECT_STORAGE = "object_storage"
    DATABASE = "database"
    MEMORY = "memory"
    CUSTOM = "custom"


class StorageManager:
    """Manager for storage operations across multiple backends.
    
    This class provides a unified interface for storage operations
    and manages multiple storage backends.
    """
    
    def __init__(
        self,
        default_backend: Optional[StorageBackend] = None,
        encryption_service: Optional[EncryptionService] = None,
        enable_encryption: bool = False
    ):
        """Initialize the storage manager.
        
        Args:
            default_backend: Default storage backend
            encryption_service: Optional encryption service
            enable_encryption: Whether to enable encryption by default
        """
        self.backends: Dict[str, StorageBackend] = {}
        self.encryption_service = encryption_service
        self.enable_encryption = enable_encryption
        
        # Set the default backend
        if default_backend:
            self.set_default_backend(default_backend)
        else:
            # Create a default file system backend
            default_path = os.path.expanduser("~/.circle-core/storage")
            os.makedirs(default_path, exist_ok=True)
            self.set_default_backend(FileSystemStorage(default_path))
    
    def register_backend(
        self,
        name: str,
        backend: StorageBackend,
        encrypt: Optional[bool] = None
    ) -> None:
        """Register a storage backend.
        
        Args:
            name: Backend name
            backend: Storage backend instance
            encrypt: Whether to encrypt this backend (None = use default)
        """
        # Determine whether to encrypt
        should_encrypt = self.enable_encryption if encrypt is None else encrypt
        
        # Wrap with encryption if needed
        if should_encrypt and self.encryption_service:
            backend = EncryptedStorageWrapper(
                backend=backend,
                encryption_service=self.encryption_service
            )
        
        # Register the backend
        self.backends[name] = backend
    
    def set_default_backend(self, backend: StorageBackend) -> None:
        """Set the default storage backend.
        
        Args:
            backend: Storage backend instance
        """
        self.register_backend("default", backend)
    
    def get_backend(self, name: str = "default") -> StorageBackend:
        """Get a storage backend.
        
        Args:
            name: Backend name
            
        Returns:
            Storage backend
            
        Raises:
            KeyError: If the backend doesn't exist
        """
        if name not in self.backends:
            raise KeyError(f"Storage backend not found: {name}")
        
        return self.backends[name]
    
    def create_file_system_backend(
        self,
        name: str,
        base_path: str,
        encrypt: Optional[bool] = None
    ) -> StorageBackend:
        """Create and register a file system backend.
        
        Args:
            name: Backend name
            base_path: Base directory path
            encrypt: Whether to encrypt this backend
            
        Returns:
            The created backend
        """
        backend = FileSystemStorage(base_path)
        self.register_backend(name, backend, encrypt)
        return self.get_backend(name)
    
    def put_object(
        self, 
        key: str, 
        data: Union[bytes, BinaryIO, str],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        visibility: StorageVisibility = StorageVisibility.PRIVATE,
        backend: str = "default"
    ) -> StorageMetadata:
        """Store an object.
        
        Args:
            key: Object key
            data: Object data
            content_type: Optional MIME type
            metadata: Optional custom metadata
            visibility: Object visibility
            backend: Backend name
            
        Returns:
            Object metadata
        """
        return self.get_backend(backend).put_object(
            key=key,
            data=data,
            content_type=content_type,
            metadata=metadata,
            visibility=visibility
        )
    
    def get_object(
        self,
        key: str,
        backend: str = "default"
    ) -> StorageObject:
        """Retrieve an object.
        
        Args:
            key: Object key
            backend: Backend name
            
        Returns:
            Storage object
            
        Raises:
            KeyError: If the object doesn't exist
        """
        return self.get_backend(backend).get_object(key)
    
    def get_object_metadata(
        self,
        key: str,
        backend: str = "default"
    ) -> StorageMetadata:
        """Get object metadata.
        
        Args:
            key: Object key
            backend: Backend name
            
        Returns:
            Object metadata
            
        Raises:
            KeyError: If the object doesn't exist
        """
        return self.get_backend(backend).get_object_metadata(key)
    
    def delete_object(
        self,
        key: str,
        backend: str = "default"
    ) -> bool:
        """Delete an object.
        
        Args:
            key: Object key
            backend: Backend name
            
        Returns:
            True if object was deleted, False if it didn't exist
        """
        return self.get_backend(backend).delete_object(key)
    
    def list_objects(
        self, 
        prefix: Optional[str] = None,
        max_results: Optional[int] = None,
        backend: str = "default"
    ) -> List[StorageMetadata]:
        """List objects.
        
        Args:
            prefix: Optional key prefix to filter objects
            max_results: Maximum number of results to return
            backend: Backend name
            
        Returns:
            List of object metadata
        """
        return self.get_backend(backend).list_objects(
            prefix=prefix,
            max_results=max_results
        )
    
    def exists(
        self,
        key: str,
        backend: str = "default"
    ) -> bool:
        """Check if an object exists.
        
        Args:
            key: Object key
            backend: Backend name
            
        Returns:
            True if the object exists, False otherwise
        """
        return self.get_backend(backend).exists(key)
    
    def copy_object(
        self, 
        source_key: str, 
        destination_key: str,
        metadata: Optional[Dict[str, str]] = None,
        visibility: Optional[StorageVisibility] = None,
        source_backend: str = "default",
        destination_backend: str = "default"
    ) -> StorageMetadata:
        """Copy an object.
        
        Args:
            source_key: Source object key
            destination_key: Destination object key
            metadata: Optional new metadata
            visibility: Optional new visibility
            source_backend: Source backend name
            destination_backend: Destination backend name
            
        Returns:
            Metadata of the copied object
        """
        # If same backend, use its copy method
        if source_backend == destination_backend:
            return self.get_backend(source_backend).copy_object(
                source_key=source_key,
                destination_key=destination_key,
                metadata=metadata,
                visibility=visibility
            )
        
        # Otherwise, get from source and put to destination
        source_obj = self.get_object(source_key, source_backend)
        
        return self.put_object(
            key=destination_key,
            data=source_obj.data,
            content_type=source_obj.metadata.content_type,
            metadata=metadata or source_obj.metadata.custom_metadata,
            visibility=visibility or source_obj.metadata.visibility,
            backend=destination_backend
        )
    
    def move_object(
        self,
        source_key: str,
        destination_key: str,
        source_backend: str = "default",
        destination_backend: str = "default"
    ) -> StorageMetadata:
        """Move/rename an object.
        
        Args:
            source_key: Source object key
            destination_key: Destination object key
            source_backend: Source backend name
            destination_backend: Destination backend name
            
        Returns:
            Metadata of the moved object
        """
        # If same backend, use its move method
        if source_backend == destination_backend:
            return self.get_backend(source_backend).move_object(
                source_key=source_key,
                destination_key=destination_key
            )
        
        # Otherwise, copy and delete
        metadata = self.copy_object(
            source_key=source_key,
            destination_key=destination_key,
            source_backend=source_backend,
            destination_backend=destination_backend
        )
        
        self.delete_object(source_key, source_backend)
        
        return metadata
    
    def get_signed_url(
        self,
        key: str,
        expires_in: int = 3600,
        method: str = "GET",
        backend: str = "default"
    ) -> Optional[str]:
        """Generate a signed URL for temporary access.
        
        Args:
            key: Object key
            expires_in: Expiration time in seconds
            method: HTTP method to allow
            backend: Backend name
            
        Returns:
            Signed URL string or None if not supported
        """
        return self.get_backend(backend).get_signed_url(
            key=key,
            expires_in=expires_in,
            method=method
        )
    
    def stream_object(
        self,
        key: str,
        chunk_size: int = 8192,
        backend: str = "default"
    ) -> Iterator[bytes]:
        """Stream an object in chunks.
        
        Args:
            key: Object key
            chunk_size: Size of chunks in bytes
            backend: Backend name
            
        Yields:
            Object data in chunks
        """
        return self.get_backend(backend).stream_object(
            key=key,
            chunk_size=chunk_size
        )
    
    def update_metadata(
        self,
        key: str,
        metadata: Dict[str, str],
        merge: bool = True,
        backend: str = "default"
    ) -> StorageMetadata:
        """Update object metadata.
        
        Args:
            key: Object key
            metadata: New metadata
            merge: Whether to merge with existing metadata
            backend: Backend name
            
        Returns:
            Updated metadata
        """
        return self.get_backend(backend).update_metadata(
            key=key,
            metadata=metadata,
            merge=merge
        )

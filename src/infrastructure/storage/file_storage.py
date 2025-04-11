"""File system storage backend.

Provides storage backend implementation using the local file system.
"""

import datetime
import hashlib
import io
import json
import mimetypes
import os
import shutil
import stat
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, BinaryIO, Iterator

from .interface import StorageBackend, StorageMetadata, StorageObject, StorageVisibility


class FileSystemStorage(StorageBackend):
    """File system storage backend.
    
    Stores objects in the local file system with metadata stored in a parallel structure.
    """
    
    def __init__(
        self,
        base_path: str,
        create_if_missing: bool = True,
        metadata_suffix: str = ".metadata.json",
        default_permissions: int = 0o600,  # Default: user read-write only
        public_permissions: int = 0o644,   # Public: user read-write, others read-only
    ):
        """Initialize the file system storage.
        
        Args:
            base_path: Base directory path for storage
            create_if_missing: Create base directory if it doesn't exist
            metadata_suffix: Suffix for metadata files
            default_permissions: Default file permissions (octal)
            public_permissions: Permissions for public files (octal)
        """
        self.base_path = os.path.abspath(base_path)
        self.metadata_suffix = metadata_suffix
        self.default_permissions = default_permissions
        self.public_permissions = public_permissions
        
        # Create base directory if it doesn't exist
        if create_if_missing and not os.path.exists(self.base_path):
            os.makedirs(self.base_path, exist_ok=True)
        elif not os.path.isdir(self.base_path):
            raise ValueError(f"Base path {base_path} is not a directory")
    
    def _get_file_path(self, key: str) -> str:
        """Get the file path for an object key.
        
        Args:
            key: Object key
            
        Returns:
            Absolute file path
        """
        # Normalize the key (replace backslashes, remove leading/trailing slashes)
        key = key.replace('\\', '/').strip('/')
        
        # Join with base path
        path = os.path.join(self.base_path, key)
        
        # Ensure the path is within the base directory (security)
        if not os.path.abspath(path).startswith(self.base_path):
            raise ValueError(f"Invalid key: {key} (path traversal attempt)")
        
        return path
    
    def _get_metadata_path(self, key: str) -> str:
        """Get the metadata file path for an object key.
        
        Args:
            key: Object key
            
        Returns:
            Metadata file path
        """
        return self._get_file_path(key) + self.metadata_suffix
    
    def _ensure_directory_exists(self, file_path: str) -> None:
        """Ensure the directory for a file path exists.
        
        Args:
            file_path: File path
        """
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
    
    def _calculate_checksum(self, data: Union[bytes, BinaryIO]) -> str:
        """Calculate SHA-256 checksum for data.
        
        Args:
            data: Data to hash
            
        Returns:
            Hex-encoded SHA-256 hash
        """
        sha256 = hashlib.sha256()
        
        if isinstance(data, bytes):
            sha256.update(data)
        else:
            # Save the current position
            current_pos = data.tell()
            
            # Reset to beginning
            data.seek(0)
            
            # Read and hash in chunks
            chunk = data.read(8192)
            while chunk:
                sha256.update(chunk)
                chunk = data.read(8192)
            
            # Restore position
            data.seek(current_pos)
        
        return sha256.hexdigest()
    
    def _save_metadata(self, metadata: StorageMetadata) -> None:
        """Save metadata to a file.
        
        Args:
            metadata: Object metadata
        """
        metadata_path = self._get_metadata_path(metadata.key)
        self._ensure_directory_exists(metadata_path)
        
        # Convert to dictionary for serialization
        meta_dict = {
            "key": metadata.key,
            "size": metadata.size,
            "last_modified": metadata.last_modified.isoformat(),
            "etag": metadata.etag,
            "content_type": metadata.content_type,
            "visibility": metadata.visibility.value,
            "checksum": metadata.checksum,
            "custom_metadata": metadata.custom_metadata,
        }
        
        # Write to file
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(meta_dict, f, indent=2)
        
        # Set permissions
        os.chmod(metadata_path, self.default_permissions)
    
    def _load_metadata(self, key: str) -> StorageMetadata:
        """Load metadata from a file.
        
        Args:
            key: Object key
            
        Returns:
            Object metadata
            
        Raises:
            KeyError: If metadata file doesn't exist
        """
        metadata_path = self._get_metadata_path(key)
        if not os.path.exists(metadata_path):
            raise KeyError(f"Object metadata not found: {key}")
        
        # Read metadata file
        with open(metadata_path, 'r', encoding='utf-8') as f:
            meta_dict = json.load(f)
        
        # Convert to StorageMetadata
        return StorageMetadata(
            key=meta_dict["key"],
            size=meta_dict["size"],
            last_modified=datetime.datetime.fromisoformat(meta_dict["last_modified"]),
            etag=meta_dict.get("etag"),
            content_type=meta_dict.get("content_type"),
            visibility=StorageVisibility(meta_dict.get("visibility", StorageVisibility.PRIVATE.value)),
            checksum=meta_dict.get("checksum"),
            custom_metadata=meta_dict.get("custom_metadata", {})
        )
    
    def _set_file_permissions(self, file_path: str, visibility: StorageVisibility) -> None:
        """Set file permissions based on visibility.
        
        Args:
            file_path: File path
            visibility: Object visibility
        """
        if visibility == StorageVisibility.PUBLIC:
            os.chmod(file_path, self.public_permissions)
        else:
            os.chmod(file_path, self.default_permissions)
    
    def put_object(
        self, 
        key: str, 
        data: Union[bytes, BinaryIO, str],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        visibility: StorageVisibility = StorageVisibility.PRIVATE
    ) -> StorageMetadata:
        """Store an object in the file system.
        
        Args:
            key: Object key
            data: Object data
            content_type: Optional MIME type
            metadata: Optional custom metadata
            visibility: Object visibility
            
        Returns:
            Object metadata
        """
        file_path = self._get_file_path(key)
        self._ensure_directory_exists(file_path)
        
        # Handle different data types
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
            write_mode = 'wb'
        elif isinstance(data, bytes):
            data_bytes = data
            write_mode = 'wb'
        else:  # File-like object
            data_bytes = None
            write_mode = 'wb'
        
        # Write the data
        if data_bytes:
            with open(file_path, write_mode) as f:
                f.write(data_bytes)
            size = len(data_bytes)
            checksum = self._calculate_checksum(data_bytes)
        else:
            # Save the current position
            current_pos = data.tell()
            
            # Reset to beginning
            data.seek(0)
            
            # Calculate size
            data.seek(0, os.SEEK_END)
            size = data.tell()
            data.seek(0)
            
            # Write data
            with open(file_path, write_mode) as f:
                shutil.copyfileobj(data, f)
            
            # Calculate checksum
            checksum = self._calculate_checksum(data)
            
            # Restore position
            data.seek(current_pos)
        
        # Set permissions
        self._set_file_permissions(file_path, visibility)
        
        # Determine content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(key)
        
        # Create metadata
        storage_metadata = StorageMetadata(
            key=key,
            size=size,
            last_modified=datetime.datetime.now(),
            content_type=content_type,
            visibility=visibility,
            checksum=checksum,
            custom_metadata=metadata or {}
        )
        
        # Save metadata
        self._save_metadata(storage_metadata)
        
        return storage_metadata
    
    def get_object(self, key: str) -> StorageObject:
        """Retrieve an object from the file system.
        
        Args:
            key: Object key
            
        Returns:
            Storage object (data + metadata)
            
        Raises:
            KeyError: If the object does not exist
        """
        file_path = self._get_file_path(key)
        if not os.path.exists(file_path):
            raise KeyError(f"Object not found: {key}")
        
        # Load metadata
        metadata = self._load_metadata(key)
        
        # Read file data
        with open(file_path, 'rb') as f:
            data = f.read()
        
        return StorageObject(data=data, metadata=metadata)
    
    def get_object_metadata(self, key: str) -> StorageMetadata:
        """Get object metadata without retrieving the object data.
        
        Args:
            key: Object key
            
        Returns:
            Object metadata
            
        Raises:
            KeyError: If the object does not exist
        """
        # Check if file exists
        file_path = self._get_file_path(key)
        if not os.path.exists(file_path):
            raise KeyError(f"Object not found: {key}")
        
        return self._load_metadata(key)
    
    def delete_object(self, key: str) -> bool:
        """Delete an object from the file system.
        
        Args:
            key: Object key
            
        Returns:
            True if object was deleted, False if it didn't exist
        """
        file_path = self._get_file_path(key)
        metadata_path = self._get_metadata_path(key)
        
        # Check if file exists
        if not os.path.exists(file_path):
            return False
        
        # Delete file
        os.remove(file_path)
        
        # Delete metadata if it exists
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
        
        return True
    
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
        results = []
        prefix_path = ""
        
        if prefix:
            # Normalize the prefix (replace backslashes, remove leading/trailing slashes)
            prefix = prefix.replace('\\', '/').strip('/')
            prefix_path = os.path.join(self.base_path, prefix)
        
        for root, _, files in os.walk(self.base_path):
            # Skip metadata files
            files = [f for f in files if not f.endswith(self.metadata_suffix)]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Skip if not in prefix path
                if prefix and not file_path.startswith(prefix_path):
                    continue
                
                # Get the key (relative path from base)
                rel_path = os.path.relpath(file_path, self.base_path)
                key = rel_path.replace('\\', '/')
                
                try:
                    # Get metadata
                    metadata = self._load_metadata(key)
                    results.append(metadata)
                    
                    # Check max results
                    if max_results and len(results) >= max_results:
                        break
                except KeyError:
                    # Skip if metadata doesn't exist
                    continue
            
            # Check max results
            if max_results and len(results) >= max_results:
                break
        
        return results
    
    def exists(self, key: str) -> bool:
        """Check if an object exists.
        
        Args:
            key: Object key
            
        Returns:
            True if the object exists, False otherwise
        """
        file_path = self._get_file_path(key)
        metadata_path = self._get_metadata_path(key)
        
        return os.path.exists(file_path) and os.path.exists(metadata_path)
    
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
        # Check if source exists
        if not self.exists(source_key):
            raise KeyError(f"Source object not found: {source_key}")
        
        # Get source object
        source_obj = self.get_object(source_key)
        source_metadata = source_obj.metadata
        
        # Determine visibility
        new_visibility = visibility if visibility is not None else source_metadata.visibility
        
        # Create new metadata
        new_metadata = source_metadata.custom_metadata.copy()
        if metadata:
            new_metadata.update(metadata)
        
        # Put the new object
        return self.put_object(
            key=destination_key,
            data=source_obj.data,
            content_type=source_metadata.content_type,
            metadata=new_metadata,
            visibility=new_visibility
        )
    
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
        # Copy the object
        dest_metadata = self.copy_object(source_key, destination_key)
        
        # Delete the source object
        self.delete_object(source_key)
        
        return dest_metadata
    
    def get_signed_url(
        self,
        key: str,
        expires_in: int = 3600,
        method: str = "GET"
    ) -> Optional[str]:
        """Generate a signed URL for temporary access.
        
        For file system storage, this returns a file:// URL.
        Note that this is only useful for local access and doesn't provide
        expiration or access control.
        
        Args:
            key: Object key
            expires_in: Expiration time in seconds (ignored)
            method: HTTP method to allow (ignored)
            
        Returns:
            URL string or None if the object doesn't exist
        """
        # Check if object exists
        if not self.exists(key):
            return None
        
        # Get absolute file path
        file_path = self._get_file_path(key)
        
        # Convert to URL
        return f"file://{urllib.parse.quote(os.path.abspath(file_path))}"
    
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
        file_path = self._get_file_path(key)
        if not os.path.exists(file_path):
            raise KeyError(f"Object not found: {key}")
        
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    
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
        # Check if object exists
        if not self.exists(key):
            raise KeyError(f"Object not found: {key}")
        
        # Get existing metadata
        existing_metadata = self._load_metadata(key)
        
        # Update custom metadata
        if merge:
            existing_metadata.custom_metadata.update(metadata)
        else:
            existing_metadata.custom_metadata = metadata
        
        # Update last modified timestamp
        existing_metadata.last_modified = datetime.datetime.now()
        
        # Save updated metadata
        self._save_metadata(existing_metadata)
        
        return existing_metadata

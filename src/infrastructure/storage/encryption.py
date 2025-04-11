"""Encrypted storage wrapper.

Provides encryption capabilities for storage backends.
"""

import io
import json
import os
import tempfile
from typing import Any, Dict, List, Optional, Union, BinaryIO, Iterator

from ...core.encryption import EncryptionService, EncryptionAlgorithm
from .interface import StorageBackend, StorageMetadata, StorageObject, StorageVisibility


class EncryptedStorageWrapper(StorageBackend):
    """Wrapper to add encryption to any storage backend.
    
    This class wraps another storage backend and provides transparent
    encryption/decryption of objects using the encryption service.
    """
    
    def __init__(
        self,
        backend: StorageBackend,
        encryption_service: EncryptionService,
        encrypt_metadata: bool = False,
        encrypted_suffix: str = ".encrypted",
        algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_GCM
    ):
        """Initialize the encrypted storage wrapper.
        
        Args:
            backend: Storage backend to wrap
            encryption_service: Encryption service to use
            encrypt_metadata: Whether to encrypt metadata
            encrypted_suffix: Suffix to add to keys to indicate encryption
            algorithm: Encryption algorithm to use
        """
        self.backend = backend
        self.encryption_service = encryption_service
        self.encrypt_metadata = encrypt_metadata
        self.encrypted_suffix = encrypted_suffix
        self.algorithm = algorithm
    
    def _encrypt_key(self, key: str) -> str:
        """Add encryption suffix to key.
        
        Args:
            key: Original key
            
        Returns:
            Key with encryption suffix
        """
        return key + self.encrypted_suffix
    
    def _decrypt_key(self, key: str) -> str:
        """Remove encryption suffix from key.
        
        Args:
            key: Key with encryption suffix
            
        Returns:
            Original key
        """
        if key.endswith(self.encrypted_suffix):
            return key[:-len(self.encrypted_suffix)]
        return key
    
    def _encrypt_metadata(self, metadata: Dict[str, str]) -> Dict[str, str]:
        """Encrypt metadata.
        
        Args:
            metadata: Original metadata
            
        Returns:
            Encrypted metadata
        """
        if not metadata or not self.encrypt_metadata:
            return metadata
        
        # Convert to JSON string
        json_data = json.dumps(metadata)
        
        # Encrypt
        encrypted_data = self.encryption_service.encrypt(
            json_data, algorithm=self.algorithm
        )
        
        # Format for storage
        return {
            "encrypted": "true",
            "algorithm": encrypted_data.algorithm.value,
            "key_id": encrypted_data.key_id,
            "iv": encrypted_data.iv.hex() if encrypted_data.iv else None,
            "tag": encrypted_data.tag.hex() if encrypted_data.tag else None,
            "data": encrypted_data.ciphertext.hex()
        }
    
    def _decrypt_metadata(self, metadata: Dict[str, str]) -> Dict[str, str]:
        """Decrypt metadata.
        
        Args:
            metadata: Encrypted metadata
            
        Returns:
            Original metadata
        """
        if not metadata or not self.encrypt_metadata:
            return metadata
        
        # Check if encrypted
        if metadata.get("encrypted") != "true":
            return metadata
        
        try:
            from ...core.encryption import EncryptedData
            
            # Parse encrypted data
            algorithm = EncryptionAlgorithm(metadata["algorithm"])
            key_id = metadata["key_id"]
            iv = bytes.fromhex(metadata["iv"]) if metadata.get("iv") else None
            tag = bytes.fromhex(metadata["tag"]) if metadata.get("tag") else None
            ciphertext = bytes.fromhex(metadata["data"])
            
            # Create EncryptedData object
            encrypted_data = EncryptedData(
                ciphertext=ciphertext,
                algorithm=algorithm,
                key_id=key_id,
                iv=iv,
                tag=tag
            )
            
            # Decrypt
            decrypted_data = self.encryption_service.decrypt(encrypted_data)
            
            # Parse JSON
            return json.loads(decrypted_data.decode('utf-8'))
        except Exception as e:
            # If decryption fails, return the encrypted metadata as is
            return metadata
    
    def put_object(
        self, 
        key: str, 
        data: Union[bytes, BinaryIO, str],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        visibility: StorageVisibility = StorageVisibility.PRIVATE
    ) -> StorageMetadata:
        """Store an encrypted object.
        
        Args:
            key: Object key
            data: Object data
            content_type: Optional MIME type
            metadata: Optional custom metadata
            visibility: Object visibility
            
        Returns:
            Object metadata
        """
        # Prepare data for encryption
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        elif isinstance(data, bytes):
            data_bytes = data
        else:  # File-like object
            # Read all data into memory
            data_bytes = data.read()
            # Reset position if possible
            try:
                data.seek(0)
            except:
                pass
        
        # Encrypt data
        encrypted_data = self.encryption_service.encrypt(
            data_bytes, algorithm=self.algorithm
        )
        
        # Add encryption metadata
        encryption_info = {
            "encryption_algorithm": encrypted_data.algorithm.value,
            "encryption_key_id": encrypted_data.key_id,
            "original_content_type": content_type
        }
        
        # Store metadata
        obj_metadata = metadata.copy() if metadata else {}
        obj_metadata.update(encryption_info)
        
        # Encrypt metadata if configured
        if self.encrypt_metadata:
            obj_metadata = self._encrypt_metadata(obj_metadata)
        
        # Store encrypted data with modified key
        encrypted_key = self._encrypt_key(key)
        
        # Store in backend
        stored_metadata = self.backend.put_object(
            key=encrypted_key,
            data=encrypted_data.ciphertext,
            content_type="application/octet-stream",  # Always use binary type for encrypted data
            metadata=obj_metadata,
            visibility=visibility
        )
        
        # Return metadata with original key
        return StorageMetadata(
            key=key,  # Return original key, not encrypted key
            size=stored_metadata.size,
            last_modified=stored_metadata.last_modified,
            etag=stored_metadata.etag,
            content_type=content_type,  # Return original content type
            visibility=stored_metadata.visibility,
            checksum=stored_metadata.checksum,
            custom_metadata=metadata or {}  # Return original metadata
        )
    
    def get_object(self, key: str) -> StorageObject:
        """Retrieve and decrypt an object.
        
        Args:
            key: Object key
            
        Returns:
            Decrypted storage object
            
        Raises:
            KeyError: If the object does not exist
        """
        # Get encrypted object
        encrypted_key = self._encrypt_key(key)
        try:
            encrypted_obj = self.backend.get_object(encrypted_key)
        except KeyError:
            raise KeyError(f"Object not found: {key}")
        
        # Get encryption metadata
        metadata = encrypted_obj.metadata.custom_metadata
        
        # Decrypt metadata if needed
        if self.encrypt_metadata:
            metadata = self._decrypt_metadata(metadata)
        
        # Get encryption info
        algorithm = EncryptionAlgorithm(metadata.get("encryption_algorithm", self.algorithm.value))
        key_id = metadata.get("encryption_key_id")
        content_type = metadata.get("original_content_type", encrypted_obj.metadata.content_type)
        
        # Create EncryptedData object
        from ...core.encryption import EncryptedData
        encrypted_data = EncryptedData(
            ciphertext=encrypted_obj.data,
            algorithm=algorithm,
            key_id=key_id,
            iv=None,  # IV is included in ciphertext for AES-GCM
            tag=None   # Tag is included in ciphertext for AES-GCM
        )
        
        # Decrypt data
        decrypted_data = self.encryption_service.decrypt(encrypted_data)
        
        # Create decrypted metadata
        decrypted_metadata = StorageMetadata(
            key=key,  # Original key
            size=len(decrypted_data),  # Size of decrypted data
            last_modified=encrypted_obj.metadata.last_modified,
            etag=encrypted_obj.metadata.etag,
            content_type=content_type,
            visibility=encrypted_obj.metadata.visibility,
            checksum=encrypted_obj.metadata.checksum,
            custom_metadata={k: v for k, v in metadata.items() 
                            if not k.startswith("encryption_")}  # Remove encryption metadata
        )
        
        return StorageObject(data=decrypted_data, metadata=decrypted_metadata)
    
    def get_object_metadata(self, key: str) -> StorageMetadata:
        """Get object metadata.
        
        Args:
            key: Object key
            
        Returns:
            Object metadata
            
        Raises:
            KeyError: If the object does not exist
        """
        # Get encrypted object metadata
        encrypted_key = self._encrypt_key(key)
        try:
            encrypted_metadata = self.backend.get_object_metadata(encrypted_key)
        except KeyError:
            raise KeyError(f"Object not found: {key}")
        
        # Get custom metadata
        metadata = encrypted_metadata.custom_metadata
        
        # Decrypt metadata if needed
        if self.encrypt_metadata:
            metadata = self._decrypt_metadata(metadata)
        
        # Get original content type
        content_type = metadata.get("original_content_type", encrypted_metadata.content_type)
        
        # Return metadata with original key and content type
        return StorageMetadata(
            key=key,  # Original key
            size=encrypted_metadata.size,  # Size of encrypted data
            last_modified=encrypted_metadata.last_modified,
            etag=encrypted_metadata.etag,
            content_type=content_type,
            visibility=encrypted_metadata.visibility,
            checksum=encrypted_metadata.checksum,
            custom_metadata={k: v for k, v in metadata.items() 
                            if not k.startswith("encryption_")}  # Remove encryption metadata
        )
    
    def delete_object(self, key: str) -> bool:
        """Delete an object.
        
        Args:
            key: Object key
            
        Returns:
            True if object was deleted, False if it didn't exist
        """
        encrypted_key = self._encrypt_key(key)
        return self.backend.delete_object(encrypted_key)
    
    def list_objects(
        self, 
        prefix: Optional[str] = None,
        max_results: Optional[int] = None
    ) -> List[StorageMetadata]:
        """List objects.
        
        Args:
            prefix: Optional key prefix to filter objects
            max_results: Maximum number of results to return
            
        Returns:
            List of object metadata
        """
        # List encrypted objects
        encrypted_prefix = self._encrypt_key(prefix) if prefix else None
        encrypted_objects = self.backend.list_objects(
            prefix=encrypted_prefix,
            max_results=max_results
        )
        
        # Decrypt object metadata
        decrypted_objects = []
        for encrypted_metadata in encrypted_objects:
            # Get original key
            key = self._decrypt_key(encrypted_metadata.key)
            
            # Get custom metadata
            metadata = encrypted_metadata.custom_metadata
            
            # Decrypt metadata if needed
            if self.encrypt_metadata:
                metadata = self._decrypt_metadata(metadata)
            
            # Get original content type
            content_type = metadata.get("original_content_type", encrypted_metadata.content_type)
            
            # Create decrypted metadata
            decrypted_metadata = StorageMetadata(
                key=key,  # Original key
                size=encrypted_metadata.size,  # Size of encrypted data
                last_modified=encrypted_metadata.last_modified,
                etag=encrypted_metadata.etag,
                content_type=content_type,
                visibility=encrypted_metadata.visibility,
                checksum=encrypted_metadata.checksum,
                custom_metadata={k: v for k, v in metadata.items() 
                                if not k.startswith("encryption_")}  # Remove encryption metadata
            )
            
            decrypted_objects.append(decrypted_metadata)
        
        return decrypted_objects
    
    def exists(self, key: str) -> bool:
        """Check if an object exists.
        
        Args:
            key: Object key
            
        Returns:
            True if the object exists, False otherwise
        """
        encrypted_key = self._encrypt_key(key)
        return self.backend.exists(encrypted_key)
    
    def copy_object(
        self, 
        source_key: str, 
        destination_key: str,
        metadata: Optional[Dict[str, str]] = None,
        visibility: Optional[StorageVisibility] = None
    ) -> StorageMetadata:
        """Copy an object.
        
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
        # Get the source object (decrypted)
        source_obj = self.get_object(source_key)
        
        # Determine visibility
        new_visibility = visibility if visibility is not None else source_obj.metadata.visibility
        
        # Create new metadata
        new_metadata = source_obj.metadata.custom_metadata.copy()
        if metadata:
            new_metadata.update(metadata)
        
        # Store the object (will be encrypted)
        return self.put_object(
            key=destination_key,
            data=source_obj.data,
            content_type=source_obj.metadata.content_type,
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
        
        Encrypted storage doesn't support signed URLs because
        the data is encrypted and would require decryption.
        
        Args:
            key: Object key
            expires_in: Expiration time in seconds
            method: HTTP method to allow
            
        Returns:
            None (not supported)
        """
        # Signed URLs not supported for encrypted storage
        return None
    
    def stream_object(self, key: str, chunk_size: int = 8192) -> Iterator[bytes]:
        """Stream an object in chunks.
        
        For encrypted storage, we must decrypt the entire object at once,
        then stream the decrypted data.
        
        Args:
            key: Object key
            chunk_size: Size of chunks in bytes
            
        Yields:
            Decrypted object data in chunks
            
        Raises:
            KeyError: If the object doesn't exist
        """
        # Get the decrypted object
        decrypted_obj = self.get_object(key)
        
        # Stream the decrypted data
        data = decrypted_obj.data
        total_size = len(data)
        
        for i in range(0, total_size, chunk_size):
            yield data[i:i+chunk_size]
    
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
        # Get encrypted key
        encrypted_key = self._encrypt_key(key)
        
        # Get existing metadata
        try:
            encrypted_metadata = self.backend.get_object_metadata(encrypted_key)
        except KeyError:
            raise KeyError(f"Object not found: {key}")
        
        # Get existing custom metadata
        existing_metadata = encrypted_metadata.custom_metadata
        
        # Decrypt metadata if needed
        if self.encrypt_metadata:
            existing_metadata = self._decrypt_metadata(existing_metadata)
        
        # Preserve encryption metadata
        encryption_metadata = {k: v for k, v in existing_metadata.items() 
                              if k.startswith("encryption_")}
        
        # Remove encryption metadata from existing metadata
        existing_metadata = {k: v for k, v in existing_metadata.items() 
                            if not k.startswith("encryption_")}
        
        # Update metadata
        if merge:
            existing_metadata.update(metadata)
        else:
            existing_metadata = metadata
        
        # Add back encryption metadata
        existing_metadata.update(encryption_metadata)
        
        # Encrypt metadata if configured
        if self.encrypt_metadata:
            existing_metadata = self._encrypt_metadata(existing_metadata)
        
        # Update in backend
        updated_metadata = self.backend.update_metadata(
            key=encrypted_key,
            metadata=existing_metadata,
            merge=False  # Always replace the entire metadata
        )
        
        # Return decrypted metadata
        metadata = updated_metadata.custom_metadata
        
        # Decrypt metadata if needed
        if self.encrypt_metadata:
            metadata = self._decrypt_metadata(metadata)
        
        # Get original content type
        content_type = metadata.get("original_content_type", updated_metadata.content_type)
        
        return StorageMetadata(
            key=key,  # Original key
            size=updated_metadata.size,
            last_modified=updated_metadata.last_modified,
            etag=updated_metadata.etag,
            content_type=content_type,
            visibility=updated_metadata.visibility,
            checksum=updated_metadata.checksum,
            custom_metadata={k: v for k, v in metadata.items() 
                            if not k.startswith("encryption_")}  # Remove encryption metadata
        )

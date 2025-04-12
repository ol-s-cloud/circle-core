"""Package storage implementation for the registry module.

This module provides implementations for storing and retrieving package files.
"""

import os
import hashlib
from typing import Dict, List, Optional, Any, BinaryIO

from ...core.audit import AuditLogger
from ..storage import StorageManager, StorageVisibility, StorageMetadata
from .interface import PackageStorageProvider


class FileSystemPackageStorageProvider(PackageStorageProvider):
    """File system implementation of the package storage provider.
    
    This implementation stores package files in a storage backend.
    """
    
    def __init__(
        self, 
        storage_manager: StorageManager,
        backend_name: str = "default",
        packages_prefix: str = "packages/",
        audit_logger: Optional[AuditLogger] = None
    ):
        """Initialize the file system package storage provider.
        
        Args:
            storage_manager: Storage manager instance
            backend_name: Storage backend name
            packages_prefix: Prefix for package storage paths
            audit_logger: Optional audit logger
        """
        self.storage_manager = storage_manager
        self.backend_name = backend_name
        self.packages_prefix = packages_prefix
        self.audit_logger = audit_logger
        
        # Ensure packages directory exists
        if not self.storage_manager.exists(self.packages_prefix, self.backend_name):
            # Create an empty file to ensure the directory exists
            self.storage_manager.put_object(
                f"{self.packages_prefix}.placeholder",
                data="",
                content_type="text/plain",
                backend=self.backend_name
            )
    
    def _get_package_path(self, package_name: str, version: str) -> str:
        """Get the storage path for a package file.
        
        Args:
            package_name: Package name
            version: Package version
            
        Returns:
            Storage path
        """
        return f"{self.packages_prefix}{package_name}/{version}/{package_name}-{version}.pkg"
    
    def _get_package_dir(self, package_name: str, version: Optional[str] = None) -> str:
        """Get the directory path for a package.
        
        Args:
            package_name: Package name
            version: Optional package version
            
        Returns:
            Directory path
        """
        if version:
            return f"{self.packages_prefix}{package_name}/{version}/"
        return f"{self.packages_prefix}{package_name}/"
    
    def _compute_hash(self, data: bytes) -> str:
        """Compute the SHA-256 hash of data.
        
        Args:
            data: Data to hash
            
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(data).hexdigest()
    
    def store_package(self, package_name: str, version: str, package_data: bytes) -> bool:
        """Store a package file.
        
        Args:
            package_name: Name of the package
            version: Package version
            package_data: Binary package data
            
        Returns:
            True if successful, False otherwise
        """
        # Generate package path
        package_path = self._get_package_path(package_name, version)
        
        # Compute hash
        package_hash = self._compute_hash(package_data)
        
        # Store package
        try:
            metadata = {
                "package_name": package_name,
                "version": version,
                "hash": package_hash,
                "size": len(package_data)
            }
            
            self.storage_manager.put_object(
                package_path,
                data=package_data,
                content_type="application/octet-stream",
                metadata=metadata,
                backend=self.backend_name
            )
            
            # Log the package storage
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_store",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "size": len(package_data),
                        "hash": package_hash,
                        "success": True
                    }
                )
            
            return True
        except Exception as e:
            # Log the failed package storage
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_store",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "size": len(package_data) if package_data else 0,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def retrieve_package(self, package_name: str, version: str) -> Optional[bytes]:
        """Retrieve a package file.
        
        Args:
            package_name: Name of the package
            version: Package version
            
        Returns:
            Binary package data or None if not found
        """
        # Generate package path
        package_path = self._get_package_path(package_name, version)
        
        try:
            # Get package from storage
            package_obj = self.storage_manager.get_object(package_path, self.backend_name)
            
            # Convert to bytes if necessary
            if isinstance(package_obj.data, bytes):
                package_data = package_obj.data
            else:
                # Handle file-like objects
                package_data = package_obj.data.read()
            
            # Log the package retrieval
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_retrieve",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "size": len(package_data) if package_data else 0,
                        "success": True
                    }
                )
            
            return package_data
        except KeyError:
            # Package not found
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_retrieve",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": False,
                        "error": "Package not found"
                    }
                )
            
            return None
        except Exception as e:
            # Log the failed package retrieval
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_retrieve",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def delete_package(self, package_name: str, version: Optional[str] = None) -> bool:
        """Delete a package file or all versions.
        
        Args:
            package_name: Name of the package
            version: Package version (None for all versions)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if version:
                # Delete specific version
                package_path = self._get_package_path(package_name, version)
                
                # Check if the package exists
                if not self.storage_manager.exists(package_path, self.backend_name):
                    return False
                
                # Delete the package file
                self.storage_manager.delete_object(package_path, self.backend_name)
                
                # Also delete any other files in the version directory
                version_dir = self._get_package_dir(package_name, version)
                try:
                    objects = self.storage_manager.list_objects(
                        prefix=version_dir,
                        backend=self.backend_name
                    )
                    
                    for obj in objects:
                        self.storage_manager.delete_object(obj.key, self.backend_name)
                except KeyError:
                    # No additional files
                    pass
            else:
                # Delete all versions
                package_dir = self._get_package_dir(package_name)
                
                # List all objects in the package directory
                try:
                    objects = self.storage_manager.list_objects(
                        prefix=package_dir,
                        backend=self.backend_name
                    )
                    
                    # Delete each object
                    for obj in objects:
                        self.storage_manager.delete_object(obj.key, self.backend_name)
                except KeyError:
                    # No package directory
                    return False
            
            # Log the package deletion
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_delete",
                    data={
                        "package_name": package_name,
                        "version": version if version else "all",
                        "success": True
                    }
                )
            
            return True
        except Exception as e:
            # Log the failed package deletion
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_delete",
                    data={
                        "package_name": package_name,
                        "version": version if version else "all",
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def package_exists(self, package_name: str, version: str) -> bool:
        """Check if a package file exists.
        
        Args:
            package_name: Name of the package
            version: Package version
            
        Returns:
            True if file exists, False otherwise
        """
        package_path = self._get_package_path(package_name, version)
        return self.storage_manager.exists(package_path, self.backend_name)
    
    def get_package_size(self, package_name: str, version: str) -> Optional[int]:
        """Get the size of a package file.
        
        Args:
            package_name: Name of the package
            version: Package version
            
        Returns:
            Size in bytes or None if not found
        """
        package_path = self._get_package_path(package_name, version)
        
        try:
            metadata = self.storage_manager.get_object_metadata(package_path, self.backend_name)
            return metadata.size
        except KeyError:
            return None
    
    def get_package_hash(self, package_name: str, version: str) -> Optional[str]:
        """Get the hash of a package file.
        
        Args:
            package_name: Name of the package
            version: Package version
            
        Returns:
            Hash string or None if not found
        """
        package_path = self._get_package_path(package_name, version)
        
        try:
            metadata = self.storage_manager.get_object_metadata(package_path, self.backend_name)
            
            # Check if hash is in custom metadata
            if "hash" in metadata.custom_metadata:
                return metadata.custom_metadata["hash"]
            
            # If not in metadata, compute it
            package_data = self.retrieve_package(package_name, version)
            if package_data:
                return self._compute_hash(package_data)
            
            return None
        except KeyError:
            return None
    
    def get_packages(self) -> List[Dict[str, Any]]:
        """Get a list of all stored packages.
        
        Returns:
            List of package info dictionaries (name, version, size, hash)
        """
        packages = []
        
        try:
            # List all objects in the packages directory
            objects = self.storage_manager.list_objects(
                prefix=self.packages_prefix,
                backend=self.backend_name
            )
            
            # Process each object
            for obj in objects:
                # Skip placeholder files
                if obj.key == f"{self.packages_prefix}.placeholder":
                    continue
                
                # Extract package name and version from path
                # Expected format: packages/{package_name}/{version}/{package_name}-{version}.pkg
                parts = obj.key[len(self.packages_prefix):].split('/')
                if len(parts) >= 3 and parts[2].endswith(".pkg"):
                    package_name = parts[0]
                    version = parts[1]
                    
                    # Only process .pkg files
                    if obj.key.endswith(f"{package_name}-{version}.pkg"):
                        packages.append({
                            "name": package_name,
                            "version": version,
                            "size": obj.size,
                            "hash": obj.custom_metadata.get("hash", ""),
                            "path": obj.key
                        })
            
            # Log the package listing
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_list_all",
                    data={
                        "success": True,
                        "count": len(packages)
                    }
                )
        except Exception as e:
            # Log the failed package listing
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_list_all",
                    data={
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
        
        return packages

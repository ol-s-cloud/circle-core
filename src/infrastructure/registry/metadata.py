"""Package metadata management for the registry module.

This module provides implementations for storing and retrieving package metadata.
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Set

from ...core.audit import AuditLogger
from ..storage import StorageManager, StorageVisibility
from .interface import PackageMetadataProvider


class FileSystemMetadataProvider(PackageMetadataProvider):
    """File system implementation of the package metadata provider.
    
    This implementation stores metadata in JSON files within a storage backend.
    """
    
    def __init__(
        self, 
        storage_manager: StorageManager,
        backend_name: str = "default",
        metadata_prefix: str = "metadata/",
        audit_logger: Optional[AuditLogger] = None
    ):
        """Initialize the file system metadata provider.
        
        Args:
            storage_manager: Storage manager instance
            backend_name: Storage backend name
            metadata_prefix: Prefix for metadata storage paths
            audit_logger: Optional audit logger
        """
        self.storage_manager = storage_manager
        self.backend_name = backend_name
        self.metadata_prefix = metadata_prefix
        self.audit_logger = audit_logger
        
        # Ensure metadata directory exists
        if not self.storage_manager.exists(self.metadata_prefix, self.backend_name):
            # Create an empty file to ensure the directory exists
            self.storage_manager.put_object(
                f"{self.metadata_prefix}.placeholder",
                data="",
                content_type="text/plain",
                backend=self.backend_name
            )
    
    def _get_metadata_path(self, package_name: str, version: Optional[str] = None) -> str:
        """Get the storage path for package metadata.
        
        Args:
            package_name: Package name
            version: Optional package version
            
        Returns:
            Storage path
        """
        if version:
            return f"{self.metadata_prefix}{package_name}/{version}.json"
        return f"{self.metadata_prefix}{package_name}/index.json"
    
    def _get_package_dir(self, package_name: str) -> str:
        """Get the directory path for a package.
        
        Args:
            package_name: Package name
            
        Returns:
            Directory path
        """
        return f"{self.metadata_prefix}{package_name}/"
    
    def get_package_metadata(self, package_name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Get metadata for a specific package and version.
        
        Args:
            package_name: Name of the package
            version: Package version (None for latest)
            
        Returns:
            Dictionary containing package metadata
            
        Raises:
            KeyError: If the package or version doesn't exist
        """
        # If version is None, get the latest version
        if version is None:
            # Get all versions and sort them
            versions = self.get_package_versions(package_name)
            if not versions:
                raise KeyError(f"Package {package_name} has no versions")
            
            # Get the latest version
            version = sorted(versions, key=lambda v: [int(x) for x in v.split('.') if x.isdigit()])[-1]
        
        # Get metadata from storage
        metadata_path = self._get_metadata_path(package_name, version)
        try:
            metadata_obj = self.storage_manager.get_object(metadata_path, self.backend_name)
            metadata_str = metadata_obj.data.decode('utf-8') if isinstance(metadata_obj.data, bytes) else metadata_obj.data
            metadata = json.loads(metadata_str)
            
            # Log the metadata access
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_metadata_access",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": True
                    }
                )
            
            return metadata
        except (KeyError, json.JSONDecodeError) as e:
            # Log the failed metadata access
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_metadata_access",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise KeyError(f"Metadata not found for package {package_name} version {version}")
    
    def add_package_metadata(self, package_name: str, version: str, metadata: Dict[str, Any]) -> bool:
        """Add metadata for a package version.
        
        Args:
            package_name: Name of the package
            version: Package version
            metadata: Package metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        # Validate metadata
        if not isinstance(metadata, dict):
            raise ValueError("Metadata must be a dictionary")
        
        # Ensure required fields
        required_fields = {"name", "version", "description", "author"}
        missing_fields = required_fields - set(metadata.keys())
        if missing_fields:
            raise ValueError(f"Missing required metadata fields: {', '.join(missing_fields)}")
        
        # Ensure name and version match
        if metadata["name"] != package_name:
            raise ValueError(f"Metadata name '{metadata['name']}' does not match package_name '{package_name}'")
        if metadata["version"] != version:
            raise ValueError(f"Metadata version '{metadata['version']}' does not match version '{version}'")
        
        # Add timestamps
        metadata["created_at"] = metadata.get("created_at", datetime.now().isoformat())
        metadata["updated_at"] = datetime.now().isoformat()
        
        # Convert to JSON
        metadata_json = json.dumps(metadata, indent=2)
        
        # Store metadata
        metadata_path = self._get_metadata_path(package_name, version)
        try:
            self.storage_manager.put_object(
                metadata_path,
                data=metadata_json,
                content_type="application/json",
                backend=self.backend_name
            )
            
            # Update package index
            self._update_package_index(package_name, version, metadata)
            
            # Log the metadata addition
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_metadata_add",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": True
                    }
                )
            
            return True
        except Exception as e:
            # Log the failed metadata addition
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_metadata_add",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def update_package_metadata(self, package_name: str, version: str, metadata: Dict[str, Any]) -> bool:
        """Update metadata for a package version.
        
        Args:
            package_name: Name of the package
            version: Package version
            metadata: Updated metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        # Check if the package exists
        if not self.package_exists(package_name, version):
            raise KeyError(f"Package {package_name} version {version} not found")
        
        # Get existing metadata
        try:
            existing_metadata = self.get_package_metadata(package_name, version)
        except KeyError:
            # If no metadata exists, treat as an add operation
            return self.add_package_metadata(package_name, version, metadata)
        
        # Merge metadata
        existing_metadata.update(metadata)
        
        # Update timestamps
        existing_metadata["updated_at"] = datetime.now().isoformat()
        
        # Convert to JSON
        metadata_json = json.dumps(existing_metadata, indent=2)
        
        # Store updated metadata
        metadata_path = self._get_metadata_path(package_name, version)
        try:
            self.storage_manager.put_object(
                metadata_path,
                data=metadata_json,
                content_type="application/json",
                backend=self.backend_name
            )
            
            # Update package index
            self._update_package_index(package_name, version, existing_metadata)
            
            # Log the metadata update
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_metadata_update",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": True
                    }
                )
            
            return True
        except Exception as e:
            # Log the failed metadata update
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_metadata_update",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def _update_package_index(self, package_name: str, version: str, metadata: Dict[str, Any]) -> None:
        """Update the package index with new version information.
        
        Args:
            package_name: Package name
            version: Package version
            metadata: Package metadata
        """
        index_path = self._get_metadata_path(package_name)
        
        # Get existing index or create new one
        try:
            index_obj = self.storage_manager.get_object(index_path, self.backend_name)
            index_str = index_obj.data.decode('utf-8') if isinstance(index_obj.data, bytes) else index_obj.data
            index = json.loads(index_str)
        except (KeyError, json.JSONDecodeError):
            # Create new index
            index = {
                "name": package_name,
                "versions": {},
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
        
        # Update index with version info
        summary = {
            "version": version,
            "description": metadata.get("description", ""),
            "author": metadata.get("author", ""),
            "dependencies": metadata.get("dependencies", {}),
            "created_at": metadata.get("created_at", datetime.now().isoformat()),
            "updated_at": metadata.get("updated_at", datetime.now().isoformat()),
        }
        
        index["versions"][version] = summary
        index["updated_at"] = datetime.now().isoformat()
        index["latest_version"] = self._get_latest_version(index["versions"])
        
        # Save the updated index
        self.storage_manager.put_object(
            index_path,
            data=json.dumps(index, indent=2),
            content_type="application/json",
            backend=self.backend_name
        )
    
    def _get_latest_version(self, versions: Dict[str, Any]) -> str:
        """Get the latest version from a versions dictionary.
        
        Args:
            versions: Dictionary of version info
            
        Returns:
            Latest version string
        """
        if not versions:
            return ""
        
        # Simple version sorting (assuming semantic versioning)
        version_list = list(versions.keys())
        return sorted(version_list, key=lambda v: [int(x) for x in v.split('.') if x.isdigit()])[-1]
    
    def list_packages(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List all packages matching the filter criteria.
        
        Args:
            filter_criteria: Dictionary of filter criteria
            
        Returns:
            List of package metadata dictionaries
        """
        filter_criteria = filter_criteria or {}
        
        # List all package directories
        packages = []
        try:
            metadata_objects = self.storage_manager.list_objects(
                prefix=self.metadata_prefix,
                backend=self.backend_name
            )
            
            # Extract package names from paths
            package_dirs = set()
            for obj in metadata_objects:
                # Skip the placeholder file
                if obj.key == f"{self.metadata_prefix}.placeholder":
                    continue
                
                # Extract package name from path
                parts = obj.key[len(self.metadata_prefix):].split('/')
                if len(parts) >= 1:
                    package_dirs.add(parts[0])
            
            # Get index for each package
            for package_name in package_dirs:
                try:
                    index = self.get_package_metadata(package_name, None)
                    
                    # Apply filters
                    if self._matches_filters(index, filter_criteria):
                        packages.append(index)
                except KeyError:
                    # Skip packages with no index
                    continue
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_list",
                    data={
                        "success": False,
                        "error": str(e),
                        "filter_criteria": filter_criteria
                    }
                )
            raise
        
        # Log the package listing
        if self.audit_logger:
            self.audit_logger.log_event(
                event_type="package_list",
                data={
                    "success": True,
                    "count": len(packages),
                    "filter_criteria": filter_criteria
                }
            )
        
        return packages
    
    def _matches_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if metadata matches filter criteria.
        
        Args:
            metadata: Package metadata
            filters: Filter criteria
            
        Returns:
            True if matches, False otherwise
        """
        for key, value in filters.items():
            # Handle special cases like tags, dependencies
            if key == "tags" and isinstance(value, list):
                metadata_tags = set(metadata.get("tags", []))
                if not all(tag in metadata_tags for tag in value):
                    return False
            elif key == "dependencies" and isinstance(value, dict):
                metadata_deps = metadata.get("dependencies", {})
                for dep_name, dep_version in value.items():
                    if dep_name not in metadata_deps:
                        return False
                    if dep_version and metadata_deps[dep_name] != dep_version:
                        return False
            # Regular field comparison
            elif metadata.get(key) != value:
                return False
        
        return True
    
    def get_package_versions(self, package_name: str) -> List[str]:
        """Get all available versions for a package.
        
        Args:
            package_name: Name of the package
            
        Returns:
            List of version strings
        """
        try:
            # Get package index
            index_path = self._get_metadata_path(package_name)
            index_obj = self.storage_manager.get_object(index_path, self.backend_name)
            index_str = index_obj.data.decode('utf-8') if isinstance(index_obj.data, bytes) else index_obj.data
            index = json.loads(index_str)
            
            # Get versions
            versions = list(index.get("versions", {}).keys())
            
            # Log the version listing
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_versions_list",
                    data={
                        "package_name": package_name,
                        "success": True,
                        "count": len(versions)
                    }
                )
            
            return versions
        except (KeyError, json.JSONDecodeError) as e:
            # Log the failed version listing
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_versions_list",
                    data={
                        "package_name": package_name,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            return []
    
    def package_exists(self, package_name: str, version: Optional[str] = None) -> bool:
        """Check if a package version exists.
        
        Args:
            package_name: Name of the package
            version: Package version (None for any version)
            
        Returns:
            True if package exists, False otherwise
        """
        if version:
            # Check for specific version
            metadata_path = self._get_metadata_path(package_name, version)
            return self.storage_manager.exists(metadata_path, self.backend_name)
        else:
            # Check for any version
            index_path = self._get_metadata_path(package_name)
            return self.storage_manager.exists(index_path, self.backend_name)
    
    def delete_package_metadata(self, package_name: str, version: Optional[str] = None) -> bool:
        """Delete metadata for a package version or entire package.
        
        Args:
            package_name: Name of the package
            version: Package version (None for all versions)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if version:
                # Delete specific version
                metadata_path = self._get_metadata_path(package_name, version)
                
                # Check if the version exists
                if not self.storage_manager.exists(metadata_path, self.backend_name):
                    return False
                
                # Delete the version metadata
                self.storage_manager.delete_object(metadata_path, self.backend_name)
                
                # Update the package index
                try:
                    index_path = self._get_metadata_path(package_name)
                    index_obj = self.storage_manager.get_object(index_path, self.backend_name)
                    index_str = index_obj.data.decode('utf-8') if isinstance(index_obj.data, bytes) else index_obj.data
                    index = json.loads(index_str)
                    
                    # Remove version from index
                    if version in index.get("versions", {}):
                        del index["versions"][version]
                    
                    # Update latest version
                    index["updated_at"] = datetime.now().isoformat()
                    if index["versions"]:
                        index["latest_version"] = self._get_latest_version(index["versions"])
                    else:
                        index["latest_version"] = ""
                    
                    # Save updated index
                    self.storage_manager.put_object(
                        index_path,
                        data=json.dumps(index, indent=2),
                        content_type="application/json",
                        backend=self.backend_name
                    )
                except (KeyError, json.JSONDecodeError):
                    # No index to update
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
            
            # Log the metadata deletion
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_metadata_delete",
                    data={
                        "package_name": package_name,
                        "version": version if version else "all",
                        "success": True
                    }
                )
            
            return True
        except Exception as e:
            # Log the failed metadata deletion
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_metadata_delete",
                    data={
                        "package_name": package_name,
                        "version": version if version else "all",
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise

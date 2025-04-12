"""Registry manager for the Circle Core registry module.

This module provides a unified interface for all registry operations.
"""

import os
import json
from typing import Dict, List, Optional, Any, BinaryIO, Union
from datetime import datetime

from ...core.audit import AuditLogger
from ...core.encryption import EncryptionService
from ...security.dependency_scanner import DependencyScanner
from ..storage import StorageManager
from .interface import (
    RegistryManager, 
    PackageMetadataProvider, 
    PackageStorageProvider,
    PackageVersioningProvider,
    PackageValidationProvider,
    PackageSearchProvider
)
from .metadata import FileSystemMetadataProvider
from .storage import FileSystemPackageStorageProvider
from .versioning import SemanticVersionProvider
from .validation import BasicPackageValidationProvider
from .search import SimpleSearchProvider


class CoreRegistryManager(RegistryManager):
    """Core implementation of the registry manager.
    
    This class coordinates all registry components and provides a unified
    interface for registry operations.
    """
    
    def __init__(
        self,
        storage_manager: Optional[StorageManager] = None,
        storage_backend: str = "default",
        registry_prefix: str = "registry/",
        encryption_service: Optional[EncryptionService] = None,
        dependency_scanner: Optional[DependencyScanner] = None,
        audit_logger: Optional[AuditLogger] = None,
        metadata_provider: Optional[PackageMetadataProvider] = None,
        storage_provider: Optional[PackageStorageProvider] = None,
        versioning_provider: Optional[PackageVersioningProvider] = None,
        validation_provider: Optional[PackageValidationProvider] = None,
        search_provider: Optional[PackageSearchProvider] = None
    ):
        """Initialize the registry manager.
        
        Args:
            storage_manager: Storage manager for registry storage
            storage_backend: Storage backend name
            registry_prefix: Prefix for registry storage paths
            encryption_service: Optional encryption service
            dependency_scanner: Optional dependency scanner
            audit_logger: Optional audit logger
            metadata_provider: Optional metadata provider (created if None)
            storage_provider: Optional storage provider (created if None)
            versioning_provider: Optional versioning provider (created if None)
            validation_provider: Optional validation provider (created if None)
            search_provider: Optional search provider (created if None)
        """
        # Create default storage manager if needed
        if not storage_manager:
            # Create a default storage manager
            home_dir = os.path.expanduser("~")
            registry_dir = os.path.join(home_dir, ".circle-core", "registry")
            os.makedirs(registry_dir, exist_ok=True)
            
            # Create storage manager (uses default FileSystemStorage)
            from ..storage import StorageManager
            storage_manager = StorageManager()
        
        # Store the storage manager
        self.storage_manager = storage_manager
        self.storage_backend = storage_backend
        self.registry_prefix = registry_prefix
        self.encryption_service = encryption_service
        self.dependency_scanner = dependency_scanner
        self.audit_logger = audit_logger
        
        # Create or use the metadata provider
        if metadata_provider:
            self.metadata_provider = metadata_provider
        else:
            self.metadata_provider = FileSystemMetadataProvider(
                storage_manager=self.storage_manager,
                backend_name=self.storage_backend,
                metadata_prefix=f"{self.registry_prefix}metadata/",
                audit_logger=self.audit_logger
            )
        
        # Create or use the storage provider
        if storage_provider:
            self.storage_provider = storage_provider
        else:
            self.storage_provider = FileSystemPackageStorageProvider(
                storage_manager=self.storage_manager,
                backend_name=self.storage_backend,
                packages_prefix=f"{self.registry_prefix}packages/",
                audit_logger=self.audit_logger
            )
        
        # Create or use the versioning provider
        if versioning_provider:
            self.versioning_provider = versioning_provider
        else:
            self.versioning_provider = SemanticVersionProvider(
                metadata_provider=self.metadata_provider,
                audit_logger=self.audit_logger
            )
        
        # Create or use the validation provider
        if validation_provider:
            self.validation_provider = validation_provider
        else:
            self.validation_provider = BasicPackageValidationProvider(
                encryption_service=self.encryption_service,
                dependency_scanner=self.dependency_scanner,
                audit_logger=self.audit_logger
            )
        
        # Create or use the search provider
        if search_provider:
            self.search_provider = search_provider
        else:
            self.search_provider = SimpleSearchProvider(
                metadata_provider=self.metadata_provider,
                audit_logger=self.audit_logger
            )
        
        # Initialize the registry
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize the registry manager.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Ensure required directories exist
            if not self.storage_manager.exists(f"{self.registry_prefix}", self.storage_backend):
                # Create registry directory structure
                self.storage_manager.put_object(
                    f"{self.registry_prefix}.placeholder",
                    data="",
                    content_type="text/plain",
                    backend=self.storage_backend
                )
            
            # Log initialization
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="registry_initialize",
                    data={"success": True}
                )
            
            self._initialized = True
            return True
        except Exception as e:
            # Log initialization failure
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="registry_initialize",
                    data={
                        "success": False,
                        "error": str(e)
                    }
                )
            
            self._initialized = False
            return False
    
    def _ensure_initialized(self) -> None:
        """Ensure the registry is initialized before operations.
        
        Raises:
            RuntimeError: If registry is not initialized
        """
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("Failed to initialize registry")
    
    def publish_package(
        self, 
        package_name: str, 
        version: str, 
        package_data: bytes, 
        metadata: Dict[str, Any], 
        signature: Optional[bytes] = None
    ) -> bool:
        """Publish a new package version.
        
        Args:
            package_name: Name of the package
            version: Package version
            package_data: Binary package data
            metadata: Package metadata
            signature: Package signature (optional)
            
        Returns:
            True if publish successful, False otherwise
        """
        self._ensure_initialized()
        
        try:
            # Validate metadata
            metadata_validation = self.validation_provider.validate_metadata(metadata)
            if not metadata_validation.get("valid", False):
                # Log validation failure
                if self.audit_logger:
                    self.audit_logger.log_event(
                        event_type="package_publish",
                        data={
                            "package_name": package_name,
                            "version": version,
                            "success": False,
                            "error": "Metadata validation failed",
                            "validation": metadata_validation
                        }
                    )
                return False
            
            # Validate package
            package_validation = self.validation_provider.validate_package(
                package_name, version, package_data
            )
            if not package_validation.get("valid", False):
                # Log validation failure
                if self.audit_logger:
                    self.audit_logger.log_event(
                        event_type="package_publish",
                        data={
                            "package_name": package_name,
                            "version": version,
                            "success": False,
                            "error": "Package validation failed",
                            "validation": package_validation
                        }
                    )
                return False
            
            # Verify signature if provided
            if signature and not self.validation_provider.verify_signature(
                package_name, version, signature
            ):
                # Log signature verification failure
                if self.audit_logger:
                    self.audit_logger.log_event(
                        event_type="package_publish",
                        data={
                            "package_name": package_name,
                            "version": version,
                            "success": False,
                            "error": "Signature verification failed"
                        }
                    )
                return False
            
            # Store package file
            if not self.storage_provider.store_package(package_name, version, package_data):
                # Log storage failure
                if self.audit_logger:
                    self.audit_logger.log_event(
                        event_type="package_publish",
                        data={
                            "package_name": package_name,
                            "version": version,
                            "success": False,
                            "error": "Failed to store package file"
                        }
                    )
                return False
            
            # Add package metadata
            if not self.metadata_provider.add_package_metadata(package_name, version, metadata):
                # Log metadata failure and try to clean up
                if self.audit_logger:
                    self.audit_logger.log_event(
                        event_type="package_publish",
                        data={
                            "package_name": package_name,
                            "version": version,
                            "success": False,
                            "error": "Failed to add package metadata"
                        }
                    )
                # Try to clean up the stored package file
                self.storage_provider.delete_package(package_name, version)
                return False
            
            # Log successful publish
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_publish",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "size": len(package_data),
                        "success": True
                    }
                )
            
            return True
        except Exception as e:
            # Log publish failure
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_publish",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            # Try to clean up any partially stored data
            try:
                self.storage_provider.delete_package(package_name, version)
            except:
                pass
            
            try:
                self.metadata_provider.delete_package_metadata(package_name, version)
            except:
                pass
            
            raise
    
    def download_package(
        self, package_name: str, version: Optional[str] = None
    ) -> Optional[bytes]:
        """Download a package.
        
        Args:
            package_name: Name of the package
            version: Package version (None for latest)
            
        Returns:
            Binary package data or None if not found
        """
        self._ensure_initialized()
        
        try:
            # Resolve version if not specified
            if version is None:
                version = self.versioning_provider.get_latest_version(package_name)
                if not version:
                    # No versions available
                    if self.audit_logger:
                        self.audit_logger.log_event(
                            event_type="package_download",
                            data={
                                "package_name": package_name,
                                "version": "latest",
                                "success": False,
                                "error": "No versions available"
                            }
                        )
                    return None
            
            # Get package data
            package_data = self.storage_provider.retrieve_package(package_name, version)
            if package_data is None:
                # Package not found
                if self.audit_logger:
                    self.audit_logger.log_event(
                        event_type="package_download",
                        data={
                            "package_name": package_name,
                            "version": version,
                            "success": False,
                            "error": "Package not found"
                        }
                    )
                return None
            
            # Log successful download
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_download",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "size": len(package_data),
                        "success": True
                    }
                )
            
            return package_data
        except Exception as e:
            # Log download failure
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_download",
                    data={
                        "package_name": package_name,
                        "version": version if version else "latest",
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def search_packages(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search for packages.
        
        Args:
            query: Search query string
            **kwargs: Additional search parameters
            
        Returns:
            List of package metadata dictionaries
        """
        self._ensure_initialized()
        
        try:
            # Extract common search parameters
            filters = kwargs.get("filters")
            limit = kwargs.get("limit", 100)
            offset = kwargs.get("offset", 0)
            
            # Perform search
            results = self.search_provider.search_packages(
                query=query,
                filters=filters,
                limit=limit,
                offset=offset
            )
            
            return results
        except Exception as e:
            # Log search failure
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_search",
                    data={
                        "query": query,
                        "kwargs": kwargs,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def get_package_info(
        self, package_name: str, version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get information about a package.
        
        Args:
            package_name: Name of the package
            version: Package version (None for latest)
            
        Returns:
            Package information dictionary or None if not found
        """
        self._ensure_initialized()
        
        try:
            # Get metadata
            try:
                metadata = self.metadata_provider.get_package_metadata(package_name, version)
            except KeyError:
                # Package not found
                if self.audit_logger:
                    self.audit_logger.log_event(
                        event_type="package_info",
                        data={
                            "package_name": package_name,
                            "version": version if version else "latest",
                            "success": False,
                            "error": "Package not found"
                        }
                    )
                return None
            
            # Resolve version if not specified
            if version is None:
                version = metadata.get("version")
            
            # Add extra info
            if version:
                try:
                    size = self.storage_provider.get_package_size(package_name, version)
                    if size is not None:
                        metadata["size"] = size
                    
                    hash_value = self.storage_provider.get_package_hash(package_name, version)
                    if hash_value is not None:
                        metadata["hash"] = hash_value
                except:
                    # Ignore errors in getting extra info
                    pass
            
            # Log successful info request
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_info",
                    data={
                        "package_name": package_name,
                        "version": version if version else "latest",
                        "success": True
                    }
                )
            
            return metadata
        except Exception as e:
            # Log info failure
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_info",
                    data={
                        "package_name": package_name,
                        "version": version if version else "latest",
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def delete_package(
        self, package_name: str, version: Optional[str] = None
    ) -> bool:
        """Delete a package.
        
        Args:
            package_name: Name of the package
            version: Package version (None for all versions)
            
        Returns:
            True if deletion successful, False otherwise
        """
        self._ensure_initialized()
        
        try:
            # Delete metadata
            metadata_deleted = self.metadata_provider.delete_package_metadata(
                package_name, version
            )
            
            # Delete package file
            storage_deleted = self.storage_provider.delete_package(
                package_name, version
            )
            
            # Log deletion
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_delete",
                    data={
                        "package_name": package_name,
                        "version": version if version else "all",
                        "metadata_deleted": metadata_deleted,
                        "storage_deleted": storage_deleted,
                        "success": metadata_deleted or storage_deleted
                    }
                )
            
            return metadata_deleted or storage_deleted
        except Exception as e:
            # Log deletion failure
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
    
    def get_package_versions(self, package_name: str) -> List[str]:
        """Get all available versions for a package.
        
        Args:
            package_name: Name of the package
            
        Returns:
            List of version strings
        """
        self._ensure_initialized()
        
        try:
            versions = self.metadata_provider.get_package_versions(package_name)
            
            # Log versions request
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_versions",
                    data={
                        "package_name": package_name,
                        "count": len(versions),
                        "success": True
                    }
                )
            
            return versions
        except Exception as e:
            # Log versions failure
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_versions",
                    data={
                        "package_name": package_name,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def resolve_dependency(
        self, package_name: str, version_spec: str
    ) -> Optional[str]:
        """Resolve a dependency to a concrete version.
        
        Args:
            package_name: Name of the package
            version_spec: Version specification
            
        Returns:
            Resolved version string or None if not found
        """
        self._ensure_initialized()
        
        try:
            # Resolve version
            resolved_version = self.versioning_provider.resolve_version(
                package_name, version_spec
            )
            
            # Log resolution
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="dependency_resolution",
                    data={
                        "package_name": package_name,
                        "version_spec": version_spec,
                        "resolved_version": resolved_version,
                        "success": resolved_version is not None
                    }
                )
            
            return resolved_version
        except Exception as e:
            # Log resolution failure
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="dependency_resolution",
                    data={
                        "package_name": package_name,
                        "version_spec": version_spec,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def get_dependency_tree(
        self, package_name: str, version: str
    ) -> Dict[str, Any]:
        """Get the dependency tree for a package.
        
        Args:
            package_name: Name of the package
            version: Package version
            
        Returns:
            Dependency tree dictionary
        """
        self._ensure_initialized()
        
        try:
            # Build dependency tree
            tree = self.versioning_provider.resolve_dependency_tree(
                package_name, version
            )
            
            # Log dependency tree request
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="dependency_tree",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": True
                    }
                )
            
            return tree
        except Exception as e:
            # Log dependency tree failure
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="dependency_tree",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def validate_package(
        self, package_name: str, version: str, package_data: bytes
    ) -> Dict[str, Any]:
        """Validate a package.
        
        Args:
            package_name: Name of the package
            version: Package version
            package_data: Binary package data
            
        Returns:
            Validation result dictionary
        """
        self._ensure_initialized()
        
        try:
            # Validate package
            validation_result = self.validation_provider.validate_package(
                package_name, version, package_data
            )
            
            # Log validation
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_validation",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": validation_result.get("valid", False)
                    }
                )
            
            return validation_result
        except Exception as e:
            # Log validation failure
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_validation",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def list_packages(
        self, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """List all packages with optional filtering.
        
        Args:
            filters: Optional filter criteria
            
        Returns:
            List of package metadata dictionaries
        """
        self._ensure_initialized()
        
        try:
            # List packages
            packages = self.metadata_provider.list_packages(filters)
            
            # Log package listing
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_list",
                    data={
                        "filters": filters,
                        "count": len(packages),
                        "success": True
                    }
                )
            
            return packages
        except Exception as e:
            # Log listing failure
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_list",
                    data={
                        "filters": filters,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def get_popular_packages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get a list of popular packages.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of package metadata dictionaries
        """
        self._ensure_initialized()
        
        try:
            # Get popular packages
            packages = self.search_provider.get_popular_packages(limit)
            
            # Log popular packages request
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="popular_packages",
                    data={
                        "limit": limit,
                        "count": len(packages),
                        "success": True
                    }
                )
            
            return packages
        except Exception as e:
            # Log popular packages failure
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="popular_packages",
                    data={
                        "limit": limit,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def get_recent_packages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get a list of recently added or updated packages.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of package metadata dictionaries
        """
        self._ensure_initialized()
        
        try:
            # Get recent packages
            packages = self.search_provider.get_recent_packages(limit)
            
            # Log recent packages request
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="recent_packages",
                    data={
                        "limit": limit,
                        "count": len(packages),
                        "success": True
                    }
                )
            
            return packages
        except Exception as e:
            # Log recent packages failure
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="recent_packages",
                    data={
                        "limit": limit,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise

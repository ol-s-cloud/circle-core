"""Interface definitions for the Circle Core Registry module.

This module defines the abstract base classes for all registry components,
ensuring a consistent API across different implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, BinaryIO, Set
from datetime import datetime


class PackageMetadataProvider(ABC):
    """Abstract interface for package metadata operations."""
    
    @abstractmethod
    def get_package_metadata(self, package_name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Get metadata for a specific package and version.
        
        Args:
            package_name: Name of the package
            version: Package version (None for latest)
            
        Returns:
            Dictionary containing package metadata
        """
        pass
    
    @abstractmethod
    def add_package_metadata(self, package_name: str, version: str, metadata: Dict[str, Any]) -> bool:
        """Add metadata for a package version.
        
        Args:
            package_name: Name of the package
            version: Package version
            metadata: Package metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def update_package_metadata(self, package_name: str, version: str, metadata: Dict[str, Any]) -> bool:
        """Update metadata for a package version.
        
        Args:
            package_name: Name of the package
            version: Package version
            metadata: Updated metadata dictionary
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def list_packages(self, filter_criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """List all packages matching the filter criteria.
        
        Args:
            filter_criteria: Dictionary of filter criteria
            
        Returns:
            List of package metadata dictionaries
        """
        pass

    @abstractmethod
    def get_package_versions(self, package_name: str) -> List[str]:
        """Get all available versions for a package.
        
        Args:
            package_name: Name of the package
            
        Returns:
            List of version strings
        """
        pass

    @abstractmethod
    def package_exists(self, package_name: str, version: Optional[str] = None) -> bool:
        """Check if a package version exists.
        
        Args:
            package_name: Name of the package
            version: Package version (None for any version)
            
        Returns:
            True if package exists, False otherwise
        """
        pass

    @abstractmethod
    def delete_package_metadata(self, package_name: str, version: Optional[str] = None) -> bool:
        """Delete metadata for a package version or entire package.
        
        Args:
            package_name: Name of the package
            version: Package version (None for all versions)
            
        Returns:
            True if successful, False otherwise
        """
        pass


class PackageStorageProvider(ABC):
    """Abstract interface for package storage operations."""
    
    @abstractmethod
    def store_package(self, package_name: str, version: str, package_data: bytes) -> bool:
        """Store a package file.
        
        Args:
            package_name: Name of the package
            version: Package version
            package_data: Binary package data
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def retrieve_package(self, package_name: str, version: str) -> Optional[bytes]:
        """Retrieve a package file.
        
        Args:
            package_name: Name of the package
            version: Package version
            
        Returns:
            Binary package data or None if not found
        """
        pass
    
    @abstractmethod
    def delete_package(self, package_name: str, version: Optional[str] = None) -> bool:
        """Delete a package file or all versions.
        
        Args:
            package_name: Name of the package
            version: Package version (None for all versions)
            
        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def package_exists(self, package_name: str, version: str) -> bool:
        """Check if a package file exists.
        
        Args:
            package_name: Name of the package
            version: Package version
            
        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    def get_package_size(self, package_name: str, version: str) -> Optional[int]:
        """Get the size of a package file.
        
        Args:
            package_name: Name of the package
            version: Package version
            
        Returns:
            Size in bytes or None if not found
        """
        pass

    @abstractmethod
    def get_package_hash(self, package_name: str, version: str) -> Optional[str]:
        """Get the hash of a package file.
        
        Args:
            package_name: Name of the package
            version: Package version
            
        Returns:
            Hash string or None if not found
        """
        pass

    @abstractmethod
    def get_packages(self) -> List[Dict[str, Any]]:
        """Get a list of all stored packages.
        
        Returns:
            List of package info dictionaries (name, version, size, hash)
        """
        pass


class PackageVersioningProvider(ABC):
    """Abstract interface for package versioning operations."""
    
    @abstractmethod
    def resolve_version(self, package_name: str, version_spec: str) -> Optional[str]:
        """Resolve a version specification to a concrete version.
        
        Args:
            package_name: Name of the package
            version_spec: Version specification (e.g., >=1.0.0,<2.0.0)
            
        Returns:
            Resolved version string or None if not found
        """
        pass
    
    @abstractmethod
    def compare_versions(self, version1: str, version2: str) -> int:
        """Compare two versions, returning -1, 0, or 1.
        
        Args:
            version1: First version string
            version2: Second version string
            
        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        pass
    
    @abstractmethod
    def resolve_dependencies(self, package_name: str, version: str) -> Dict[str, str]:
        """Resolve all dependencies for a package version.
        
        Args:
            package_name: Name of the package
            version: Package version
            
        Returns:
            Dictionary mapping dependency names to versions
        """
        pass

    @abstractmethod
    def parse_version_spec(self, version_spec: str) -> Any:
        """Parse a version specification into a structured format.
        
        Args:
            version_spec: Version specification string
            
        Returns:
            Structured version specification
        """
        pass

    @abstractmethod
    def is_compatible(self, version: str, version_spec: str) -> bool:
        """Check if a version is compatible with a version specification.
        
        Args:
            version: Version string
            version_spec: Version specification string
            
        Returns:
            True if compatible, False otherwise
        """
        pass

    @abstractmethod
    def get_latest_version(self, package_name: str) -> Optional[str]:
        """Get the latest version of a package.
        
        Args:
            package_name: Name of the package
            
        Returns:
            Latest version string or None if not found
        """
        pass


class PackageValidationProvider(ABC):
    """Abstract interface for package validation operations."""
    
    @abstractmethod
    def validate_package(self, package_name: str, version: str, package_data: bytes) -> Dict[str, Any]:
        """Validate a package file.
        
        Args:
            package_name: Name of the package
            version: Package version
            package_data: Binary package data
            
        Returns:
            Validation result dictionary
        """
        pass
    
    @abstractmethod
    def verify_signature(self, package_name: str, version: str, signature: bytes, public_key: Optional[bytes] = None) -> bool:
        """Verify the signature of a package.
        
        Args:
            package_name: Name of the package
            version: Package version
            signature: Signature bytes
            public_key: Public key bytes (optional)
            
        Returns:
            True if signature is valid, False otherwise
        """
        pass

    @abstractmethod
    def check_integrity(self, package_name: str, version: str, package_data: bytes, expected_hash: Optional[str] = None) -> bool:
        """Check the integrity of a package file.
        
        Args:
            package_name: Name of the package
            version: Package version
            package_data: Binary package data
            expected_hash: Expected hash string (optional)
            
        Returns:
            True if integrity check passes, False otherwise
        """
        pass

    @abstractmethod
    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate package metadata.
        
        Args:
            metadata: Package metadata dictionary
            
        Returns:
            Validation result dictionary
        """
        pass

    @abstractmethod
    def scan_security(self, package_name: str, version: str, package_data: bytes) -> Dict[str, Any]:
        """Scan a package for security issues.
        
        Args:
            package_name: Name of the package
            version: Package version
            package_data: Binary package data
            
        Returns:
            Security scan result dictionary
        """
        pass


class PackageSearchProvider(ABC):
    """Abstract interface for package search operations."""
    
    @abstractmethod
    def search_packages(self, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Search for packages matching the query and filters.
        
        Args:
            query: Search query string
            filters: Dictionary of filter criteria
            limit: Maximum number of results
            offset: Result offset for pagination
            
        Returns:
            List of package metadata dictionaries
        """
        pass
    
    @abstractmethod
    def search_by_tag(self, tag: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Search for packages with a specific tag.
        
        Args:
            tag: Tag to search for
            limit: Maximum number of results
            offset: Result offset for pagination
            
        Returns:
            List of package metadata dictionaries
        """
        pass
    
    @abstractmethod
    def get_popular_packages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get a list of popular packages.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of package metadata dictionaries
        """
        pass
    
    @abstractmethod
    def get_recent_packages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get a list of recently added or updated packages.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of package metadata dictionaries
        """
        pass


class RegistryManager(ABC):
    """Abstract interface for the registry manager."""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the registry manager.
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def publish_package(self, package_name: str, version: str, package_data: bytes, metadata: Dict[str, Any], signature: Optional[bytes] = None) -> bool:
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
        pass
    
    @abstractmethod
    def download_package(self, package_name: str, version: Optional[str] = None) -> Optional[bytes]:
        """Download a package.
        
        Args:
            package_name: Name of the package
            version: Package version (None for latest)
            
        Returns:
            Binary package data or None if not found
        """
        pass
    
    @abstractmethod
    def search_packages(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Search for packages.
        
        Args:
            query: Search query string
            **kwargs: Additional search parameters
            
        Returns:
            List of package metadata dictionaries
        """
        pass
    
    @abstractmethod
    def get_package_info(self, package_name: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get information about a package.
        
        Args:
            package_name: Name of the package
            version: Package version (None for latest)
            
        Returns:
            Package information dictionary or None if not found
        """
        pass
    
    @abstractmethod
    def delete_package(self, package_name: str, version: Optional[str] = None) -> bool:
        """Delete a package.
        
        Args:
            package_name: Name of the package
            version: Package version (None for all versions)
            
        Returns:
            True if deletion successful, False otherwise
        """
        pass

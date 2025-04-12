"""Interface definitions for the Circle Core licensing module.

This module defines the abstract base classes for all licensing components,
ensuring a consistent API across different implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from enum import Enum, auto


class LicenseType(Enum):
    """Types of licenses available in the system."""
    
    TRIAL = auto()
    STANDARD = auto()
    PROFESSIONAL = auto()
    ENTERPRISE = auto()
    CUSTOM = auto()


class LicenseStatus(Enum):
    """Status of a license."""
    
    VALID = auto()
    EXPIRED = auto()
    INVALID = auto()
    REVOKED = auto()
    TRIAL = auto()


class LicenseFeature(ABC):
    """Base class for license features."""
    
    @property
    @abstractmethod
    def feature_id(self) -> str:
        """Get the unique ID of the feature."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the display name of the feature."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Get the description of the feature."""
        pass


class License(ABC):
    """Abstract base class for license objects."""
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Get the unique ID of the license."""
        pass
    
    @property
    @abstractmethod
    def type(self) -> LicenseType:
        """Get the type of the license."""
        pass
    
    @property
    @abstractmethod
    def status(self) -> LicenseStatus:
        """Get the current status of the license."""
        pass
    
    @property
    @abstractmethod
    def licensee(self) -> str:
        """Get the name of the licensee."""
        pass
    
    @property
    @abstractmethod
    def issue_date(self) -> datetime:
        """Get the date when the license was issued."""
        pass
    
    @property
    @abstractmethod
    def expiry_date(self) -> Optional[datetime]:
        """Get the expiry date of the license, if any."""
        pass
    
    @property
    @abstractmethod
    def features(self) -> Set[str]:
        """Get the set of features enabled by this license."""
        pass
    
    @abstractmethod
    def is_valid(self) -> bool:
        """Check if the license is currently valid."""
        pass
    
    @abstractmethod
    def has_feature(self, feature_id: str) -> bool:
        """Check if the license includes a specific feature.
        
        Args:
            feature_id: ID of the feature to check
            
        Returns:
            True if the feature is included, False otherwise
        """
        pass
    
    @abstractmethod
    def is_expired(self) -> bool:
        """Check if the license has expired."""
        pass
    
    @abstractmethod
    def days_until_expiry(self) -> Optional[int]:
        """Get the number of days until the license expires.
        
        Returns:
            Number of days until expiry, or None if the license doesn't expire
        """
        pass


class LicenseValidator(ABC):
    """Abstract interface for license validation."""
    
    @abstractmethod
    def validate_license(self, license_data: str) -> License:
        """Validate a license from its serialized form.
        
        Args:
            license_data: Serialized license data
            
        Returns:
            License object if valid
            
        Raises:
            InvalidLicenseError: If the license is invalid
        """
        pass
    
    @abstractmethod
    def verify_signature(self, license_data: str, signature: str) -> bool:
        """Verify the signature of a license.
        
        Args:
            license_data: Serialized license data
            signature: License signature
            
        Returns:
            True if signature is valid, False otherwise
        """
        pass


class LicenseManager(ABC):
    """Abstract interface for license management."""
    
    @abstractmethod
    def load_license(self, license_data: str) -> License:
        """Load a license from its serialized form.
        
        Args:
            license_data: Serialized license data
            
        Returns:
            License object
            
        Raises:
            InvalidLicenseError: If the license is invalid
        """
        pass
    
    @abstractmethod
    def save_license(self, license_obj: License) -> str:
        """Save a license to its serialized form.
        
        Args:
            license_obj: License object
            
        Returns:
            Serialized license data
        """
        pass
    
    @abstractmethod
    def generate_license(
        self,
        licensee: str,
        license_type: LicenseType,
        features: Set[str],
        duration: Optional[timedelta] = None,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> License:
        """Generate a new license.
        
        Args:
            licensee: Name of the licensee
            license_type: Type of license
            features: Set of feature IDs to include
            duration: Optional duration of the license
            custom_data: Optional custom data to include
            
        Returns:
            Generated license object
        """
        pass
    
    @abstractmethod
    def get_active_license(self) -> Optional[License]:
        """Get the currently active license.
        
        Returns:
            Active license or None if no license is active
        """
        pass
    
    @abstractmethod
    def check_feature_access(self, feature_id: str) -> bool:
        """Check if a feature is accessible with the current license.
        
        Args:
            feature_id: ID of the feature to check
            
        Returns:
            True if the feature is accessible, False otherwise
        """
        pass
    
    @abstractmethod
    def register_license(self, license_data: str) -> License:
        """Register a license with the system.
        
        Args:
            license_data: Serialized license data
            
        Returns:
            Registered license object
            
        Raises:
            InvalidLicenseError: If the license is invalid
        """
        pass


class LicenseStorage(ABC):
    """Abstract interface for license storage."""
    
    @abstractmethod
    def store_license(self, license_obj: License) -> bool:
        """Store a license.
        
        Args:
            license_obj: License object
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def retrieve_license(self, license_id: str) -> Optional[License]:
        """Retrieve a license by ID.
        
        Args:
            license_id: License ID
            
        Returns:
            License object or None if not found
        """
        pass
    
    @abstractmethod
    def retrieve_active_license(self) -> Optional[License]:
        """Retrieve the currently active license.
        
        Returns:
            Active license or None if no license is active
        """
        pass
    
    @abstractmethod
    def set_active_license(self, license_id: str) -> bool:
        """Set the active license.
        
        Args:
            license_id: License ID
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def list_licenses(self) -> List[License]:
        """List all stored licenses.
        
        Returns:
            List of license objects
        """
        pass
    
    @abstractmethod
    def delete_license(self, license_id: str) -> bool:
        """Delete a license.
        
        Args:
            license_id: License ID
            
        Returns:
            True if successful, False otherwise
        """
        pass


# Custom exceptions
class InvalidLicenseError(Exception):
    """Raised when a license is invalid."""
    pass


class LicenseExpiredError(Exception):
    """Raised when a license has expired."""
    pass


class LicenseFeatureNotAvailableError(Exception):
    """Raised when a feature is not available in the license."""
    pass


class LicenseRevocationList(ABC):
    """Abstract interface for license revocation."""
    
    @abstractmethod
    def add_to_revocation_list(self, license_id: str, reason: str) -> bool:
        """Add a license to the revocation list.
        
        Args:
            license_id: License ID
            reason: Reason for revocation
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def remove_from_revocation_list(self, license_id: str) -> bool:
        """Remove a license from the revocation list.
        
        Args:
            license_id: License ID
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_revoked(self, license_id: str) -> bool:
        """Check if a license is revoked.
        
        Args:
            license_id: License ID
            
        Returns:
            True if revoked, False otherwise
        """
        pass
    
    @abstractmethod
    def get_revocation_reason(self, license_id: str) -> Optional[str]:
        """Get the reason for license revocation.
        
        Args:
            license_id: License ID
            
        Returns:
            Reason string or None if not revoked
        """
        pass
    
    @abstractmethod
    def update_from_remote(self) -> bool:
        """Update the revocation list from a remote source.
        
        Returns:
            True if update successful, False otherwise
        """
        pass

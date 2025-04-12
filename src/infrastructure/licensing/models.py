"""License models for the Circle Core licensing module.

This module provides concrete implementations of the license data models.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Union
import json

from .interface import License, LicenseType, LicenseStatus, LicenseFeature


class StandardFeature(LicenseFeature):
    """Standard implementation of license feature."""
    
    def __init__(self, feature_id: str, name: str, description: str):
        """Initialize a standard feature.
        
        Args:
            feature_id: Unique feature ID
            name: Display name
            description: Feature description
        """
        self._feature_id = feature_id
        self._name = name
        self._description = description
    
    @property
    def feature_id(self) -> str:
        """Get the unique ID of the feature."""
        return self._feature_id
    
    @property
    def name(self) -> str:
        """Get the display name of the feature."""
        return self._name
    
    @property
    def description(self) -> str:
        """Get the description of the feature."""
        return self._description


class StandardLicense(License):
    """Standard implementation of license."""
    
    def __init__(
        self,
        license_id: str,
        license_type: LicenseType,
        licensee: str,
        issue_date: datetime,
        features: Set[str],
        expiry_date: Optional[datetime] = None,
        status: Optional[LicenseStatus] = None,
        custom_data: Optional[Dict[str, Any]] = None
    ):
        """Initialize a standard license.
        
        Args:
            license_id: Unique license ID
            license_type: Type of license
            licensee: Name of the licensee
            issue_date: Date when the license was issued
            features: Set of feature IDs enabled by this license
            expiry_date: Optional expiry date
            status: Optional status (defaults to VALID)
            custom_data: Optional custom data
        """
        self._id = license_id
        self._type = license_type
        self._licensee = licensee
        self._issue_date = issue_date
        self._expiry_date = expiry_date
        self._features = features
        self._status = status or self._determine_status()
        self._custom_data = custom_data or {}
    
    def _determine_status(self) -> LicenseStatus:
        """Determine the license status based on its properties."""
        if self._type == LicenseType.TRIAL:
            return LicenseStatus.TRIAL
        elif self._expiry_date and self._expiry_date <= datetime.now():
            return LicenseStatus.EXPIRED
        else:
            return LicenseStatus.VALID
    
    @property
    def id(self) -> str:
        """Get the unique ID of the license."""
        return self._id
    
    @property
    def type(self) -> LicenseType:
        """Get the type of the license."""
        return self._type
    
    @property
    def status(self) -> LicenseStatus:
        """Get the current status of the license."""
        # Update status if needed
        if self._status not in {LicenseStatus.INVALID, LicenseStatus.REVOKED}:
            self._status = self._determine_status()
        return self._status
    
    @property
    def licensee(self) -> str:
        """Get the name of the licensee."""
        return self._licensee
    
    @property
    def issue_date(self) -> datetime:
        """Get the date when the license was issued."""
        return self._issue_date
    
    @property
    def expiry_date(self) -> Optional[datetime]:
        """Get the expiry date of the license, if any."""
        return self._expiry_date
    
    @property
    def features(self) -> Set[str]:
        """Get the set of features enabled by this license."""
        return self._features
    
    @property
    def custom_data(self) -> Dict[str, Any]:
        """Get the custom data of the license."""
        return self._custom_data
    
    def is_valid(self) -> bool:
        """Check if the license is currently valid."""
        return self.status in {LicenseStatus.VALID, LicenseStatus.TRIAL}
    
    def has_feature(self, feature_id: str) -> bool:
        """Check if the license includes a specific feature.
        
        Args:
            feature_id: ID of the feature to check
            
        Returns:
            True if the feature is included, False otherwise
        """
        return feature_id in self._features
    
    def is_expired(self) -> bool:
        """Check if the license has expired."""
        return self.status == LicenseStatus.EXPIRED
    
    def days_until_expiry(self) -> Optional[int]:
        """Get the number of days until the license expires.
        
        Returns:
            Number of days until expiry, or None if the license doesn't expire
        """
        if not self._expiry_date:
            return None
        
        delta = self._expiry_date - datetime.now()
        return max(0, delta.days)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the license to a dictionary.
        
        Returns:
            Dictionary representation of the license
        """
        return {
            "id": self._id,
            "type": self._type.name,
            "licensee": self._licensee,
            "issue_date": self._issue_date.isoformat(),
            "expiry_date": self._expiry_date.isoformat() if self._expiry_date else None,
            "features": list(self._features),
            "status": self._status.name,
            "custom_data": self._custom_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StandardLicense":
        """Create a license from a dictionary.
        
        Args:
            data: Dictionary representation of a license
            
        Returns:
            License object
        """
        return cls(
            license_id=data["id"],
            license_type=LicenseType[data["type"]],
            licensee=data["licensee"],
            issue_date=datetime.fromisoformat(data["issue_date"]),
            expiry_date=datetime.fromisoformat(data["expiry_date"]) if data.get("expiry_date") else None,
            features=set(data["features"]),
            status=LicenseStatus[data["status"]] if "status" in data else None,
            custom_data=data.get("custom_data")
        )


def generate_license_id() -> str:
    """Generate a unique license ID.
    
    Returns:
        Unique license ID string
    """
    return str(uuid.uuid4())


# Feature catalog for common features
class FeatureCatalog:
    """Catalog of common license features."""
    
    # Base features
    FEATURE_API_ACCESS = "api_access"
    FEATURE_CLI_ACCESS = "cli_access"
    FEATURE_STORAGE = "storage"
    FEATURE_REGISTRY = "registry"
    FEATURE_CONFIGURATION = "configuration"
    
    # Security features
    FEATURE_ENCRYPTION = "encryption"
    FEATURE_AUDIT_LOGGING = "audit_logging"
    FEATURE_MFA = "mfa"
    FEATURE_SECURE_STORAGE = "secure_storage"
    
    # Advanced features
    FEATURE_CLOUD_INTEGRATION = "cloud_integration"
    FEATURE_KUBERNETES_SUPPORT = "kubernetes_support"
    FEATURE_HIGH_AVAILABILITY = "high_availability"
    FEATURE_DISTRIBUTED_CACHING = "distributed_caching"
    
    # Usage limits
    FEATURE_UNLIMITED_STORAGE = "unlimited_storage"
    FEATURE_UNLIMITED_USERS = "unlimited_users"
    FEATURE_UNLIMITED_PROJECTS = "unlimited_projects"
    
    # Product-specific features
    FEATURE_TRADING_BOT = "trading_bot"
    FEATURE_MLOPS = "mlops"
    FEATURE_DATA_ANALYTICS = "data_analytics"
    FEATURE_PHARMACOVIGILANCE = "pharmacovigilance"
    FEATURE_RHEO_ML = "rheo_ml"
    FEATURE_CARBON_ANALYTICS = "carbon_analytics"
    
    @classmethod
    def get_all_features(cls) -> Dict[str, StandardFeature]:
        """Get all features in the catalog.
        
        Returns:
            Dictionary mapping feature IDs to feature objects
        """
        features = {}
        
        features[cls.FEATURE_API_ACCESS] = StandardFeature(
            cls.FEATURE_API_ACCESS,
            "API Access",
            "Access to the Circle Core API"
        )
        
        features[cls.FEATURE_CLI_ACCESS] = StandardFeature(
            cls.FEATURE_CLI_ACCESS,
            "CLI Access",
            "Access to the Circle Core CLI"
        )
        
        features[cls.FEATURE_STORAGE] = StandardFeature(
            cls.FEATURE_STORAGE,
            "Storage",
            "Access to the storage system"
        )
        
        features[cls.FEATURE_REGISTRY] = StandardFeature(
            cls.FEATURE_REGISTRY,
            "Package Registry",
            "Access to the package registry"
        )
        
        features[cls.FEATURE_CONFIGURATION] = StandardFeature(
            cls.FEATURE_CONFIGURATION,
            "Configuration Management",
            "Access to the configuration management system"
        )
        
        features[cls.FEATURE_ENCRYPTION] = StandardFeature(
            cls.FEATURE_ENCRYPTION,
            "Encryption",
            "Access to the encryption services"
        )
        
        features[cls.FEATURE_AUDIT_LOGGING] = StandardFeature(
            cls.FEATURE_AUDIT_LOGGING,
            "Audit Logging",
            "Access to the audit logging system"
        )
        
        features[cls.FEATURE_MFA] = StandardFeature(
            cls.FEATURE_MFA,
            "Multi-Factor Authentication",
            "Access to multi-factor authentication features"
        )
        
        features[cls.FEATURE_SECURE_STORAGE] = StandardFeature(
            cls.FEATURE_SECURE_STORAGE,
            "Secure Storage",
            "Access to the secure storage system"
        )
        
        features[cls.FEATURE_CLOUD_INTEGRATION] = StandardFeature(
            cls.FEATURE_CLOUD_INTEGRATION,
            "Cloud Integration",
            "Integration with cloud providers"
        )
        
        features[cls.FEATURE_KUBERNETES_SUPPORT] = StandardFeature(
            cls.FEATURE_KUBERNETES_SUPPORT,
            "Kubernetes Support",
            "Support for Kubernetes deployments"
        )
        
        features[cls.FEATURE_HIGH_AVAILABILITY] = StandardFeature(
            cls.FEATURE_HIGH_AVAILABILITY,
            "High Availability",
            "High availability features"
        )
        
        features[cls.FEATURE_DISTRIBUTED_CACHING] = StandardFeature(
            cls.FEATURE_DISTRIBUTED_CACHING,
            "Distributed Caching",
            "Distributed caching features"
        )
        
        features[cls.FEATURE_UNLIMITED_STORAGE] = StandardFeature(
            cls.FEATURE_UNLIMITED_STORAGE,
            "Unlimited Storage",
            "Unlimited storage capacity"
        )
        
        features[cls.FEATURE_UNLIMITED_USERS] = StandardFeature(
            cls.FEATURE_UNLIMITED_USERS,
            "Unlimited Users",
            "Unlimited user accounts"
        )
        
        features[cls.FEATURE_UNLIMITED_PROJECTS] = StandardFeature(
            cls.FEATURE_UNLIMITED_PROJECTS,
            "Unlimited Projects",
            "Unlimited project count"
        )
        
        features[cls.FEATURE_TRADING_BOT] = StandardFeature(
            cls.FEATURE_TRADING_BOT,
            "Trading Bot",
            "Access to the trading bot platform"
        )
        
        features[cls.FEATURE_MLOPS] = StandardFeature(
            cls.FEATURE_MLOPS,
            "MLOps",
            "Access to MLOps tools"
        )
        
        features[cls.FEATURE_DATA_ANALYTICS] = StandardFeature(
            cls.FEATURE_DATA_ANALYTICS,
            "Data Analytics",
            "Access to data analytics platform"
        )
        
        features[cls.FEATURE_PHARMACOVIGILANCE] = StandardFeature(
            cls.FEATURE_PHARMACOVIGILANCE,
            "Pharmacovigilance",
            "Access to pharmacovigilance system"
        )
        
        features[cls.FEATURE_RHEO_ML] = StandardFeature(
            cls.FEATURE_RHEO_ML,
            "Rheo ML",
            "Access to Rheo ML platform"
        )
        
        features[cls.FEATURE_CARBON_ANALYTICS] = StandardFeature(
            cls.FEATURE_CARBON_ANALYTICS,
            "Carbon Analytics",
            "Access to carbon analytics platform"
        )
        
        return features
    
    @classmethod
    def get_feature(cls, feature_id: str) -> Optional[StandardFeature]:
        """Get a feature by ID.
        
        Args:
            feature_id: Feature ID
            
        Returns:
            Feature object or None if not found
        """
        return cls.get_all_features().get(feature_id)
    
    @classmethod
    def get_features_for_license_type(cls, license_type: LicenseType) -> Set[str]:
        """Get the set of features for a license type.
        
        Args:
            license_type: License type
            
        Returns:
            Set of feature IDs
        """
        if license_type == LicenseType.TRIAL:
            return {
                cls.FEATURE_API_ACCESS,
                cls.FEATURE_CLI_ACCESS,
                cls.FEATURE_STORAGE,
                cls.FEATURE_REGISTRY,
                cls.FEATURE_CONFIGURATION,
                cls.FEATURE_ENCRYPTION,
                cls.FEATURE_AUDIT_LOGGING
            }
        elif license_type == LicenseType.STANDARD:
            return {
                cls.FEATURE_API_ACCESS,
                cls.FEATURE_CLI_ACCESS,
                cls.FEATURE_STORAGE,
                cls.FEATURE_REGISTRY,
                cls.FEATURE_CONFIGURATION,
                cls.FEATURE_ENCRYPTION,
                cls.FEATURE_AUDIT_LOGGING,
                cls.FEATURE_MFA,
                cls.FEATURE_SECURE_STORAGE
            }
        elif license_type == LicenseType.PROFESSIONAL:
            return {
                cls.FEATURE_API_ACCESS,
                cls.FEATURE_CLI_ACCESS,
                cls.FEATURE_STORAGE,
                cls.FEATURE_REGISTRY,
                cls.FEATURE_CONFIGURATION,
                cls.FEATURE_ENCRYPTION,
                cls.FEATURE_AUDIT_LOGGING,
                cls.FEATURE_MFA,
                cls.FEATURE_SECURE_STORAGE,
                cls.FEATURE_CLOUD_INTEGRATION,
                cls.FEATURE_KUBERNETES_SUPPORT,
                cls.FEATURE_UNLIMITED_STORAGE
            }
        elif license_type == LicenseType.ENTERPRISE:
            return {
                cls.FEATURE_API_ACCESS,
                cls.FEATURE_CLI_ACCESS,
                cls.FEATURE_STORAGE,
                cls.FEATURE_REGISTRY,
                cls.FEATURE_CONFIGURATION,
                cls.FEATURE_ENCRYPTION,
                cls.FEATURE_AUDIT_LOGGING,
                cls.FEATURE_MFA,
                cls.FEATURE_SECURE_STORAGE,
                cls.FEATURE_CLOUD_INTEGRATION,
                cls.FEATURE_KUBERNETES_SUPPORT,
                cls.FEATURE_HIGH_AVAILABILITY,
                cls.FEATURE_DISTRIBUTED_CACHING,
                cls.FEATURE_UNLIMITED_STORAGE,
                cls.FEATURE_UNLIMITED_USERS,
                cls.FEATURE_UNLIMITED_PROJECTS
            }
        else:  # CUSTOM
            return set()

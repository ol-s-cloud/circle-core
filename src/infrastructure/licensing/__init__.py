"""Circle Core licensing module.

This module provides comprehensive license validation and management capabilities
for Circle Core applications and components.
"""

from typing import Dict, List, Optional, Any, Set

from .interface import (
    License, LicenseType, LicenseStatus, LicenseFeature,
    LicenseValidator, LicenseManager, LicenseStorage, LicenseRevocationList,
    InvalidLicenseError, LicenseExpiredError, LicenseFeatureNotAvailableError
)

from .models import (
    StandardFeature, StandardLicense, FeatureCatalog,
    generate_license_id
)

from .validation import CryptoLicenseValidator
from .storage import FileSystemLicenseStorage
from .revocation import FileSystemRevocationList
from .manager import CoreLicenseManager

# Set up default license manager
_default_manager = None


def get_license_manager() -> CoreLicenseManager:
    """Get the default license manager instance.
    
    Returns:
        Default license manager
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = CoreLicenseManager()
    
    return _default_manager


def set_license_manager(manager: CoreLicenseManager) -> None:
    """Set the default license manager instance.
    
    Args:
        manager: License manager to use as default
    """
    global _default_manager
    _default_manager = manager


def register_license(license_data: str) -> License:
    """Register a license with the system.
    
    Args:
        license_data: Serialized license data
        
    Returns:
        Registered license object
        
    Raises:
        InvalidLicenseError: If the license is invalid
    """
    return get_license_manager().register_license(license_data)


def has_feature(feature_id: str) -> bool:
    """Check if a feature is available with the current license.
    
    Args:
        feature_id: Feature ID to check
        
    Returns:
        True if the feature is available, False otherwise
    """
    return get_license_manager().check_feature_access(feature_id)


def verify_feature(feature_id: str) -> None:
    """Verify access to a feature.
    
    This function raises an exception if the feature is not available.
    
    Args:
        feature_id: Feature ID to check
        
    Raises:
        LicenseFeatureNotAvailableError: If feature is not available
        InvalidLicenseError: If no valid license is active
        LicenseExpiredError: If the active license is expired
    """
    return get_license_manager().verify_feature_access(feature_id)


def get_active_license() -> Optional[License]:
    """Get the currently active license.
    
    Returns:
        Active license or None if no license is active
    """
    return get_license_manager().get_active_license()


def list_licenses() -> List[License]:
    """List all registered licenses.
    
    Returns:
        List of license objects
    """
    return get_license_manager().list_licenses()


# Common feature IDs for easy access
# Storage features
FEATURE_STORAGE = FeatureCatalog.FEATURE_STORAGE
FEATURE_SECURE_STORAGE = FeatureCatalog.FEATURE_SECURE_STORAGE
FEATURE_UNLIMITED_STORAGE = FeatureCatalog.FEATURE_UNLIMITED_STORAGE

# Registry features
FEATURE_REGISTRY = FeatureCatalog.FEATURE_REGISTRY

# Security features
FEATURE_ENCRYPTION = FeatureCatalog.FEATURE_ENCRYPTION
FEATURE_AUDIT_LOGGING = FeatureCatalog.FEATURE_AUDIT_LOGGING
FEATURE_MFA = FeatureCatalog.FEATURE_MFA

# Access features
FEATURE_API_ACCESS = FeatureCatalog.FEATURE_API_ACCESS
FEATURE_CLI_ACCESS = FeatureCatalog.FEATURE_CLI_ACCESS
FEATURE_CONFIGURATION = FeatureCatalog.FEATURE_CONFIGURATION

# Advanced features
FEATURE_CLOUD_INTEGRATION = FeatureCatalog.FEATURE_CLOUD_INTEGRATION
FEATURE_KUBERNETES_SUPPORT = FeatureCatalog.FEATURE_KUBERNETES_SUPPORT
FEATURE_HIGH_AVAILABILITY = FeatureCatalog.FEATURE_HIGH_AVAILABILITY
FEATURE_DISTRIBUTED_CACHING = FeatureCatalog.FEATURE_DISTRIBUTED_CACHING

# Usage limits
FEATURE_UNLIMITED_USERS = FeatureCatalog.FEATURE_UNLIMITED_USERS
FEATURE_UNLIMITED_PROJECTS = FeatureCatalog.FEATURE_UNLIMITED_PROJECTS

# Product-specific features
FEATURE_TRADING_BOT = FeatureCatalog.FEATURE_TRADING_BOT
FEATURE_MLOPS = FeatureCatalog.FEATURE_MLOPS
FEATURE_DATA_ANALYTICS = FeatureCatalog.FEATURE_DATA_ANALYTICS
FEATURE_PHARMACOVIGILANCE = FeatureCatalog.FEATURE_PHARMACOVIGILANCE
FEATURE_RHEO_ML = FeatureCatalog.FEATURE_RHEO_ML
FEATURE_CARBON_ANALYTICS = FeatureCatalog.FEATURE_CARBON_ANALYTICS

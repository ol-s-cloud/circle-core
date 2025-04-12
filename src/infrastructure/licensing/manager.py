"""License manager for the Circle Core licensing module.

This module provides the main interface for managing licenses.
"""

import json
import base64
import uuid
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta

from ...core.encryption import EncryptionService
from ...core.audit import AuditLogger
from .interface import (
    License, LicenseManager, LicenseValidator, LicenseStorage,
    LicenseType, LicenseStatus, LicenseFeature,
    InvalidLicenseError, LicenseExpiredError, LicenseFeatureNotAvailableError
)
from .models import StandardLicense, generate_license_id, FeatureCatalog
from .validation import CryptoLicenseValidator
from .storage import FileSystemLicenseStorage


class CoreLicenseManager(LicenseManager):
    """Core implementation of license manager."""
    
    def __init__(
        self,
        storage: Optional[LicenseStorage] = None,
        validator: Optional[LicenseValidator] = None,
        encryption_service: Optional[EncryptionService] = None,
        shared_secret: Optional[bytes] = None,
        audit_logger: Optional[AuditLogger] = None
    ):
        """Initialize the license manager.
        
        Args:
            storage: License storage (created if None)
            validator: License validator (created if None)
            encryption_service: Optional encryption service
            shared_secret: Optional shared secret for HMAC
            audit_logger: Optional audit logger
        """
        self.encryption_service = encryption_service
        self.audit_logger = audit_logger
        
        # Create default components if needed
        if not storage:
            self.storage = FileSystemLicenseStorage(
                audit_logger=audit_logger
            )
        else:
            self.storage = storage
        
        if not validator:
            self.validator = CryptoLicenseValidator(
                encryption_service=encryption_service,
                shared_secret=shared_secret,
                audit_logger=audit_logger
            )
        else:
            self.validator = validator
        
        # Cache for active license
        self._active_license_cache = None
    
    def load_license(self, license_data: str) -> License:
        """Load a license from its serialized form.
        
        Args:
            license_data: Serialized license data
            
        Returns:
            License object
            
        Raises:
            InvalidLicenseError: If the license is invalid
        """
        try:
            # Validate the license
            license_obj = self.validator.validate_license(license_data)
            
            # Log the license loading
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_loaded",
                    data={
                        "license_id": license_obj.id,
                        "licensee": license_obj.licensee,
                        "type": license_obj.type.name
                    }
                )
            
            return license_obj
        except InvalidLicenseError as e:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_load_failed",
                    data={"error": str(e)}
                )
            
            # Re-raise the exception
            raise
    
    def save_license(self, license_obj: License) -> str:
        """Save a license to its serialized form.
        
        Args:
            license_obj: License object
            
        Returns:
            Serialized license data
        """
        try:
            # Convert license to dictionary
            if isinstance(license_obj, StandardLicense):
                license_dict = license_obj.to_dict()
            else:
                # For other license types, convert to dict if possible
                if hasattr(license_obj, "to_dict"):
                    license_dict = license_obj.to_dict()
                else:
                    raise ValueError(f"Unsupported license type: {type(license_obj)}")
            
            # Convert to JSON and encode
            license_json = json.dumps(license_dict)
            license_base64 = base64.b64encode(license_json.encode("utf-8")).decode("utf-8")
            
            # Create a signature if we have encryption service
            if self.encryption_service:
                signature = self._sign_license_data(license_json)
            else:
                # Use a dummy signature for testing
                signature = base64.b64encode(b"test_signature").decode("utf-8")
            
            # Combine license data and signature
            license_data = f"{license_base64}.{signature}"
            
            # Log the license saving
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_saved",
                    data={
                        "license_id": license_obj.id,
                        "licensee": license_obj.licensee,
                        "type": license_obj.type.name if hasattr(license_obj.type, "name") else str(license_obj.type)
                    }
                )
            
            return license_data
        except Exception as e:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_save_failed",
                    data={
                        "license_id": license_obj.id if hasattr(license_obj, "id") else "unknown",
                        "error": str(e)
                    }
                )
            
            raise
    
    def _sign_license_data(self, license_data: str) -> str:
        """Sign license data.
        
        Args:
            license_data: License data JSON
            
        Returns:
            Base64-encoded signature
        """
        if not self.encryption_service:
            # Return a dummy signature for testing
            return base64.b64encode(b"test_signature").decode("utf-8")
        
        try:
            # Sign the data
            signature = self.encryption_service.sign(
                data=license_data.encode("utf-8"),
                key_id="license_signing_key"
            )
            
            # Encode the signature
            return base64.b64encode(signature).decode("utf-8")
        except Exception as e:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_signing_failed",
                    data={"error": str(e)}
                )
            
            # Return a dummy signature for testing
            return base64.b64encode(b"test_signature").decode("utf-8")
    
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
        try:
            # Generate license ID
            license_id = generate_license_id()
            
            # Set issue date
            issue_date = datetime.now()
            
            # Set expiry date if duration provided
            expiry_date = None
            if duration:
                expiry_date = issue_date + duration
            
            # Create the license
            license_obj = StandardLicense(
                license_id=license_id,
                license_type=license_type,
                licensee=licensee,
                issue_date=issue_date,
                expiry_date=expiry_date,
                features=features,
                custom_data=custom_data
            )
            
            # Store the license
            self.storage.store_license(license_obj)
            
            # Log the license generation
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_generated",
                    data={
                        "license_id": license_id,
                        "licensee": licensee,
                        "type": license_type.name,
                        "features": list(features),
                        "duration": str(duration) if duration else "unlimited",
                        "expiry_date": expiry_date.isoformat() if expiry_date else None
                    }
                )
            
            return license_obj
        except Exception as e:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_generation_failed",
                    data={
                        "licensee": licensee,
                        "type": license_type.name if hasattr(license_type, "name") else str(license_type),
                        "error": str(e)
                    }
                )
            
            raise
    
    def get_active_license(self) -> Optional[License]:
        """Get the currently active license.
        
        Returns:
            Active license or None if no license is active
        """
        # Use cached license if available
        if self._active_license_cache is not None:
            # Check if the cached license is still valid
            if self._active_license_cache.is_valid():
                return self._active_license_cache
        
        # Get license from storage
        license_obj = self.storage.retrieve_active_license()
        
        # Update cache and return
        self._active_license_cache = license_obj
        return license_obj
    
    def check_feature_access(self, feature_id: str) -> bool:
        """Check if a feature is accessible with the current license.
        
        Args:
            feature_id: ID of the feature to check
            
        Returns:
            True if the feature is accessible, False otherwise
        """
        # Get active license
        license_obj = self.get_active_license()
        
        # If no active license, access denied
        if not license_obj:
            return False
        
        # Check if the license has the feature
        return license_obj.has_feature(feature_id)
    
    def register_license(self, license_data: str) -> License:
        """Register a license with the system.
        
        Args:
            license_data: Serialized license data
            
        Returns:
            Registered license object
            
        Raises:
            InvalidLicenseError: If the license is invalid
        """
        try:
            # Load and validate the license
            license_obj = self.load_license(license_data)
            
            # Store the license
            self.storage.store_license(license_obj)
            
            # Make it the active license
            self.storage.set_active_license(license_obj.id)
            
            # Update cache
            self._active_license_cache = license_obj
            
            # Log the license registration
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_registered",
                    data={
                        "license_id": license_obj.id,
                        "licensee": license_obj.licensee,
                        "type": license_obj.type.name,
                        "features": list(license_obj.features)
                    }
                )
            
            return license_obj
        except Exception as e:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_registration_failed",
                    data={"error": str(e)}
                )
            
            # Re-raise as InvalidLicenseError
            if not isinstance(e, InvalidLicenseError):
                raise InvalidLicenseError(str(e))
            else:
                raise
    
    def generate_trial_license(
        self,
        licensee: str,
        duration: timedelta = timedelta(days=30),
        custom_data: Optional[Dict[str, Any]] = None
    ) -> License:
        """Generate a trial license.
        
        Args:
            licensee: Name of the licensee
            duration: Trial duration (default: 30 days)
            custom_data: Optional custom data
            
        Returns:
            Trial license object
        """
        # Get trial features
        features = FeatureCatalog.get_features_for_license_type(LicenseType.TRIAL)
        
        # Generate the license
        return self.generate_license(
            licensee=licensee,
            license_type=LicenseType.TRIAL,
            features=features,
            duration=duration,
            custom_data=custom_data
        )
    
    def generate_standard_license(
        self,
        licensee: str,
        duration: Optional[timedelta] = None,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> License:
        """Generate a standard license.
        
        Args:
            licensee: Name of the licensee
            duration: Optional license duration
            custom_data: Optional custom data
            
        Returns:
            Standard license object
        """
        # Get standard features
        features = FeatureCatalog.get_features_for_license_type(LicenseType.STANDARD)
        
        # Generate the license
        return self.generate_license(
            licensee=licensee,
            license_type=LicenseType.STANDARD,
            features=features,
            duration=duration,
            custom_data=custom_data
        )
    
    def generate_professional_license(
        self,
        licensee: str,
        duration: Optional[timedelta] = None,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> License:
        """Generate a professional license.
        
        Args:
            licensee: Name of the licensee
            duration: Optional license duration
            custom_data: Optional custom data
            
        Returns:
            Professional license object
        """
        # Get professional features
        features = FeatureCatalog.get_features_for_license_type(LicenseType.PROFESSIONAL)
        
        # Generate the license
        return self.generate_license(
            licensee=licensee,
            license_type=LicenseType.PROFESSIONAL,
            features=features,
            duration=duration,
            custom_data=custom_data
        )
    
    def generate_enterprise_license(
        self,
        licensee: str,
        duration: Optional[timedelta] = None,
        custom_data: Optional[Dict[str, Any]] = None
    ) -> License:
        """Generate an enterprise license.
        
        Args:
            licensee: Name of the licensee
            duration: Optional license duration
            custom_data: Optional custom data
            
        Returns:
            Enterprise license object
        """
        # Get enterprise features
        features = FeatureCatalog.get_features_for_license_type(LicenseType.ENTERPRISE)
        
        # Generate the license
        return self.generate_license(
            licensee=licensee,
            license_type=LicenseType.ENTERPRISE,
            features=features,
            duration=duration,
            custom_data=custom_data
        )
    
    def get_feature_list(self) -> Dict[str, LicenseFeature]:
        """Get a list of all available features.
        
        Returns:
            Dictionary mapping feature IDs to feature objects
        """
        return FeatureCatalog.get_all_features()
    
    def get_license_types(self) -> List[LicenseType]:
        """Get a list of all license types.
        
        Returns:
            List of license types
        """
        return list(LicenseType)
    
    def list_licenses(self) -> List[License]:
        """List all registered licenses.
        
        Returns:
            List of license objects
        """
        return self.storage.list_licenses()
    
    def delete_license(self, license_id: str) -> bool:
        """Delete a license.
        
        Args:
            license_id: License ID
            
        Returns:
            True if successful, False otherwise
        """
        # Clear cache if this is the active license
        if (self._active_license_cache 
                and self._active_license_cache.id == license_id):
            self._active_license_cache = None
        
        # Delete the license
        return self.storage.delete_license(license_id)
    
    def set_active_license(self, license_id: str) -> bool:
        """Set the active license.
        
        Args:
            license_id: License ID
            
        Returns:
            True if successful, False otherwise
        """
        # Clear cache
        self._active_license_cache = None
        
        # Set active license
        return self.storage.set_active_license(license_id)
    
    def verify_feature_access(self, feature_id: str) -> None:
        """Verify access to a feature.
        
        Args:
            feature_id: ID of the feature to check
            
        Raises:
            LicenseFeatureNotAvailableError: If feature is not available
            InvalidLicenseError: If no valid license is active
            LicenseExpiredError: If the active license is expired
        """
        # Get active license
        license_obj = self.get_active_license()
        
        # Check if license exists
        if not license_obj:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="feature_access_denied",
                    data={
                        "feature_id": feature_id,
                        "reason": "No active license"
                    }
                )
            
            raise InvalidLicenseError("No active license")
        
        # Check if license is valid
        if not license_obj.is_valid():
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="feature_access_denied",
                    data={
                        "feature_id": feature_id,
                        "license_id": license_obj.id,
                        "reason": f"License status is {license_obj.status.name}"
                    }
                )
            
            if license_obj.is_expired():
                raise LicenseExpiredError("License has expired")
            else:
                raise InvalidLicenseError(f"License is not valid: {license_obj.status.name}")
        
        # Check if license has the feature
        if not license_obj.has_feature(feature_id):
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="feature_access_denied",
                    data={
                        "feature_id": feature_id,
                        "license_id": license_obj.id,
                        "license_type": license_obj.type.name,
                        "reason": "Feature not included in license"
                    }
                )
            
            raise LicenseFeatureNotAvailableError(
                f"Feature '{feature_id}' is not included in the current license"
            )
        
        # Log successful feature access
        if self.audit_logger:
            self.audit_logger.log_event(
                event_type="feature_access_granted",
                data={
                    "feature_id": feature_id,
                    "license_id": license_obj.id,
                    "license_type": license_obj.type.name
                }
            )

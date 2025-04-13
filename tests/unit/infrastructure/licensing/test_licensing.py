"""Unit tests for the Circle Core licensing module.

This module contains tests for the licensing functionality.
"""

import unittest
import tempfile
import os
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.infrastructure.licensing import (
    LicenseType, LicenseStatus, StandardLicense, 
    CoreLicenseManager, FeatureCatalog,
    InvalidLicenseError, LicenseExpiredError, LicenseFeatureNotAvailableError
)
from src.infrastructure.storage import StorageManager


class TestLicensing(unittest.TestCase):
    """Test cases for the licensing module."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for storage
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Create a storage manager
        self.storage_manager = StorageManager()
        self.storage_manager.create_file_system_backend(
            "test_storage",
            self.temp_dir.name
        )
        
        # Create a license manager
        self.license_manager = CoreLicenseManager(
            encryption_service=None,  # No encryption for testing
            shared_secret=b"test_secret"  # Use a simple shared secret
        )
        
        # Sample license data
        self.licensee = "Test User"
        self.license_type = LicenseType.STANDARD
        self.duration = timedelta(days=30)
        self.features = FeatureCatalog.get_features_for_license_type(self.license_type)
    
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    def test_license_generation(self):
        """Test license generation."""
        # Generate a license
        license_obj = self.license_manager.generate_license(
            licensee=self.licensee,
            license_type=self.license_type,
            features=self.features,
            duration=self.duration
        )
        
        # Check license properties
        self.assertEqual(license_obj.licensee, self.licensee)
        self.assertEqual(license_obj.type, self.license_type)
        self.assertEqual(license_obj.status, LicenseStatus.VALID)
        self.assertIsNotNone(license_obj.id)
        self.assertIsNotNone(license_obj.issue_date)
        self.assertIsNotNone(license_obj.expiry_date)
        self.assertEqual(license_obj.features, self.features)
    
    def test_license_serialization(self):
        """Test license serialization and deserialization."""
        # Generate a license
        license_obj = self.license_manager.generate_license(
            licensee=self.licensee,
            license_type=self.license_type,
            features=self.features,
            duration=self.duration
        )
        
        # Serialize the license
        license_data = self.license_manager.save_license(license_obj)
        
        # Deserialize the license
        loaded_license = self.license_manager.load_license(license_data)
        
        # Check properties match
        self.assertEqual(loaded_license.id, license_obj.id)
        self.assertEqual(loaded_license.licensee, license_obj.licensee)
        self.assertEqual(loaded_license.type, license_obj.type)
        self.assertEqual(loaded_license.features, license_obj.features)
    
    def test_license_registration(self):
        """Test license registration."""
        # Generate a license
        license_obj = self.license_manager.generate_license(
            licensee=self.licensee,
            license_type=self.license_type,
            features=self.features,
            duration=self.duration
        )
        
        # Serialize the license
        license_data = self.license_manager.save_license(license_obj)
        
        # Register the license
        registered_license = self.license_manager.register_license(license_data)
        
        # Check active license
        active_license = self.license_manager.get_active_license()
        self.assertIsNotNone(active_license)
        self.assertEqual(active_license.id, license_obj.id)
    
    def test_feature_access(self):
        """Test feature access checking."""
        # Generate a license with specific features
        test_features = {FeatureCatalog.FEATURE_STORAGE, FeatureCatalog.FEATURE_ENCRYPTION}
        license_obj = self.license_manager.generate_license(
            licensee=self.licensee,
            license_type=LicenseType.CUSTOM,
            features=test_features,
            duration=self.duration
        )
        
        # Serialize and register the license
        license_data = self.license_manager.save_license(license_obj)
        self.license_manager.register_license(license_data)
        
        # Check feature access
        self.assertTrue(self.license_manager.check_feature_access(FeatureCatalog.FEATURE_STORAGE))
        self.assertTrue(self.license_manager.check_feature_access(FeatureCatalog.FEATURE_ENCRYPTION))
        self.assertFalse(self.license_manager.check_feature_access(FeatureCatalog.FEATURE_REGISTRY))
        
        # Verify feature access
        self.license_manager.verify_feature_access(FeatureCatalog.FEATURE_STORAGE)  # Should not raise
        
        # Should raise for unavailable feature
        with self.assertRaises(LicenseFeatureNotAvailableError):
            self.license_manager.verify_feature_access(FeatureCatalog.FEATURE_REGISTRY)
    
    def test_expired_license(self):
        """Test expired license detection."""
        # Generate a license that is already expired
        expired_license = StandardLicense(
            license_id="expired_test",
            license_type=self.license_type,
            licensee=self.licensee,
            issue_date=datetime.now() - timedelta(days=60),
            expiry_date=datetime.now() - timedelta(days=30),
            features=self.features
        )
        
        # Check status
        self.assertEqual(expired_license.status, LicenseStatus.EXPIRED)
        self.assertTrue(expired_license.is_expired())
        self.assertFalse(expired_license.is_valid())
    
    def test_license_storage(self):
        """Test license storage and retrieval."""
        # Generate a license
        license_obj = self.license_manager.generate_license(
            licensee=self.licensee,
            license_type=self.license_type,
            features=self.features,
            duration=self.duration
        )
        
        # Store should happen automatically during generation
        # Retrieve the license
        retrieved_license = self.license_manager.storage.retrieve_license(license_obj.id)
        
        # Check properties match
        self.assertIsNotNone(retrieved_license)
        self.assertEqual(retrieved_license.id, license_obj.id)
        self.assertEqual(retrieved_license.licensee, license_obj.licensee)
    
    def test_trial_license(self):
        """Test trial license generation."""
        # Generate a trial license
        trial_license = self.license_manager.generate_trial_license(
            licensee=self.licensee
        )
        
        # Check properties
        self.assertEqual(trial_license.type, LicenseType.TRIAL)
        self.assertEqual(trial_license.status, LicenseStatus.TRIAL)
        self.assertTrue(trial_license.is_valid())
        
        # Check features
        expected_features = FeatureCatalog.get_features_for_license_type(LicenseType.TRIAL)
        self.assertEqual(trial_license.features, expected_features)
    
    def test_license_listing(self):
        """Test license listing."""
        # Generate multiple licenses
        license1 = self.license_manager.generate_license(
            licensee=self.licensee,
            license_type=self.license_type,
            features=self.features,
            duration=self.duration
        )
        
        license2 = self.license_manager.generate_trial_license(
            licensee="Trial User"
        )
        
        # List licenses
        licenses = self.license_manager.list_licenses()
        
        # Check results
        self.assertGreaterEqual(len(licenses), 2)
        license_ids = [license.id for license in licenses]
        self.assertIn(license1.id, license_ids)
        self.assertIn(license2.id, license_ids)


if __name__ == "__main__":
    unittest.main()

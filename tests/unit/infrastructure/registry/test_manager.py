"""Unit tests for the registry manager.

This module contains tests for the registry manager functionality.
"""

import unittest
import tempfile
import os
import zipfile
import json
from io import BytesIO
from unittest.mock import MagicMock, patch

from src.infrastructure.registry.manager import CoreRegistryManager
from src.infrastructure.storage import StorageManager


class TestRegistryManager(unittest.TestCase):
    """Test cases for the registry manager."""
    
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
        
        # Create a registry manager
        self.registry_manager = CoreRegistryManager(
            storage_manager=self.storage_manager,
            storage_backend="test_storage",
            registry_prefix="test_registry/"
        )
        
        # Initialize the registry
        self.registry_manager.initialize()
        
        # Sample package metadata
        self.sample_metadata = {
            "name": "sample-package",
            "version": "1.0.0",
            "description": "A sample package for testing",
            "author": "Test Author",
            "dependencies": {
                "dep-package": ">=0.5.0"
            },
            "tags": ["test", "sample"]
        }
        
        # Create a sample package
        self.sample_package = self._create_sample_package(
            "sample-package",
            "1.0.0",
            self.sample_metadata
        )
    
    def tearDown(self):
        """Clean up after tests."""
        self.temp_dir.cleanup()
    
    def _create_sample_package(self, package_name, version, metadata):
        """Create a sample package file."""
        # Create an in-memory zip file
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            # Add metadata.json
            zip_file.writestr("metadata.json", json.dumps(metadata))
            
            # Add manifest.json with file info
            manifest = {
                "name": package_name,
                "version": version,
                "files": {
                    "metadata.json": {
                        "hash": "dummy_hash"
                    },
                    "manifest.json": {
                        "hash": "dummy_hash"
                    },
                    "sample_file.txt": {
                        "hash": "dummy_hash"
                    }
                }
            }
            zip_file.writestr("manifest.json", json.dumps(manifest))
            
            # Add a sample file
            zip_file.writestr("sample_file.txt", "This is a sample text file.")
        
        # Get the zip data
        zip_buffer.seek(0)
        return zip_buffer.read()
    
    def test_publish_package(self):
        """Test publishing a package."""
        # Mock the validation provider to always return valid
        self.registry_manager.validation_provider.validate_metadata = MagicMock(
            return_value={"valid": True}
        )
        self.registry_manager.validation_provider.validate_package = MagicMock(
            return_value={"valid": True}
        )
        
        # Publish the package
        result = self.registry_manager.publish_package(
            "sample-package",
            "1.0.0",
            self.sample_package,
            self.sample_metadata
        )
        
        # Check if publication was successful
        self.assertTrue(result)
        
        # Check if the package metadata exists
        self.assertTrue(
            self.registry_manager.metadata_provider.package_exists(
                "sample-package", "1.0.0"
            )
        )
        
        # Check if the package file exists
        self.assertTrue(
            self.registry_manager.storage_provider.package_exists(
                "sample-package", "1.0.0"
            )
        )
    
    def test_download_package(self):
        """Test downloading a package."""
        # First publish a package
        self.test_publish_package()
        
        # Download the package
        package_data = self.registry_manager.download_package(
            "sample-package", "1.0.0"
        )
        
        # Check if the package data matches
        self.assertEqual(package_data, self.sample_package)
    
    def test_get_package_info(self):
        """Test retrieving package information."""
        # First publish a package
        self.test_publish_package()
        
        # Get package info
        info = self.registry_manager.get_package_info("sample-package", "1.0.0")
        
        # Check if the info contains expected fields
        self.assertEqual(info["name"], "sample-package")
        self.assertEqual(info["version"], "1.0.0")
        self.assertEqual(info["description"], "A sample package for testing")
        self.assertEqual(info["author"], "Test Author")
    
    def test_search_packages(self):
        """Test searching for packages."""
        # First publish a package
        self.test_publish_package()
        
        # Search for the package
        results = self.registry_manager.search_packages("sample")
        
        # Check if the package is found
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "sample-package")
    
    def test_delete_package(self):
        """Test deleting a package."""
        # First publish a package
        self.test_publish_package()
        
        # Delete the package
        result = self.registry_manager.delete_package("sample-package", "1.0.0")
        
        # Check if deletion was successful
        self.assertTrue(result)
        
        # Check if the package no longer exists
        self.assertFalse(
            self.registry_manager.metadata_provider.package_exists(
                "sample-package", "1.0.0"
            )
        )
        
        self.assertFalse(
            self.registry_manager.storage_provider.package_exists(
                "sample-package", "1.0.0"
            )
        )
    
    def test_get_package_versions(self):
        """Test retrieving package versions."""
        # First publish a package
        self.test_publish_package()
        
        # Publish another version
        updated_metadata = self.sample_metadata.copy()
        updated_metadata["version"] = "1.1.0"
        updated_package = self._create_sample_package(
            "sample-package",
            "1.1.0",
            updated_metadata
        )
        
        # Mock the validation provider again
        self.registry_manager.validation_provider.validate_metadata = MagicMock(
            return_value={"valid": True}
        )
        self.registry_manager.validation_provider.validate_package = MagicMock(
            return_value={"valid": True}
        )
        
        # Publish the new version
        self.registry_manager.publish_package(
            "sample-package",
            "1.1.0",
            updated_package,
            updated_metadata
        )
        
        # Get versions
        versions = self.registry_manager.get_package_versions("sample-package")
        
        # Check if both versions are listed
        self.assertEqual(len(versions), 2)
        self.assertIn("1.0.0", versions)
        self.assertIn("1.1.0", versions)


if __name__ == "__main__":
    unittest.main()

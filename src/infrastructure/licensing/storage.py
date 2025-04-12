"""License storage for the Circle Core licensing module.

This module provides mechanisms for storing and retrieving licenses.
"""

import os
import json
from typing import Dict, List, Optional, Any, Set
from pathlib import Path

from ...core.audit import AuditLogger
from ..storage import StorageManager, StorageVisibility
from .interface import License, LicenseStorage, InvalidLicenseError
from .models import StandardLicense


class FileSystemLicenseStorage(LicenseStorage):
    """File system implementation of license storage."""
    
    def __init__(
        self,
        storage_manager: Optional[StorageManager] = None,
        storage_backend: str = "default",
        licenses_prefix: str = "licenses/",
        audit_logger: Optional[AuditLogger] = None
    ):
        """Initialize the file system license storage.
        
        Args:
            storage_manager: Storage manager (created if None)
            storage_backend: Storage backend name
            licenses_prefix: Prefix for license storage paths
            audit_logger: Optional audit logger
        """
        # Create default storage manager if needed
        if not storage_manager:
            # Create a default storage manager
            home_dir = os.path.expanduser("~")
            licenses_dir = os.path.join(home_dir, ".circle-core", "licenses")
            os.makedirs(licenses_dir, exist_ok=True)
            
            from ..storage import StorageManager
            storage_manager = StorageManager()
            storage_manager.create_file_system_backend(
                "license_storage",
                licenses_dir
            )
            storage_backend = "license_storage"
        
        self.storage_manager = storage_manager
        self.storage_backend = storage_backend
        self.licenses_prefix = licenses_prefix
        self.audit_logger = audit_logger
        
        # Ensure licenses directory exists
        self._ensure_storage_exists()
    
    def _ensure_storage_exists(self) -> None:
        """Ensure the licenses storage exists."""
        if not self.storage_manager.exists(self.licenses_prefix, self.storage_backend):
            # Create placeholder file to ensure the directory exists
            self.storage_manager.put_object(
                f"{self.licenses_prefix}.placeholder",
                data="",
                content_type="text/plain",
                backend=self.storage_backend
            )
            
            # Create active license pointer
            self.storage_manager.put_object(
                f"{self.licenses_prefix}active_license",
                data="",
                content_type="text/plain",
                backend=self.storage_backend
            )
    
    def _get_license_path(self, license_id: str) -> str:
        """Get the storage path for a license.
        
        Args:
            license_id: License ID
            
        Returns:
            Storage path
        """
        return f"{self.licenses_prefix}{license_id}.json"
    
    def _get_active_license_path(self) -> str:
        """Get the storage path for the active license pointer.
        
        Returns:
            Storage path
        """
        return f"{self.licenses_prefix}active_license"
    
    def store_license(self, license_obj: License) -> bool:
        """Store a license.
        
        Args:
            license_obj: License object
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert license to JSON
            if isinstance(license_obj, StandardLicense):
                license_data = json.dumps(license_obj.to_dict())
            else:
                # For other license types, convert to dict if possible
                if hasattr(license_obj, "to_dict"):
                    license_data = json.dumps(license_obj.to_dict())
                else:
                    raise ValueError(f"Unsupported license type: {type(license_obj)}")
            
            # Store the license
            license_path = self._get_license_path(license_obj.id)
            self.storage_manager.put_object(
                license_path,
                data=license_data,
                content_type="application/json",
                backend=self.storage_backend
            )
            
            # Log the license storage
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_stored",
                    data={
                        "license_id": license_obj.id,
                        "licensee": license_obj.licensee,
                        "type": license_obj.type.name if hasattr(license_obj.type, "name") else str(license_obj.type)
                    }
                )
            
            return True
        except Exception as e:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_storage_failed",
                    data={
                        "license_id": license_obj.id if hasattr(license_obj, "id") else "unknown",
                        "error": str(e)
                    }
                )
            return False
    
    def retrieve_license(self, license_id: str) -> Optional[License]:
        """Retrieve a license by ID.
        
        Args:
            license_id: License ID
            
        Returns:
            License object or None if not found
        """
        try:
            # Get license path
            license_path = self._get_license_path(license_id)
            
            # Check if license exists
            if not self.storage_manager.exists(license_path, self.storage_backend):
                return None
            
            # Retrieve license data
            license_obj = self.storage_manager.get_object(license_path, self.storage_backend)
            license_data = license_obj.data.decode("utf-8") if isinstance(license_obj.data, bytes) else license_obj.data
            
            # Parse license data
            license_dict = json.loads(license_data)
            
            # Create license object
            license = StandardLicense.from_dict(license_dict)
            
            # Log the license retrieval
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_retrieved",
                    data={
                        "license_id": license.id,
                        "licensee": license.licensee,
                        "type": license.type.name
                    }
                )
            
            return license
        except Exception as e:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_retrieval_failed",
                    data={
                        "license_id": license_id,
                        "error": str(e)
                    }
                )
            return None
    
    def retrieve_active_license(self) -> Optional[License]:
        """Retrieve the currently active license.
        
        Returns:
            Active license or None if no license is active
        """
        try:
            # Get active license path
            active_license_path = self._get_active_license_path()
            
            # Check if active license pointer exists
            if not self.storage_manager.exists(active_license_path, self.storage_backend):
                return None
            
            # Get active license ID
            active_license_obj = self.storage_manager.get_object(active_license_path, self.storage_backend)
            active_license_id = active_license_obj.data.decode("utf-8") if isinstance(active_license_obj.data, bytes) else active_license_obj.data
            
            # If no active license is set, return None
            if not active_license_id:
                return None
            
            # Retrieve the active license
            return self.retrieve_license(active_license_id)
        except Exception as e:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="active_license_retrieval_failed",
                    data={"error": str(e)}
                )
            return None
    
    def set_active_license(self, license_id: str) -> bool:
        """Set the active license.
        
        Args:
            license_id: License ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if license exists
            if not self.storage_manager.exists(self._get_license_path(license_id), self.storage_backend):
                # Log the error
                if self.audit_logger:
                    self.audit_logger.log_event(
                        event_type="set_active_license_failed",
                        data={
                            "license_id": license_id,
                            "error": "License not found"
                        }
                    )
                return False
            
            # Set active license
            active_license_path = self._get_active_license_path()
            self.storage_manager.put_object(
                active_license_path,
                data=license_id,
                content_type="text/plain",
                backend=self.storage_backend
            )
            
            # Log the active license change
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="active_license_set",
                    data={"license_id": license_id}
                )
            
            return True
        except Exception as e:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="set_active_license_failed",
                    data={
                        "license_id": license_id,
                        "error": str(e)
                    }
                )
            return False
    
    def list_licenses(self) -> List[License]:
        """List all stored licenses.
        
        Returns:
            List of license objects
        """
        try:
            # Ensure directory exists
            self._ensure_storage_exists()
            
            # List license files
            licenses = []
            objects = self.storage_manager.list_objects(
                prefix=self.licenses_prefix,
                backend=self.storage_backend
            )
            
            for obj in objects:
                # Skip non-license files
                if not obj.key.endswith(".json") or obj.key == f"{self.licenses_prefix}.placeholder":
                    continue
                
                # Extract license ID from path
                license_id = os.path.basename(obj.key)[:-5]  # Remove .json extension
                
                # Retrieve license
                license_obj = self.retrieve_license(license_id)
                if license_obj:
                    licenses.append(license_obj)
            
            # Log the licenses retrieval
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="licenses_listed",
                    data={"count": len(licenses)}
                )
            
            return licenses
        except Exception as e:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="list_licenses_failed",
                    data={"error": str(e)}
                )
            return []
    
    def delete_license(self, license_id: str) -> bool:
        """Delete a license.
        
        Args:
            license_id: License ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get license path
            license_path = self._get_license_path(license_id)
            
            # Check if license exists
            if not self.storage_manager.exists(license_path, self.storage_backend):
                return False
            
            # Check if this is the active license
            active_license = self.retrieve_active_license()
            if active_license and active_license.id == license_id:
                # Clear active license
                self.storage_manager.put_object(
                    self._get_active_license_path(),
                    data="",
                    content_type="text/plain",
                    backend=self.storage_backend
                )
            
            # Delete the license
            self.storage_manager.delete_object(license_path, self.storage_backend)
            
            # Log the license deletion
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_deleted",
                    data={"license_id": license_id}
                )
            
            return True
        except Exception as e:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_deletion_failed",
                    data={
                        "license_id": license_id,
                        "error": str(e)
                    }
                )
            return False

"""License revocation for the Circle Core licensing module.

This module provides mechanisms for tracking revoked licenses.
"""

import os
import json
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
import urllib.request
import ssl

from ...core.audit import AuditLogger
from ..storage import StorageManager
from .interface import LicenseRevocationList


class FileSystemRevocationList(LicenseRevocationList):
    """File system implementation of license revocation list."""
    
    def __init__(
        self,
        storage_manager: Optional[StorageManager] = None,
        storage_backend: str = "default",
        revocation_prefix: str = "licenses/revoked/",
        revocation_list_file: str = "licenses/revoked_list.json",
        audit_logger: Optional[AuditLogger] = None,
        remote_url: Optional[str] = None
    ):
        """Initialize the file system revocation list.
        
        Args:
            storage_manager: Storage manager (created if None)
            storage_backend: Storage backend name
            revocation_prefix: Prefix for revocation storage paths
            revocation_list_file: Path to the revocation list file
            audit_logger: Optional audit logger
            remote_url: Optional URL for remote revocation list
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
                "revocation_storage",
                licenses_dir
            )
            storage_backend = "revocation_storage"
        
        self.storage_manager = storage_manager
        self.storage_backend = storage_backend
        self.revocation_prefix = revocation_prefix
        self.revocation_list_file = revocation_list_file
        self.audit_logger = audit_logger
        self.remote_url = remote_url
        
        # Ensure revocation directory exists
        self._ensure_storage_exists()
        
        # Load the revocation list
        self._revocation_list = self._load_revocation_list()
    
    def _ensure_storage_exists(self) -> None:
        """Ensure the revocation storage exists."""
        if not self.storage_manager.exists(self.revocation_prefix, self.storage_backend):
            # Create placeholder file to ensure the directory exists
            self.storage_manager.put_object(
                f"{self.revocation_prefix}.placeholder",
                data="",
                content_type="text/plain",
                backend=self.storage_backend
            )
        
        # Ensure revocation list file exists
        if not self.storage_manager.exists(self.revocation_list_file, self.storage_backend):
            # Create empty revocation list
            self.storage_manager.put_object(
                self.revocation_list_file,
                data=json.dumps({}),
                content_type="application/json",
                backend=self.storage_backend
            )
    
    def _load_revocation_list(self) -> Dict[str, Dict[str, Any]]:
        """Load the revocation list from storage.
        
        Returns:
            Dictionary mapping license IDs to revocation info
        """
        try:
            # Get revocation list file
            revocation_obj = self.storage_manager.get_object(
                self.revocation_list_file,
                self.storage_backend
            )
            
            # Parse JSON
            revocation_data = revocation_obj.data.decode("utf-8") if isinstance(revocation_obj.data, bytes) else revocation_obj.data
            revocation_list = json.loads(revocation_data)
            
            return revocation_list
        except Exception as e:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="revocation_list_load_failed",
                    data={"error": str(e)}
                )
            
            # Return empty list
            return {}
    
    def _save_revocation_list(self) -> bool:
        """Save the revocation list to storage.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to JSON
            revocation_data = json.dumps(self._revocation_list)
            
            # Save to storage
            self.storage_manager.put_object(
                self.revocation_list_file,
                data=revocation_data,
                content_type="application/json",
                backend=self.storage_backend
            )
            
            return True
        except Exception as e:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="revocation_list_save_failed",
                    data={"error": str(e)}
                )
            
            return False
    
    def add_to_revocation_list(self, license_id: str, reason: str) -> bool:
        """Add a license to the revocation list.
        
        Args:
            license_id: License ID
            reason: Reason for revocation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add to revocation list
            self._revocation_list[license_id] = {
                "reason": reason,
                "revoked_at": datetime.now().isoformat()
            }
            
            # Save the updated list
            success = self._save_revocation_list()
            
            # Log the revocation
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_revoked",
                    data={
                        "license_id": license_id,
                        "reason": reason,
                        "success": success
                    }
                )
            
            return success
        except Exception as e:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_revocation_failed",
                    data={
                        "license_id": license_id,
                        "reason": reason,
                        "error": str(e)
                    }
                )
            
            return False
    
    def remove_from_revocation_list(self, license_id: str) -> bool:
        """Remove a license from the revocation list.
        
        Args:
            license_id: License ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if license is in revocation list
            if license_id not in self._revocation_list:
                return False
            
            # Remove from revocation list
            del self._revocation_list[license_id]
            
            # Save the updated list
            success = self._save_revocation_list()
            
            # Log the un-revocation
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_unrevoked",
                    data={
                        "license_id": license_id,
                        "success": success
                    }
                )
            
            return success
        except Exception as e:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_unrevocation_failed",
                    data={
                        "license_id": license_id,
                        "error": str(e)
                    }
                )
            
            return False
    
    def is_revoked(self, license_id: str) -> bool:
        """Check if a license is revoked.
        
        Args:
            license_id: License ID
            
        Returns:
            True if revoked, False otherwise
        """
        return license_id in self._revocation_list
    
    def get_revocation_reason(self, license_id: str) -> Optional[str]:
        """Get the reason for license revocation.
        
        Args:
            license_id: License ID
            
        Returns:
            Reason string or None if not revoked
        """
        if license_id not in self._revocation_list:
            return None
        
        return self._revocation_list[license_id].get("reason")
    
    def update_from_remote(self) -> bool:
        """Update the revocation list from a remote source.
        
        Returns:
            True if update successful, False otherwise
        """
        if not self.remote_url:
            # No remote URL configured
            return False
        
        try:
            # Create SSL context that doesn't verify the certificate
            # This is for testing only - in production, proper certificate validation should be used
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # Download the revocation list
            with urllib.request.urlopen(self.remote_url, context=context) as response:
                remote_data = response.read().decode("utf-8")
            
            # Parse JSON
            remote_list = json.loads(remote_data)
            
            # Merge with local list
            for license_id, revocation_info in remote_list.items():
                # Only add if not already in local list
                if license_id not in self._revocation_list:
                    self._revocation_list[license_id] = revocation_info
            
            # Save the updated list
            success = self._save_revocation_list()
            
            # Log the update
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="revocation_list_updated",
                    data={
                        "url": self.remote_url,
                        "added_count": len(remote_list) - len(self._revocation_list),
                        "success": success
                    }
                )
            
            return success
        except Exception as e:
            # Log the error
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="revocation_list_update_failed",
                    data={
                        "url": self.remote_url,
                        "error": str(e)
                    }
                )
            
            return False
    
    def get_all_revoked_licenses(self) -> Dict[str, Dict[str, Any]]:
        """Get all revoked licenses.
        
        Returns:
            Dictionary mapping license IDs to revocation info
        """
        return self._revocation_list.copy()

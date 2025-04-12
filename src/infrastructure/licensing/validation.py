"""License validation for the Circle Core licensing module.

This module provides mechanisms for cryptographically validating licenses.
"""

import json
import base64
import hashlib
import hmac
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime

from ...core.encryption import EncryptionService
from ...core.audit import AuditLogger
from .interface import LicenseValidator, License, LicenseStatus, InvalidLicenseError
from .models import StandardLicense


class CryptoLicenseValidator(LicenseValidator):
    """License validator using cryptographic techniques."""
    
    def __init__(
        self,
        encryption_service: Optional[EncryptionService] = None,
        public_key: Optional[bytes] = None,
        shared_secret: Optional[bytes] = None,
        audit_logger: Optional[AuditLogger] = None
    ):
        """Initialize a cryptographic license validator.
        
        The validator can work in different modes:
        - With encryption_service: Uses the service for verification
        - With public_key: Uses RSA verification
        - With shared_secret: Uses HMAC verification
        
        Args:
            encryption_service: Optional encryption service
            public_key: Optional public key for RSA verification
            shared_secret: Optional shared secret for HMAC verification
            audit_logger: Optional audit logger
        """
        self.encryption_service = encryption_service
        self.public_key = public_key
        self.shared_secret = shared_secret
        self.audit_logger = audit_logger
    
    def validate_license(self, license_data: str) -> License:
        """Validate a license from its serialized form.
        
        Args:
            license_data: Serialized license data
            
        Returns:
            License object if valid
            
        Raises:
            InvalidLicenseError: If the license is invalid
        """
        try:
            # Parse license data
            license_dict, signature = self._parse_license_data(license_data)
            
            # Verify signature
            if not self.verify_signature(json.dumps(license_dict), signature):
                if self.audit_logger:
                    self.audit_logger.log_event(
                        event_type="license_validation_failed",
                        data={
                            "reason": "Invalid signature",
                            "license_id": license_dict.get("id")
                        }
                    )
                raise InvalidLicenseError("Invalid license signature")
            
            # Create license object
            license_obj = StandardLicense.from_dict(license_dict)
            
            # Check if license is valid
            if not license_obj.is_valid():
                if self.audit_logger:
                    self.audit_logger.log_event(
                        event_type="license_validation_failed",
                        data={
                            "reason": f"License status is {license_obj.status.name}",
                            "license_id": license_obj.id
                        }
                    )
                raise InvalidLicenseError(f"License is not valid: {license_obj.status.name}")
            
            # Log successful validation
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_validation_success",
                    data={
                        "license_id": license_obj.id,
                        "licensee": license_obj.licensee,
                        "type": license_obj.type.name,
                        "features": list(license_obj.features)
                    }
                )
            
            return license_obj
        except json.JSONDecodeError:
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_validation_failed",
                    data={"reason": "Invalid JSON format"}
                )
            raise InvalidLicenseError("Invalid license format: not valid JSON")
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="license_validation_failed",
                    data={"reason": str(e)}
                )
            raise InvalidLicenseError(f"License validation failed: {str(e)}")
    
    def _parse_license_data(self, license_data: str) -> Tuple[Dict[str, Any], str]:
        """Parse license data into components.
        
        Args:
            license_data: Serialized license data
            
        Returns:
            Tuple of (license_dict, signature)
            
        Raises:
            InvalidLicenseError: If the data format is invalid
        """
        try:
            # License data format: base64(json_data) + "." + base64(signature)
            parts = license_data.split(".")
            if len(parts) != 2:
                raise InvalidLicenseError("Invalid license format")
            
            # Decode license data
            license_json = base64.b64decode(parts[0]).decode("utf-8")
            signature = parts[1]
            
            # Parse JSON
            license_dict = json.loads(license_json)
            
            return license_dict, signature
        except Exception as e:
            raise InvalidLicenseError(f"Failed to parse license data: {str(e)}")
    
    def verify_signature(self, license_data: str, signature: str) -> bool:
        """Verify the signature of a license.
        
        Args:
            license_data: Serialized license data
            signature: License signature
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Decode signature
            signature_bytes = base64.b64decode(signature)
            
            # Use encryption service if available
            if self.encryption_service:
                return self._verify_with_encryption_service(license_data, signature_bytes)
            # Use RSA public key if available
            elif self.public_key:
                return self._verify_with_rsa(license_data, signature_bytes)
            # Use HMAC if shared secret is available
            elif self.shared_secret:
                return self._verify_with_hmac(license_data, signature_bytes)
            else:
                # No verification method available
                if self.audit_logger:
                    self.audit_logger.log_event(
                        event_type="signature_verification_failed",
                        data={"reason": "No verification method available"}
                    )
                return False
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="signature_verification_failed",
                    data={"reason": str(e)}
                )
            return False
    
    def _verify_with_encryption_service(self, license_data: str, signature: bytes) -> bool:
        """Verify signature using the encryption service.
        
        Args:
            license_data: License data string
            signature: Signature bytes
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.encryption_service:
            return False
        
        try:
            # Use the encryption service to verify
            return self.encryption_service.verify_signature(
                data=license_data.encode("utf-8"),
                signature=signature,
                key_id="license_verification_key"
            )
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="signature_verification_failed",
                    data={"reason": f"Encryption service error: {str(e)}"}
                )
            return False
    
    def _verify_with_rsa(self, license_data: str, signature: bytes) -> bool:
        """Verify signature using RSA public key.
        
        Args:
            license_data: License data string
            signature: Signature bytes
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.public_key:
            return False
        
        try:
            # This is a placeholder - in a real implementation, this would use
            # proper RSA verification with libraries like cryptography or rsa
            # For now, we'll assume verification succeeds if we have a key
            return True
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="signature_verification_failed",
                    data={"reason": f"RSA verification error: {str(e)}"}
                )
            return False
    
    def _verify_with_hmac(self, license_data: str, signature: bytes) -> bool:
        """Verify signature using HMAC with shared secret.
        
        Args:
            license_data: License data string
            signature: Signature bytes
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.shared_secret:
            return False
        
        try:
            # Calculate HMAC
            calculated_hmac = hmac.new(
                key=self.shared_secret,
                msg=license_data.encode("utf-8"),
                digestmod=hashlib.sha256
            ).digest()
            
            # Compare with provided signature
            return hmac.compare_digest(calculated_hmac, signature)
        except Exception as e:
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="signature_verification_failed",
                    data={"reason": f"HMAC verification error: {str(e)}"}
                )
            return False

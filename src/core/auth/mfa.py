"""Multi-Factor Authentication module for Circle Core Framework.

Provides TOTP (Time-based One-Time Password) implementation for enhanced authentication
security.
"""

import base64
import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple, Union
import qrcode
from io import BytesIO


class MFAType(Enum):
    """Enum representing supported MFA types."""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    RECOVERY_CODES = "recovery_codes"


@dataclass
class TOTPConfig:
    """TOTP configuration parameters."""
    digits: int = 6
    interval: int = 30
    algorithm: str = "sha1"
    issuer: str = "CircleCore"
    valid_window: int = 1  # Allow 1 interval before/after for clock skew


class MFAService:
    """Service for managing multi-factor authentication.

    Implements TOTP (RFC 6238) for secure second-factor authentication
    with configurable parameters.
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        totp_config: Optional[TOTPConfig] = None,
        backup_code_count: int = 10,
    ):
        """Initialize the MFA service.

        Args:
            storage_path: Path for storing MFA data (default: ~/.circle-core/auth/mfa)
            totp_config: TOTP configuration parameters
            backup_code_count: Number of backup codes to generate
        """
        self.storage_path = storage_path or os.path.expanduser("~/.circle-core/auth/mfa")
        os.makedirs(self.storage_path, exist_ok=True)
        
        self.totp_config = totp_config or TOTPConfig()
        self.backup_code_count = backup_code_count

    def generate_totp_secret(self) -> bytes:
        """Generate a secure random secret for TOTP.

        Returns:
            Random 32-byte secret
        """
        return os.urandom(32)

    def format_totp_secret(self, secret: bytes) -> str:
        """Format a binary secret as a Base32 string.

        Args:
            secret: Binary secret

        Returns:
            Base32 encoded string without padding
        """
        return base64.b32encode(secret).decode("utf-8").rstrip("=")

    def generate_totp_uri(self, username: str, secret: bytes, issuer: str = None) -> str:
        """Generate an otpauth URI for TOTP apps.

        Args:
            username: Username
            secret: Binary secret
            issuer: Optional issuer name (default: configured issuer)

        Returns:
            otpauth URI string for QR code generation
        """
        issuer = issuer or self.totp_config.issuer
        formatted_secret = self.format_totp_secret(secret)
        
        # Parameters for the URI
        params = {
            "secret": formatted_secret,
            "issuer": issuer,
            "algorithm": self.totp_config.algorithm.upper(),
            "digits": str(self.totp_config.digits),
            "period": str(self.totp_config.interval)
        }
        
        # Format parameters as a query string
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        
        # Format the complete URI
        label = f"{issuer}:{username}"
        uri = f"otpauth://totp/{label}?{query_string}"
        
        return uri

    def generate_totp_qr_code(self, username: str, secret: bytes, issuer: str = None) -> bytes:
        """Generate a QR code containing TOTP configuration.

        Args:
            username: Username
            secret: Binary secret
            issuer: Optional issuer name

        Returns:
            PNG image data as bytes
        """
        uri = self.generate_totp_uri(username, secret, issuer)
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        # Create an image from the QR code
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert image to bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        
        return buffer.getvalue()

    def generate_totp(self, secret: bytes, timestamp: int = None) -> str:
        """Generate a TOTP code for a given secret.

        Args:
            secret: Binary secret
            timestamp: Optional timestamp (default: current time)

        Returns:
            TOTP code as string
        """
        # Use current time if not specified
        if timestamp is None:
            timestamp = int(time.time())
        
        # Calculate number of time intervals since epoch
        intervals = timestamp // self.totp_config.interval
        
        # Convert intervals to bytes (big-endian)
        counter_bytes = intervals.to_bytes(8, byteorder="big")
        
        # Generate HMAC
        if self.totp_config.algorithm == "sha1":
            digest = hmac.new(secret, counter_bytes, hashlib.sha1).digest()
        elif self.totp_config.algorithm == "sha256":
            digest = hmac.new(secret, counter_bytes, hashlib.sha256).digest()
        elif self.totp_config.algorithm == "sha512":
            digest = hmac.new(secret, counter_bytes, hashlib.sha512).digest()
        else:
            raise ValueError(f"Unsupported algorithm: {self.totp_config.algorithm}")
        
        # Dynamic truncation
        offset = digest[-1] & 0x0F
        binary = ((digest[offset] & 0x7F) << 24 |
                  (digest[offset + 1] & 0xFF) << 16 |
                  (digest[offset + 2] & 0xFF) << 8 |
                  (digest[offset + 3] & 0xFF))
        
        # Generate code with specified number of digits
        code = binary % (10 ** self.totp_config.digits)
        return str(code).zfill(self.totp_config.digits)

    def verify_totp(self, secret: bytes, code: str, timestamp: int = None) -> bool:
        """Verify a TOTP code against a secret.

        Args:
            secret: Binary secret
            code: TOTP code
            timestamp: Optional timestamp (default: current time)

        Returns:
            True if code is valid, False otherwise
        """
        if timestamp is None:
            timestamp = int(time.time())
        
        # Check current interval and adjacent intervals (based on valid_window)
        for i in range(-self.totp_config.valid_window, self.totp_config.valid_window + 1):
            check_time = timestamp + (i * self.totp_config.interval)
            generated_code = self.generate_totp(secret, check_time)
            if generated_code == code:
                return True
                
        return False

    def generate_backup_codes(self) -> list:
        """Generate backup recovery codes.

        Returns:
            List of backup codes
        """
        backup_codes = []
        for _ in range(self.backup_code_count):
            # Generate 8-character alphanumeric code
            code_bytes = os.urandom(6)  # 6 bytes gives ~48 bits of entropy
            code = base64.b32encode(code_bytes).decode('utf-8')[:8].lower()
            
            # Format as xxxx-xxxx for easier reading
            formatted_code = f"{code[:4]}-{code[4:]}"
            backup_codes.append(formatted_code)
            
        return backup_codes

    def hash_backup_codes(self, backup_codes: list) -> list:
        """Create secure hashes of backup codes for storage.

        Args:
            backup_codes: List of backup codes

        Returns:
            List of hashed codes
        """
        hashed_codes = []
        for code in backup_codes:
            # Remove formatting
            code = code.replace("-", "")
            
            # Hash with random salt
            salt = os.urandom(16)
            hash_value = hashlib.pbkdf2_hmac(
                'sha256',
                code.encode('utf-8'),
                salt,
                100000,  # iterations
                32  # output length
            )
            
            # Store salt and hash
            hashed_codes.append({
                'salt': base64.b64encode(salt).decode('utf-8'),
                'hash': base64.b64encode(hash_value).decode('utf-8'),
                'used': False
            })
            
        return hashed_codes

    def verify_backup_code(self, code: str, hashed_codes: list) -> Tuple[bool, list]:
        """Verify a backup code against stored hashes.

        Args:
            code: Backup code
            hashed_codes: List of hashed codes

        Returns:
            Tuple of (success, updated_hashed_codes)
        """
        # Remove formatting
        code = code.replace("-", "")
        
        for i, hashed_code in enumerate(hashed_codes):
            # Skip already used codes
            if hashed_code.get('used', False):
                continue
                
            # Decode salt and hash
            salt = base64.b64decode(hashed_code['salt'])
            stored_hash = base64.b64decode(hashed_code['hash'])
            
            # Hash the provided code
            hash_value = hashlib.pbkdf2_hmac(
                'sha256',
                code.encode('utf-8'),
                salt,
                100000,  # iterations
                32  # output length
            )
            
            # Check if hashes match
            if hash_value == stored_hash:
                # Mark code as used
                hashed_codes[i]['used'] = True
                return True, hashed_codes
                
        return False, hashed_codes

    def setup_mfa_for_user(
        self, username: str, mfa_type: MFAType = MFAType.TOTP
    ) -> Dict:
        """Set up MFA for a user.

        Args:
            username: Username
            mfa_type: Type of MFA to set up

        Returns:
            Dictionary containing MFA configuration
        """
        if mfa_type == MFAType.TOTP:
            # Generate TOTP secret
            secret = self.generate_totp_secret()
            formatted_secret = self.format_totp_secret(secret)
            
            # Generate backup codes
            backup_codes = self.generate_backup_codes()
            hashed_backup_codes = self.hash_backup_codes(backup_codes)
            
            # Generate QR code URI
            uri = self.generate_totp_uri(username, secret)
            
            return {
                'type': MFAType.TOTP.value,
                'secret': base64.b64encode(secret).decode('utf-8'),
                'formatted_secret': formatted_secret,
                'backup_codes': backup_codes,
                'hashed_backup_codes': hashed_backup_codes,
                'uri': uri,
                'config': {
                    'digits': self.totp_config.digits,
                    'interval': self.totp_config.interval,
                    'algorithm': self.totp_config.algorithm,
                    'issuer': self.totp_config.issuer
                }
            }
        else:
            raise ValueError(f"Unsupported MFA type: {mfa_type}")

    def verify_mfa(
        self, 
        mfa_config: Dict, 
        code: str, 
        timestamp: int = None
    ) -> Tuple[bool, Optional[Dict]]:
        """Verify an MFA code.

        Args:
            mfa_config: MFA configuration
            code: Verification code
            timestamp: Optional timestamp

        Returns:
            Tuple of (success, updated_config)
        """
        if mfa_config['type'] == MFAType.TOTP.value:
            # Decode secret
            secret = base64.b64decode(mfa_config['secret'])
            
            # Check TOTP code
            if self.verify_totp(secret, code, timestamp):
                return True, None
                
            # If TOTP fails, try backup codes
            success, updated_backup_codes = self.verify_backup_code(
                code, mfa_config['hashed_backup_codes']
            )
            
            if success:
                # Return updated config with used backup code
                updated_config = mfa_config.copy()
                updated_config['hashed_backup_codes'] = updated_backup_codes
                return True, updated_config
                
        return False, None

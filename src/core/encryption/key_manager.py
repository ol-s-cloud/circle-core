"""Key management for encryption services.

Provides secure key generation, storage, and rotation functionality.
"""

import base64
import datetime
import json
import os
import secrets
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class KeyRotationPolicy(Enum):
    """Enum representing key rotation policies."""

    NONE = "none"  # No automatic rotation
    TIME_BASED = "time_based"  # Rotate after a specified time period
    USAGE_BASED = "usage_based"  # Rotate after a specified number of uses
    HYBRID = "hybrid"  # Rotate based on either time or usage
    MANUAL = "manual"  # Only rotate when manually triggered


@dataclass
class RotationConfig:
    """Configuration for key rotation."""

    policy: KeyRotationPolicy
    max_age_days: int = 90  # For time-based rotation
    max_uses: int = 10000  # For usage-based rotation


class KeyManager:
    """Manager for encryption keys with rotation support.

    This class provides functionality for generating, storing, and rotating
    encryption keys securely. It supports multiple key versions and
    configurable rotation policies.
    """

    def __init__(
        self,
        key_store_path: Optional[str] = None,
        master_key_path: Optional[str] = None,
        rotation_config: Optional[RotationConfig] = None,
    ):
        """Initialize the key manager.

        Args:
            key_store_path: Path to store encryption keys
            master_key_path: Path to the master key file
            rotation_config: Key rotation configuration
        """
        self.key_store_path = key_store_path or os.path.expanduser(
            "~/.circle-core/encryption/keys.json"
        )
        self.master_key_path = master_key_path or os.path.expanduser(
            "~/.circle-core/encryption/master.key"
        )
        self.rotation_config = rotation_config or RotationConfig(
            policy=KeyRotationPolicy.TIME_BASED, max_age_days=90
        )

        # Ensure directories exist
        os.makedirs(os.path.dirname(self.key_store_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.master_key_path), exist_ok=True)

        # Initialize master key if it doesn't exist
        if not os.path.exists(self.master_key_path):
            self._generate_master_key()

        # Load or initialize key store
        self.keys = self._load_keys()
        if not self.keys:
            self._initialize_key_store()

    def _generate_master_key(self) -> None:
        """Generate and store a new master key."""
        # Generate a secure random 32-byte key
        master_key = secrets.token_bytes(32)

        # Write to a temporary file first, then rename for atomicity
        temp_file = f"{self.master_key_path}.tmp"
        with open(temp_file, "wb") as f:
            f.write(master_key)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk

        # Make the file readable only by the owner
        os.chmod(temp_file, 0o600)

        # Atomically replace any existing file
        os.replace(temp_file, self.master_key_path)

    def _load_master_key(self) -> bytes:
        """Load the master key from file.

        Returns:
            Master key as bytes
        """
        try:
            with open(self.master_key_path, "rb") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"Master key not found at {self.master_key_path}")

    def _derive_key_from_master(self, salt: bytes, key_length: int = 32) -> bytes:
        """Derive a key from the master key using PBKDF2.

        Args:
            salt: Salt for derivation
            key_length: Desired key length in bytes

        Returns:
            Derived key
        """
        master_key = self._load_master_key()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=key_length,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        return kdf.derive(master_key)

    def _load_keys(self) -> Dict:
        """Load encryption keys from file.

        Returns:
            Dictionary of encryption keys
        """
        if not os.path.exists(self.key_store_path):
            return {}

        try:
            with open(self.key_store_path, "r") as f:
                encrypted_data = json.load(f)

            # Decrypt the key store
            salt = base64.b64decode(encrypted_data["salt"])
            ciphertext = base64.b64decode(encrypted_data["data"])
            
            # Derive key from master key
            key = self._derive_key_from_master(salt)
            
            # Use AES-GCM to decrypt (implementation is handled in the main encryption service)
            from .service import EncryptionService, EncryptionAlgorithm
            service = EncryptionService()
            plaintext = service._decrypt_data(
                ciphertext, key, EncryptionAlgorithm.AES_GCM
            )
            
            # Parse the JSON
            return json.loads(plaintext.decode('utf-8'))
            
        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            return {}

    def _save_keys(self, keys: Dict) -> None:
        """Save encryption keys to file.

        Args:
            keys: Dictionary of encryption keys
        """
        # Convert keys to JSON
        plaintext = json.dumps(keys).encode('utf-8')
        
        # Generate a random salt
        salt = os.urandom(16)
        
        # Derive key from master key
        key = self._derive_key_from_master(salt)
        
        # Use AES-GCM to encrypt (implementation is handled in the main encryption service)
        from .service import EncryptionService, EncryptionAlgorithm
        service = EncryptionService()
        ciphertext = service._encrypt_data(
            plaintext, key, EncryptionAlgorithm.AES_GCM
        )
        
        # Prepare encrypted data for storage
        encrypted_data = {
            "salt": base64.b64encode(salt).decode('utf-8'),
            "data": base64.b64encode(ciphertext).decode('utf-8'),
        }
        
        # Write to a temporary file first, then rename for atomicity
        temp_file = f"{self.key_store_path}.tmp"
        with open(temp_file, "w") as f:
            json.dump(encrypted_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk

        # Make the file readable only by the owner
        os.chmod(temp_file, 0o600)

        # Atomically replace any existing file
        os.replace(temp_file, self.key_store_path)

    def _initialize_key_store(self) -> None:
        """Initialize the key store with a new data encryption key."""
        # Generate an initial key
        key_id = self.generate_key()
        
        # Set it as the active key
        self.keys["active_key_id"] = key_id
        
        # Save the key store
        self._save_keys(self.keys)

    def generate_key(self, key_type: str = "data") -> str:
        """Generate a new encryption key.

        Args:
            key_type: Type of key to generate

        Returns:
            ID of the generated key
        """
        # Generate a unique ID for the key
        key_id = str(uuid.uuid4())
        
        # Generate a secure random 32-byte key
        key_data = secrets.token_bytes(32)
        
        # Record creation time
        created_at = datetime.datetime.now().isoformat()
        
        # Initialize key metadata
        if "keys" not in self.keys:
            self.keys["keys"] = {}
            
        # Store the key
        self.keys["keys"][key_id] = {
            "key": base64.b64encode(key_data).decode('utf-8'),
            "type": key_type,
            "created_at": created_at,
            "use_count": 0,
            "rotated": False,
        }
        
        # Save the key store
        self._save_keys(self.keys)
        
        return key_id

    def get_key(self, key_id: Optional[str] = None) -> Tuple[str, bytes]:
        """Get an encryption key.

        Args:
            key_id: Optional ID of the key to retrieve (uses active key if None)

        Returns:
            Tuple of (key_id, key_data)
        """
        if key_id is None:
            # Use the active key
            key_id = self.keys.get("active_key_id")
            if key_id is None:
                raise KeyError("No active key set")
        
        # Check if the key exists
        if "keys" not in self.keys or key_id not in self.keys["keys"]:
            raise KeyError(f"Key with ID {key_id} not found")
        
        # Get the key data
        key_data = base64.b64decode(self.keys["keys"][key_id]["key"])
        
        # Increment the use count
        self.keys["keys"][key_id]["use_count"] += 1
        
        # Check if rotation is needed based on use count
        if (self.rotation_config.policy == KeyRotationPolicy.USAGE_BASED or 
            self.rotation_config.policy == KeyRotationPolicy.HYBRID) and \
           self.keys["keys"][key_id]["use_count"] >= self.rotation_config.max_uses:
            self._rotate_key()
        
        # Save updates to use count
        self._save_keys(self.keys)
        
        return key_id, key_data

    def get_key_metadata(self, key_id: str) -> Dict:
        """Get metadata for a key.

        Args:
            key_id: ID of the key

        Returns:
            Key metadata
        """
        if "keys" not in self.keys or key_id not in self.keys["keys"]:
            raise KeyError(f"Key with ID {key_id} not found")
        
        # Return a copy without the actual key material
        metadata = self.keys["keys"][key_id].copy()
        metadata.pop("key", None)
        
        return metadata

    def list_keys(self) -> List[Dict]:
        """List all keys and their metadata.

        Returns:
            List of key metadata dictionaries
        """
        if "keys" not in self.keys:
            return []
        
        result = []
        for key_id, key_data in self.keys["keys"].items():
            # Add key ID to the metadata
            metadata = key_data.copy()
            metadata.pop("key", None)  # Remove the actual key material
            metadata["id"] = key_id
            metadata["is_active"] = (key_id == self.keys.get("active_key_id"))
            result.append(metadata)
            
        return result

    def check_rotation_needed(self) -> bool:
        """Check if key rotation is needed based on the rotation policy.

        Returns:
            True if rotation is needed, False otherwise
        """
        # If no rotation policy is set, return False
        if self.rotation_config.policy == KeyRotationPolicy.NONE or \
           self.rotation_config.policy == KeyRotationPolicy.MANUAL:
            return False
        
        # Get the active key
        active_key_id = self.keys.get("active_key_id")
        if active_key_id is None:
            return True  # No active key, need to create one
        
        # Get the active key metadata
        key_data = self.keys["keys"].get(active_key_id)
        if key_data is None:
            return True  # Key ID is invalid
        
        # Check rotation based on time
        if self.rotation_config.policy in (KeyRotationPolicy.TIME_BASED, KeyRotationPolicy.HYBRID):
            created_at = datetime.datetime.fromisoformat(key_data["created_at"])
            age_days = (datetime.datetime.now() - created_at).days
            if age_days >= self.rotation_config.max_age_days:
                return True
        
        # Check rotation based on usage
        if self.rotation_config.policy in (KeyRotationPolicy.USAGE_BASED, KeyRotationPolicy.HYBRID):
            if key_data["use_count"] >= self.rotation_config.max_uses:
                return True
                
        return False

    def rotate_key(self) -> str:
        """Rotate the active encryption key.

        Returns:
            ID of the new active key
        """
        # Generate a new key
        new_key_id = self.generate_key()
        
        # Mark the old active key as rotated
        old_key_id = self.keys.get("active_key_id")
        if old_key_id and old_key_id in self.keys["keys"]:
            self.keys["keys"][old_key_id]["rotated"] = True
        
        # Set the new key as active
        self.keys["active_key_id"] = new_key_id
        
        # Save the key store
        self._save_keys(self.keys)
        
        return new_key_id

    def delete_key(self, key_id: str) -> bool:
        """Delete a key.

        Args:
            key_id: ID of the key to delete

        Returns:
            True if deleted, False otherwise
        """
        # Cannot delete the active key
        if key_id == self.keys.get("active_key_id"):
            return False
        
        # Check if the key exists
        if "keys" not in self.keys or key_id not in self.keys["keys"]:
            return False
        
        # Delete the key
        del self.keys["keys"][key_id]
        
        # Save the key store
        self._save_keys(self.keys)
        
        return True

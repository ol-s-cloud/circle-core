"""Secrets Manager for Circle Core Framework.

Provides functionality to securely store and retrieve sensitive information.
"""

import base64
import json
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecretBackendType(Enum):
    """Enum representing different secret backend types."""

    FILE = "file"  # Local file storage (encrypted)
    ENV = "env"  # Environment variables
    VAULT = "vault"  # HashiCorp Vault (requires additional setup)


class SecretsManager:
    """Manager for secure storage and retrieval of sensitive information.

    This class provides functionality to store and retrieve secrets using
    different backend storage mechanisms.
    """

    def __init__(
        self,
        backend_type: SecretBackendType = SecretBackendType.FILE,
        config: Optional[Dict[str, Any]] = None,
        master_key: Optional[str] = None,
    ):
        """Initialize the secrets manager.

        Args:
            backend_type: Type of secret backend to use
            config: Configuration for the selected backend
            master_key: Master encryption key (for file backend)
        """
        self.backend_type = backend_type
        self.config = config or {}

        # Initialize the appropriate backend
        if backend_type == SecretBackendType.FILE:
            self._initialize_file_backend(master_key)
        elif backend_type == SecretBackendType.ENV:
            self._initialize_env_backend()
        elif backend_type == SecretBackendType.VAULT:
            self._initialize_vault_backend()

    def _initialize_file_backend(self, master_key: Optional[str] = None) -> None:
        """Initialize the file-based secrets backend.

        Args:
            master_key: Master encryption key (optional)
        """
        # Set default paths
        secrets_dir = self.config.get("secrets_dir", os.path.expanduser("~/.circle-core/secrets"))
        os.makedirs(secrets_dir, exist_ok=True)
        self.secrets_file = os.path.join(secrets_dir, "secrets.enc")

        # Generate or load encryption key
        key_file = os.path.join(secrets_dir, "master.key")
        
        if master_key:
            # Use provided master key
            key_bytes = self._derive_key_from_password(master_key)
        elif os.path.exists(key_file):
            # Load existing key from file
            with open(key_file, "rb") as f:
                key_bytes = f.read()
        else:
            # Generate new key
            key_bytes = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(key_bytes)
            os.chmod(key_file, 0o600)  # Restrict permissions

        self.cipher = Fernet(key_bytes)
        self.secrets_cache = {}
        self._load_secrets()

    def _derive_key_from_password(self, password: str, salt: bytes = None) -> bytes:
        """Derive an encryption key from a password.

        Args:
            password: Password to derive key from
            salt: Salt for key derivation (optional)

        Returns:
            Derived key bytes
        """
        if salt is None:
            salt = b'circle-core-salt'  # In production, use a secure random salt
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,  # High iteration count for security
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def _initialize_env_backend(self) -> None:
        """Initialize the environment variable-based secrets backend."""
        # Environment variables don't need initialization
        self.prefix = self.config.get("prefix", "CIRCLE_CORE_SECRET_")

    def _initialize_vault_backend(self) -> None:
        """Initialize the HashiCorp Vault-based secrets backend."""
        # In a real implementation, this would set up the Vault client
        # For now, this is a placeholder
        vault_url = self.config.get("vault_url", "http://localhost:8200")
        vault_token = self.config.get("vault_token")
        self.vault_path = self.config.get("vault_path", "secret/circle-core")
        
        if not vault_token:
            raise ValueError("Vault token is required for Vault backend")
            
        # This would initialize a Vault client
        # self.vault_client = hvac.Client(url=vault_url, token=vault_token)

    def _load_secrets(self) -> None:
        """Load secrets from the file backend."""
        if not os.path.exists(self.secrets_file):
            self.secrets_cache = {}
            return

        try:
            with open(self.secrets_file, "rb") as f:
                encrypted_data = f.read()
                if encrypted_data:
                    decrypted_data = self.cipher.decrypt(encrypted_data)
                    self.secrets_cache = json.loads(decrypted_data)
                else:
                    self.secrets_cache = {}
        except Exception:
            # If decryption fails, start with empty cache
            self.secrets_cache = {}

    def _save_secrets(self) -> None:
        """Save secrets to the file backend."""
        encrypted_data = self.cipher.encrypt(json.dumps(self.secrets_cache).encode())
        
        # Write to a temporary file first, then rename for atomicity
        temp_file = f"{self.secrets_file}.tmp"
        with open(temp_file, "wb") as f:
            f.write(encrypted_data)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk
            
        os.replace(temp_file, self.secrets_file)  # Atomic replace
        os.chmod(self.secrets_file, 0o600)  # Restrict permissions

    def get_secret(self, key: str) -> Optional[str]:
        """Get a secret by key.

        Args:
            key: Secret key

        Returns:
            Secret value or None if not found
        """
        if self.backend_type == SecretBackendType.FILE:
            return self.secrets_cache.get(key)
        elif self.backend_type == SecretBackendType.ENV:
            return os.environ.get(f"{self.prefix}{key}")
        elif self.backend_type == SecretBackendType.VAULT:
            # In a real implementation, this would use the Vault client
            # response = self.vault_client.read(f"{self.vault_path}/{key}")
            # return response["data"]["value"] if response else None
            pass  # Placeholder
            
        return None

    def set_secret(self, key: str, value: str) -> None:
        """Set a secret.

        Args:
            key: Secret key
            value: Secret value
        """
        if self.backend_type == SecretBackendType.FILE:
            self.secrets_cache[key] = value
            self._save_secrets()
        elif self.backend_type == SecretBackendType.ENV:
            os.environ[f"{self.prefix}{key}"] = value
        elif self.backend_type == SecretBackendType.VAULT:
            # In a real implementation, this would use the Vault client
            # self.vault_client.write(f"{self.vault_path}/{key}", value=value)
            pass  # Placeholder

    def delete_secret(self, key: str) -> bool:
        """Delete a secret.

        Args:
            key: Secret key

        Returns:
            True if deleted, False if not found
        """
        if self.backend_type == SecretBackendType.FILE:
            if key in self.secrets_cache:
                del self.secrets_cache[key]
                self._save_secrets()
                return True
        elif self.backend_type == SecretBackendType.ENV:
            env_key = f"{self.prefix}{key}"
            if env_key in os.environ:
                del os.environ[env_key]
                return True
        elif self.backend_type == SecretBackendType.VAULT:
            # In a real implementation, this would use the Vault client
            # self.vault_client.delete(f"{self.vault_path}/{key}")
            # return True
            pass  # Placeholder
            
        return False

    def list_secrets(self) -> list:
        """List all available secret keys.

        Returns:
            List of secret keys
        """
        if self.backend_type == SecretBackendType.FILE:
            return list(self.secrets_cache.keys())
        elif self.backend_type == SecretBackendType.ENV:
            return [
                k.replace(self.prefix, "") 
                for k in os.environ.keys() 
                if k.startswith(self.prefix)
            ]
        elif self.backend_type == SecretBackendType.VAULT:
            # In a real implementation, this would use the Vault client
            # response = self.vault_client.list(self.vault_path)
            # return response["data"]["keys"] if response else []
            return []  # Placeholder
            
        return []

    def rotate_encryption_key(self, new_master_key: Optional[str] = None) -> None:
        """Rotate the encryption key for the file backend.

        Args:
            new_master_key: New master key (optional)
        """
        if self.backend_type != SecretBackendType.FILE:
            raise ValueError("Key rotation is only supported for FILE backend")
            
        # Save current secrets
        current_secrets = self.secrets_cache.copy()
        
        # Generate new key
        key_file = os.path.join(os.path.dirname(self.secrets_file), "master.key")
        
        if new_master_key:
            # Use provided master key
            new_key = self._derive_key_from_password(new_master_key)
        else:
            # Generate random key
            new_key = Fernet.generate_key()
            
        # Update cipher
        self.cipher = Fernet(new_key)
        
        # Save new key
        with open(key_file, "wb") as f:
            f.write(new_key)
        os.chmod(key_file, 0o600)  # Restrict permissions
        
        # Re-encrypt and save secrets with new key
        self.secrets_cache = current_secrets
        self._save_secrets()

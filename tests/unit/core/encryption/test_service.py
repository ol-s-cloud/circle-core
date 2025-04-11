"""Unit tests for the EncryptionService."""

import os
import tempfile
from unittest import mock

import pytest

from circle_core.core.encryption import (
    EncryptionService, 
    EncryptionAlgorithm, 
    KeyManager
)


@pytest.fixture
def temp_key_store():
    """Create a temporary key store for testing."""
    temp_dir = tempfile.mkdtemp()
    key_store_path = os.path.join(temp_dir, "keys.json")
    master_key_path = os.path.join(temp_dir, "master.key")
    
    yield key_store_path, master_key_path
    
    # Clean up
    if os.path.exists(key_store_path):
        os.remove(key_store_path)
    if os.path.exists(master_key_path):
        os.remove(master_key_path)
    os.rmdir(temp_dir)


@pytest.fixture
def key_manager(temp_key_store):
    """Create a KeyManager for testing."""
    key_store_path, master_key_path = temp_key_store
    return KeyManager(
        key_store_path=key_store_path,
        master_key_path=master_key_path
    )


@pytest.fixture
def encryption_service(key_manager):
    """Create an EncryptionService for testing."""
    return EncryptionService(
        algorithm=EncryptionAlgorithm.AES_GCM,
        key_manager=key_manager
    )


class TestEncryptionService:
    """Tests for EncryptionService."""
    
    def test_init(self, key_manager):
        """Test initializing an EncryptionService."""
        service = EncryptionService(
            algorithm=EncryptionAlgorithm.AES_GCM,
            key_manager=key_manager
        )
        
        assert service.algorithm == EncryptionAlgorithm.AES_GCM
        assert service.key_manager == key_manager

    def test_encrypt_decrypt_string(self, encryption_service):
        """Test encrypting and decrypting a string."""
        original_data = "This is a test string to encrypt"
        
        # Encrypt the data
        encrypted_data = encryption_service.encrypt(original_data)
        
        # Check the encrypted data
        assert encrypted_data.ciphertext is not None
        assert encrypted_data.algorithm == EncryptionAlgorithm.AES_GCM
        assert encrypted_data.key_id is not None
        assert encrypted_data.iv is not None
        
        # Decrypt the data
        decrypted_data = encryption_service.decrypt(encrypted_data)
        
        # Check the decrypted data
        assert decrypted_data.decode('utf-8') == original_data

    def test_encrypt_decrypt_bytes(self, encryption_service):
        """Test encrypting and decrypting bytes."""
        original_data = b"This is a test bytes object to encrypt"
        
        # Encrypt the data
        encrypted_data = encryption_service.encrypt(original_data)
        
        # Decrypt the data
        decrypted_data = encryption_service.decrypt(encrypted_data)
        
        # Check the decrypted data
        assert decrypted_data == original_data

    def test_aes_gcm(self, encryption_service):
        """Test AES-GCM encryption."""
        data = "Secret data for AES-GCM"
        
        # Encrypt with AES-GCM
        encrypted_data = encryption_service.encrypt(
            data, algorithm=EncryptionAlgorithm.AES_GCM
        )
        
        assert encrypted_data.algorithm == EncryptionAlgorithm.AES_GCM
        assert encrypted_data.iv is not None
        assert len(encrypted_data.iv) == 12  # GCM uses 12-byte IV
        
        # Decrypt
        decrypted_data = encryption_service.decrypt(encrypted_data)
        assert decrypted_data.decode('utf-8') == data

    def test_aes_cbc(self, encryption_service):
        """Test AES-CBC encryption."""
        data = "Secret data for AES-CBC"
        
        # Encrypt with AES-CBC
        encrypted_data = encryption_service.encrypt(
            data, algorithm=EncryptionAlgorithm.AES_CBC
        )
        
        assert encrypted_data.algorithm == EncryptionAlgorithm.AES_CBC
        assert encrypted_data.iv is not None
        assert len(encrypted_data.iv) == 16  # CBC uses 16-byte IV
        assert encrypted_data.tag is not None  # Should have HMAC tag
        
        # Decrypt
        decrypted_data = encryption_service.decrypt(encrypted_data)
        assert decrypted_data.decode('utf-8') == data

    def test_aes_gcm_with_aad(self, encryption_service):
        """Test AES-GCM with additional authenticated data."""
        data = "Secret data with AAD"
        aad = b"Additional authenticated data"
        
        # Encrypt with AAD
        encrypted_data = encryption_service.encrypt(
            data, algorithm=EncryptionAlgorithm.AES_GCM, aad=aad
        )
        
        # Should store AAD
        assert encrypted_data.aad == aad
        
        # Decrypt with AAD
        decrypted_data = encryption_service.decrypt(encrypted_data)
        assert decrypted_data.decode('utf-8') == data
        
        # Attempt to decrypt with wrong AAD should fail
        encrypted_data.aad = b"Wrong AAD"
        with pytest.raises(Exception):
            encryption_service.decrypt(encrypted_data)

    def test_encrypt_with_specific_key(self, encryption_service):
        """Test encrypting with a specific key."""
        # Generate a specific key
        key_id = encryption_service.key_manager.generate_key()
        
        # Encrypt with specific key
        data = "Data for specific key"
        encrypted_data = encryption_service.encrypt(data, key_id=key_id)
        
        # Should use the specified key
        assert encrypted_data.key_id == key_id
        
        # Decrypt should work
        decrypted_data = encryption_service.decrypt(encrypted_data)
        assert decrypted_data.decode('utf-8') == data

    def test_envelope_encryption(self, encryption_service):
        """Test envelope encryption."""
        data = "Secret data for envelope encryption"
        
        # Use envelope encryption
        envelope = encryption_service.encrypt_envelope(data)
        
        # Check envelope format
        assert "algorithm" in envelope
        assert "key_id" in envelope
        assert "encrypted_dek" in envelope
        assert "dek_iv" in envelope
        assert "iv" in envelope
        assert "ciphertext" in envelope
        
        # Decrypt envelope
        decrypted_data = encryption_service.decrypt_envelope(envelope)
        
        # Check result
        assert decrypted_data.decode('utf-8') == data

    def test_file_encryption(self, encryption_service):
        """Test file encryption and decryption."""
        # Create a temporary file with test data
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"This is test file data for encryption")
            temp_file_path = temp_file.name
            
        # Create a temporary output file
        encrypted_file_path = temp_file_path + ".encrypted"
        decrypted_file_path = temp_file_path + ".decrypted"
        
        try:
            # Encrypt the file
            metadata = encryption_service.encrypt_file(
                temp_file_path, encrypted_file_path
            )
            
            # Check metadata
            assert "algorithm" in metadata
            assert metadata["algorithm"] == EncryptionAlgorithm.AES_GCM.value
            assert os.path.exists(encrypted_file_path)
            
            # Decrypt the file
            encryption_service.decrypt_file(
                encrypted_file_path, decrypted_file_path
            )
            
            # Check the decrypted file
            with open(temp_file_path, 'rb') as f1, open(decrypted_file_path, 'rb') as f2:
                assert f1.read() == f2.read()
                
        finally:
            # Clean up
            for path in [temp_file_path, encrypted_file_path, decrypted_file_path]:
                if os.path.exists(path):
                    os.remove(path)

    def test_key_rotation(self, encryption_service):
        """Test key rotation during encryption."""
        # Mock the key manager to trigger rotation after 1 use
        encryption_service.key_manager.rotation_config.policy = "usage_based"
        encryption_service.key_manager.rotation_config.max_uses = 1
        
        # Save the current active key
        original_key_id = encryption_service.key_manager.keys["active_key_id"]
        
        # Encrypt some data (should trigger rotation)
        data = "Data that will trigger key rotation"
        encryption_service.encrypt(data)
        
        # Key should have been rotated
        new_key_id = encryption_service.key_manager.keys["active_key_id"]
        assert new_key_id != original_key_id

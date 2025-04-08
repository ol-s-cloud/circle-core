"""Unit tests for the MFA service."""

import base64
import os
import re
import tempfile
import time
from unittest import mock

import pytest

from circle_core.core.auth import MFAService, MFAType, TOTPConfig


@pytest.fixture
def mfa_service():
    """Create an MFA service for testing."""
    return MFAService(
        storage_path=tempfile.mkdtemp(),
        totp_config=TOTPConfig(
            digits=6,
            interval=30,
            algorithm="sha1",
            issuer="TestIssuer",
            valid_window=1,
        ),
        backup_code_count=5,
    )


class TestMFAService:
    """Tests for MFAService."""

    def test_generate_totp_secret(self, mfa_service):
        """Test generating a TOTP secret."""
        secret = mfa_service.generate_totp_secret()
        
        # Should be 32 bytes
        assert len(secret) == 32
        
        # Should be bytes
        assert isinstance(secret, bytes)
        
        # Should be random (different on repeated calls)
        secret2 = mfa_service.generate_totp_secret()
        assert secret != secret2

    def test_format_totp_secret(self, mfa_service):
        """Test formatting a TOTP secret as Base32."""
        # Generate a known binary secret
        binary_secret = b'abcdefghijklmnopqrstuvwxyz123456'
        
        # Format it
        formatted = mfa_service.format_totp_secret(binary_secret)
        
        # Should be a string
        assert isinstance(formatted, str)
        
        # Should be base32 encoded (uppercase A-Z and 2-7)
        assert re.match(r'^[A-Z2-7]+$', formatted)
        
        # Should not have padding
        assert '=' not in formatted
        
        # Should decode back to the original value
        decoded = base64.b32decode(formatted + '=' * (-len(formatted) % 8))
        assert decoded == binary_secret

    def test_generate_totp_uri(self, mfa_service):
        """Test generating a TOTP URI."""
        # Generate a secret
        secret = mfa_service.generate_totp_secret()
        
        # Generate a URI
        uri = mfa_service.generate_totp_uri("testuser", secret)
        
        # URI should start with the correct protocol
        assert uri.startswith("otpauth://totp/")
        
        # URI should include the username and issuer
        assert "TestIssuer:testuser" in uri
        
        # URI should include the secret
        assert f"secret={mfa_service.format_totp_secret(secret)}" in uri
        
        # URI should include the algorithm, digits, and period
        assert "algorithm=SHA1" in uri
        assert "digits=6" in uri
        assert "period=30" in uri

    def test_generate_totp(self, mfa_service):
        """Test generating a TOTP code."""
        # Generate a secret
        secret = mfa_service.generate_totp_secret()
        
        # Generate a TOTP
        code = mfa_service.generate_totp(secret)
        
        # Should be a string
        assert isinstance(code, str)
        
        # Should be 6 digits
        assert len(code) == 6
        assert code.isdigit()
        
        # Should change based on time
        time_mock = mock.patch('time.time', return_value=time.time() + 30)
        with time_mock:
            code2 = mfa_service.generate_totp(secret)
            assert code != code2

    def test_verify_totp(self, mfa_service):
        """Test verifying a TOTP code."""
        # Generate a secret
        secret = mfa_service.generate_totp_secret()
        
        # Generate a valid TOTP code
        code = mfa_service.generate_totp(secret)
        
        # Verify the code
        assert mfa_service.verify_totp(secret, code)
        
        # Invalid code should not verify
        assert not mfa_service.verify_totp(secret, "000000")
        
        # Code should work within valid window
        time_mock = mock.patch('time.time', return_value=time.time() + 15)
        with time_mock:
            assert mfa_service.verify_totp(secret, code)
            
        # Code should not work outside valid window
        time_mock = mock.patch('time.time', return_value=time.time() + 61)
        with time_mock:
            assert not mfa_service.verify_totp(secret, code)

    def test_generate_backup_codes(self, mfa_service):
        """Test generating backup codes."""
        # Generate backup codes
        codes = mfa_service.generate_backup_codes()
        
        # Should be the specified number of codes
        assert len(codes) == 5  # backup_code_count=5
        
        # Each code should be formatted as xxxx-xxxx
        for code in codes:
            assert re.match(r'^[a-z0-9]{4}-[a-z0-9]{4}$', code)
            
        # Codes should all be unique
        assert len(set(codes)) == 5

    def test_hash_backup_codes(self, mfa_service):
        """Test hashing backup codes."""
        # Generate backup codes
        codes = mfa_service.generate_backup_codes()
        
        # Hash the codes
        hashed_codes = mfa_service.hash_backup_codes(codes)
        
        # Should return the right number of hashed codes
        assert len(hashed_codes) == len(codes)
        
        # Each hashed code should have the right format
        for hashed_code in hashed_codes:
            assert 'salt' in hashed_code
            assert 'hash' in hashed_code
            assert 'used' in hashed_code
            assert hashed_code['used'] is False
            
            # Salt and hash should be base64 encoded
            assert re.match(r'^[A-Za-z0-9+/]+=*$', hashed_code['salt'])
            assert re.match(r'^[A-Za-z0-9+/]+=*$', hashed_code['hash'])

    def test_verify_backup_code(self, mfa_service):
        """Test verifying a backup code."""
        # Generate backup codes
        codes = mfa_service.generate_backup_codes()
        
        # Hash the codes
        hashed_codes = mfa_service.hash_backup_codes(codes)
        
        # Verify a valid code
        valid, updated_hashed_codes = mfa_service.verify_backup_code(codes[0], hashed_codes)
        assert valid is True
        
        # Code should be marked as used
        assert updated_hashed_codes[0]['used'] is True
        
        # Verify an invalid code
        valid, _ = mfa_service.verify_backup_code("invalid-code", updated_hashed_codes)
        assert valid is False
        
        # Verify a code that's already been used
        valid, _ = mfa_service.verify_backup_code(codes[0], updated_hashed_codes)
        assert valid is False

    def test_setup_mfa_for_user(self, mfa_service):
        """Test setting up MFA for a user."""
        # Set up MFA
        config = mfa_service.setup_mfa_for_user("testuser")
        
        # Should have the right keys
        assert config['type'] == MFAType.TOTP.value
        assert 'secret' in config
        assert 'formatted_secret' in config
        assert 'backup_codes' in config
        assert 'hashed_backup_codes' in config
        assert 'uri' in config
        assert 'config' in config
        
        # Should have the right number of backup codes
        assert len(config['backup_codes']) == 5
        assert len(config['hashed_backup_codes']) == 5
        
        # Config should contain the TOTP settings
        assert config['config']['digits'] == 6
        assert config['config']['interval'] == 30
        assert config['config']['algorithm'] == 'sha1'
        assert config['config']['issuer'] == 'TestIssuer'

    def test_verify_mfa(self, mfa_service):
        """Test verifying an MFA code."""
        # Set up MFA for a user
        config = mfa_service.setup_mfa_for_user("testuser")
        
        # Generate a valid TOTP code
        secret = base64.b64decode(config['secret'])
        code = mfa_service.generate_totp(secret)
        
        # Verify the code
        valid, updated_config = mfa_service.verify_mfa(config, code)
        assert valid is True
        assert updated_config is None  # No changes needed
        
        # Test with an invalid code
        valid, _ = mfa_service.verify_mfa(config, "000000")
        assert valid is False
        
        # Test with a valid backup code
        valid, updated_config = mfa_service.verify_mfa(config, config['backup_codes'][0])
        assert valid is True
        assert updated_config is not None
        assert updated_config['hashed_backup_codes'][0]['used'] is True

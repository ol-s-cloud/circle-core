"""Unit tests for the authentication service."""

import datetime
import os
import tempfile
from unittest import mock

import pytest
from argon2.exceptions import VerifyMismatchError

from circle_core.core.auth import AuthenticationService, AuthResult, UserRole, MFAService


@pytest.fixture
def temp_user_db():
    """Create a temporary user database file for testing."""
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, "users.json")
    yield temp_file
    # Clean up
    if os.path.exists(temp_file):
        os.remove(temp_file)
    os.rmdir(temp_dir)


@pytest.fixture
def auth_service(temp_user_db):
    """Create an authentication service with a temporary database."""
    return AuthenticationService(
        user_db_path=temp_user_db,
        max_failed_attempts=3,
        lockout_duration_minutes=15,
        password_expiry_days=90,
        min_password_length=8,
    )


class TestAuthenticationService:
    """Tests for AuthenticationService."""

    def test_create_user(self, auth_service):
        """Test user creation."""
        # Create a test user
        result = auth_service.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
            role=UserRole.USER,
        )

        assert result is True
        assert "testuser" in auth_service.users
        assert auth_service.users["testuser"]["email"] == "test@example.com"
        assert auth_service.users["testuser"]["role"] == "user"
        assert "password_hash" in auth_service.users["testuser"]
        assert auth_service.users["testuser"]["mfa_enabled"] is False

    def test_create_user_duplicate(self, auth_service):
        """Test creating a user with a duplicate username."""
        # Create initial user
        auth_service.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
        )

        # Try to create duplicate
        result = auth_service.create_user(
            username="testuser",
            password="anotherpassword",
            email="another@example.com",
        )

        assert result is False

    def test_create_user_password_too_short(self, auth_service):
        """Test creating a user with a password that's too short."""
        with pytest.raises(ValueError):
            auth_service.create_user(
                username="testuser",
                password="short",  # Too short
                email="test@example.com",
            )

    def test_authenticate_valid(self, auth_service):
        """Test authentication with valid credentials."""
        # Create a test user
        auth_service.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
        )

        # Authenticate
        result, user = auth_service.authenticate("testuser", "testpassword123")

        assert result == AuthResult.SUCCESS
        assert user is not None
        assert user["username"] == "testuser"
        assert "failed_attempts" in user
        assert user["failed_attempts"] == 0
        assert "last_login" in user

    def test_authenticate_invalid_username(self, auth_service):
        """Test authentication with an invalid username."""
        result, user = auth_service.authenticate("nonexistent", "testpassword123")

        assert result == AuthResult.INVALID_CREDENTIALS
        assert user is None

    def test_authenticate_invalid_password(self, auth_service):
        """Test authentication with an invalid password."""
        # Create a test user
        auth_service.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
        )

        # Authenticate with wrong password
        result, user = auth_service.authenticate("testuser", "wrongpassword")

        assert result == AuthResult.INVALID_CREDENTIALS
        assert user is None
        assert auth_service.users["testuser"]["failed_attempts"] == 1
        assert "last_failed_attempt" in auth_service.users["testuser"]

    def test_authenticate_account_locked(self, auth_service):
        """Test authentication with a locked account."""
        # Create a test user
        auth_service.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
        )

        # Exceed max failed attempts to lock the account
        for _ in range(3):  # Max attempts is 3
            auth_service.authenticate("testuser", "wrongpassword")

        # Try to authenticate with correct password
        result, user = auth_service.authenticate("testuser", "testpassword123")

        assert result == AuthResult.ACCOUNT_LOCKED
        assert user is None
        assert "locked_until" in auth_service.users["testuser"]

    def test_authenticate_account_disabled(self, auth_service):
        """Test authentication with a disabled account."""
        # Create a test user
        auth_service.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
        )

        # Disable the account
        auth_service.users["testuser"]["disabled"] = True
        auth_service._save_users()

        # Try to authenticate
        result, user = auth_service.authenticate("testuser", "testpassword123")

        assert result == AuthResult.ACCOUNT_DISABLED
        assert user is None

    def test_authenticate_password_expired(self, auth_service):
        """Test authentication with an expired password."""
        # Create a test user
        auth_service.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
        )

        # Set password_last_changed to 100 days ago (> 90 days expiry)
        expiry_time = datetime.datetime.now() - datetime.timedelta(days=100)
        auth_service.users["testuser"]["password_last_changed"] = expiry_time.isoformat()
        auth_service._save_users()

        # Try to authenticate
        result, user = auth_service.authenticate("testuser", "testpassword123")

        assert result == AuthResult.ACCOUNT_EXPIRED
        assert user is None

    def test_update_password(self, auth_service):
        """Test password update."""
        # Create a test user
        auth_service.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
        )

        # Update password
        result = auth_service.update_password(
            "testuser", "testpassword123", "newpassword456"
        )

        assert result is True

        # Try to authenticate with new password
        auth_result, _ = auth_service.authenticate("testuser", "newpassword456")
        assert auth_result == AuthResult.SUCCESS

        # Try to authenticate with old password
        auth_result, _ = auth_service.authenticate("testuser", "testpassword123")
        assert auth_result == AuthResult.INVALID_CREDENTIALS

    def test_reset_password(self, auth_service):
        """Test password reset by admin."""
        # Create a test user and admin
        auth_service.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
        )
        auth_service.create_user(
            username="admin",
            password="adminpassword",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )

        # Reset password
        result = auth_service.reset_password(
            "testuser", "admin", "adminpassword", "resetpassword789"
        )

        assert result is True

        # Try to authenticate with new password
        auth_result, user = auth_service.authenticate("testuser", "resetpassword789")
        assert auth_result == AuthResult.SUCCESS
        assert user["password_change_required"] is True

    def test_reset_password_insufficient_privileges(self, auth_service):
        """Test password reset by non-admin user."""
        # Create two regular users
        auth_service.create_user(
            username="user1",
            password="password1",
            email="user1@example.com",
        )
        auth_service.create_user(
            username="user2",
            password="password2",
            email="user2@example.com",
        )

        # Try to reset password
        result = auth_service.reset_password(
            "user1", "user2", "password2", "newpassword"
        )

        assert result is False

    def test_disable_enable_user(self, auth_service):
        """Test disabling and enabling a user account."""
        # Create a test user and admin
        auth_service.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
        )
        auth_service.create_user(
            username="admin",
            password="adminpassword",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )

        # Disable account
        result = auth_service.disable_user("testuser", "admin", "adminpassword")
        assert result is True
        assert auth_service.users["testuser"]["disabled"] is True

        # Try to authenticate
        auth_result, _ = auth_service.authenticate("testuser", "testpassword123")
        assert auth_result == AuthResult.ACCOUNT_DISABLED

        # Enable account
        result = auth_service.enable_user("testuser", "admin", "adminpassword")
        assert result is True
        assert auth_service.users["testuser"]["disabled"] is False

        # Try to authenticate
        auth_result, _ = auth_service.authenticate("testuser", "testpassword123")
        assert auth_result == AuthResult.SUCCESS

    def test_unlock_account(self, auth_service):
        """Test unlocking a locked account."""
        # Create a test user and admin
        auth_service.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
        )
        auth_service.create_user(
            username="admin",
            password="adminpassword",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )

        # Exceed max failed attempts to lock the account
        for _ in range(3):  # Max attempts is 3
            auth_service.authenticate("testuser", "wrongpassword")

        # Verify account is locked
        auth_result, _ = auth_service.authenticate("testuser", "testpassword123")
        assert auth_result == AuthResult.ACCOUNT_LOCKED

        # Unlock account
        result = auth_service.unlock_account("testuser", "admin", "adminpassword")
        assert result is True
        assert "locked_until" not in auth_service.users["testuser"]
        assert auth_service.users["testuser"]["failed_attempts"] == 0

        # Try to authenticate
        auth_result, _ = auth_service.authenticate("testuser", "testpassword123")
        assert auth_result == AuthResult.SUCCESS

    @mock.patch.object(MFAService, 'verify_mfa')
    def test_verify_mfa(self, mock_verify_mfa, auth_service):
        """Test MFA verification."""
        # Setup mock
        mock_verify_mfa.return_value = (True, None)

        # Create a test user with MFA enabled
        auth_service.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
        )
        
        # Manually set MFA to enabled
        auth_service.users["testuser"]["mfa_enabled"] = True
        auth_service.users["testuser"]["mfa_config"] = {"type": "totp"}
        auth_service._save_users()

        # Authenticate first
        result, _ = auth_service.authenticate("testuser", "testpassword123")
        assert result == AuthResult.REQUIRES_MFA

        # Verify MFA
        result, user = auth_service.verify_mfa("testuser", "123456")
        assert result == AuthResult.SUCCESS
        assert user is not None
        assert user["username"] == "testuser"

        # Verify mfa_service.verify_mfa was called
        mock_verify_mfa.assert_called_once_with({"type": "totp"}, "123456")

    @mock.patch.object(MFAService, 'setup_mfa_for_user')
    def test_setup_mfa(self, mock_setup_mfa, auth_service):
        """Test setting up MFA."""
        # Setup mock
        mock_mfa_config = {
            "type": "totp",
            "secret": "base64-encoded-secret",
            "formatted_secret": "ABCD1234",
            "backup_codes": ["code1", "code2"],
            "uri": "otpauth://totp/test?secret=ABCD1234"
        }
        mock_setup_mfa.return_value = mock_mfa_config

        # Create a test user
        auth_service.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
        )

        # Setup MFA
        mfa_config = auth_service.setup_mfa("testuser", "testpassword123")
        
        assert mfa_config == mock_mfa_config
        assert auth_service.users["testuser"]["mfa_enabled"] is True
        assert auth_service.users["testuser"]["mfa_config"] == mock_mfa_config
        
        # Verify setup_mfa_for_user was called
        mock_setup_mfa.assert_called_once()

    def test_get_user_info(self, auth_service):
        """Test getting user information."""
        # Create a test user and admin
        auth_service.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
            additional_data={"custom_field": "custom_value"},
        )
        auth_service.create_user(
            username="admin",
            password="adminpassword",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )

        # Get user info
        user_info = auth_service.get_user_info("testuser", "admin", "adminpassword")
        
        assert user_info is not None
        assert user_info["username"] == "testuser"
        assert user_info["email"] == "test@example.com"
        assert user_info["custom_field"] == "custom_value"
        assert "password_hash" not in user_info  # Password hash should be excluded

    def test_list_users(self, auth_service):
        """Test listing users."""
        # Create multiple users
        auth_service.create_user(
            username="user1",
            password="password1",
            email="user1@example.com",
        )
        auth_service.create_user(
            username="user2",
            password="password2",
            email="user2@example.com",
        )
        auth_service.create_user(
            username="admin",
            password="adminpassword",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )

        # List users
        users_list = auth_service.list_users("admin", "adminpassword")
        
        assert users_list is not None
        assert len(users_list) == 3
        
        # Check that all users are included
        usernames = [user["username"] for user in users_list]
        assert "user1" in usernames
        assert "user2" in usernames
        assert "admin" in usernames
        
        # Verify no password hashes
        for user in users_list:
            assert "password_hash" not in user

    def test_password_reset_token(self, auth_service):
        """Test password reset with token."""
        # Create a test user and admin
        auth_service.create_user(
            username="testuser",
            password="testpassword123",
            email="test@example.com",
        )
        auth_service.create_user(
            username="admin",
            password="adminpassword",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )

        # Generate reset token
        token = auth_service.generate_password_reset_token("testuser", "admin", "adminpassword")
        assert token is not None
        assert "reset_token_hash" in auth_service.users["testuser"]
        assert "reset_token_expiry" in auth_service.users["testuser"]

        # Reset password with token
        result = auth_service.reset_password_with_token("testuser", token, "newpassword")
        assert result is True
        
        # Verify token is removed
        assert "reset_token_hash" not in auth_service.users["testuser"]
        assert "reset_token_expiry" not in auth_service.users["testuser"]
        
        # Test authentication with new password
        auth_result, _ = auth_service.authenticate("testuser", "newpassword")
        assert auth_result == AuthResult.SUCCESS

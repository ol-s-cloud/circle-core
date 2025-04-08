"""Authentication module for Circle Core Framework.

Provides secure user authentication with Argon2 password hashing and account lockout features.
"""

import datetime
import hashlib
import json
import os
import secrets
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


class AuthResult(Enum):
    """Enum representing authentication result states."""

    SUCCESS = "success"
    INVALID_CREDENTIALS = "invalid_credentials"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_DISABLED = "account_disabled"
    ACCOUNT_EXPIRED = "account_expired"
    REQUIRES_MFA = "requires_mfa"
    MFA_FAILED = "mfa_failed"
    ERROR = "error"


class UserRole(Enum):
    """Enum representing user role levels."""

    GUEST = "guest"
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"


class AuthenticationService:
    """Service for user authentication and password management.

    This class provides functionality for securely authenticating users,
    managing password hashing, and implementing account lockout protection.
    """

    def __init__(
        self,
        user_db_path: Optional[str] = None,
        max_failed_attempts: int = 5,
        lockout_duration_minutes: int = 30,
        password_expiry_days: int = 90,
        min_password_length: int = 12,
    ):
        """Initialize the authentication service.

        Args:
            user_db_path: Path to user database file
            max_failed_attempts: Maximum number of failed login attempts before lockout
            lockout_duration_minutes: Duration of account lockout in minutes
            password_expiry_days: Number of days before passwords expire
            min_password_length: Minimum required password length
        """
        self.user_db_path = user_db_path or os.path.expanduser("~/.circle-core/auth/users.json")
        os.makedirs(os.path.dirname(self.user_db_path), exist_ok=True)

        self.max_failed_attempts = max_failed_attempts
        self.lockout_duration_minutes = lockout_duration_minutes
        self.password_expiry_days = password_expiry_days
        self.min_password_length = min_password_length

        # Initialize password hasher with secure parameters
        self.password_hasher = PasswordHasher(
            time_cost=3,       # Number of iterations
            memory_cost=65536, # Memory usage in kibibytes
            parallelism=4,     # Degree of parallelism
            hash_len=32,       # Length of hash in bytes
            salt_len=16,       # Length of salt in bytes
        )

        # Load user database
        self.users = self._load_users()

    def _load_users(self) -> Dict:
        """Load user database from file.

        Returns:
            Dictionary of user records
        """
        if not os.path.exists(self.user_db_path):
            return {}

        try:
            with open(self.user_db_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_users(self) -> None:
        """Save user database to file."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.user_db_path), exist_ok=True)

        # Write to a temporary file first, then rename for atomicity
        temp_file = f"{self.user_db_path}.tmp"
        with open(temp_file, "w") as f:
            json.dump(self.users, f, indent=2)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk

        os.replace(temp_file, self.user_db_path)  # Atomic replace
        os.chmod(self.user_db_path, 0o600)  # Restrict permissions

    def _is_account_locked(self, user: Dict) -> bool:
        """Check if an account is locked.

        Args:
            user: User record

        Returns:
            True if account is locked, False otherwise
        """
        if "locked_until" not in user:
            return False

        # Parse the locked_until timestamp
        locked_until = datetime.datetime.fromisoformat(user["locked_until"])
        
        # Check if lock has expired
        return datetime.datetime.now() < locked_until

    def _is_password_expired(self, user: Dict) -> bool:
        """Check if a user's password has expired.

        Args:
            user: User record

        Returns:
            True if password is expired, False otherwise
        """
        if "password_last_changed" not in user:
            return False

        # Parse the password_last_changed timestamp
        last_changed = datetime.datetime.fromisoformat(user["password_last_changed"])
        
        # Calculate expiry date
        expiry_date = last_changed + datetime.timedelta(days=self.password_expiry_days)
        
        # Check if password has expired
        return datetime.datetime.now() > expiry_date

    def authenticate(self, username: str, password: str) -> Tuple[AuthResult, Optional[Dict]]:
        """Authenticate a user with username and password.

        Args:
            username: Username
            password: Password

        Returns:
            Tuple of (AuthResult, user_data or None)
        """
        # Check if user exists
        if username not in self.users:
            return AuthResult.INVALID_CREDENTIALS, None

        user = self.users[username]

        # Check if account is locked
        if self._is_account_locked(user):
            return AuthResult.ACCOUNT_LOCKED, None

        # Check if account is disabled
        if user.get("disabled", False):
            return AuthResult.ACCOUNT_DISABLED, None

        # Check if password is expired
        if self._is_password_expired(user):
            return AuthResult.ACCOUNT_EXPIRED, None

        # Verify password
        try:
            self.password_hasher.verify(user["password_hash"], password)

            # Password matches, reset failed attempts
            user["failed_attempts"] = 0
            user["last_login"] = datetime.datetime.now().isoformat()

            # Check if rehash is needed (if parameters have changed)
            if self.password_hasher.check_needs_rehash(user["password_hash"]):
                user["password_hash"] = self.password_hasher.hash(password)

            self._save_users()

            # Check if MFA is required
            if user.get("mfa_enabled", False):
                return AuthResult.REQUIRES_MFA, user

            return AuthResult.SUCCESS, user

        except VerifyMismatchError:
            # Password doesn't match, increment failed attempts
            user["failed_attempts"] = user.get("failed_attempts", 0) + 1
            user["last_failed_attempt"] = datetime.datetime.now().isoformat()

            # Lock account if max attempts reached
            if user["failed_attempts"] >= self.max_failed_attempts:
                user["locked_until"] = (
                    datetime.datetime.now() + 
                    datetime.timedelta(minutes=self.lockout_duration_minutes)
                ).isoformat()

            self._save_users()
            return AuthResult.INVALID_CREDENTIALS, None

    def verify_mfa(self, username: str, mfa_code: str) -> Tuple[AuthResult, Optional[Dict]]:
        """Verify multi-factor authentication code.

        Args:
            username: Username
            mfa_code: MFA verification code

        Returns:
            Tuple of (AuthResult, user_data or None)
        """
        # Check if user exists
        if username not in self.users:
            return AuthResult.INVALID_CREDENTIALS, None

        user = self.users[username]

        # Check if MFA is enabled
        if not user.get("mfa_enabled", False):
            return AuthResult.SUCCESS, user

        # In a real implementation, this would validate TOTP or other MFA mechanisms
        # For this example, we'll use a simple placeholder
        if mfa_code == user.get("mfa_secret", ""):
            return AuthResult.SUCCESS, user
        else:
            return AuthResult.MFA_FAILED, None

    def create_user(
        self,
        username: str,
        password: str,
        email: str,
        role: Union[UserRole, str] = UserRole.USER,
        additional_data: Optional[Dict] = None,
    ) -> bool:
        """Create a new user.

        Args:
            username: Username
            password: Password
            email: Email address
            role: User role
            additional_data: Additional user data

        Returns:
            True if user was created, False if username exists
        """
        # Check if username already exists
        if username in self.users:
            return False

        # Check password strength
        if len(password) < self.min_password_length:
            raise ValueError(f"Password must be at least {self.min_password_length} characters")

        # Convert role to string if it's an enum
        if isinstance(role, UserRole):
            role = role.value

        # Generate password hash
        password_hash = self.password_hasher.hash(password)

        # Create user record
        user = {
            "username": username,
            "password_hash": password_hash,
            "email": email,
            "role": role,
            "created_at": datetime.datetime.now().isoformat(),
            "password_last_changed": datetime.datetime.now().isoformat(),
            "failed_attempts": 0,
            "mfa_enabled": False,
        }

        # Add additional data if provided
        if additional_data:
            user.update(additional_data)

        # Save user
        self.users[username] = user
        self._save_users()

        return True

    def update_password(
        self, username: str, current_password: str, new_password: str
    ) -> bool:
        """Update a user's password.

        Args:
            username: Username
            current_password: Current password
            new_password: New password

        Returns:
            True if password was updated, False if authentication failed
        """
        # Authenticate user first
        result, user = self.authenticate(username, current_password)

        if result != AuthResult.SUCCESS and result != AuthResult.REQUIRES_MFA:
            return False

        # Check password strength
        if len(new_password) < self.min_password_length:
            raise ValueError(f"Password must be at least {self.min_password_length} characters")

        # Update password hash
        self.users[username]["password_hash"] = self.password_hasher.hash(new_password)
        self.users[username]["password_last_changed"] = datetime.datetime.now().isoformat()

        # Reset failed attempts and locks
        self.users[username]["failed_attempts"] = 0
        if "locked_until" in self.users[username]:
            del self.users[username]["locked_until"]

        self._save_users()
        return True

    def reset_password(
        self, username: str, admin_username: str, admin_password: str, new_password: str
    ) -> bool:
        """Reset a user's password (admin function).

        Args:
            username: Username to reset
            admin_username: Admin username
            admin_password: Admin password
            new_password: New password for user

        Returns:
            True if password was reset, False if admin authentication failed
        """
        # Authenticate admin
        result, admin = self.authenticate(admin_username, admin_password)

        if result != AuthResult.SUCCESS and result != AuthResult.REQUIRES_MFA:
            return False

        # Check if admin has sufficient privileges
        if admin.get("role") not in ("admin", "system"):
            return False

        # Check if user exists
        if username not in self.users:
            return False

        # Check password strength
        if len(new_password) < self.min_password_length:
            raise ValueError(f"Password must be at least {self.min_password_length} characters")

        # Reset password
        self.users[username]["password_hash"] = self.password_hasher.hash(new_password)
        self.users[username]["password_last_changed"] = datetime.datetime.now().isoformat()

        # Reset failed attempts and locks
        self.users[username]["failed_attempts"] = 0
        if "locked_until" in self.users[username]:
            del self.users[username]["locked_until"]

        # Set password change required flag
        self.users[username]["password_change_required"] = True

        self._save_users()
        return True

    def disable_user(
        self, username: str, admin_username: str, admin_password: str
    ) -> bool:
        """Disable a user account (admin function).

        Args:
            username: Username to disable
            admin_username: Admin username
            admin_password: Admin password

        Returns:
            True if account was disabled, False if admin authentication failed
        """
        # Authenticate admin
        result, admin = self.authenticate(admin_username, admin_password)

        if result != AuthResult.SUCCESS and result != AuthResult.REQUIRES_MFA:
            return False

        # Check if admin has sufficient privileges
        if admin.get("role") not in ("admin", "system"):
            return False

        # Check if user exists
        if username not in self.users:
            return False

        # Disable account
        self.users[username]["disabled"] = True
        self._save_users()
        return True

    def enable_user(
        self, username: str, admin_username: str, admin_password: str
    ) -> bool:
        """Enable a user account (admin function).

        Args:
            username: Username to enable
            admin_username: Admin username
            admin_password: Admin password

        Returns:
            True if account was enabled, False if admin authentication failed
        """
        # Authenticate admin
        result, admin = self.authenticate(admin_username, admin_password)

        if result != AuthResult.SUCCESS and result != AuthResult.REQUIRES_MFA:
            return False

        # Check if admin has sufficient privileges
        if admin.get("role") not in ("admin", "system"):
            return False

        # Check if user exists
        if username not in self.users:
            return False

        # Enable account
        self.users[username]["disabled"] = False
        self._save_users()
        return True

    def enable_mfa(
        self, username: str, password: str, mfa_secret: str
    ) -> bool:
        """Enable multi-factor authentication for a user.

        Args:
            username: Username
            password: Password
            mfa_secret: MFA secret key

        Returns:
            True if MFA was enabled, False if authentication failed
        """
        # Authenticate user first
        result, user = self.authenticate(username, password)

        if result != AuthResult.SUCCESS and result != AuthResult.REQUIRES_MFA:
            return False

        # Enable MFA
        self.users[username]["mfa_enabled"] = True
        self.users[username]["mfa_secret"] = mfa_secret

        self._save_users()
        return True

    def disable_mfa(
        self, username: str, password: str
    ) -> bool:
        """Disable multi-factor authentication for a user.

        Args:
            username: Username
            password: Password

        Returns:
            True if MFA was disabled, False if authentication failed
        """
        # Authenticate user first
        result, user = self.authenticate(username, password)

        if result != AuthResult.SUCCESS and result != AuthResult.REQUIRES_MFA:
            return False

        # If MFA is required for this authentication, verify it was already provided
        if result == AuthResult.REQUIRES_MFA:
            return False

        # Disable MFA
        self.users[username]["mfa_enabled"] = False
        if "mfa_secret" in self.users[username]:
            del self.users[username]["mfa_secret"]

        self._save_users()
        return True

    def unlock_account(
        self, username: str, admin_username: str, admin_password: str
    ) -> bool:
        """Unlock a locked user account (admin function).

        Args:
            username: Username to unlock
            admin_username: Admin username
            admin_password: Admin password

        Returns:
            True if account was unlocked, False if admin authentication failed
        """
        # Authenticate admin
        result, admin = self.authenticate(admin_username, admin_password)

        if result != AuthResult.SUCCESS and result != AuthResult.REQUIRES_MFA:
            return False

        # Check if admin has sufficient privileges
        if admin.get("role") not in ("admin", "system"):
            return False

        # Check if user exists
        if username not in self.users:
            return False

        # Reset failed attempts and locks
        self.users[username]["failed_attempts"] = 0
        if "locked_until" in self.users[username]:
            del self.users[username]["locked_until"]

        self._save_users()
        return True

    def get_user_info(
        self, username: str, admin_username: str, admin_password: str
    ) -> Optional[Dict]:
        """Get user information (admin function).

        Args:
            username: Username to get info for
            admin_username: Admin username
            admin_password: Admin password

        Returns:
            User data dictionary or None if admin authentication failed
        """
        # Authenticate admin
        result, admin = self.authenticate(admin_username, admin_password)

        if result != AuthResult.SUCCESS and result != AuthResult.REQUIRES_MFA:
            return None

        # Check if admin has sufficient privileges
        if admin.get("role") not in ("admin", "system"):
            return None

        # Check if user exists
        if username not in self.users:
            return None

        # Return user data (excluding password hash)
        user_data = self.users[username].copy()
        user_data.pop("password_hash", None)
        return user_data

    def list_users(
        self, admin_username: str, admin_password: str
    ) -> Optional[List[Dict]]:
        """List all users (admin function).

        Args:
            admin_username: Admin username
            admin_password: Admin password

        Returns:
            List of user data dictionaries or None if admin authentication failed
        """
        # Authenticate admin
        result, admin = self.authenticate(admin_username, admin_password)

        if result != AuthResult.SUCCESS and result != AuthResult.REQUIRES_MFA:
            return None

        # Check if admin has sufficient privileges
        if admin.get("role") not in ("admin", "system"):
            return None

        # Return list of users (excluding password hashes)
        users_list = []
        for username, user_data in self.users.items():
            user_copy = user_data.copy()
            user_copy.pop("password_hash", None)
            users_list.append(user_copy)
            
        return users_list

    def generate_password_reset_token(
        self, username: str, admin_username: str, admin_password: str, expiry_hours: int = 24
    ) -> Optional[str]:
        """Generate a password reset token for a user (admin function).

        Args:
            username: Username to generate token for
            admin_username: Admin username
            admin_password: Admin password
            expiry_hours: Token expiry in hours

        Returns:
            Reset token or None if admin authentication failed
        """
        # Authenticate admin
        result, admin = self.authenticate(admin_username, admin_password)

        if result != AuthResult.SUCCESS and result != AuthResult.REQUIRES_MFA:
            return None

        # Check if admin has sufficient privileges
        if admin.get("role") not in ("admin", "system"):
            return None

        # Check if user exists
        if username not in self.users:
            return None

        # Generate secure token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expiry = (datetime.datetime.now() + datetime.timedelta(hours=expiry_hours)).isoformat()

        # Store token hash and expiry
        self.users[username]["reset_token_hash"] = token_hash
        self.users[username]["reset_token_expiry"] = expiry

        self._save_users()
        return token

    def reset_password_with_token(
        self, username: str, token: str, new_password: str
    ) -> bool:
        """Reset a password using a reset token.

        Args:
            username: Username
            token: Password reset token
            new_password: New password

        Returns:
            True if password was reset, False if token is invalid
        """
        # Check if user exists
        if username not in self.users:
            return False

        user = self.users[username]

        # Check if reset token exists and is not expired
        if "reset_token_hash" not in user or "reset_token_expiry" not in user:
            return False

        # Verify token hash
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if token_hash != user["reset_token_hash"]:
            return False

        # Check if token is expired
        expiry = datetime.datetime.fromisoformat(user["reset_token_expiry"])
        if datetime.datetime.now() > expiry:
            return False

        # Check password strength
        if len(new_password) < self.min_password_length:
            raise ValueError(f"Password must be at least {self.min_password_length} characters")

        # Reset password
        user["password_hash"] = self.password_hasher.hash(new_password)
        user["password_last_changed"] = datetime.datetime.now().isoformat()

        # Reset failed attempts and locks
        user["failed_attempts"] = 0
        if "locked_until" in user:
            del user["locked_until"]

        # Remove reset token
        del user["reset_token_hash"]
        del user["reset_token_expiry"]

        # Set password change required flag
        user["password_change_required"] = False

        self._save_users()
        return True

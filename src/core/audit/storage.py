"""Storage backends for audit logs.

Provides various storage options for secure audit log storage and retrieval.
"""

import abc
import base64
import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union

from ..encryption import EncryptionService, EncryptionAlgorithm, EncryptedData


class LogStorageBackend(abc.ABC):
    """Abstract base class for audit log storage backends."""

    @abc.abstractmethod
    def store_log_entry(self, entry: Dict) -> bool:
        """Store a log entry.

        Args:
            entry: Log entry to store

        Returns:
            True if successful, False otherwise
        """
        pass

    @abc.abstractmethod
    def store_log_entries(self, entries: List[Dict]) -> bool:
        """Store multiple log entries.

        Args:
            entries: List of log entries to store

        Returns:
            True if successful, False otherwise
        """
        pass

    @abc.abstractmethod
    def retrieve_log_entries(
        self, 
        start_time: Optional[float] = None, 
        end_time: Optional[float] = None,
        filters: Optional[Dict] = None,
        max_entries: Optional[int] = None
    ) -> List[Dict]:
        """Retrieve log entries within a time range.

        Args:
            start_time: Optional start time (Unix timestamp)
            end_time: Optional end time (Unix timestamp)
            filters: Optional filters to apply (field-value pairs)
            max_entries: Optional maximum number of entries to retrieve

        Returns:
            List of log entries
        """
        pass

    @abc.abstractmethod
    def get_chain_entries(self) -> List[Dict]:
        """Get all chain entries for verification.

        Returns:
            List of chain entries
        """
        pass

    @abc.abstractmethod
    def store_chain_entries(self, entries: List[Dict]) -> bool:
        """Store chain entries for verification.

        Args:
            entries: List of chain entries to store

        Returns:
            True if successful, False otherwise
        """
        pass


class FileLogStorage(LogStorageBackend):
    """File-based storage backend for audit logs.

    Stores logs in JSON files with rotation based on time or size.
    """

    def __init__(
        self,
        log_dir: Optional[str] = None,
        max_file_size_mb: int = 10,
        rotation_interval_hours: int = 24,
        retention_days: int = 90,
    ):
        """Initialize the file storage backend.

        Args:
            log_dir: Directory for log files
            max_file_size_mb: Maximum log file size in MB
            rotation_interval_hours: Rotate files after this many hours
            retention_days: Keep logs for this many days
        """
        self.log_dir = log_dir or os.path.expanduser("~/.circle-core/audit/logs")
        self.chain_file = os.path.join(self.log_dir, "chain.json")
        self.max_file_size = max_file_size_mb * 1024 * 1024  # Convert to bytes
        self.rotation_interval = timedelta(hours=rotation_interval_hours)
        self.retention_period = timedelta(days=retention_days)
        
        # Create log directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Initialize current log file
        self.current_log_file = self._get_current_log_file()

    def _get_current_log_file(self) -> str:
        """Get the path to the current log file.

        If no log files exist or all are rotated, create a new one.

        Returns:
            Path to the current log file
        """
        # List log files (excluding chain.json)
        log_files = [
            f for f in os.listdir(self.log_dir)
            if f.endswith(".json") and f != "chain.json"
        ]
        
        if not log_files:
            # Create a new log file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return os.path.join(self.log_dir, f"audit_{timestamp}.json")
            
        # Find the most recent log file
        log_files.sort(reverse=True)
        latest_file = os.path.join(self.log_dir, log_files[0])
        
        # Check if we need to rotate
        if self._should_rotate(latest_file):
            # Create a new log file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return os.path.join(self.log_dir, f"audit_{timestamp}.json")
            
        return latest_file

    def _should_rotate(self, log_file: str) -> bool:
        """Check if the log file should be rotated.

        Args:
            log_file: Path to the log file

        Returns:
            True if the file should be rotated, False otherwise
        """
        # Check if the file exists
        if not os.path.exists(log_file):
            return False
            
        # Check file size
        if os.path.getsize(log_file) >= self.max_file_size:
            return True
            
        # Check file age
        try:
            # Extract timestamp from filename
            filename = os.path.basename(log_file)
            timestamp_str = filename.replace("audit_", "").replace(".json", "")
            file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            
            # Check if file is older than rotation interval
            if datetime.now() - file_time > self.rotation_interval:
                return True
        except (ValueError, IndexError):
            # If we can't parse the timestamp, assume it's time to rotate
            return True
            
        return False

    def _clean_old_logs(self) -> None:
        """Remove log files older than the retention period."""
        # List log files (excluding chain.json)
        log_files = [
            f for f in os.listdir(self.log_dir)
            if f.endswith(".json") and f != "chain.json"
        ]
        
        for filename in log_files:
            try:
                # Extract timestamp from filename
                timestamp_str = filename.replace("audit_", "").replace(".json", "")
                file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                
                # Check if file is older than retention period
                if datetime.now() - file_time > self.retention_period:
                    # Remove the file
                    os.remove(os.path.join(self.log_dir, filename))
            except (ValueError, IndexError):
                # If we can't parse the timestamp, leave the file alone
                continue

    def store_log_entry(self, entry: Dict) -> bool:
        """Store a log entry in the current log file.

        Args:
            entry: Log entry to store

        Returns:
            True if successful, False otherwise
        """
        # Check if we need to clean up old logs
        self._clean_old_logs()
        
        # Check if we need to rotate
        if self._should_rotate(self.current_log_file):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_log_file = os.path.join(self.log_dir, f"audit_{timestamp}.json")
        
        # Initialize the file if it doesn't exist
        if not os.path.exists(self.current_log_file):
            with open(self.current_log_file, "w") as f:
                json.dump([], f)
                
        # Read existing entries
        try:
            with open(self.current_log_file, "r") as f:
                entries = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            entries = []
            
        # Add the new entry
        entries.append(entry)
        
        # Write to a temporary file first, then rename for atomicity
        temp_file = f"{self.current_log_file}.tmp"
        try:
            with open(temp_file, "w") as f:
                json.dump(entries, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Ensure data is written to disk
                
            # Make the file readable only by the owner
            os.chmod(temp_file, 0o600)
            
            # Atomically replace the log file
            os.replace(temp_file, self.current_log_file)
            
            return True
        except Exception:
            # Clean up temporary file if there was an error
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False

    def store_log_entries(self, entries: List[Dict]) -> bool:
        """Store multiple log entries.

        Args:
            entries: List of log entries to store

        Returns:
            True if all entries were stored, False otherwise
        """
        # Store each entry individually
        success = True
        for entry in entries:
            if not self.store_log_entry(entry):
                success = False
                
        return success

    def store_chain_entries(self, entries: List[Dict]) -> bool:
        """Store chain entries for verification.

        Args:
            entries: List of chain entries to store

        Returns:
            True if successful, False otherwise
        """
        # Write to a temporary file first, then rename for atomicity
        temp_file = f"{self.chain_file}.tmp"
        try:
            with open(temp_file, "w") as f:
                json.dump(entries, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Ensure data is written to disk
                
            # Make the file readable only by the owner
            os.chmod(temp_file, 0o600)
            
            # Atomically replace the chain file
            os.replace(temp_file, self.chain_file)
            
            return True
        except Exception:
            # Clean up temporary file if there was an error
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return False

    def retrieve_log_entries(
        self, 
        start_time: Optional[float] = None, 
        end_time: Optional[float] = None,
        filters: Optional[Dict] = None,
        max_entries: Optional[int] = None
    ) -> List[Dict]:
        """Retrieve log entries within a time range.

        Args:
            start_time: Optional start time (Unix timestamp)
            end_time: Optional end time (Unix timestamp)
            filters: Optional filters to apply (field-value pairs)
            max_entries: Optional maximum number of entries to retrieve

        Returns:
            List of log entries
        """
        # List log files (excluding chain.json)
        log_files = [
            os.path.join(self.log_dir, f) for f in os.listdir(self.log_dir)
            if f.endswith(".json") and f != "chain.json"
        ]
        
        # Sort log files by timestamp (newest first)
        log_files.sort(reverse=True)
        
        # Collect entries from all log files
        all_entries = []
        entries_count = 0
        
        for log_file in log_files:
            try:
                with open(log_file, "r") as f:
                    entries = json.load(f)
                    
                # Filter entries by time range and fields
                for entry in entries:
                    # Skip if we've reached the maximum
                    if max_entries is not None and entries_count >= max_entries:
                        break
                        
                    # Skip if outside time range
                    timestamp = entry.get("timestamp", 0)
                    if start_time is not None and timestamp < start_time:
                        continue
                    if end_time is not None and timestamp > end_time:
                        continue
                        
                    # Skip if filters don't match
                    if filters:
                        match = True
                        for key, value in filters.items():
                            if key not in entry or entry[key] != value:
                                match = False
                                break
                        if not match:
                            continue
                            
                    # Add the entry
                    all_entries.append(entry)
                    entries_count += 1
            except (json.JSONDecodeError, FileNotFoundError):
                # Skip invalid files
                continue
                
            # Stop if we've reached the maximum
            if max_entries is not None and entries_count >= max_entries:
                break
                
        return all_entries

    def get_chain_entries(self) -> List[Dict]:
        """Get all chain entries for verification.

        Returns:
            List of chain entries
        """
        try:
            with open(self.chain_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []


class EncryptedLogStorage(LogStorageBackend):
    """Encrypted storage backend for audit logs.

    Stores logs in encrypted format using the encryption service.
    """

    def __init__(
        self,
        base_storage: LogStorageBackend,
        encryption_service: Optional[EncryptionService] = None,
    ):
        """Initialize the encrypted storage backend.

        Args:
            base_storage: Base storage backend to use
            encryption_service: Encryption service to use
        """
        self.base_storage = base_storage
        self.encryption_service = encryption_service or EncryptionService()

    def _encrypt_entry(self, entry: Dict) -> Dict:
        """Encrypt a log entry.

        Args:
            entry: Log entry to encrypt

        Returns:
            Encrypted entry
        """
        # Convert to JSON
        json_data = json.dumps(entry)
        
        # Encrypt
        encrypted_data = self.encryption_service.encrypt(json_data)
        
        # Format for storage
        return {
            "timestamp": entry.get("timestamp", 0),  # Keep timestamp in plaintext for filtering
            "encrypted": True,
            "algorithm": encrypted_data.algorithm.value,
            "key_id": encrypted_data.key_id,
            "iv": base64.b64encode(encrypted_data.iv).decode('utf-8') if encrypted_data.iv else None,
            "tag": base64.b64encode(encrypted_data.tag).decode('utf-8') if encrypted_data.tag else None,
            "data": base64.b64encode(encrypted_data.ciphertext).decode('utf-8')
        }

    def _decrypt_entry(self, encrypted_entry: Dict) -> Dict:
        """Decrypt a log entry.

        Args:
            encrypted_entry: Encrypted log entry

        Returns:
            Decrypted entry
        """
        # Skip if not encrypted
        if not encrypted_entry.get("encrypted", False):
            return encrypted_entry
            
        # Parse encrypted data
        algorithm = EncryptionAlgorithm(encrypted_entry["algorithm"])
        key_id = encrypted_entry["key_id"]
        iv = base64.b64decode(encrypted_entry["iv"]) if encrypted_entry.get("iv") else None
        tag = base64.b64decode(encrypted_entry["tag"]) if encrypted_entry.get("tag") else None
        ciphertext = base64.b64decode(encrypted_entry["data"])
        
        # Create EncryptedData object
        encrypted_data = EncryptedData(
            ciphertext=ciphertext,
            algorithm=algorithm,
            key_id=key_id,
            iv=iv,
            tag=tag
        )
        
        # Decrypt
        decrypted_data = self.encryption_service.decrypt(encrypted_data)
        
        # Parse JSON
        return json.loads(decrypted_data.decode('utf-8'))

    def store_log_entry(self, entry: Dict) -> bool:
        """Store an encrypted log entry.

        Args:
            entry: Log entry to store

        Returns:
            True if successful, False otherwise
        """
        # Encrypt the entry
        encrypted_entry = self._encrypt_entry(entry)
        
        # Store using base storage
        return self.base_storage.store_log_entry(encrypted_entry)

    def store_log_entries(self, entries: List[Dict]) -> bool:
        """Store multiple encrypted log entries.

        Args:
            entries: List of log entries to store

        Returns:
            True if all entries were stored, False otherwise
        """
        # Encrypt each entry
        encrypted_entries = [self._encrypt_entry(entry) for entry in entries]
        
        # Store using base storage
        return self.base_storage.store_log_entries(encrypted_entries)

    def retrieve_log_entries(
        self, 
        start_time: Optional[float] = None, 
        end_time: Optional[float] = None,
        filters: Optional[Dict] = None,
        max_entries: Optional[int] = None
    ) -> List[Dict]:
        """Retrieve and decrypt log entries within a time range.

        Args:
            start_time: Optional start time (Unix timestamp)
            end_time: Optional end time (Unix timestamp)
            filters: Optional filters to apply (field-value pairs)
            max_entries: Optional maximum number of entries to retrieve

        Returns:
            List of decrypted log entries
        """
        # Retrieve encrypted entries
        encrypted_entries = self.base_storage.retrieve_log_entries(
            start_time=start_time,
            end_time=end_time,
            filters=filters,
            max_entries=max_entries
        )
        
        # Decrypt each entry
        decrypted_entries = []
        for entry in encrypted_entries:
            try:
                decrypted_entry = self._decrypt_entry(entry)
                decrypted_entries.append(decrypted_entry)
            except Exception:
                # Skip entries that can't be decrypted
                continue
                
        return decrypted_entries

    def get_chain_entries(self) -> List[Dict]:
        """Get all chain entries for verification.

        Returns:
            List of chain entries
        """
        # Chain entries are not encrypted
        return self.base_storage.get_chain_entries()
        
    def store_chain_entries(self, entries: List[Dict]) -> bool:
        """Store chain entries for verification.

        Args:
            entries: List of chain entries to store

        Returns:
            True if successful, False otherwise
        """
        # Chain entries are not encrypted
        return self.base_storage.store_chain_entries(entries)

"""Audit logging for Circle Core Framework.

Provides a secure audit logging facility with tamper-evident features.
"""

import enum
import json
import os
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from .chain import HashChain, ChainVerificationResult
from .storage import LogStorageBackend, FileLogStorage, EncryptedLogStorage


class AuditLogLevel(enum.Enum):
    """Enum representing audit log levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    ALERT = "alert"
    CRITICAL = "critical"


@dataclass
class AuditLogEntry:
    """Container for audit log entry data."""

    id: str
    timestamp: float
    level: AuditLogLevel
    event_type: str
    message: str
    user_id: Optional[str] = None
    source: Optional[str] = None
    resource: Optional[str] = None
    details: Optional[Dict] = None
    chain_hash: Optional[str] = None


class AuditLogger:
    """Secure audit logging facility with tamper-evident features.

    This class provides a comprehensive audit logging facility with
    cryptographic integrity protection, secure storage, and compliance features.
    """

    def __init__(
        self,
        app_name: str,
        storage_backend: Optional[LogStorageBackend] = None,
        hash_chain: Optional[HashChain] = None,
        min_log_level: AuditLogLevel = AuditLogLevel.INFO,
        use_encryption: bool = True,
        sync_interval_seconds: int = 10,
    ):
        """Initialize the audit logger.

        Args:
            app_name: Name of the application
            storage_backend: Optional storage backend
            hash_chain: Optional hash chain for tamper-evidence
            min_log_level: Minimum log level to record
            use_encryption: Whether to encrypt log entries
            sync_interval_seconds: Interval for syncing the hash chain to storage
        """
        self.app_name = app_name
        self.min_log_level = min_log_level
        self.hostname = socket.gethostname()
        
        # Initialize storage backend
        base_storage = storage_backend or FileLogStorage()
        self.storage = EncryptedLogStorage(base_storage) if use_encryption else base_storage
        
        # Initialize hash chain
        self.hash_chain = hash_chain or HashChain()
        
        # Load existing chain if available
        chain_entries = self.storage.get_chain_entries()
        if chain_entries:
            result, invalid_seq = self.hash_chain.import_chain(chain_entries)
            if result != ChainVerificationResult.VALID:
                # Handle invalid chain (for now, just warn and start a new chain)
                print(f"WARNING: Invalid hash chain detected: {result}. Starting new chain.")
                self.hash_chain = HashChain()
        
        # Buffer for batching log entries
        self.log_buffer = []
        self.buffer_lock = threading.Lock()
        
        # Set up synchronization
        self.sync_interval = sync_interval_seconds
        self.last_sync_time = time.time()
        self.sync_thread = None
        
        # Start sync thread if interval > 0
        if self.sync_interval > 0:
            self._start_sync_thread()

    def _start_sync_thread(self) -> None:
        """Start the background thread for syncing the hash chain."""
        if self.sync_thread is not None and self.sync_thread.is_alive():
            return
            
        self.sync_thread = threading.Thread(
            target=self._sync_loop,
            daemon=True,
            name="AuditLogSyncThread"
        )
        self.sync_thread.start()

    def _sync_loop(self) -> None:
        """Background loop for syncing the hash chain to storage."""
        while True:
            time.sleep(self.sync_interval)
            try:
                self._sync_chain()
                self._flush_buffer()
            except Exception as e:
                # Log any errors but don't crash
                print(f"ERROR in audit log sync: {e}")

    def _sync_chain(self) -> bool:
        """Sync the hash chain to storage.

        Returns:
            True if successful, False otherwise
        """
        chain_entries = self.hash_chain.export_chain()
        return self.storage.store_chain_entries(chain_entries)

    def _flush_buffer(self) -> bool:
        """Flush the log buffer to storage.

        Returns:
            True if successful, False otherwise
        """
        with self.buffer_lock:
            if not self.log_buffer:
                return True
                
            entries_to_flush = self.log_buffer.copy()
            self.log_buffer.clear()
            
        return self.storage.store_log_entries(entries_to_flush)

    def log(
        self,
        level: AuditLogLevel,
        event_type: str,
        message: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict] = None,
    ) -> Optional[AuditLogEntry]:
        """Log an audit event.

        Args:
            level: Severity level
            event_type: Type of event (e.g., "login", "access", "modify")
            message: Human-readable message
            user_id: Optional ID of the user who performed the action
            resource: Optional resource that was accessed/modified
            details: Optional additional details about the event

        Returns:
            AuditLogEntry if logged, None if below minimum level
        """
        # Check if below minimum log level
        if level.value < self.min_log_level.value:
            return None
            
        # Create log entry
        entry_id = str(uuid.uuid4())
        timestamp = time.time()
        
        # Create basic entry data
        entry_data = {
            "id": entry_id,
            "timestamp": timestamp,
            "level": level.value,
            "event_type": event_type,
            "message": message,
            "app_name": self.app_name,
            "hostname": self.hostname,
        }
        
        # Add optional fields
        if user_id:
            entry_data["user_id"] = user_id
        if resource:
            entry_data["resource"] = resource
        if details:
            entry_data["details"] = details
            
        # Add to hash chain for tamper-evidence
        chain_entry = self.hash_chain.add_entry(entry_data)
        entry_data["chain_hash"] = chain_entry.hash
        
        # Create the log entry object
        log_entry = AuditLogEntry(
            id=entry_id,
            timestamp=timestamp,
            level=level,
            event_type=event_type,
            message=message,
            user_id=user_id,
            source=f"{self.app_name}@{self.hostname}",
            resource=resource,
            details=details,
            chain_hash=chain_entry.hash
        )
        
        # Add to buffer
        with self.buffer_lock:
            self.log_buffer.append(entry_data)
            
        # Sync immediately for high-severity events
        if level in (AuditLogLevel.ALERT, AuditLogLevel.CRITICAL):
            self._sync_chain()
            self._flush_buffer()
            
        # Check if it's time for a regular sync
        current_time = time.time()
        if current_time - self.last_sync_time > self.sync_interval:
            self.last_sync_time = current_time
            self._sync_chain()
            self._flush_buffer()
            
        return log_entry

    def info(
        self,
        event_type: str,
        message: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict] = None,
    ) -> Optional[AuditLogEntry]:
        """Log an informational audit event.

        Args:
            event_type: Type of event
            message: Human-readable message
            user_id: Optional ID of the user who performed the action
            resource: Optional resource that was accessed/modified
            details: Optional additional details about the event

        Returns:
            AuditLogEntry if logged, None if below minimum level
        """
        return self.log(
            level=AuditLogLevel.INFO,
            event_type=event_type,
            message=message,
            user_id=user_id,
            resource=resource,
            details=details
        )

    def warning(
        self,
        event_type: str,
        message: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict] = None,
    ) -> Optional[AuditLogEntry]:
        """Log a warning audit event.

        Args:
            event_type: Type of event
            message: Human-readable message
            user_id: Optional ID of the user who performed the action
            resource: Optional resource that was accessed/modified
            details: Optional additional details about the event

        Returns:
            AuditLogEntry if logged, None if below minimum level
        """
        return self.log(
            level=AuditLogLevel.WARNING,
            event_type=event_type,
            message=message,
            user_id=user_id,
            resource=resource,
            details=details
        )

    def error(
        self,
        event_type: str,
        message: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict] = None,
    ) -> Optional[AuditLogEntry]:
        """Log an error audit event.

        Args:
            event_type: Type of event
            message: Human-readable message
            user_id: Optional ID of the user who performed the action
            resource: Optional resource that was accessed/modified
            details: Optional additional details about the event

        Returns:
            AuditLogEntry if logged, None if below minimum level
        """
        return self.log(
            level=AuditLogLevel.ERROR,
            event_type=event_type,
            message=message,
            user_id=user_id,
            resource=resource,
            details=details
        )

    def alert(
        self,
        event_type: str,
        message: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict] = None,
    ) -> Optional[AuditLogEntry]:
        """Log an alert audit event.

        Args:
            event_type: Type of event
            message: Human-readable message
            user_id: Optional ID of the user who performed the action
            resource: Optional resource that was accessed/modified
            details: Optional additional details about the event

        Returns:
            AuditLogEntry if logged, None if below minimum level
        """
        return self.log(
            level=AuditLogLevel.ALERT,
            event_type=event_type,
            message=message,
            user_id=user_id,
            resource=resource,
            details=details
        )

    def critical(
        self,
        event_type: str,
        message: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        details: Optional[Dict] = None,
    ) -> Optional[AuditLogEntry]:
        """Log a critical audit event.

        Args:
            event_type: Type of event
            message: Human-readable message
            user_id: Optional ID of the user who performed the action
            resource: Optional resource that was accessed/modified
            details: Optional additional details about the event

        Returns:
            AuditLogEntry if logged, None if below minimum level
        """
        return self.log(
            level=AuditLogLevel.CRITICAL,
            event_type=event_type,
            message=message,
            user_id=user_id,
            resource=resource,
            details=details
        )

    def get_logs(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        level: Optional[AuditLogLevel] = None,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        max_entries: Optional[int] = None,
    ) -> List[Dict]:
        """Retrieve audit logs with optional filtering.

        Args:
            start_time: Optional start time (Unix timestamp)
            end_time: Optional end time (Unix timestamp)
            level: Optional log level filter
            event_type: Optional event type filter
            user_id: Optional user ID filter
            resource: Optional resource filter
            max_entries: Optional maximum number of entries to retrieve

        Returns:
            List of audit log entries
        """
        # Build filters
        filters = {}
        if level:
            filters["level"] = level.value
        if event_type:
            filters["event_type"] = event_type
        if user_id:
            filters["user_id"] = user_id
        if resource:
            filters["resource"] = resource
            
        # Retrieve from storage
        return self.storage.retrieve_log_entries(
            start_time=start_time,
            end_time=end_time,
            filters=filters,
            max_entries=max_entries
        )

    def verify_integrity(self) -> Tuple[ChainVerificationResult, Optional[int]]:
        """Verify the integrity of the audit log chain.

        Returns:
            Tuple of (verification_result, first_invalid_sequence)
        """
        # Load chain from storage
        chain_entries = self.storage.get_chain_entries()
        
        # Create a temporary chain for verification
        verification_chain = HashChain(
            algorithm=self.hash_chain.algorithm,
            secret_key=self.hash_chain.secret_key
        )
        
        # Import and verify
        return verification_chain.import_chain(chain_entries)

    def close(self) -> None:
        """Flush logs and close the logger."""
        # Sync the chain and flush the buffer
        self._sync_chain()
        self._flush_buffer()
        
        # Stop the sync thread if running
        if self.sync_thread is not None and self.sync_thread.is_alive():
            # We can't really stop the thread, but we can make sure
            # everything is flushed before exiting
            pass

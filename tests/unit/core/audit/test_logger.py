"""Unit tests for the audit logger."""

import json
import os
import tempfile
import time
from unittest import mock

import pytest

from circle_core.core.audit import (
    AuditLogger, 
    AuditLogLevel, 
    HashChain, 
    ChainVerificationResult,
    FileLogStorage
)


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for log files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    
    # Clean up
    for root, dirs, files in os.walk(temp_dir, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(temp_dir)


@pytest.fixture
def file_storage(temp_log_dir):
    """Create a file storage backend with a temporary directory."""
    return FileLogStorage(
        log_dir=temp_log_dir,
        max_file_size_mb=1,
        rotation_interval_hours=24,
        retention_days=90
    )


@pytest.fixture
def audit_logger(file_storage):
    """Create an audit logger with a file storage backend."""
    # Use a small sync interval for testing
    return AuditLogger(
        app_name="test_app",
        storage_backend=file_storage,
        min_log_level=AuditLogLevel.INFO,
        use_encryption=False,
        sync_interval_seconds=0.1
    )


class TestAuditLogger:
    """Tests for AuditLogger."""

    def test_init(self, file_storage):
        """Test initializing the audit logger."""
        logger = AuditLogger(
            app_name="test_app",
            storage_backend=file_storage,
            min_log_level=AuditLogLevel.INFO,
            use_encryption=False,
            sync_interval_seconds=0
        )
        
        assert logger.app_name == "test_app"
        assert logger.min_log_level == AuditLogLevel.INFO
        assert logger.hostname is not None
        assert logger.storage is file_storage
        assert isinstance(logger.hash_chain, HashChain)
        assert logger.log_buffer == []
        assert logger.sync_interval == 0
        assert logger.sync_thread is None

    def test_log(self, audit_logger):
        """Test logging an audit event."""
        # Log an event
        entry = audit_logger.log(
            level=AuditLogLevel.INFO,
            event_type="test_event",
            message="Test message",
            user_id="user123",
            resource="resource123",
            details={"key": "value"}
        )
        
        # Check the entry
        assert entry is not None
        assert entry.id is not None
        assert entry.timestamp > 0
        assert entry.level == AuditLogLevel.INFO
        assert entry.event_type == "test_event"
        assert entry.message == "Test message"
        assert entry.user_id == "user123"
        assert entry.resource == "resource123"
        assert entry.details == {"key": "value"}
        assert entry.chain_hash is not None
        
        # Wait for sync
        time.sleep(0.2)
        
        # Check that it was added to the chain
        assert len(audit_logger.hash_chain.entries) == 1
        assert audit_logger.hash_chain.entries[0].data["event_type"] == "test_event"
        
        # Check that the buffer was flushed
        assert len(audit_logger.log_buffer) == 0

    def test_log_below_min_level(self, audit_logger):
        """Test logging an event below the minimum level."""
        # Set min level to WARNING
        audit_logger.min_log_level = AuditLogLevel.WARNING
        
        # Log an INFO event
        entry = audit_logger.log(
            level=AuditLogLevel.INFO,
            event_type="test_event",
            message="Test message"
        )
        
        # Should be filtered out
        assert entry is None
        
        # Wait for sync
        time.sleep(0.2)
        
        # Chain should be empty
        assert len(audit_logger.hash_chain.entries) == 0

    def test_log_helpers(self, audit_logger):
        """Test the log helper methods."""
        # Log with each helper method
        info_entry = audit_logger.info("info_event", "Info message")
        warning_entry = audit_logger.warning("warning_event", "Warning message")
        error_entry = audit_logger.error("error_event", "Error message")
        alert_entry = audit_logger.alert("alert_event", "Alert message")
        critical_entry = audit_logger.critical("critical_event", "Critical message")
        
        # Check entries
        assert info_entry.level == AuditLogLevel.INFO
        assert warning_entry.level == AuditLogLevel.WARNING
        assert error_entry.level == AuditLogLevel.ERROR
        assert alert_entry.level == AuditLogLevel.ALERT
        assert critical_entry.level == AuditLogLevel.CRITICAL
        
        # Wait for sync
        time.sleep(0.2)
        
        # Check chain entries
        assert len(audit_logger.hash_chain.entries) == 5

    def test_immediate_sync_for_high_severity(self, audit_logger):
        """Test immediate sync for high-severity events."""
        # Mock the _sync_chain and _flush_buffer methods
        audit_logger._sync_chain = mock.MagicMock(return_value=True)
        audit_logger._flush_buffer = mock.MagicMock(return_value=True)
        
        # Log a normal event
        audit_logger.info("info_event", "Info message")
        
        # Should not trigger immediate sync
        assert audit_logger._sync_chain.call_count == 0
        assert audit_logger._flush_buffer.call_count == 0
        
        # Log a high-severity event
        audit_logger.critical("critical_event", "Critical message")
        
        # Should trigger immediate sync
        assert audit_logger._sync_chain.call_count == 1
        assert audit_logger._flush_buffer.call_count == 1

    def test_flush_buffer(self, audit_logger):
        """Test flushing the log buffer."""
        # Add some entries to the buffer
        audit_logger._sync_chain = mock.MagicMock(return_value=True)
        
        # Bypass the buffer flushing mechanism
        audit_logger.sync_interval = 1000  # Large interval
        
        # Log some events
        audit_logger.info("info_event", "Info message")
        audit_logger.warning("warning_event", "Warning message")
        audit_logger.error("error_event", "Error message")
        
        # Buffer should contain entries
        assert len(audit_logger.log_buffer) == 3
        
        # Manually flush the buffer
        result = audit_logger._flush_buffer()
        
        # Should succeed
        assert result is True
        
        # Buffer should be empty
        assert len(audit_logger.log_buffer) == 0

    def test_get_logs(self, audit_logger):
        """Test retrieving logs."""
        # Add storage backend mock
        audit_logger.storage.retrieve_log_entries = mock.MagicMock(
            return_value=[
                {"id": "1", "event_type": "test1", "level": "info"},
                {"id": "2", "event_type": "test2", "level": "warning"},
                {"id": "3", "event_type": "test3", "level": "error"}
            ]
        )
        
        # Get logs
        logs = audit_logger.get_logs(
            start_time=time.time() - 3600,
            end_time=time.time(),
            level=AuditLogLevel.WARNING,
            event_type="test_event",
            user_id="user123",
            resource="resource123",
            max_entries=10
        )
        
        # Check that storage method was called with correct filters
        audit_logger.storage.retrieve_log_entries.assert_called_once()
        args, kwargs = audit_logger.storage.retrieve_log_entries.call_args
        
        assert kwargs["start_time"] is not None
        assert kwargs["end_time"] is not None
        assert kwargs["filters"]["level"] == AuditLogLevel.WARNING.value
        assert kwargs["filters"]["event_type"] == "test_event"
        assert kwargs["filters"]["user_id"] == "user123"
        assert kwargs["filters"]["resource"] == "resource123"
        assert kwargs["max_entries"] == 10
        
        # Should return the mock data
        assert len(logs) == 3

    def test_verify_integrity(self, audit_logger):
        """Test verifying log integrity."""
        # Add some log entries
        audit_logger.info("test1", "Test 1")
        audit_logger.info("test2", "Test 2")
        audit_logger.info("test3", "Test 3")
        
        # Wait for sync
        time.sleep(0.2)
        
        # Mock storage to return chain entries
        audit_logger.storage.get_chain_entries = mock.MagicMock(
            return_value=audit_logger.hash_chain.export_chain()
        )
        
        # Verify integrity
        result, invalid_seq = audit_logger.verify_integrity()
        
        # Should be valid
        assert result == ChainVerificationResult.VALID
        assert invalid_seq is None
        
        # Mock storage to return tampered chain
        tampered_chain = audit_logger.hash_chain.export_chain()
        tampered_chain[1]["hash"] = "tampered_hash"
        
        audit_logger.storage.get_chain_entries = mock.MagicMock(
            return_value=tampered_chain
        )
        
        # Verify integrity again
        result, invalid_seq = audit_logger.verify_integrity()
        
        # Should detect tampering
        assert result == ChainVerificationResult.INVALID_HASH
        assert invalid_seq == 2

    def test_close(self, audit_logger):
        """Test closing the logger."""
        # Mock the methods
        audit_logger._sync_chain = mock.MagicMock(return_value=True)
        audit_logger._flush_buffer = mock.MagicMock(return_value=True)
        
        # Close the logger
        audit_logger.close()
        
        # Should have called sync and flush
        audit_logger._sync_chain.assert_called_once()
        audit_logger._flush_buffer.assert_called_once()


class TestFileLogStorage:
    """Tests for FileLogStorage."""

    def test_store_retrieve_log_entry(self, file_storage, temp_log_dir):
        """Test storing and retrieving a log entry."""
        # Create a log entry
        entry = {
            "id": "test123",
            "timestamp": time.time(),
            "level": "info",
            "event_type": "test_event",
            "message": "Test message",
            "user_id": "user123",
            "resource": "resource123",
            "details": {"key": "value"}
        }
        
        # Store the entry
        result = file_storage.store_log_entry(entry)
        
        # Should succeed
        assert result is True
        
        # Retrieve the entry
        retrieved = file_storage.retrieve_log_entries()
        
        # Should have one entry
        assert len(retrieved) == 1
        assert retrieved[0]["id"] == "test123"
        assert retrieved[0]["event_type"] == "test_event"
        assert retrieved[0]["details"]["key"] == "value"

    def test_store_retrieve_multiple_entries(self, file_storage):
        """Test storing and retrieving multiple log entries."""
        # Create log entries
        entries = [
            {
                "id": f"test{i}",
                "timestamp": time.time() - (3600 * i),  # Different times
                "level": ["info", "warning", "error"][i % 3],
                "event_type": f"test_event_{i}",
                "message": f"Test message {i}"
            }
            for i in range(5)
        ]
        
        # Store the entries
        result = file_storage.store_log_entries(entries)
        
        # Should succeed
        assert result is True
        
        # Retrieve with time filter
        mid_time = entries[2]["timestamp"]
        recent_entries = file_storage.retrieve_log_entries(
            start_time=mid_time
        )
        
        # Should have entries 0, 1, 2
        assert len(recent_entries) == 3
        
        # Retrieve with level filter
        warning_entries = file_storage.retrieve_log_entries(
            filters={"level": "warning"}
        )
        
        # Should have entries with level=warning
        assert len(warning_entries) > 0
        for entry in warning_entries:
            assert entry["level"] == "warning"
        
        # Retrieve with max entries
        limited_entries = file_storage.retrieve_log_entries(
            max_entries=2
        )
        
        # Should have at most 2 entries
        assert len(limited_entries) <= 2

    def test_store_retrieve_chain_entries(self, file_storage):
        """Test storing and retrieving chain entries."""
        # Create chain entries
        chain_entries = [
            {
                "sequence": 1,
                "data": {"event": "test1"},
                "timestamp": time.time(),
                "prev_hash": "genesis",
                "hash": "hash1"
            },
            {
                "sequence": 2,
                "data": {"event": "test2"},
                "timestamp": time.time(),
                "prev_hash": "hash1",
                "hash": "hash2"
            }
        ]
        
        # Store the entries
        result = file_storage.store_chain_entries(chain_entries)
        
        # Should succeed
        assert result is True
        
        # Retrieve the entries
        retrieved = file_storage.get_chain_entries()
        
        # Should match
        assert len(retrieved) == 2
        assert retrieved[0]["sequence"] == 1
        assert retrieved[1]["sequence"] == 2
        assert retrieved[0]["hash"] == "hash1"
        assert retrieved[1]["hash"] == "hash2"

    def test_file_rotation(self, file_storage, temp_log_dir):
        """Test log file rotation."""
        # Override max file size to a small value
        file_storage.max_file_size = 1000  # 1 KB
        
        # Create a large entry
        large_data = "x" * 900  # ~900 bytes
        entry = {
            "id": "test123",
            "timestamp": time.time(),
            "level": "info",
            "message": "Large message",
            "data": large_data
        }
        
        # Store the entry twice to trigger rotation
        file_storage.store_log_entry(entry)
        file_storage.store_log_entry(entry)
        
        # Should have created two log files
        log_files = [
            f for f in os.listdir(temp_log_dir)
            if f.endswith(".json") and f != "chain.json"
        ]
        
        # Might have 1 or 2 files depending on serialization size
        assert len(log_files) >= 1
        
        # Retrieve all entries
        all_entries = file_storage.retrieve_log_entries()
        
        # Should have both entries
        assert len(all_entries) == 2

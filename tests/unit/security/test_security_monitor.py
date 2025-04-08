"""Unit tests for the security monitor module."""

import datetime
import json
import tempfile
from unittest import mock

import pytest

from src.security.security_monitor.monitor import (
    SecurityEvent,
    SecurityMonitor,
    SeverityLevel,
)


class TestSecurityEvent:
    """Test cases for the SecurityEvent class."""

    def test_event_initialization(self):
        """Test initialization of a security event."""
        event = SecurityEvent(
            event_type="authentication_failure",
            severity=SeverityLevel.MEDIUM,
            source="auth_service",
            details={"username": "test_user", "ip": "192.168.1.1"},
        )

        assert event.event_type == "authentication_failure"
        assert event.severity == SeverityLevel.MEDIUM
        assert event.source == "auth_service"
        assert event.details["username"] == "test_user"
        assert event.details["ip"] == "192.168.1.1"
        assert event.timestamp is not None
        assert event.event_id is not None

    def test_event_to_dict(self):
        """Test converting a security event to a dictionary."""
        timestamp = datetime.datetime(2025, 4, 8, 12, 0, 0)
        event = SecurityEvent(
            event_type="authentication_failure",
            severity=SeverityLevel.MEDIUM,
            source="auth_service",
            details={"username": "test_user"},
            timestamp=timestamp,
        )

        event_dict = event.to_dict()

        assert event_dict["event_type"] == "authentication_failure"
        assert event_dict["severity"] == "medium"
        assert event_dict["source"] == "auth_service"
        assert event_dict["details"]["username"] == "test_user"
        assert event_dict["timestamp"] == "2025-04-08T12:00:00"


class TestSecurityMonitor:
    """Test cases for the SecurityMonitor class."""

    def test_monitor_initialization(self):
        """Test initialization of a security monitor."""
        with tempfile.NamedTemporaryFile() as temp_file:
            monitor = SecurityMonitor(log_path=temp_file.name)

            assert monitor.log_path == temp_file.name
            assert monitor.alert_handlers == []
            assert monitor.anomaly_detection_enabled is True
            assert monitor.event_history == []

    def test_create_and_log_event(self):
        """Test creating and logging a security event."""
        with tempfile.NamedTemporaryFile() as temp_file:
            monitor = SecurityMonitor(log_path=temp_file.name)

            # Create and log event
            event = monitor.create_event(
                event_type="data_access",
                severity="info",
                source="storage_service",
                details={"file": "test.txt", "user": "test_user"},
            )

            # Check event was added to history
            assert len(monitor.event_history) == 1
            assert monitor.event_history[0] == event

            # Check event was logged to file
            temp_file.seek(0)
            log_content = temp_file.read().decode("utf-8")
            assert "data_access" in log_content
            assert "storage_service" in log_content

    def test_get_recent_events(self):
        """Test retrieving recent security events."""
        with tempfile.NamedTemporaryFile() as temp_file:
            monitor = SecurityMonitor(log_path=temp_file.name)

            # Create events with different severities
            monitor.create_event(
                event_type="authentication_success",
                severity=SeverityLevel.INFO,
                source="auth_service",
                details={"username": "user1"},
            )
            monitor.create_event(
                event_type="authentication_failure",
                severity=SeverityLevel.MEDIUM,
                source="auth_service",
                details={"username": "user2"},
            )
            monitor.create_event(
                event_type="unauthorized_access",
                severity=SeverityLevel.HIGH,
                source="api_gateway",
                details={"endpoint": "/admin"},
            )

            # Get all recent events
            recent_events = monitor.get_recent_events()
            assert len(recent_events) == 3

            # Get events filtered by severity
            medium_events = monitor.get_recent_events(severity=SeverityLevel.MEDIUM)
            assert len(medium_events) == 1
            assert medium_events[0].event_type == "authentication_failure"

    def test_anomaly_detection(self):
        """Test anomaly detection in security events."""
        with tempfile.NamedTemporaryFile() as temp_file:
            monitor = SecurityMonitor(log_path=temp_file.name)

            # Create multiple authentication failures in quick succession
            # We need to mock the timestamp to ensure they appear to happen within the time window
            now = datetime.datetime.now()
            
            # Patch the datetime.now() method
            with mock.patch(
                "src.security.security_monitor.monitor.datetime.datetime"
            ) as mock_datetime:
                mock_datetime.now.return_value = now
                # For the SecurityEvent._generate_event_id method
                mock_datetime.datetime = datetime.datetime

                # Create first authentication failure
                monitor.create_event(
                    event_type="authentication_failure",
                    severity=SeverityLevel.MEDIUM,
                    source="auth_service",
                    details={"username": "user1"},
                )

                # Create second authentication failure
                monitor.create_event(
                    event_type="authentication_failure",
                    severity=SeverityLevel.MEDIUM,
                    source="auth_service",
                    details={"username": "user1"},
                )

                # Create third authentication failure (should trigger anomaly)
                monitor.create_event(
                    event_type="authentication_failure",
                    severity=SeverityLevel.MEDIUM,
                    source="auth_service",
                    details={"username": "user1"},
                )

                # Check for anomaly event
                anomaly_events = [
                    e for e in monitor.event_history if e.event_type == "anomaly_detected"
                ]
                assert len(anomaly_events) == 1
                assert anomaly_events[0].severity == SeverityLevel.HIGH
                assert "rapid_auth_failures" in anomaly_events[0].details["anomaly_type"]

    def test_alert_handlers(self):
        """Test alert handlers for security events."""
        with tempfile.NamedTemporaryFile() as temp_file:
            # Create a mock alert handler
            mock_handler = mock.MagicMock()
            
            # Initialize monitor with the mock handler
            monitor = SecurityMonitor(
                log_path=temp_file.name,
                alert_handlers=[mock_handler],
            )

            # Create a high severity event (should trigger alert)
            high_event = monitor.create_event(
                event_type="unauthorized_access",
                severity=SeverityLevel.HIGH,
                source="api_gateway",
                details={"endpoint": "/admin"},
            )

            # Check that alert handler was called
            mock_handler.assert_called_once()
            called_with_event = mock_handler.call_args[0][0]
            assert called_with_event.event_type == "unauthorized_access"
            assert called_with_event.severity == SeverityLevel.HIGH

            # Reset mock and create a low severity event (should not trigger alert)
            mock_handler.reset_mock()
            monitor.create_event(
                event_type="data_access",
                severity=SeverityLevel.INFO,
                source="storage_service",
                details={"file": "public.txt"},
            )

            # Check that alert handler was not called for low severity
            mock_handler.assert_not_called()

    def test_add_alert_handler(self):
        """Test adding an alert handler."""
        with tempfile.NamedTemporaryFile() as temp_file:
            monitor = SecurityMonitor(log_path=temp_file.name)
            assert len(monitor.alert_handlers) == 0

            # Add a handler
            mock_handler = mock.MagicMock()
            monitor.add_alert_handler(mock_handler)
            assert len(monitor.alert_handlers) == 1

            # Create a high severity event (should trigger alert)
            monitor.create_event(
                event_type="malware_detected",
                severity=SeverityLevel.CRITICAL,
                source="scanner",
                details={"file": "malicious.exe"},
            )

            # Check that alert handler was called
            mock_handler.assert_called_once()

    def test_clear_event_history(self):
        """Test clearing the event history."""
        with tempfile.NamedTemporaryFile() as temp_file:
            monitor = SecurityMonitor(log_path=temp_file.name)

            # Create some events
            monitor.create_event(
                event_type="login",
                severity=SeverityLevel.INFO,
                source="auth_service",
                details={"username": "user1"},
            )
            monitor.create_event(
                event_type="logout",
                severity=SeverityLevel.INFO,
                source="auth_service",
                details={"username": "user1"},
            )

            assert len(monitor.event_history) == 2

            # Clear history
            monitor.clear_event_history()
            assert len(monitor.event_history) == 0

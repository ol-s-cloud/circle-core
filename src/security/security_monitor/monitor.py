"""Security Monitor for Circle Core Framework.

Provides functionality for real-time security monitoring and anomaly detection.
"""

import datetime
import json
import logging
import os
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class SeverityLevel(Enum):
    """Enum representing different severity levels for security events."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityEvent:
    """Represents a security event detected by the monitor."""

    def __init__(
        self,
        event_type: str,
        severity: SeverityLevel,
        source: str,
        details: Dict[str, Any],
        timestamp: Optional[datetime.datetime] = None,
    ):
        """Initialize a security event.

        Args:
            event_type: Type of security event
            severity: Severity level of the event
            source: Source of the event (component, module, etc.)
            details: Additional details about the event
            timestamp: Event timestamp (defaults to current time)
        """
        self.event_type = event_type
        self.severity = severity
        self.source = source
        self.details = details
        self.timestamp = timestamp or datetime.datetime.now()
        self.event_id = self._generate_event_id()

    def _generate_event_id(self) -> str:
        """Generate a unique ID for the event.

        Returns:
            Unique event ID
        """
        # Simple implementation - in production would use UUID or similar
        return f"{self.timestamp.strftime('%Y%m%d%H%M%S')}-{hash(self.event_type)}-{hash(self.source)}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary.

        Returns:
            Event as a dictionary
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "severity": self.severity.value,
            "source": self.source,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        """String representation of the event.

        Returns:
            Event as a string
        """
        return f"SecurityEvent({self.event_type}, {self.severity.value}, {self.source})"


class SecurityMonitor:
    """Monitor for detecting and responding to security events.

    This class provides functionality to detect, log, and respond to
    security events in real-time.
    """

    def __init__(
        self,
        log_path: Optional[str] = None,
        alert_handlers: Optional[List[callable]] = None,
        anomaly_detection_enabled: bool = True,
    ):
        """Initialize the security monitor.

        Args:
            log_path: Path to security log file
            alert_handlers: List of alert handler functions
            anomaly_detection_enabled: Whether to enable anomaly detection
        """
        self.log_path = log_path or os.path.expanduser("~/.circle-core/security/events.log")
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

        self.alert_handlers = alert_handlers or []
        self.anomaly_detection_enabled = anomaly_detection_enabled
        self.event_history: List[SecurityEvent] = []

        # Set up logging
        self.logger = logging.getLogger("circle_core.security.monitor")
        self.logger.setLevel(logging.INFO)

        # Add file handler
        file_handler = logging.FileHandler(self.log_path)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def log_event(self, event: SecurityEvent) -> None:
        """Log a security event.

        Args:
            event: Security event to log
        """
        # Add to history
        self.event_history.append(event)

        # Log to file
        event_dict = event.to_dict()
        self.logger.info(json.dumps(event_dict))

        # Check for anomalies if enabled
        if self.anomaly_detection_enabled:
            self._detect_anomalies(event)

        # Trigger alerts for medium or higher severity
        if event.severity.value in ("medium", "high", "critical"):
            self._trigger_alerts(event)

    def create_event(
        self,
        event_type: str,
        severity: Union[SeverityLevel, str],
        source: str,
        details: Dict[str, Any],
    ) -> SecurityEvent:
        """Create and log a new security event.

        Args:
            event_type: Type of security event
            severity: Severity level of the event
            source: Source of the event
            details: Additional details

        Returns:
            Created security event
        """
        # Convert string severity to enum if needed
        if isinstance(severity, str):
            severity = SeverityLevel(severity)

        # Create event
        event = SecurityEvent(event_type, severity, source, details)

        # Log it
        self.log_event(event)

        return event

    def get_recent_events(
        self, count: int = 10, severity: Optional[SeverityLevel] = None
    ) -> List[SecurityEvent]:
        """Get recent security events.

        Args:
            count: Number of events to retrieve
            severity: Filter by severity level

        Returns:
            List of recent events
        """
        events = self.event_history

        # Filter by severity if specified
        if severity:
            events = [e for e in events if e.severity == severity]

        # Return most recent first
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:count]

    def _detect_anomalies(self, event: SecurityEvent) -> None:
        """Detect anomalies in security events.

        Args:
            event: Current security event
        """
        # In a real implementation, this would use more sophisticated
        # anomaly detection algorithms (e.g., statistical analysis,
        # machine learning models, pattern recognition)

        # Simple example: detect rapid succession of authentication failures
        if event.event_type == "authentication_failure":
            # Count recent authentication failures from the same source
            recent_failures = [
                e
                for e in self.event_history[-10:]
                if e.event_type == "authentication_failure"
                and e.source == event.source
                and (datetime.datetime.now() - e.timestamp).seconds < 60
            ]

            if len(recent_failures) >= 3:
                # Create a new high-severity event for the anomaly
                anomaly_event = SecurityEvent(
                    event_type="anomaly_detected",
                    severity=SeverityLevel.HIGH,
                    source="security_monitor",
                    details={
                        "anomaly_type": "rapid_auth_failures",
                        "source": event.source,
                        "count": len(recent_failures),
                        "related_events": [e.event_id for e in recent_failures],
                    },
                )
                self.log_event(anomaly_event)

    def _trigger_alerts(self, event: SecurityEvent) -> None:
        """Trigger alerts for a security event.

        Args:
            event: Security event to trigger alerts for
        """
        for handler in self.alert_handlers:
            try:
                handler(event)
            except Exception as e:
                self.logger.error(f"Error in alert handler: {e}")

    def add_alert_handler(self, handler: callable) -> None:
        """Add an alert handler function.

        Args:
            handler: Alert handler function that takes a SecurityEvent
        """
        self.alert_handlers.append(handler)

    def clear_event_history(self) -> None:
        """Clear the event history."""
        self.event_history = []


# Example alert handlers
def email_alert_handler(event: SecurityEvent) -> None:
    """Send an email alert for a security event."""
    print(f"[Email Alert] {event}")
    # In a real implementation, this would send an email


def sms_alert_handler(event: SecurityEvent) -> None:
    """Send an SMS alert for a security event."""
    print(f"[SMS Alert] {event}")
    # In a real implementation, this would send an SMS


def webhook_alert_handler(event: SecurityEvent) -> None:
    """Send a webhook alert for a security event."""
    print(f"[Webhook Alert] {event}")
    # In a real implementation, this would call a webhook
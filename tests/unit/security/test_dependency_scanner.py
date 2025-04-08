"""Unit tests for the dependency scanner module."""

import os
import tempfile
from unittest import mock

import pytest

from src.security.dependency_scanner.scanner import DependencyScanner


class TestDependencyScanner:
    """Test cases for the DependencyScanner class."""

    def test_init_with_default_db(self):
        """Test initialization with the default vulnerability database."""
        scanner = DependencyScanner()
        assert scanner.vulnerability_db is not None
        assert "requests" in scanner.vulnerability_db
        assert "pyyaml" in scanner.vulnerability_db

    def test_scan_package_with_known_vulnerability(self):
        """Test scanning a package with a known vulnerability."""
        scanner = DependencyScanner()
        result = scanner.scan_package("pyyaml", "5.3.1")

        assert result["package"] == "pyyaml"
        assert result["version"] == "5.3.1"
        assert len(result["vulnerabilities"]) > 0
        assert result["vulnerabilities"][0]["id"] == "CVE-2023-67890"
        assert result["vulnerabilities"][0]["severity"] == "high"
        assert result["risk_score"] > 0

    def test_scan_package_without_vulnerabilities(self):
        """Test scanning a package without known vulnerabilities."""
        scanner = DependencyScanner()
        result = scanner.scan_package("requests", "2.25.0")

        assert result["package"] == "requests"
        assert result["version"] == "2.25.0"
        assert len(result["vulnerabilities"]) == 0
        assert result["risk_score"] == 0

    def test_scan_requirements_file(self):
        """Test scanning a requirements file."""
        # Create a temporary requirements file
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
            f.write("requests==2.25.0\n")
            f.write("pyyaml==5.3.1\n")
            f.write("# This is a comment\n")
            f.write("pytest>=7.0.0\n")
            requirements_file = f.name

        try:
            scanner = DependencyScanner()
            results = scanner.scan_requirements_file(requirements_file)

            assert len(results) == 3
            
            # Find pyyaml result
            pyyaml_result = next((r for r in results if r["package"] == "pyyaml"), None)
            assert pyyaml_result is not None
            assert pyyaml_result["version"] == "5.3.1"
            assert len(pyyaml_result["vulnerabilities"]) > 0
            
            # Find requests result
            requests_result = next((r for r in results if r["package"] == "requests"), None)
            assert requests_result is not None
            assert requests_result["version"] == "2.25.0"
            assert len(requests_result["vulnerabilities"]) == 0
            
            # Find pytest result
            pytest_result = next((r for r in results if r["package"] == "pytest"), None)
            assert pytest_result is not None
            assert pytest_result["version"] == "7.0.0"

        finally:
            # Clean up the temporary file
            os.unlink(requirements_file)

    def test_generate_sbom(self):
        """Test generating a Software Bill of Materials."""
        scanner = DependencyScanner()
        sbom = scanner.generate_sbom("./")

        assert sbom["bomFormat"] == "CycloneDX"
        assert sbom["specVersion"] == "1.4"
        assert "serialNumber" in sbom
        assert "components" in sbom

    def test_risk_score_calculation(self):
        """Test risk score calculation."""
        scanner = DependencyScanner()
        
        # Empty vulnerabilities
        assert scanner._calculate_risk_score([]) == 0
        
        # One critical vulnerability
        assert scanner._calculate_risk_score([{"severity": "critical"}]) == 30
        
        # Multiple vulnerabilities
        vulnerabilities = [
            {"severity": "critical"},
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "low"}
        ]
        assert scanner._calculate_risk_score(vulnerabilities) == 65
        
        # Score capped at 100
        many_critical = [{"severity": "critical"} for _ in range(10)]
        assert scanner._calculate_risk_score(many_critical) == 100

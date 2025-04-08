"""Dependency Scanner for Circle Core Framework.

Provides functionality to scan project dependencies for security vulnerabilities.
"""

import json
import os
from typing import Dict, List, Optional, Tuple


class DependencyScanner:
    """Scanner for detecting security vulnerabilities in dependencies.

    This class provides functionality to scan Python packages and requirements files
    for known security vulnerabilities.
    """

    def __init__(self, vulnerability_db_path: Optional[str] = None):
        """Initialize the dependency scanner.

        Args:
            vulnerability_db_path: Path to custom vulnerability database
        """
        self.vulnerability_db_path = vulnerability_db_path
        self._load_vulnerability_db()

    def _load_vulnerability_db(self) -> None:
        """Load the vulnerability database.

        If a custom database path is provided, loads from that path.
        Otherwise, uses a default internal database.
        """
        self.vulnerability_db = {}
        # In a real implementation, this would load from a real database
        # For now, this is a placeholder implementation
        default_db = {
            "requests": {
                "2.25.0": [],
                "2.24.0": [{"id": "CVE-2023-12345", "severity": "medium"}],
            },
            "pyyaml": {
                "5.4.0": [],
                "5.3.1": [{"id": "CVE-2023-67890", "severity": "high"}],
            },
        }

        if self.vulnerability_db_path and os.path.exists(self.vulnerability_db_path):
            try:
                with open(self.vulnerability_db_path, "r") as f:
                    self.vulnerability_db = json.load(f)
            except (json.JSONDecodeError, IOError):
                # Fallback to default DB if there's an error
                self.vulnerability_db = default_db
        else:
            self.vulnerability_db = default_db

    def scan_package(self, package_name: str, version: Optional[str] = None) -> Dict:
        """Scan a single package for vulnerabilities.

        Args:
            package_name: Name of the package to scan
            version: Specific version to scan, or None for latest

        Returns:
            Dictionary containing scan results
        """
        package_name = package_name.lower()
        vulnerabilities = []
        risk_score = 0

        if package_name in self.vulnerability_db:
            pkg_vulns = self.vulnerability_db[package_name]
            if version and version in pkg_vulns:
                vulnerabilities = pkg_vulns[version]
                risk_score = self._calculate_risk_score(vulnerabilities)

        return {
            "package": package_name,
            "version": version or "latest",
            "vulnerabilities": vulnerabilities,
            "risk_score": risk_score,
            "scan_date": "2025-04-08",  # In real implementation, use datetime.now()
        }

    def scan_requirements_file(self, file_path: str) -> List[Dict]:
        """Scan all packages listed in a requirements file.

        Args:
            file_path: Path to requirements.txt or similar file

        Returns:
            List of dictionaries containing scan results for each package
        """
        results = []

        try:
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Parse package name and version
                    if "==" in line:
                        package_name, version = line.split("==", 1)
                    elif ">=" in line:
                        package_name, version = line.split(">=", 1)
                    else:
                        package_name = line.split("[")
                        package_name = package_name[0]
                        version = None

                    # Scan individual package
                    results.append(self.scan_package(package_name, version))
        except IOError:
            # Handle file not found or other IO errors
            print(f"Error: Could not open requirements file {file_path}")

        return results

    def generate_sbom(self, project_path: str) -> Dict:
        """Generate a Software Bill of Materials for the project.

        Args:
            project_path: Path to the project root

        Returns:
            SBOM in CycloneDX format (dictionary)
        """
        # This would use CycloneDX or similar tools
        # Placeholder implementation
        return {
            "bomFormat": "CycloneDX",
            "specVersion": "1.4",
            "serialNumber": "urn:uuid:3e671687-395b-41f5-a30f-a58921a69b79",
            "version": 1,
            "components": [],
        }

    def _calculate_risk_score(self, vulnerabilities: List[Dict]) -> int:
        """Calculate a risk score based on vulnerabilities.

        Args:
            vulnerabilities: List of vulnerability dictionaries

        Returns:
            Risk score (0-100)
        """
        if not vulnerabilities:
            return 0

        score = 0
        for vuln in vulnerabilities:
            if vuln.get("severity") == "critical":
                score += 30
            elif vuln.get("severity") == "high":
                score += 20
            elif vuln.get("severity") == "medium":
                score += 10
            elif vuln.get("severity") == "low":
                score += 5

        # Cap at 100
        return min(score, 100)

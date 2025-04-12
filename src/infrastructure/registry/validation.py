"""Package validation implementation for the registry module.

This module provides implementations for package validation and verification.
"""

import os
import json
import hashlib
import zipfile
import tempfile
from typing import Dict, List, Optional, Any, BinaryIO, Set, Tuple
from enum import Enum, auto
from dataclasses import dataclass, field

from ...core.audit import AuditLogger
from ...core.encryption import EncryptionService
from ...security.dependency_scanner import DependencyScanner
from .interface import PackageValidationProvider


class ValidationSeverity(Enum):
    """Validation result severity levels."""
    
    INFO = auto()
    WARNING = auto()
    ERROR = auto()


@dataclass
class ValidationResult:
    """Result of a validation check."""
    
    check_name: str
    severity: ValidationSeverity
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


class BasicPackageValidationProvider(PackageValidationProvider):
    """Basic implementation of the package validation provider.
    
    This implementation validates package structure, integrity, and performs
    basic security checks.
    """
    
    def __init__(
        self, 
        encryption_service: Optional[EncryptionService] = None,
        dependency_scanner: Optional[DependencyScanner] = None,
        audit_logger: Optional[AuditLogger] = None
    ):
        """Initialize the basic package validation provider.
        
        Args:
            encryption_service: Optional encryption service for signature verification
            dependency_scanner: Optional dependency scanner for security scanning
            audit_logger: Optional audit logger
        """
        self.encryption_service = encryption_service
        self.dependency_scanner = dependency_scanner
        self.audit_logger = audit_logger
        
        # Define required metadata fields
        self.required_metadata_fields = {
            "name", "version", "description", "author"
        }
        
        # Define required package files
        self.required_package_files = {
            "manifest.json", "metadata.json"
        }
    
    def validate_package(self, package_name: str, version: str, package_data: bytes) -> Dict[str, Any]:
        """Validate a package file.
        
        Args:
            package_name: Name of the package
            version: Package version
            package_data: Binary package data
            
        Returns:
            Validation result dictionary
        """
        validation_results = []
        
        try:
            # Validate package structure
            structure_results = self._validate_package_structure(
                package_name, version, package_data
            )
            validation_results.extend(structure_results)
            
            # Check for critical structure errors
            if any(r.severity == ValidationSeverity.ERROR for r in structure_results):
                # If there are critical structure errors, skip further validation
                validation_result = self._format_validation_results(validation_results)
                
                if self.audit_logger:
                    self.audit_logger.log_event(
                        event_type="package_validation",
                        data={
                            "package_name": package_name,
                            "version": version,
                            "success": False,
                            "errors": [r.message for r in validation_results if r.severity == ValidationSeverity.ERROR]
                        }
                    )
                
                return validation_result
            
            # Validate package metadata
            try:
                metadata, metadata_results = self._extract_and_validate_metadata(
                    package_name, version, package_data
                )
                validation_results.extend(metadata_results)
            except Exception as e:
                validation_results.append(ValidationResult(
                    check_name="metadata_extraction",
                    severity=ValidationSeverity.ERROR,
                    message=f"Failed to extract or validate metadata: {str(e)}"
                ))
            
            # Validate package manifest
            try:
                manifest, manifest_results = self._extract_and_validate_manifest(
                    package_name, version, package_data
                )
                validation_results.extend(manifest_results)
            except Exception as e:
                validation_results.append(ValidationResult(
                    check_name="manifest_extraction",
                    severity=ValidationSeverity.ERROR,
                    message=f"Failed to extract or validate manifest: {str(e)}"
                ))
            
            # Validate file integrity if manifest is available
            if 'manifest' in locals() and isinstance(manifest, dict):
                integrity_results = self._validate_file_integrity(
                    package_data, manifest
                )
                validation_results.extend(integrity_results)
            
            # Perform security scanning if dependency scanner is available
            if self.dependency_scanner:
                try:
                    security_results = self._scan_security(
                        package_name, version, package_data
                    )
                    validation_results.extend(security_results)
                except Exception as e:
                    validation_results.append(ValidationResult(
                        check_name="security_scan",
                        severity=ValidationSeverity.WARNING,
                        message=f"Failed to perform security scan: {str(e)}"
                    ))
            
            # Format and return results
            validation_result = self._format_validation_results(validation_results)
            
            # Log validation
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_validation",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": not any(r.severity == ValidationSeverity.ERROR for r in validation_results),
                        "errors": [r.message for r in validation_results if r.severity == ValidationSeverity.ERROR],
                        "warnings": [r.message for r in validation_results if r.severity == ValidationSeverity.WARNING]
                    }
                )
            
            return validation_result
        except Exception as e:
            # Log the failed validation
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_validation",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            # Return error result
            return {
                "valid": False,
                "errors": [f"Validation process failed: {str(e)}"],
                "warnings": [],
                "info": []
            }
    
    def _format_validation_results(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Format validation results into a structured dictionary.
        
        Args:
            results: List of validation results
            
        Returns:
            Formatted results dictionary
        """
        formatted = {
            "valid": not any(r.severity == ValidationSeverity.ERROR for r in results),
            "errors": [],
            "warnings": [],
            "info": [],
            "details": {}
        }
        
        # Categorize results by severity
        for result in results:
            if result.severity == ValidationSeverity.ERROR:
                formatted["errors"].append(result.message)
            elif result.severity == ValidationSeverity.WARNING:
                formatted["warnings"].append(result.message)
            elif result.severity == ValidationSeverity.INFO:
                formatted["info"].append(result.message)
            
            # Add detailed information
            if result.details:
                formatted["details"][result.check_name] = result.details
        
        return formatted
    
    def _validate_package_structure(
        self, package_name: str, version: str, package_data: bytes
    ) -> List[ValidationResult]:
        """Validate the structure of a package.
        
        Args:
            package_name: Package name
            version: Package version
            package_data: Package data
            
        Returns:
            List of validation results
        """
        results = []
        
        # Check if package is a valid zip file
        try:
            with zipfile.ZipFile(tempfile.BytesIO(package_data)) as zip_file:
                # Check for required files
                file_list = zip_file.namelist()
                
                # Add validation result for zip structure
                results.append(ValidationResult(
                    check_name="zip_structure",
                    severity=ValidationSeverity.INFO,
                    message="Package is a valid zip archive",
                    details={"files": file_list}
                ))
                
                # Check for required files
                missing_files = self.required_package_files - set(file_list)
                if missing_files:
                    results.append(ValidationResult(
                        check_name="required_files",
                        severity=ValidationSeverity.ERROR,
                        message=f"Missing required files: {', '.join(missing_files)}",
                        details={"missing_files": list(missing_files)}
                    ))
                else:
                    results.append(ValidationResult(
                        check_name="required_files",
                        severity=ValidationSeverity.INFO,
                        message="All required files are present",
                        details={"required_files": list(self.required_package_files)}
                    ))
        except zipfile.BadZipFile:
            results.append(ValidationResult(
                check_name="zip_structure",
                severity=ValidationSeverity.ERROR,
                message="Package is not a valid zip archive"
            ))
        
        return results
    
    def _extract_and_validate_metadata(
        self, package_name: str, version: str, package_data: bytes
    ) -> Tuple[Dict[str, Any], List[ValidationResult]]:
        """Extract and validate package metadata.
        
        Args:
            package_name: Package name
            version: Package version
            package_data: Package data
            
        Returns:
            Tuple of (metadata, validation_results)
        """
        results = []
        
        try:
            with zipfile.ZipFile(tempfile.BytesIO(package_data)) as zip_file:
                # Extract metadata
                try:
                    metadata_bytes = zip_file.read("metadata.json")
                    metadata = json.loads(metadata_bytes.decode("utf-8"))
                    
                    results.append(ValidationResult(
                        check_name="metadata_format",
                        severity=ValidationSeverity.INFO,
                        message="Metadata is valid JSON"
                    ))
                except json.JSONDecodeError:
                    results.append(ValidationResult(
                        check_name="metadata_format",
                        severity=ValidationSeverity.ERROR,
                        message="Metadata is not valid JSON"
                    ))
                    return {}, results
                
                # Validate required fields
                missing_fields = self.required_metadata_fields - set(metadata.keys())
                if missing_fields:
                    results.append(ValidationResult(
                        check_name="metadata_required_fields",
                        severity=ValidationSeverity.ERROR,
                        message=f"Missing required metadata fields: {', '.join(missing_fields)}",
                        details={"missing_fields": list(missing_fields)}
                    ))
                else:
                    results.append(ValidationResult(
                        check_name="metadata_required_fields",
                        severity=ValidationSeverity.INFO,
                        message="All required metadata fields are present"
                    ))
                
                # Validate package name and version
                if metadata.get("name") != package_name:
                    results.append(ValidationResult(
                        check_name="metadata_package_name",
                        severity=ValidationSeverity.ERROR,
                        message=f"Metadata package name '{metadata.get('name')}' does not match expected '{package_name}'"
                    ))
                else:
                    results.append(ValidationResult(
                        check_name="metadata_package_name",
                        severity=ValidationSeverity.INFO,
                        message="Metadata package name matches expected name"
                    ))
                
                if metadata.get("version") != version:
                    results.append(ValidationResult(
                        check_name="metadata_package_version",
                        severity=ValidationSeverity.ERROR,
                        message=f"Metadata package version '{metadata.get('version')}' does not match expected '{version}'"
                    ))
                else:
                    results.append(ValidationResult(
                        check_name="metadata_package_version",
                        severity=ValidationSeverity.INFO,
                        message="Metadata package version matches expected version"
                    ))
                
                return metadata, results
        except Exception as e:
            results.append(ValidationResult(
                check_name="metadata_extraction",
                severity=ValidationSeverity.ERROR,
                message=f"Failed to extract metadata: {str(e)}"
            ))
            return {}, results
    
    def _extract_and_validate_manifest(
        self, package_name: str, version: str, package_data: bytes
    ) -> Tuple[Dict[str, Any], List[ValidationResult]]:
        """Extract and validate package manifest.
        
        Args:
            package_name: Package name
            version: Package version
            package_data: Package data
            
        Returns:
            Tuple of (manifest, validation_results)
        """
        results = []
        
        try:
            with zipfile.ZipFile(tempfile.BytesIO(package_data)) as zip_file:
                # Extract manifest
                try:
                    manifest_bytes = zip_file.read("manifest.json")
                    manifest = json.loads(manifest_bytes.decode("utf-8"))
                    
                    results.append(ValidationResult(
                        check_name="manifest_format",
                        severity=ValidationSeverity.INFO,
                        message="Manifest is valid JSON"
                    ))
                except json.JSONDecodeError:
                    results.append(ValidationResult(
                        check_name="manifest_format",
                        severity=ValidationSeverity.ERROR,
                        message="Manifest is not valid JSON"
                    ))
                    return {}, results
                
                # Check if manifest has files section
                if "files" not in manifest:
                    results.append(ValidationResult(
                        check_name="manifest_files",
                        severity=ValidationSeverity.ERROR,
                        message="Manifest is missing 'files' section"
                    ))
                    return manifest, results
                
                # Check if manifest files are in the package
                file_list = zip_file.namelist()
                manifest_files = set(manifest["files"].keys())
                missing_files = manifest_files - set(file_list)
                
                if missing_files:
                    results.append(ValidationResult(
                        check_name="manifest_missing_files",
                        severity=ValidationSeverity.ERROR,
                        message=f"Files listed in manifest are missing from package: {', '.join(missing_files)}",
                        details={"missing_files": list(missing_files)}
                    ))
                else:
                    results.append(ValidationResult(
                        check_name="manifest_files_present",
                        severity=ValidationSeverity.INFO,
                        message="All files listed in manifest are present in package"
                    ))
                
                return manifest, results
        except Exception as e:
            results.append(ValidationResult(
                check_name="manifest_extraction",
                severity=ValidationSeverity.ERROR,
                message=f"Failed to extract manifest: {str(e)}"
            ))
            return {}, results
    
    def _validate_file_integrity(
        self, package_data: bytes, manifest: Dict[str, Any]
    ) -> List[ValidationResult]:
        """Validate file integrity using manifest checksums.
        
        Args:
            package_data: Package data
            manifest: Package manifest
            
        Returns:
            List of validation results
        """
        results = []
        
        try:
            with zipfile.ZipFile(tempfile.BytesIO(package_data)) as zip_file:
                manifest_files = manifest.get("files", {})
                integrity_errors = []
                
                for file_path, file_info in manifest_files.items():
                    expected_hash = file_info.get("hash")
                    if not expected_hash:
                        continue
                    
                    # Compute actual hash
                    try:
                        file_data = zip_file.read(file_path)
                        actual_hash = hashlib.sha256(file_data).hexdigest()
                        
                        if actual_hash != expected_hash:
                            integrity_errors.append({
                                "file": file_path,
                                "expected": expected_hash,
                                "actual": actual_hash
                            })
                    except Exception as e:
                        integrity_errors.append({
                            "file": file_path,
                            "error": str(e)
                        })
                
                if integrity_errors:
                    results.append(ValidationResult(
                        check_name="file_integrity",
                        severity=ValidationSeverity.ERROR,
                        message=f"File integrity check failed for {len(integrity_errors)} files",
                        details={"errors": integrity_errors}
                    ))
                else:
                    results.append(ValidationResult(
                        check_name="file_integrity",
                        severity=ValidationSeverity.INFO,
                        message="All file integrity checks passed",
                        details={"file_count": len(manifest_files)}
                    ))
        except Exception as e:
            results.append(ValidationResult(
                check_name="file_integrity",
                severity=ValidationSeverity.ERROR,
                message=f"Failed to validate file integrity: {str(e)}"
            ))
        
        return results
    
    def _scan_security(
        self, package_name: str, version: str, package_data: bytes
    ) -> List[ValidationResult]:
        """Scan package for security issues.
        
        Args:
            package_name: Package name
            version: Package version
            package_data: Package data
            
        Returns:
            List of validation results
        """
        results = []
        
        # Skip if no dependency scanner
        if not self.dependency_scanner:
            results.append(ValidationResult(
                check_name="security_scan",
                severity=ValidationSeverity.INFO,
                message="Security scanning skipped (no scanner available)"
            ))
            return results
        
        try:
            # Create a temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract package
                with zipfile.ZipFile(tempfile.BytesIO(package_data)) as zip_file:
                    zip_file.extractall(temp_dir)
                
                # Scan the extracted content
                scan_results = self.dependency_scanner.scan_directory(temp_dir)
                
                # Process scan results
                issues = scan_results.get("issues", [])
                if issues:
                    # Categorize issues by severity
                    high_severity = [i for i in issues if i.get("severity") == "high"]
                    medium_severity = [i for i in issues if i.get("severity") == "medium"]
                    low_severity = [i for i in issues if i.get("severity") == "low"]
                    
                    # Add validation results
                    if high_severity:
                        results.append(ValidationResult(
                            check_name="security_high_severity",
                            severity=ValidationSeverity.ERROR,
                            message=f"Found {len(high_severity)} high severity security issues",
                            details={"issues": high_severity}
                        ))
                    
                    if medium_severity:
                        results.append(ValidationResult(
                            check_name="security_medium_severity",
                            severity=ValidationSeverity.WARNING,
                            message=f"Found {len(medium_severity)} medium severity security issues",
                            details={"issues": medium_severity}
                        ))
                    
                    if low_severity:
                        results.append(ValidationResult(
                            check_name="security_low_severity",
                            severity=ValidationSeverity.INFO,
                            message=f"Found {len(low_severity)} low severity security issues",
                            details={"issues": low_severity}
                        ))
                else:
                    results.append(ValidationResult(
                        check_name="security_scan",
                        severity=ValidationSeverity.INFO,
                        message="No security issues found",
                        details={"scan_report": scan_results}
                    ))
        except Exception as e:
            results.append(ValidationResult(
                check_name="security_scan",
                severity=ValidationSeverity.WARNING,
                message=f"Failed to perform security scan: {str(e)}"
            ))
        
        return results
    
    def verify_signature(
        self, package_name: str, version: str, signature: bytes, public_key: Optional[bytes] = None
    ) -> bool:
        """Verify the signature of a package.
        
        Args:
            package_name: Name of the package
            version: Package version
            signature: Signature bytes
            public_key: Public key bytes (optional)
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Skip if no encryption service
            if not self.encryption_service:
                if self.audit_logger:
                    self.audit_logger.log_event(
                        event_type="signature_verification",
                        data={
                            "package_name": package_name,
                            "version": version,
                            "success": False,
                            "error": "No encryption service available"
                        }
                    )
                return False
            
            # TODO: Implement signature verification using the encryption service
            # This is a placeholder for now
            is_valid = False
            
            # Log the signature verification
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="signature_verification",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": is_valid
                    }
                )
            
            return is_valid
        except Exception as e:
            # Log the failed signature verification
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="signature_verification",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            return False
    
    def check_integrity(
        self, package_name: str, version: str, package_data: bytes, expected_hash: Optional[str] = None
    ) -> bool:
        """Check the integrity of a package file.
        
        Args:
            package_name: Name of the package
            version: Package version
            package_data: Binary package data
            expected_hash: Expected hash string (optional)
            
        Returns:
            True if integrity check passes, False otherwise
        """
        try:
            # Compute hash
            actual_hash = hashlib.sha256(package_data).hexdigest()
            
            # If no expected hash provided, just return the actual hash
            if not expected_hash:
                return True
            
            # Compare hashes
            is_valid = actual_hash == expected_hash
            
            # Log the integrity check
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="integrity_check",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "expected_hash": expected_hash,
                        "actual_hash": actual_hash,
                        "success": is_valid
                    }
                )
            
            return is_valid
        except Exception as e:
            # Log the failed integrity check
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="integrity_check",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "expected_hash": expected_hash,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            return False
    
    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate package metadata.
        
        Args:
            metadata: Package metadata dictionary
            
        Returns:
            Validation result dictionary
        """
        results = []
        
        # Check for required fields
        missing_fields = self.required_metadata_fields - set(metadata.keys())
        if missing_fields:
            results.append(ValidationResult(
                check_name="metadata_required_fields",
                severity=ValidationSeverity.ERROR,
                message=f"Missing required metadata fields: {', '.join(missing_fields)}",
                details={"missing_fields": list(missing_fields)}
            ))
        else:
            results.append(ValidationResult(
                check_name="metadata_required_fields",
                severity=ValidationSeverity.INFO,
                message="All required metadata fields are present"
            ))
        
        # Validate field formats
        if "name" in metadata and not self._validate_package_name(metadata["name"]):
            results.append(ValidationResult(
                check_name="metadata_name_format",
                severity=ValidationSeverity.ERROR,
                message="Package name format is invalid"
            ))
        
        if "version" in metadata and not self._validate_package_version(metadata["version"]):
            results.append(ValidationResult(
                check_name="metadata_version_format",
                severity=ValidationSeverity.ERROR,
                message="Package version format is invalid"
            ))
        
        # Format and return results
        return self._format_validation_results(results)
    
    def scan_security(self, package_name: str, version: str, package_data: bytes) -> Dict[str, Any]:
        """Scan a package for security issues.
        
        Args:
            package_name: Name of the package
            version: Package version
            package_data: Binary package data
            
        Returns:
            Security scan result dictionary
        """
        # Use the security scanning implementation from validate_package
        results = self._scan_security(package_name, version, package_data)
        return self._format_validation_results(results)
    
    def _validate_package_name(self, name: str) -> bool:
        """Validate a package name format.
        
        Args:
            name: Package name
            
        Returns:
            True if valid, False otherwise
        """
        if not name:
            return False
        
        # Package name should be alphanumeric with optional hyphens and underscores
        return bool(re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9_]*$', name))
    
    def _validate_package_version(self, version: str) -> bool:
        """Validate a package version format.
        
        Args:
            version: Package version
            
        Returns:
            True if valid, False otherwise
        """
        if not version:
            return False
        
        # Semantic version format: major.minor.patch with optional pre-release
        return bool(re.match(r'^(\d+)\.(\d+)\.(\d+)(?:[-+].+)?$', version))

"""Package versioning implementation for the registry module.

This module provides implementations for version management and dependency resolution.
"""

import re
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass

from ...core.audit import AuditLogger
from .interface import PackageVersioningProvider


@dataclass
class VersionSpec:
    """Version specification representation."""
    
    operator: str  # ==, >=, <=, >, <, ~=, !=
    version: str  # The version number


class SemanticVersionProvider(PackageVersioningProvider):
    """Semantic versioning implementation.
    
    This implementation follows semantic versioning 2.0.0 (https://semver.org/).
    """
    
    def __init__(
        self, 
        metadata_provider: Any,  # Avoid circular import with typing
        audit_logger: Optional[AuditLogger] = None
    ):
        """Initialize the semantic versioning provider.
        
        Args:
            metadata_provider: Package metadata provider
            audit_logger: Optional audit logger
        """
        self.metadata_provider = metadata_provider
        self.audit_logger = audit_logger
        
        # Valid version spec operators
        self._operators = {"==", ">=", "<=", ">", "<", "~=", "!="}
    
    def _parse_version(self, version: str) -> List[int]:
        """Parse a version string into components.
        
        Args:
            version: Version string (e.g., "1.2.3")
            
        Returns:
            List of version components as integers
            
        Raises:
            ValueError: If version is invalid
        """
        # Remove any build/pre-release information for now
        if "+" in version:
            version = version.split("+")[0]
        if "-" in version:
            version = version.split("-")[0]
        
        components = []
        for part in version.split("."):
            try:
                components.append(int(part))
            except ValueError:
                raise ValueError(f"Invalid version format: {version}")
        
        # Ensure at least three components (major.minor.patch)
        while len(components) < 3:
            components.append(0)
        
        return components
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """Compare two versions, returning -1, 0, or 1.
        
        Args:
            version1: First version string
            version2: Second version string
            
        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        v1_parts = self._parse_version(version1)
        v2_parts = self._parse_version(version2)
        
        # Compare each component
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1_val = v1_parts[i] if i < len(v1_parts) else 0
            v2_val = v2_parts[i] if i < len(v2_parts) else 0
            
            if v1_val < v2_val:
                return -1
            elif v1_val > v2_val:
                return 1
        
        # All components are equal
        return 0
    
    def parse_version_spec(self, version_spec: str) -> List[VersionSpec]:
        """Parse a version specification into a structured format.
        
        Args:
            version_spec: Version specification string (e.g., ">=1.0.0,<2.0.0")
            
        Returns:
            List of VersionSpec objects
            
        Raises:
            ValueError: If specification is invalid
        """
        spec_list = []
        
        # Multiple specs are separated by commas
        for part in version_spec.split(","):
            part = part.strip()
            if not part:
                continue
            
            # Check for operator
            match = re.match(r"([<>=!~]+)?(.*)", part)
            if not match:
                raise ValueError(f"Invalid version specification: {part}")
            
            operator, version = match.groups()
            
            # Default to equality if no operator given
            operator = operator or "=="
            
            # Validate operator
            if operator not in self._operators:
                raise ValueError(f"Invalid operator: {operator}")
            
            # Validate and normalize version
            version = version.strip()
            if not version:
                raise ValueError(f"Missing version in specification: {part}")
            
            try:
                self._parse_version(version)
            except ValueError:
                raise ValueError(f"Invalid version in specification: {part}")
            
            spec_list.append(VersionSpec(operator=operator, version=version))
        
        return spec_list
    
    def is_compatible(self, version: str, version_spec: str) -> bool:
        """Check if a version is compatible with a version specification.
        
        Args:
            version: Version string
            version_spec: Version specification string
            
        Returns:
            True if compatible, False otherwise
        """
        # Parse the spec
        specs = self.parse_version_spec(version_spec)
        
        # Must match all specs in the list
        for spec in specs:
            if not self._check_spec(version, spec):
                return False
        
        return True
    
    def _check_spec(self, version: str, spec: VersionSpec) -> bool:
        """Check if a version matches a specific version spec.
        
        Args:
            version: Version string
            spec: Version specification
            
        Returns:
            True if match, False otherwise
        """
        comparison = self.compare_versions(version, spec.version)
        
        if spec.operator == "==":
            return comparison == 0
        elif spec.operator == "!=":
            return comparison != 0
        elif spec.operator == ">":
            return comparison > 0
        elif spec.operator == ">=":
            return comparison >= 0
        elif spec.operator == "<":
            return comparison < 0
        elif spec.operator == "<=":
            return comparison <= 0
        elif spec.operator == "~=":
            # Compatible release: ~=1.2 is equivalent to >=1.2,<2.0
            # ~=1.2.3 is equivalent to >=1.2.3,<1.3.0
            v_parts = self._parse_version(spec.version)
            if len(v_parts) < 2:
                # Need at least major.minor
                v_parts = v_parts + [0] * (2 - len(v_parts))
            
            if len(v_parts) == 2:
                # Major.minor format: ~=1.2 means >=1.2.0,<2.0.0
                lower = ".".join(str(p) for p in v_parts + [0])
                upper = f"{v_parts[0] + 1}.0.0"
            else:
                # Full format: ~=1.2.3 means >=1.2.3,<1.3.0
                lower = ".".join(str(p) for p in v_parts)
                upper = ".".join(str(p) for p in v_parts[:-2] + [v_parts[-2] + 1, 0])
            
            return (self.compare_versions(version, lower) >= 0 and 
                    self.compare_versions(version, upper) < 0)
        
        return False
    
    def resolve_version(self, package_name: str, version_spec: str) -> Optional[str]:
        """Resolve a version specification to a concrete version.
        
        Args:
            package_name: Name of the package
            version_spec: Version specification (e.g., ">=1.0.0,<2.0.0")
            
        Returns:
            Resolved version string or None if not found
        """
        try:
            # Get all available versions
            versions = self.metadata_provider.get_package_versions(package_name)
            if not versions:
                return None
            
            # Filter by spec
            compatible_versions = [v for v in versions if self.is_compatible(v, version_spec)]
            
            if not compatible_versions:
                return None
            
            # Return highest compatible version
            return sorted(compatible_versions, key=lambda v: self._parse_version(v))[-1]
        except Exception as e:
            # Log the failed version resolution
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="version_resolution",
                    data={
                        "package_name": package_name,
                        "version_spec": version_spec,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def get_latest_version(self, package_name: str) -> Optional[str]:
        """Get the latest version of a package.
        
        Args:
            package_name: Name of the package
            
        Returns:
            Latest version string or None if not found
        """
        try:
            # Get all available versions
            versions = self.metadata_provider.get_package_versions(package_name)
            if not versions:
                return None
            
            # Return highest version
            return sorted(versions, key=lambda v: self._parse_version(v))[-1]
        except Exception as e:
            # Log the failed latest version retrieval
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="latest_version_retrieval",
                    data={
                        "package_name": package_name,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def resolve_dependencies(self, package_name: str, version: str) -> Dict[str, str]:
        """Resolve all dependencies for a package version.
        
        Args:
            package_name: Name of the package
            version: Package version
            
        Returns:
            Dictionary mapping dependency names to versions
        """
        try:
            # Get package metadata
            metadata = self.metadata_provider.get_package_metadata(package_name, version)
            
            # Get dependencies from metadata
            dependencies = metadata.get("dependencies", {})
            
            # Resolve each dependency to a concrete version
            resolved_deps = {}
            for dep_name, dep_spec in dependencies.items():
                resolved_version = self.resolve_version(dep_name, dep_spec)
                if resolved_version:
                    resolved_deps[dep_name] = resolved_version
                else:
                    # Dependency not found or not satisfiable
                    if self.audit_logger:
                        self.audit_logger.log_event(
                            event_type="dependency_resolution",
                            data={
                                "package_name": package_name,
                                "version": version,
                                "dependency": dep_name,
                                "spec": dep_spec,
                                "success": False,
                                "error": "Dependency not found or not satisfiable"
                            }
                        )
            
            # Log the dependency resolution
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="dependency_resolution",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "resolved_dependencies": resolved_deps,
                        "success": True
                    }
                )
            
            return resolved_deps
        except Exception as e:
            # Log the failed dependency resolution
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="dependency_resolution",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def resolve_dependency_tree(self, package_name: str, version: str) -> Dict[str, Any]:
        """Resolve the full dependency tree for a package.
        
        Args:
            package_name: Name of the package
            version: Package version
            
        Returns:
            Dependency tree as a nested dictionary
        """
        try:
            # Use a set to track processed dependencies to avoid circular dependencies
            processed = set()
            return self._build_dependency_tree(package_name, version, processed)
        except Exception as e:
            # Log the failed dependency tree resolution
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="dependency_tree_resolution",
                    data={
                        "package_name": package_name,
                        "version": version,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def _build_dependency_tree(self, package_name: str, version: str, processed: Set[str]) -> Dict[str, Any]:
        """Recursively build a dependency tree.
        
        Args:
            package_name: Name of the package
            version: Package version
            processed: Set of already processed packages
            
        Returns:
            Dependency tree as a nested dictionary
        """
        # Check for circular dependencies
        package_key = f"{package_name}@{version}"
        if package_key in processed:
            return {"name": package_name, "version": version, "circular": True}
        
        processed.add(package_key)
        
        # Get direct dependencies
        dependencies = self.resolve_dependencies(package_name, version)
        
        # Build tree
        dependency_tree = {
            "name": package_name,
            "version": version,
            "dependencies": {}
        }
        
        # Recursively process dependencies
        for dep_name, dep_version in dependencies.items():
            dependency_tree["dependencies"][dep_name] = self._build_dependency_tree(
                dep_name, dep_version, processed.copy()
            )
        
        return dependency_tree

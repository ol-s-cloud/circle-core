"""Package search implementation for the registry module.

This module provides implementations for package search functionality.
"""

import re
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime

from ...core.audit import AuditLogger
from .interface import PackageSearchProvider, PackageMetadataProvider


class SimpleSearchProvider(PackageSearchProvider):
    """Simple implementation of the package search provider.
    
    This implementation provides basic search functionality using
    in-memory filtering of metadata.
    """
    
    def __init__(
        self, 
        metadata_provider: PackageMetadataProvider,
        audit_logger: Optional[AuditLogger] = None
    ):
        """Initialize the simple search provider.
        
        Args:
            metadata_provider: Package metadata provider
            audit_logger: Optional audit logger
        """
        self.metadata_provider = metadata_provider
        self.audit_logger = audit_logger
    
    def search_packages(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search for packages matching the query and filters.
        
        Args:
            query: Search query string
            filters: Dictionary of filter criteria
            limit: Maximum number of results
            offset: Result offset for pagination
            
        Returns:
            List of package metadata dictionaries
        """
        try:
            # Get all packages
            all_packages = self.metadata_provider.list_packages()
            
            # Apply search query
            if query:
                matched_packages = self._apply_query(all_packages, query)
            else:
                matched_packages = all_packages
            
            # Apply filters
            if filters:
                matched_packages = self._apply_filters(matched_packages, filters)
            
            # Sort by relevance (most recently updated first, for now)
            sorted_packages = self._sort_by_relevance(matched_packages, query)
            
            # Apply pagination
            paginated_packages = sorted_packages[offset:offset + limit]
            
            # Log the search
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_search",
                    data={
                        "query": query,
                        "filters": filters,
                        "limit": limit,
                        "offset": offset,
                        "total_results": len(matched_packages),
                        "returned_results": len(paginated_packages),
                        "success": True
                    }
                )
            
            return paginated_packages
        except Exception as e:
            # Log the failed search
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_search",
                    data={
                        "query": query,
                        "filters": filters,
                        "limit": limit,
                        "offset": offset,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def _apply_query(self, packages: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Apply a search query to a list of packages.
        
        Args:
            packages: List of package metadata
            query: Search query string
            
        Returns:
            Filtered list of packages
        """
        if not query:
            return packages
        
        # Normalize query
        query_terms = query.lower().split()
        
        # Match against package metadata
        matched_packages = []
        for package in packages:
            # Fields to search in
            search_fields = [
                package.get("name", ""),
                package.get("description", ""),
                package.get("author", ""),
                *package.get("tags", [])
            ]
            
            # Combine fields into a single search text
            search_text = " ".join([str(field).lower() for field in search_fields if field])
            
            # Check if all query terms are in the search text
            if all(term in search_text for term in query_terms):
                matched_packages.append(package)
        
        return matched_packages
    
    def _apply_filters(
        self, packages: List[Dict[str, Any]], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply filters to a list of packages.
        
        Args:
            packages: List of package metadata
            filters: Dictionary of filter criteria
            
        Returns:
            Filtered list of packages
        """
        if not filters:
            return packages
        
        filtered_packages = []
        for package in packages:
            if self._matches_filters(package, filters):
                filtered_packages.append(package)
        
        return filtered_packages
    
    def _matches_filters(self, package: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if a package matches the filter criteria.
        
        Args:
            package: Package metadata
            filters: Filter criteria
            
        Returns:
            True if matches, False otherwise
        """
        for key, value in filters.items():
            # Handle special cases
            if key == "tags" and isinstance(value, list):
                # Check if package has all specified tags
                package_tags = set(package.get("tags", []))
                if not all(tag in package_tags for tag in value):
                    return False
            elif key == "dependencies" and isinstance(value, dict):
                # Check if package has specified dependencies
                package_deps = package.get("dependencies", {})
                for dep_name, dep_version in value.items():
                    if dep_name not in package_deps:
                        return False
                    if dep_version and package_deps[dep_name] != dep_version:
                        return False
            elif key == "version_range":
                # Check if package version is in the specified range
                # Implement version range filtering here
                pass
            elif key == "created_after" and isinstance(value, str):
                # Check if package was created after the specified date
                created_at = package.get("created_at")
                if not created_at or created_at < value:
                    return False
            elif key == "updated_after" and isinstance(value, str):
                # Check if package was updated after the specified date
                updated_at = package.get("updated_at")
                if not updated_at or updated_at < value:
                    return False
            # Regular field matching
            elif package.get(key) != value:
                return False
        
        return True
    
    def _sort_by_relevance(
        self, packages: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """Sort packages by relevance to the query.
        
        Args:
            packages: List of package metadata
            query: Search query string
            
        Returns:
            Sorted list of packages
        """
        # For now, sort by updated_at (most recent first)
        # A more sophisticated relevance algorithm could be implemented later
        return sorted(
            packages,
            key=lambda p: p.get("updated_at", ""),
            reverse=True
        )
    
    def search_by_tag(self, tag: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Search for packages with a specific tag.
        
        Args:
            tag: Tag to search for
            limit: Maximum number of results
            offset: Result offset for pagination
            
        Returns:
            List of package metadata dictionaries
        """
        try:
            # Get all packages
            all_packages = self.metadata_provider.list_packages()
            
            # Filter by tag
            tagged_packages = [
                package for package in all_packages
                if tag in package.get("tags", [])
            ]
            
            # Sort by updated_at (most recent first)
            sorted_packages = sorted(
                tagged_packages,
                key=lambda p: p.get("updated_at", ""),
                reverse=True
            )
            
            # Apply pagination
            paginated_packages = sorted_packages[offset:offset + limit]
            
            # Log the tag search
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_tag_search",
                    data={
                        "tag": tag,
                        "limit": limit,
                        "offset": offset,
                        "total_results": len(tagged_packages),
                        "returned_results": len(paginated_packages),
                        "success": True
                    }
                )
            
            return paginated_packages
        except Exception as e:
            # Log the failed tag search
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="package_tag_search",
                    data={
                        "tag": tag,
                        "limit": limit,
                        "offset": offset,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def get_popular_packages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get a list of popular packages.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of package metadata dictionaries
        """
        try:
            # Get all packages
            all_packages = self.metadata_provider.list_packages()
            
            # In a real implementation, this would use download counts or other
            # popularity metrics. For now, just sort by name as a placeholder.
            sorted_packages = sorted(
                all_packages,
                key=lambda p: p.get("name", "")
            )
            
            # Apply limit
            limited_packages = sorted_packages[:limit]
            
            # Log the popular packages request
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="popular_packages",
                    data={
                        "limit": limit,
                        "total_packages": len(all_packages),
                        "returned_packages": len(limited_packages),
                        "success": True
                    }
                )
            
            return limited_packages
        except Exception as e:
            # Log the failed popular packages request
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="popular_packages",
                    data={
                        "limit": limit,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise
    
    def get_recent_packages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get a list of recently added or updated packages.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of package metadata dictionaries
        """
        try:
            # Get all packages
            all_packages = self.metadata_provider.list_packages()
            
            # Sort by updated_at (most recent first)
            sorted_packages = sorted(
                all_packages,
                key=lambda p: p.get("updated_at", ""),
                reverse=True
            )
            
            # Apply limit
            limited_packages = sorted_packages[:limit]
            
            # Log the recent packages request
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="recent_packages",
                    data={
                        "limit": limit,
                        "total_packages": len(all_packages),
                        "returned_packages": len(limited_packages),
                        "success": True
                    }
                )
            
            return limited_packages
        except Exception as e:
            # Log the failed recent packages request
            if self.audit_logger:
                self.audit_logger.log_event(
                    event_type="recent_packages",
                    data={
                        "limit": limit,
                        "success": False,
                        "error": str(e)
                    }
                )
            
            raise

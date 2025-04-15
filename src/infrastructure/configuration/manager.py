"""Configuration manager for Circle Core.

This module provides the main configuration manager for the application.
It coordinates configuration sources, loading, validation, and access.
"""

import os
from typing import Dict, List, Optional, Any, Set, Union, Type, TypeVar
from pathlib import Path

from ...core.audit import AuditLogger
from .interface import (
    ConfigManager, ConfigProvider, ConfigEnvironment, ConfigSource,
    ValidationLevel, ConfigSchema, ValidationResult
)
from .providers import (
    DictConfigProvider, EnvironmentConfigProvider,
    FileConfigProvider, ChainConfigProvider
)
from .loaders import StandardConfigLoader, ConfigLoaderError
from .schema import get_schema_registry

# Type variable for configuration objects
T = TypeVar('T')


class StandardConfigManager(ConfigManager):
    """Standard implementation of the ConfigManager interface.
    
    This class provides a complete configuration management solution with:
    - Multiple configuration sources with priority
    - Environment-specific configuration
    - Schema validation
    - Configuration namespaces
    """
    
    def __init__(
        self,
        environment: ConfigEnvironment = ConfigEnvironment.DEVELOPMENT,
        env_prefix: str = "",
        env_separator: str = "__",
        audit_logger: Optional[AuditLogger] = None
    ):
        """Initialize the configuration manager.
        
        Args:
            environment: Current environment
            env_prefix: Prefix for environment variables
            env_separator: Separator for nested keys in environment variables
            audit_logger: Optional audit logger for configuration changes
        """
        self._environment = environment
        self._env_prefix = env_prefix
        self._env_separator = env_separator
        self._audit_logger = audit_logger
        
        # Create chain provider for multiple sources
        self._chain_provider = ChainConfigProvider()
        
        # Dictionary of source providers by name
        self._sources: Dict[str, ConfigProvider] = {}
        
        # Dictionary of registered schemas by namespace
        self._schemas: Dict[str, ConfigSchema] = {}
        
        # Default schema for root namespace
        self._default_schema: Optional[ConfigSchema] = None
        
        # Initialize standard loaders
        self._loader = StandardConfigLoader()
        
        # Add environment provider by default (lowest priority)
        env_provider = EnvironmentConfigProvider(env_prefix, env_separator)
        self.register_source(env_provider, ConfigSource.ENVIRONMENT, priority=-100)
        
        # Add defaults provider (lowest priority)
        defaults_provider = DictConfigProvider({})
        self.register_source(defaults_provider, ConfigSource.DEFAULT, priority=-999)
        
        # Flag to track if configuration has been loaded
        self._loaded = False
    
    def register_source(
        self, 
        source: Any, 
        source_type: ConfigSource, 
        priority: int = 0, 
        namespace: Optional[str] = None
    ) -> None:
        """Register a configuration source.
        
        Args:
            source: Configuration source
            source_type: Source type
            priority: Source priority (higher overwrites lower)
            namespace: Optional namespace for the source
        """
        # Generate a unique name for the source
        source_name = f"{source_type.value}_{priority}_{namespace or 'root'}"
        
        # Create provider based on source type
        if source_type == ConfigSource.FILE:
            provider = FileConfigProvider(source, self._loader)
        elif source_type == ConfigSource.ENVIRONMENT:
            if isinstance(source, EnvironmentConfigProvider):
                provider = source
            else:
                provider = EnvironmentConfigProvider(
                    self._env_prefix, self._env_separator
                )
        elif source_type == ConfigSource.DEFAULT:
            if isinstance(source, Dict):
                provider = DictConfigProvider(source)
            else:
                provider = source
        elif source_type == ConfigSource.MEMORY:
            if isinstance(source, Dict):
                provider = DictConfigProvider(source)
            else:
                provider = source
        elif source_type == ConfigSource.REMOTE:
            # Remote providers are expected to be already initialized
            provider = source
        elif source_type == ConfigSource.SECRET:
            # Secret providers are expected to be already initialized
            provider = source
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
        
        # Add to sources dictionary
        self._sources[source_name] = provider
        
        # Update the chain provider (remove first if already exists)
        # Find existing providers with the same name and remove them
        providers_to_keep = [p for p in self._chain_provider.providers
                           if id(p) not in [id(self._sources.get(name)) for name in self._sources
                                         if name == source_name]]
        
        # Create a new list with all providers sorted by priority
        all_providers = providers_to_keep + [provider]
        
        # Get all source names and their priorities
        source_priorities = [(name, int(name.split('_')[1]))
                            for name in self._sources.keys()]
        
        # Sort by priority (higher first)
        source_priorities.sort(key=lambda x: x[1], reverse=True)
        
        # Create a new chain provider with sorted providers
        sorted_providers = [self._sources[name] for name, _ in source_priorities]
        self._chain_provider.providers = sorted_providers
    
    def load(self) -> None:
        """Load configuration from all registered sources."""
        # Nothing to do if no sources
        if not self._sources:
            return
        
        # Mark as loaded
        self._loaded = True
        
        # Load default values from schemas
        if self._default_schema:
            defaults = self._default_schema.get_default()
            for provider in self._chain_provider.providers:
                if isinstance(provider, DictConfigProvider) and provider == self._sources.get(f"{ConfigSource.DEFAULT.value}_-999_root"):
                    provider.set_many(defaults)
        
        # Log configuration loading if audit logger is available
        if self._audit_logger:
            self._audit_logger.log_info(
                "config_load",
                {"environment": self._environment.value, 
                 "sources": list(self._sources.keys())}
            )
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        # Load if not already loaded
        if not self._loaded:
            self.load()
        
        return self._chain_provider.get(key, default)
    
    def set(self, key: str, value: Any, source: Optional[ConfigSource] = None) -> None:
        """Set a configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
            value: Configuration value
            source: Optional source to set the value in
        """
        # Load if not already loaded
        if not self._loaded:
            self.load()
        
        # If source is specified, find the provider
        if source:
            source_providers = [(name, provider) for name, provider in self._sources.items()
                                if name.startswith(f"{source.value}_")]
            if not source_providers:
                raise ValueError(f"No providers found for source type: {source}")
            
            # Use the highest priority provider
            source_providers.sort(key=lambda x: int(x[0].split('_')[1]), reverse=True)
            provider = source_providers[0][1]
            provider.set(key, value)
        else:
            # Otherwise, use the chain provider (will set in highest priority provider that supports setting)
            self._chain_provider.set(key, value)
        
        # Log configuration change if audit logger is available
        if self._audit_logger:
            self._audit_logger.log_info(
                "config_change",
                {"key": key, "source": source.value if source else "default"}
            )
    
    def has(self, key: str) -> bool:
        """Check if a configuration key exists.
        
        Args:
            key: Configuration key (dot notation supported)
            
        Returns:
            True if key exists, False otherwise
        """
        # Load if not already loaded
        if not self._loaded:
            self.load()
        
        return self._chain_provider.has(key)
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values.
        
        Returns:
            Dictionary of all configuration values
        """
        # Load if not already loaded
        if not self._loaded:
            self.load()
        
        return self._chain_provider.get_all()
    
    def get_namespace(self, namespace: str) -> Dict[str, Any]:
        """Get configuration values for a namespace.
        
        Args:
            namespace: Configuration namespace
            
        Returns:
            Dictionary of namespace configuration values
        """
        # Load if not already loaded
        if not self._loaded:
            self.load()
        
        # Get all configuration
        all_config = self.get_all()
        
        # Find all keys that start with the namespace
        namespace_prefix = f"{namespace}."
        namespace_config = {}
        
        # Extract nested keys directly
        if namespace in all_config and isinstance(all_config[namespace], dict):
            return all_config[namespace]
        
        # Find keys with dot notation
        for key, value in all_config.items():
            if key == namespace:
                namespace_config = value if isinstance(value, dict) else {key: value}
                break
            elif key.startswith(namespace_prefix):
                # Remove namespace prefix
                sub_key = key[len(namespace_prefix):]
                namespace_config[sub_key] = value
        
        return namespace_config
    
    def validate(
        self, 
        schema: Optional[ConfigSchema] = None, 
        level: ValidationLevel = ValidationLevel.SCHEMA
    ) -> ValidationResult:
        """Validate configuration.
        
        Args:
            schema: Configuration schema (if None, use registered schema)
            level: Validation level
            
        Returns:
            Validation result
        """
        # Load if not already loaded
        if not self._loaded:
            self.load()
        
        # Use provided schema or default schema
        if schema is None:
            schema = self._default_schema
        
        # Skip validation if no schema
        if schema is None:
            return ValidationResult(True)
        
        # Get all configuration
        config = self.get_all()
        
        # Validate based on level
        if level == ValidationLevel.NONE:
            return ValidationResult(True)
        elif level == ValidationLevel.SCHEMA:
            return schema.validate(config)
        elif level == ValidationLevel.STRICT:
            # First validate schema
            result = schema.validate(config)
            if not result:
                return result
            
            # Then perform additional type checking (already done in schema validation)
            return result
        elif level == ValidationLevel.CUSTOM:
            # Custom validation should be handled by the schema implementation
            return schema.validate(config)
        else:
            raise ValueError(f"Unsupported validation level: {level}")
    
    def get_environment(self) -> ConfigEnvironment:
        """Get current environment.
        
        Returns:
            Current environment
        """
        return self._environment
    
    def set_environment(self, environment: ConfigEnvironment) -> None:
        """Set current environment.
        
        Args:
            environment: Environment to set
        """
        self._environment = environment
        
        # Log environment change if audit logger is available
        if self._audit_logger:
            self._audit_logger.log_info(
                "config_environment_change",
                {"environment": environment.value}
            )
    
    def register_schema(self, schema: ConfigSchema, namespace: Optional[str] = None) -> None:
        """Register a schema for validation.
        
        Args:
            schema: Schema to register
            namespace: Optional namespace (if None, use as default schema)
        """
        if namespace:
            self._schemas[namespace] = schema
        else:
            self._default_schema = schema
            
            # If not loaded yet, add default values to the defaults provider
            if not self._loaded:
                defaults = schema.get_default()
                for provider in self._chain_provider.providers:
                    if isinstance(provider, DictConfigProvider) and provider == self._sources.get(f"{ConfigSource.DEFAULT.value}_-999_root"):
                        provider.set_many(defaults)


def create_config_manager(
    environment: ConfigEnvironment = ConfigEnvironment.DEVELOPMENT,
    env_prefix: str = "",
    env_separator: str = "__",
    audit_logger: Optional[AuditLogger] = None
) -> ConfigManager:
    """Create a configuration manager.
    
    Args:
        environment: Current environment
        env_prefix: Prefix for environment variables
        env_separator: Separator for nested keys in environment variables
        audit_logger: Optional audit logger for configuration changes
        
    Returns:
        Configuration manager
    """
    return StandardConfigManager(
        environment=environment,
        env_prefix=env_prefix,
        env_separator=env_separator,
        audit_logger=audit_logger
    )

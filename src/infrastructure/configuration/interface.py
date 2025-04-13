"""Interface definitions for the Circle Core configuration module.

This module defines the abstract base classes for all configuration components,
ensuring a consistent API across different implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set, Union, Type, TypeVar, Generic
from enum import Enum
from pathlib import Path
import os

# Type for configuration values
ConfigValue = Union[str, int, float, bool, Dict[str, Any], List[Any]]
T = TypeVar('T')


class ConfigFormat(Enum):
    """Supported configuration file formats."""
    
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    INI = "ini"
    ENV = "env"
    PYTHON = "py"


class ConfigSource(Enum):
    """Configuration source types."""
    
    FILE = "file"           # Configuration from file
    ENVIRONMENT = "env"     # Configuration from environment variables
    DEFAULT = "default"     # Default configuration
    MEMORY = "memory"       # In-memory configuration
    REMOTE = "remote"       # Remote configuration (e.g., API)
    SECRET = "secret"       # Secret configuration (e.g., vault)


class ConfigEnvironment(Enum):
    """Environment types for configuration."""
    
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    CUSTOM = "custom"


class ValidationLevel(Enum):
    """Validation levels for configuration."""
    
    NONE = "none"           # No validation
    SCHEMA = "schema"       # Validate against schema
    STRICT = "strict"       # Strict validation with type checking
    CUSTOM = "custom"       # Custom validation logic


class ValidationError:
    """Validation error details."""
    
    def __init__(self, path: str, message: str, value: Any = None):
        """Initialize validation error.
        
        Args:
            path: Path to the configuration value
            message: Error message
            value: The invalid value (optional)
        """
        self.path = path
        self.message = message
        self.value = value
    
    def __str__(self) -> str:
        """Convert to string.
        
        Returns:
            String representation
        """
        if self.value is not None:
            return f"{self.path}: {self.message} (value: {self.value})"
        return f"{self.path}: {self.message}"


class ValidationResult:
    """Result of configuration validation."""
    
    def __init__(self, is_valid: bool, errors: Optional[List[ValidationError]] = None):
        """Initialize validation result.
        
        Args:
            is_valid: Whether the configuration is valid
            errors: List of validation errors (if any)
        """
        self.is_valid = is_valid
        self.errors = errors or []
    
    def __bool__(self) -> bool:
        """Convert to boolean.
        
        Returns:
            True if valid, False otherwise
        """
        return self.is_valid


class ConfigSchema(ABC, Generic[T]):
    """Abstract base class for configuration schema."""
    
    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration against the schema.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Validation result
        """
        pass
    
    @abstractmethod
    def get_default(self) -> Dict[str, Any]:
        """Get default configuration values.
        
        Returns:
            Default configuration
        """
        pass
    
    @abstractmethod
    def parse(self, config: Dict[str, Any]) -> T:
        """Parse and convert configuration to a typed object.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Typed configuration object
        """
        pass


class ConfigProvider(ABC):
    """Abstract interface for configuration providers."""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
            value: Configuration value
        """
        pass
    
    @abstractmethod
    def has(self, key: str) -> bool:
        """Check if a configuration key exists.
        
        Args:
            key: Configuration key (dot notation supported)
            
        Returns:
            True if key exists, False otherwise
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
        """
        pass
    
    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values.
        
        Returns:
            Dictionary of all configuration values
        """
        pass
    
    @abstractmethod
    def set_many(self, config: Dict[str, Any], prefix: str = "") -> None:
        """Set multiple configuration values.
        
        Args:
            config: Dictionary of configuration values
            prefix: Optional prefix for keys
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all configuration values."""
        pass


class ConfigLoader(ABC):
    """Abstract interface for configuration loaders."""
    
    @abstractmethod
    def load(self, source: Union[str, Path, Dict[str, Any]], format: Optional[ConfigFormat] = None) -> Dict[str, Any]:
        """Load configuration from a source.
        
        Args:
            source: Configuration source (file path or dictionary)
            format: Configuration format (auto-detect if None)
            
        Returns:
            Configuration dictionary
        """
        pass
    
    @abstractmethod
    def save(self, config: Dict[str, Any], destination: Union[str, Path], format: ConfigFormat) -> None:
        """Save configuration to a destination.
        
        Args:
            config: Configuration dictionary
            destination: Destination file path
            format: Configuration format
        """
        pass


class ConfigManager(ABC):
    """Abstract interface for configuration managers."""
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def load(self) -> None:
        """Load configuration from all registered sources."""
        pass
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, source: Optional[ConfigSource] = None) -> None:
        """Set a configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
            value: Configuration value
            source: Optional source to set the value in
        """
        pass
    
    @abstractmethod
    def has(self, key: str) -> bool:
        """Check if a configuration key exists.
        
        Args:
            key: Configuration key (dot notation supported)
            
        Returns:
            True if key exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values.
        
        Returns:
            Dictionary of all configuration values
        """
        pass
    
    @abstractmethod
    def get_namespace(self, namespace: str) -> Dict[str, Any]:
        """Get configuration values for a namespace.
        
        Args:
            namespace: Configuration namespace
            
        Returns:
            Dictionary of namespace configuration values
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    def get_environment(self) -> ConfigEnvironment:
        """Get current environment.
        
        Returns:
            Current environment
        """
        pass
    
    @abstractmethod
    def set_environment(self, environment: ConfigEnvironment) -> None:
        """Set current environment.
        
        Args:
            environment: Environment to set
        """
        pass

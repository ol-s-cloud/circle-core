"""Circle Core Configuration Module.

This module provides comprehensive configuration management capabilities
for Circle Core applications and components.
"""

from .interface import (
    ConfigEnvironment, ConfigFormat, ConfigSource, ValidationLevel,
    ConfigSchema, ValidationResult, ValidationError
)
from .loaders import StandardConfigLoader, create_config_loader
from .providers import (
    DictConfigProvider, EnvironmentConfigProvider,
    FileConfigProvider, ChainConfigProvider
)
from .schema import (
    JsonSchema, DataclassSchema, SchemaRegistry, get_schema_registry,
    range_validator, length_validator, pattern_validator, enum_validator, type_validator
)
from .manager import StandardConfigManager, create_config_manager

# Global configuration manager instance
_config_manager = None

def get_config_manager():
    """Get the global configuration manager.
    
    Returns:
        Configuration manager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = create_config_manager()
    return _config_manager

def get_config(key, default=None):
    """Get a configuration value from the global manager.
    
    Args:
        key: Configuration key
        default: Default value if key not found
        
    Returns:
        Configuration value
    """
    return get_config_manager().get(key, default)

def set_config(key, value):
    """Set a configuration value in the global manager.
    
    Args:
        key: Configuration key
        value: Configuration value
    """
    get_config_manager().set(key, value)

__all__ = [
    'ConfigEnvironment', 'ConfigFormat', 'ConfigSource', 'ValidationLevel',
    'ConfigSchema', 'ValidationResult', 'ValidationError',
    'StandardConfigLoader', 'create_config_loader',
    'DictConfigProvider', 'EnvironmentConfigProvider',
    'FileConfigProvider', 'ChainConfigProvider',
    'JsonSchema', 'DataclassSchema', 'SchemaRegistry', 'get_schema_registry',
    'range_validator', 'length_validator', 'pattern_validator', 'enum_validator', 'type_validator',
    'StandardConfigManager', 'create_config_manager',
    'get_config_manager', 'get_config', 'set_config'
]

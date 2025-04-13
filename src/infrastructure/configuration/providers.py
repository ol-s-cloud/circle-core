"""Configuration providers for Circle Core.

This module provides implementations of various configuration providers.
"""

import os
from typing import Dict, List, Optional, Any, Set, Union, Type, TypeVar
from pathlib import Path

from ...core.audit import AuditLogger
from .interface import ConfigProvider


class DictConfigProvider(ConfigProvider):
    """Dictionary-based configuration provider.
    
    This provider stores configuration values in a dictionary.
    """
    
    def __init__(self, initial_config: Optional[Dict[str, Any]] = None):
        """Initialize dictionary config provider.
        
        Args:
            initial_config: Initial configuration dictionary
        """
        self._config = initial_config or {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        # Handle nested keys
        if "." in key:
            return self._get_nested(key, default)
        
        return self._config.get(key, default)
    
    def _get_nested(self, key: str, default: Any = None) -> Any:
        """Get a nested configuration value.
        
        Args:
            key: Configuration key (dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split(".")
        current = self._config
        
        for k in keys[:-1]:
            if not isinstance(current, dict) or k not in current:
                return default
            current = current[k]
        
        return current.get(keys[-1], default) if isinstance(current, dict) else default
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
            value: Configuration value
        """
        # Handle nested keys
        if "." in key:
            self._set_nested(key, value)
        else:
            self._config[key] = value
    
    def _set_nested(self, key: str, value: Any) -> None:
        """Set a nested configuration value.
        
        Args:
            key: Configuration key (dot notation)
            value: Configuration value
        """
        keys = key.split(".")
        current = self._config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            elif not isinstance(current[k], dict):
                current[k] = {}
            
            current = current[k]
        
        current[keys[-1]] = value
    
    def has(self, key: str) -> bool:
        """Check if a configuration key exists.
        
        Args:
            key: Configuration key (dot notation supported)
            
        Returns:
            True if key exists, False otherwise
        """
        # Handle nested keys
        if "." in key:
            return self._has_nested(key)
        
        return key in self._config
    
    def _has_nested(self, key: str) -> bool:
        """Check if a nested configuration key exists.
        
        Args:
            key: Configuration key (dot notation)
            
        Returns:
            True if key exists, False otherwise
        """
        keys = key.split(".")
        current = self._config
        
        for k in keys[:-1]:
            if not isinstance(current, dict) or k not in current:
                return False
            current = current[k]
        
        return isinstance(current, dict) and keys[-1] in current
    
    def delete(self, key: str) -> None:
        """Delete a configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
        """
        # Handle nested keys
        if "." in key:
            self._delete_nested(key)
        elif key in self._config:
            del self._config[key]
    
    def _delete_nested(self, key: str) -> None:
        """Delete a nested configuration value.
        
        Args:
            key: Configuration key (dot notation)
        """
        keys = key.split(".")
        current = self._config
        
        for k in keys[:-1]:
            if not isinstance(current, dict) or k not in current:
                return
            current = current[k]
        
        if isinstance(current, dict) and keys[-1] in current:
            del current[keys[-1]]
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values.
        
        Returns:
            Dictionary of all configuration values
        """
        return self._config.copy()
    
    def set_many(self, config: Dict[str, Any], prefix: str = "") -> None:
        """Set multiple configuration values.
        
        Args:
            config: Dictionary of configuration values
            prefix: Optional prefix for keys
        """
        for key, value in config.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                self.set_many(value, full_key)
            else:
                self.set(full_key, value)
    
    def clear(self) -> None:
        """Clear all configuration values."""
        self._config.clear()


class EnvironmentConfigProvider(ConfigProvider):
    """Environment variables configuration provider.
    
    This provider reads configuration values from environment variables.
    """
    
    def __init__(self, prefix: str = "", separator: str = "__"):
        """Initialize environment config provider.
        
        Args:
            prefix: Environment variable prefix
            separator: Separator for nested keys
        """
        self.prefix = prefix
        self.separator = separator
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        # Convert dot notation to environment variable format
        env_key = self._to_env_key(key)
        
        # Get from environment
        if env_key in os.environ:
            return self._convert_value(os.environ[env_key])
        
        return default
    
    def _to_env_key(self, key: str) -> str:
        """Convert a configuration key to an environment variable name.
        
        Args:
            key: Configuration key (dot notation)
            
        Returns:
            Environment variable name
        """
        # Replace dots with separator
        env_key = key.replace(".", self.separator)
        
        # Add prefix if specified
        if self.prefix:
            env_key = f"{self.prefix}{env_key}"
        
        # Convert to uppercase
        return env_key.upper()
    
    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type.
        
        Args:
            value: String value
            
        Returns:
            Converted value
        """
        # Boolean values
        if value.lower() in ("true", "yes", "on", "1"):
            return True
        elif value.lower() in ("false", "no", "off", "0"):
            return False
        
        # Numeric values
        if value.isdigit():
            return int(value)
        
        try:
            return float(value)
        except ValueError:
            pass
        
        # String value
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.
        
        This operation is not supported for environment variables.
        
        Args:
            key: Configuration key (dot notation supported)
            value: Configuration value
            
        Raises:
            NotImplementedError: Always raised
        """
        raise NotImplementedError("Cannot set environment variables")
    
    def has(self, key: str) -> bool:
        """Check if a configuration key exists.
        
        Args:
            key: Configuration key (dot notation supported)
            
        Returns:
            True if key exists, False otherwise
        """
        env_key = self._to_env_key(key)
        return env_key in os.environ
    
    def delete(self, key: str) -> None:
        """Delete a configuration value.
        
        This operation is not supported for environment variables.
        
        Args:
            key: Configuration key (dot notation supported)
            
        Raises:
            NotImplementedError: Always raised
        """
        raise NotImplementedError("Cannot delete environment variables")
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values.
        
        Returns:
            Dictionary of all configuration values
        """
        config = {}
        prefix_len = len(self.prefix)
        
        for key, value in os.environ.items():
            # Check if key starts with prefix (if prefix is specified)
            if self.prefix and not key.startswith(self.prefix):
                continue
            
            # Remove prefix
            if self.prefix:
                key = key[prefix_len:]
            
            # Skip if key is empty after removing prefix
            if not key:
                continue
            
            # Convert to lowercase
            key = key.lower()
            
            # Convert separator to dots
            key = key.replace(self.separator, ".")
            
            # Set value
            self._set_nested_value(config, key.split("."), self._convert_value(value))
        
        return config
    
    def _set_nested_value(self, config: Dict[str, Any], keys: List[str], value: Any) -> None:
        """Set a nested value in the configuration dictionary.
        
        Args:
            config: Configuration dictionary
            keys: List of keys representing the path
            value: Value to set
        """
        current = config
        last_idx = len(keys) - 1
        
        for i, key in enumerate(keys):
            if i == last_idx:
                current[key] = value
            else:
                if key not in current:
                    current[key] = {}
                elif not isinstance(current[key], dict):
                    current[key] = {}
                
                current = current[key]
    
    def set_many(self, config: Dict[str, Any], prefix: str = "") -> None:
        """Set multiple configuration values.
        
        This operation is not supported for environment variables.
        
        Args:
            config: Dictionary of configuration values
            prefix: Optional prefix for keys
            
        Raises:
            NotImplementedError: Always raised
        """
        raise NotImplementedError("Cannot set environment variables")
    
    def clear(self) -> None:
        """Clear all configuration values.
        
        This operation is not supported for environment variables.
        
        Raises:
            NotImplementedError: Always raised
        """
        raise NotImplementedError("Cannot clear environment variables")


class FileConfigProvider(ConfigProvider):
    """File-based configuration provider.
    
    This provider reads configuration values from a file.
    """
    
    def __init__(self, file_path: Union[str, Path], loader=None):
        """Initialize file config provider.
        
        Args:
            file_path: Configuration file path
            loader: Optional config loader (if None, use default loader)
        """
        self.file_path = Path(file_path)
        
        # Create loader if not provided
        if loader is None:
            from .loaders import create_config_loader
            self.loader = create_config_loader()
        else:
            self.loader = loader
        
        # Load configuration
        self._config = {}
        if self.file_path.exists():
            self._config = self.loader.load(self.file_path)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        # Use DictConfigProvider implementation
        provider = DictConfigProvider(self._config)
        return provider.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
            value: Configuration value
        """
        # Use DictConfigProvider implementation
        provider = DictConfigProvider(self._config)
        provider.set(key, value)
        
        # Save to file
        self._save()
    
    def has(self, key: str) -> bool:
        """Check if a configuration key exists.
        
        Args:
            key: Configuration key (dot notation supported)
            
        Returns:
            True if key exists, False otherwise
        """
        # Use DictConfigProvider implementation
        provider = DictConfigProvider(self._config)
        return provider.has(key)
    
    def delete(self, key: str) -> None:
        """Delete a configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
        """
        # Use DictConfigProvider implementation
        provider = DictConfigProvider(self._config)
        provider.delete(key)
        
        # Save to file
        self._save()
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values.
        
        Returns:
            Dictionary of all configuration values
        """
        return self._config.copy()
    
    def set_many(self, config: Dict[str, Any], prefix: str = "") -> None:
        """Set multiple configuration values.
        
        Args:
            config: Dictionary of configuration values
            prefix: Optional prefix for keys
        """
        # Use DictConfigProvider implementation
        provider = DictConfigProvider(self._config)
        provider.set_many(config, prefix)
        
        # Save to file
        self._save()
    
    def clear(self) -> None:
        """Clear all configuration values."""
        self._config.clear()
        
        # Save to file
        self._save()
    
    def _save(self) -> None:
        """Save configuration to file."""
        # Create directory if it doesn't exist
        os.makedirs(self.file_path.parent, exist_ok=True)
        
        # Determine format from file extension
        from .interface import ConfigFormat
        
        # Map file extensions to formats
        formats = {
            ".json": ConfigFormat.JSON,
            ".yaml": ConfigFormat.YAML,
            ".yml": ConfigFormat.YAML,
            ".toml": ConfigFormat.TOML,
            ".ini": ConfigFormat.INI,
            ".env": ConfigFormat.ENV
        }
        
        format = formats.get(self.file_path.suffix.lower(), ConfigFormat.JSON)
        
        # Save to file
        self.loader.save(self._config, self.file_path, format)


class ChainConfigProvider(ConfigProvider):
    """Chain of configuration providers.
    
    This provider combines multiple providers with priority.
    """
    
    def __init__(self, providers: Optional[List[ConfigProvider]] = None):
        """Initialize chain config provider.
        
        Args:
            providers: List of configuration providers (highest priority first)
        """
        self.providers = providers or []
    
    def add_provider(self, provider: ConfigProvider, index: Optional[int] = None) -> None:
        """Add a provider to the chain.
        
        Args:
            provider: Configuration provider
            index: Optional index (None to append)
        """
        if index is None:
            self.providers.append(provider)
        else:
            self.providers.insert(index, provider)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key (dot notation supported)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        # Try each provider in order
        for provider in self.providers:
            if provider.has(key):
                return provider.get(key)
        
        return default
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.
        
        Sets the value in the first provider that supports setting.
        
        Args:
            key: Configuration key (dot notation supported)
            value: Configuration value
        """
        # Try to set in first provider that supports it
        for provider in self.providers:
            try:
                provider.set(key, value)
                return
            except NotImplementedError:
                continue
        
        # If no provider supports setting, raise an error
        raise NotImplementedError("No provider in the chain supports setting values")
    
    def has(self, key: str) -> bool:
        """Check if a configuration key exists.
        
        Args:
            key: Configuration key (dot notation supported)
            
        Returns:
            True if key exists in any provider, False otherwise
        """
        # Check each provider
        for provider in self.providers:
            if provider.has(key):
                return True
        
        return False
    
    def delete(self, key: str) -> None:
        """Delete a configuration value.
        
        Deletes the value from all providers that support deletion.
        
        Args:
            key: Configuration key (dot notation supported)
        """
        # Delete from all providers that support it
        for provider in self.providers:
            try:
                if provider.has(key):
                    provider.delete(key)
            except NotImplementedError:
                continue
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values.
        
        Returns:
            Dictionary of all configuration values
        """
        # Merge configurations from all providers
        result = {}
        
        # Start from lowest priority and overwrite with higher priority
        for provider in reversed(self.providers):
            result.update(provider.get_all())
        
        return result
    
    def set_many(self, config: Dict[str, Any], prefix: str = "") -> None:
        """Set multiple configuration values.
        
        Sets values in the first provider that supports setting.
        
        Args:
            config: Dictionary of configuration values
            prefix: Optional prefix for keys
        """
        # Try to set in first provider that supports it
        for provider in self.providers:
            try:
                provider.set_many(config, prefix)
                return
            except NotImplementedError:
                continue
        
        # If no provider supports setting, raise an error
        raise NotImplementedError("No provider in the chain supports setting values")
    
    def clear(self) -> None:
        """Clear all configuration values.
        
        Clears values from all providers that support clearing.
        """
        # Clear all providers that support it
        for provider in self.providers:
            try:
                provider.clear()
            except NotImplementedError:
                continue

"""Configuration loaders for Circle Core.

This module provides loading and saving functionality for various configuration formats.
"""

import os
import json
import importlib.util
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import re

from .interface import ConfigLoader, ConfigFormat


class FormatNotSupportedError(Exception):
    """Exception raised when a configuration format is not supported."""
    pass


class StandardConfigLoader(ConfigLoader):
    """Standard implementation of configuration loader.
    
    Supports JSON, YAML, TOML, INI, ENV, and Python formats.
    """
    
    def __init__(self):
        """Initialize the configuration loader."""
        self._format_handlers = {
            ConfigFormat.JSON: self._load_json,
            ConfigFormat.YAML: self._load_yaml,
            ConfigFormat.TOML: self._load_toml,
            ConfigFormat.INI: self._load_ini,
            ConfigFormat.ENV: self._load_env,
            ConfigFormat.PYTHON: self._load_python
        }
        
        self._format_savers = {
            ConfigFormat.JSON: self._save_json,
            ConfigFormat.YAML: self._save_yaml,
            ConfigFormat.TOML: self._save_toml,
            ConfigFormat.INI: self._save_ini,
            ConfigFormat.ENV: self._save_env,
            ConfigFormat.PYTHON: self._save_python
        }
        
        self._extension_map = {
            ".json": ConfigFormat.JSON,
            ".yaml": ConfigFormat.YAML,
            ".yml": ConfigFormat.YAML,
            ".toml": ConfigFormat.TOML,
            ".ini": ConfigFormat.INI,
            ".env": ConfigFormat.ENV,
            ".py": ConfigFormat.PYTHON
        }
    
    def load(self, source: Union[str, Path, Dict[str, Any]], format: Optional[ConfigFormat] = None) -> Dict[str, Any]:
        """Load configuration from a source.
        
        Args:
            source: Configuration source (file path or dictionary)
            format: Configuration format (auto-detect if None)
            
        Returns:
            Configuration dictionary
            
        Raises:
            FormatNotSupportedError: If format is not supported
            FileNotFoundError: If source file does not exist
            ValueError: If format cannot be determined
        """
        # If source is already a dictionary, return it
        if isinstance(source, dict):
            return source
        
        # Convert Path to string
        if isinstance(source, Path):
            source = str(source)
        
        # Determine format if not specified
        if format is None:
            format = self._detect_format(source)
        
        # Get handler for format
        handler = self._format_handlers.get(format)
        if handler is None:
            raise FormatNotSupportedError(f"Format {format} is not supported")
        
        # Load configuration
        return handler(source)
    
    def save(self, config: Dict[str, Any], destination: Union[str, Path], format: ConfigFormat) -> None:
        """Save configuration to a destination.
        
        Args:
            config: Configuration dictionary
            destination: Destination file path
            format: Configuration format
            
        Raises:
            FormatNotSupportedError: If format is not supported
        """
        # Convert Path to string
        if isinstance(destination, Path):
            destination = str(destination)
        
        # Get saver for format
        saver = self._format_savers.get(format)
        if saver is None:
            raise FormatNotSupportedError(f"Format {format} is not supported")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Save configuration
        saver(config, destination)
    
    def _detect_format(self, source: str) -> ConfigFormat:
        """Detect configuration format from file extension.
        
        Args:
            source: File path
            
        Returns:
            Configuration format
            
        Raises:
            ValueError: If format cannot be determined
        """
        extension = os.path.splitext(source)[1].lower()
        format = self._extension_map.get(extension)
        
        if format is None:
            raise ValueError(f"Cannot determine format for extension '{extension}'")
        
        return format
    
    def _load_json(self, source: str) -> Dict[str, Any]:
        """Load JSON configuration.
        
        Args:
            source: JSON file path
            
        Returns:
            Configuration dictionary
        """
        with open(source, "r") as f:
            return json.load(f)
    
    def _save_json(self, config: Dict[str, Any], destination: str) -> None:
        """Save JSON configuration.
        
        Args:
            config: Configuration dictionary
            destination: JSON file path
        """
        with open(destination, "w") as f:
            json.dump(config, f, indent=2)
    
    def _load_yaml(self, source: str) -> Dict[str, Any]:
        """Load YAML configuration.
        
        Args:
            source: YAML file path
            
        Returns:
            Configuration dictionary
            
        Raises:
            ImportError: If PyYAML is not installed
        """
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML is required for YAML support. Install it with 'pip install pyyaml'.")
        
        with open(source, "r") as f:
            return yaml.safe_load(f)
    
    def _save_yaml(self, config: Dict[str, Any], destination: str) -> None:
        """Save YAML configuration.
        
        Args:
            config: Configuration dictionary
            destination: YAML file path
            
        Raises:
            ImportError: If PyYAML is not installed
        """
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML is required for YAML support. Install it with 'pip install pyyaml'.")
        
        with open(destination, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
    
    def _load_toml(self, source: str) -> Dict[str, Any]:
        """Load TOML configuration.
        
        Args:
            source: TOML file path
            
        Returns:
            Configuration dictionary
            
        Raises:
            ImportError: If toml or tomli is not installed
        """
        try:
            import toml
            return toml.load(source)
        except ImportError:
            try:
                import tomli
                with open(source, "rb") as f:
                    return tomli.load(f)
            except ImportError:
                raise ImportError("toml or tomli is required for TOML support. "
                                 "Install one with 'pip install toml' or 'pip install tomli'.")
    
    def _save_toml(self, config: Dict[str, Any], destination: str) -> None:
        """Save TOML configuration.
        
        Args:
            config: Configuration dictionary
            destination: TOML file path
            
        Raises:
            ImportError: If toml or tomli_w is not installed
        """
        try:
            import toml
            with open(destination, "w") as f:
                toml.dump(config, f)
        except ImportError:
            try:
                import tomli_w
                with open(destination, "wb") as f:
                    tomli_w.dump(config, f)
            except ImportError:
                raise ImportError("toml or tomli_w is required for TOML support. "
                                 "Install one with 'pip install toml' or 'pip install tomli_w'.")
    
    def _load_ini(self, source: str) -> Dict[str, Any]:
        """Load INI configuration.
        
        Args:
            source: INI file path
            
        Returns:
            Configuration dictionary
        """
        try:
            import configparser
        except ImportError:
            # configparser is in the standard library, but just in case
            raise ImportError("configparser is required for INI support.")
        
        config = configparser.ConfigParser()
        config.read(source)
        
        # Convert to dictionary
        result = {}
        for section in config.sections():
            result[section] = {}
            for key, value in config[section].items():
                # Try to parse as JSON for types
                try:
                    result[section][key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    result[section][key] = value
        
        return result
    
    def _save_ini(self, config: Dict[str, Any], destination: str) -> None:
        """Save INI configuration.
        
        Args:
            config: Configuration dictionary
            destination: INI file path
        """
        try:
            import configparser
        except ImportError:
            # configparser is in the standard library, but just in case
            raise ImportError("configparser is required for INI support.")
        
        ini_config = configparser.ConfigParser()
        
        for section, section_config in config.items():
            if not isinstance(section_config, dict):
                # Skip non-dict sections
                continue
            
            ini_config[section] = {}
            for key, value in section_config.items():
                if isinstance(value, (dict, list)):
                    # Convert complex types to JSON
                    ini_config[section][key] = json.dumps(value)
                else:
                    ini_config[section][key] = str(value)
        
        with open(destination, "w") as f:
            ini_config.write(f)
    
    def _load_env(self, source: str) -> Dict[str, Any]:
        """Load environment variables from .env file.
        
        Args:
            source: .env file path
            
        Returns:
            Configuration dictionary
        """
        result = {}
        
        with open(source, "r") as f:
            for line in f:
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue
                
                # Parse key-value pair
                match = re.match(r"^([A-Za-z0-9_]+)=(.*)$", line)
                if match:
                    key, value = match.groups()
                    
                    # Remove quotes if present
                    value = value.strip()
                    if value and value[0] == value[-1] and value[0] in ('"', "'"):
                        value = value[1:-1]
                    
                    # Try to parse as JSON for types
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = value
        
        return result
    
    def _save_env(self, config: Dict[str, Any], destination: str) -> None:
        """Save configuration as environment variables.
        
        Args:
            config: Configuration dictionary
            destination: .env file path
        """
        with open(destination, "w") as f:
            for key, value in config.items():
                if isinstance(value, (dict, list)):
                    # Convert complex types to JSON
                    f.write(f"{key}='{json.dumps(value)}'\n")
                elif isinstance(value, str):
                    # Quote strings
                    f.write(f'{key}="{value}"\n')
                else:
                    f.write(f"{key}={value}\n")
    
    def _load_python(self, source: str) -> Dict[str, Any]:
        """Load Python configuration.
        
        Args:
            source: Python file path
            
        Returns:
            Configuration dictionary
        """
        # Load the Python module
        spec = importlib.util.spec_from_file_location("config_module", source)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load Python module from {source}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Extract configuration
        result = {}
        for key in dir(module):
            # Skip private attributes
            if key.startswith("_"):
                continue
            
            value = getattr(module, key)
            
            # Skip functions and modules
            if callable(value) or isinstance(value, type):
                continue
            
            result[key] = value
        
        return result
    
    def _save_python(self, config: Dict[str, Any], destination: str) -> None:
        """Save configuration as Python file.
        
        Args:
            config: Configuration dictionary
            destination: Python file path
        """
        with open(destination, "w") as f:
            f.write("# Generated configuration file\n\n")
            
            for key, value in config.items():
                if isinstance(value, str):
                    # Quote strings
                    f.write(f'{key} = "{value}"\n')
                else:
                    # Use repr for other types
                    f.write(f"{key} = {repr(value)}\n")


class EnvironmentLoader:
    """Environment variable configuration loader."""
    
    def __init__(self, prefix: str = "APP_"):
        """Initialize environment loader.
        
        Args:
            prefix: Environment variable prefix
        """
        self.prefix = prefix
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from environment variables.
        
        Returns:
            Configuration dictionary
        """
        result = {}
        prefix_len = len(self.prefix)
        
        for key, value in os.environ.items():
            # Skip variables without prefix
            if not key.startswith(self.prefix):
                continue
            
            # Remove prefix
            config_key = key[prefix_len:].lower()
            
            # Handle nested keys (e.g., APP_DATABASE_HOST -> database.host)
            parts = config_key.split("_")
            current = result
            
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                elif not isinstance(current[part], dict):
                    # If the key already exists but is not a dict, make it a dict
                    current[part] = {"value": current[part]}
                
                current = current[part]
            
            # Set the final value
            final_key = parts[-1]
            
            # Try to parse as JSON for types
            try:
                current[final_key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                current[final_key] = value
        
        return result


# Common loader instances
standard_loader = StandardConfigLoader()
environment_loader = EnvironmentLoader()


def load_config_file(path: Union[str, Path], format: Optional[ConfigFormat] = None) -> Dict[str, Any]:
    """Load configuration from a file.
    
    Args:
        path: File path
        format: Configuration format (auto-detect if None)
        
    Returns:
        Configuration dictionary
    """
    return standard_loader.load(path, format)


def save_config_file(config: Dict[str, Any], path: Union[str, Path], format: ConfigFormat) -> None:
    """Save configuration to a file.
    
    Args:
        config: Configuration dictionary
        path: File path
        format: Configuration format
    """
    standard_loader.save(config, path, format)


def load_env_config(prefix: str = "APP_") -> Dict[str, Any]:
    """Load configuration from environment variables.
    
    Args:
        prefix: Environment variable prefix
        
    Returns:
        Configuration dictionary
    """
    loader = EnvironmentLoader(prefix)
    return loader.load()

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


class ConfigLoaderError(Exception):
    """Error raised during configuration loading."""
    pass


class StandardConfigLoader(ConfigLoader):
    """Standard implementation of configuration loader.
    
    Supports loading from multiple formats:
    - JSON
    - YAML (if PyYAML is installed)
    - TOML (if tomli/tomllib is installed)
    - INI (using Python's configparser)
    - ENV (environment variables)
    - Python modules
    """
    
    def __init__(self):
        """Initialize the configuration loader."""
        # Check for optional dependencies
        self._yaml_available = self._check_yaml()
        self._toml_available = self._check_toml()
    
    def _check_yaml(self) -> bool:
        """Check if PyYAML is available.
        
        Returns:
            True if available, False otherwise
        """
        try:
            import yaml
            return True
        except ImportError:
            return False
    
    def _check_toml(self) -> bool:
        """Check if TOML support is available.
        
        Returns:
            True if available, False otherwise
        """
        try:
            # Python 3.11+
            import tomllib
            return True
        except ImportError:
            try:
                # Python 3.6-3.10 with tomli installed
                import tomli
                return True
            except ImportError:
                return False
    
    def load(self, source: Union[str, Path, Dict[str, Any]], format: Optional[ConfigFormat] = None) -> Dict[str, Any]:
        """Load configuration from a source.
        
        Args:
            source: Configuration source (file path or dictionary)
            format: Configuration format (auto-detect if None)
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigLoaderError: If loading fails
        """
        # If source is already a dictionary, return it
        if isinstance(source, dict):
            return source
        
        # Convert to Path if it's a string
        if isinstance(source, str):
            source = Path(source)
        
        # Check if the file exists
        if not source.exists():
            raise ConfigLoaderError(f"Configuration file not found: {source}")
        
        # Auto-detect format if not specified
        if format is None:
            format = self._detect_format(source)
        
        # Load based on format
        if format == ConfigFormat.JSON:
            return self._load_json(source)
        elif format == ConfigFormat.YAML:
            return self._load_yaml(source)
        elif format == ConfigFormat.TOML:
            return self._load_toml(source)
        elif format == ConfigFormat.INI:
            return self._load_ini(source)
        elif format == ConfigFormat.ENV:
            return self._load_env(source)
        elif format == ConfigFormat.PYTHON:
            return self._load_python(source)
        else:
            raise ConfigLoaderError(f"Unsupported configuration format: {format}")
    
    def save(self, config: Dict[str, Any], destination: Union[str, Path], format: ConfigFormat) -> None:
        """Save configuration to a destination.
        
        Args:
            config: Configuration dictionary
            destination: Destination file path
            format: Configuration format
            
        Raises:
            ConfigLoaderError: If saving fails
        """
        # Convert to Path if it's a string
        if isinstance(destination, str):
            destination = Path(destination)
        
        # Ensure the directory exists
        os.makedirs(destination.parent, exist_ok=True)
        
        # Save based on format
        if format == ConfigFormat.JSON:
            self._save_json(config, destination)
        elif format == ConfigFormat.YAML:
            self._save_yaml(config, destination)
        elif format == ConfigFormat.TOML:
            self._save_toml(config, destination)
        elif format == ConfigFormat.INI:
            self._save_ini(config, destination)
        elif format == ConfigFormat.ENV:
            self._save_env(config, destination)
        else:
            raise ConfigLoaderError(f"Unsupported configuration format for saving: {format}")
    
    def _detect_format(self, path: Path) -> ConfigFormat:
        """Detect configuration format from file extension.
        
        Args:
            path: File path
            
        Returns:
            Detected format
            
        Raises:
            ConfigLoaderError: If format cannot be detected
        """
        extension = path.suffix.lower()
        
        if extension in (".json",):
            return ConfigFormat.JSON
        elif extension in (".yaml", ".yml"):
            if not self._yaml_available:
                raise ConfigLoaderError("PyYAML is not installed, cannot load YAML files")
            return ConfigFormat.YAML
        elif extension in (".toml",):
            if not self._toml_available:
                raise ConfigLoaderError("TOML support not available, cannot load TOML files")
            return ConfigFormat.TOML
        elif extension in (".ini", ".cfg"):
            return ConfigFormat.INI
        elif extension in (".env",):
            return ConfigFormat.ENV
        elif extension in (".py",):
            return ConfigFormat.PYTHON
        else:
            raise ConfigLoaderError(f"Could not detect configuration format from extension: {extension}")
    
    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON configuration.
        
        Args:
            path: JSON file path
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigLoaderError: If loading fails
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise ConfigLoaderError(f"Failed to load JSON configuration: {e}")
    
    def _save_json(self, config: Dict[str, Any], path: Path) -> None:
        """Save JSON configuration.
        
        Args:
            config: Configuration dictionary
            path: JSON file path
            
        Raises:
            ConfigLoaderError: If saving fails
        """
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            raise ConfigLoaderError(f"Failed to save JSON configuration: {e}")
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML configuration.
        
        Args:
            path: YAML file path
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigLoaderError: If loading fails
        """
        if not self._yaml_available:
            raise ConfigLoaderError("PyYAML is not installed, cannot load YAML files")
        
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise ConfigLoaderError(f"Failed to load YAML configuration: {e}")
    
    def _save_yaml(self, config: Dict[str, Any], path: Path) -> None:
        """Save YAML configuration.
        
        Args:
            config: Configuration dictionary
            path: YAML file path
            
        Raises:
            ConfigLoaderError: If saving fails
        """
        if not self._yaml_available:
            raise ConfigLoaderError("PyYAML is not installed, cannot save YAML files")
        
        try:
            import yaml
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False)
        except Exception as e:
            raise ConfigLoaderError(f"Failed to save YAML configuration: {e}")
    
    def _load_toml(self, path: Path) -> Dict[str, Any]:
        """Load TOML configuration.
        
        Args:
            path: TOML file path
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigLoaderError: If loading fails
        """
        if not self._toml_available:
            raise ConfigLoaderError("TOML support not available, cannot load TOML files")
        
        try:
            # Try Python 3.11+ tomllib first
            try:
                import tomllib
                with open(path, "rb") as f:
                    return tomllib.load(f)
            except ImportError:
                # Fall back to tomli
                import tomli
                with open(path, "rb") as f:
                    return tomli.load(f)
        except Exception as e:
            raise ConfigLoaderError(f"Failed to load TOML configuration: {e}")
    
    def _save_toml(self, config: Dict[str, Any], path: Path) -> None:
        """Save TOML configuration.
        
        Args:
            config: Configuration dictionary
            path: TOML file path
            
        Raises:
            ConfigLoaderError: If saving fails
        """
        if not self._toml_available:
            raise ConfigLoaderError("TOML support not available, cannot save TOML files")
        
        try:
            # tomli-w for writing
            try:
                import tomli_w
                with open(path, "wb") as f:
                    tomli_w.dump(config, f)
            except ImportError:
                raise ConfigLoaderError("tomli-w is not installed, cannot save TOML files")
        except Exception as e:
            raise ConfigLoaderError(f"Failed to save TOML configuration: {e}")
    
    def _load_ini(self, path: Path) -> Dict[str, Any]:
        """Load INI configuration.
        
        Args:
            path: INI file path
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigLoaderError: If loading fails
        """
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(path)
            
            # Convert to dictionary
            result = {}
            for section in config.sections():
                result[section] = {}
                for key, value in config[section].items():
                    # Try to convert to appropriate types
                    try:
                        if value.lower() in ("true", "yes", "on", "1"):
                            result[section][key] = True
                        elif value.lower() in ("false", "no", "off", "0"):
                            result[section][key] = False
                        elif value.isdigit():
                            result[section][key] = int(value)
                        elif self._is_float(value):
                            result[section][key] = float(value)
                        else:
                            result[section][key] = value
                    except (ValueError, AttributeError):
                        result[section][key] = value
            
            return result
        except Exception as e:
            raise ConfigLoaderError(f"Failed to load INI configuration: {e}")
    
    def _is_float(self, value: str) -> bool:
        """Check if a string can be converted to a float.
        
        Args:
            value: String value
            
        Returns:
            True if convertible to float, False otherwise
        """
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    def _save_ini(self, config: Dict[str, Any], path: Path) -> None:
        """Save INI configuration.
        
        Args:
            config: Configuration dictionary
            path: INI file path
            
        Raises:
            ConfigLoaderError: If saving fails
        """
        try:
            import configparser
            ini_config = configparser.ConfigParser()
            
            # Convert dictionary to INI
            for section, values in config.items():
                if not isinstance(values, dict):
                    raise ConfigLoaderError(f"INI configuration requires dictionary values for sections, got {type(values)} for section {section}")
                
                ini_config[section] = {}
                for key, value in values.items():
                    ini_config[section][key] = str(value)
            
            with open(path, "w", encoding="utf-8") as f:
                ini_config.write(f)
        except Exception as e:
            raise ConfigLoaderError(f"Failed to save INI configuration: {e}")
    
    def _load_env(self, path: Path) -> Dict[str, Any]:
        """Load environment variables from .env file.
        
        Args:
            path: .env file path
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigLoaderError: If loading fails
        """
        try:
            # Parse .env file
            result = {}
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    
                    # Parse key=value
                    match = re.match(r'^([A-Za-z0-9_]+)=(.*)$', line)
                    if match:
                        key, value = match.groups()
                        
                        # Strip quotes
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        
                        # Convert to appropriate types
                        if value.lower() in ("true", "yes", "on", "1"):
                            result[key] = True
                        elif value.lower() in ("false", "no", "off", "0"):
                            result[key] = False
                        elif value.isdigit():
                            result[key] = int(value)
                        elif self._is_float(value):
                            result[key] = float(value)
                        else:
                            result[key] = value
            
            return result
        except Exception as e:
            raise ConfigLoaderError(f"Failed to load .env configuration: {e}")
    
    def _save_env(self, config: Dict[str, Any], path: Path) -> None:
        """Save environment variables to .env file.
        
        Args:
            config: Configuration dictionary
            path: .env file path
            
        Raises:
            ConfigLoaderError: If saving fails
        """
        try:
            with open(path, "w", encoding="utf-8") as f:
                for key, value in config.items():
                    # Quote strings with spaces
                    if isinstance(value, str) and (" " in value or "=" in value):
                        value = f'"{value}"'
                    
                    f.write(f"{key}={value}\n")
        except Exception as e:
            raise ConfigLoaderError(f"Failed to save .env configuration: {e}")
    
    def _load_python(self, path: Path) -> Dict[str, Any]:
        """Load configuration from Python module.
        
        Args:
            path: Python file path
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigLoaderError: If loading fails
        """
        try:
            # Load module
            module_name = path.stem
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                raise ConfigLoaderError(f"Failed to load Python module: {path}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Extract uppercase variables as configuration
            config = {}
            for key in dir(module):
                if key.isupper():
                    config[key] = getattr(module, key)
            
            return config
        except Exception as e:
            raise ConfigLoaderError(f"Failed to load Python configuration: {e}")


class EnvironmentConfigLoader:
    """Load configuration from environment variables."""
    
    def __init__(self, prefix: str = "", separator: str = "__"):
        """Initialize environment config loader.
        
        Args:
            prefix: Environment variable prefix
            separator: Separator for nested keys
        """
        self.prefix = prefix
        self.separator = separator
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from environment variables.
        
        Returns:
            Configuration dictionary
        """
        config = {}
        prefix_len = len(self.prefix)
        
        for key, value in os.environ.items():
            # Check if key starts with prefix
            if self.prefix and not key.startswith(self.prefix):
                continue
            
            # Remove prefix
            if self.prefix:
                key = key[prefix_len:]
            
            # Skip if key is empty after removing prefix
            if not key:
                continue
            
            # Process nested keys
            if self.separator in key:
                self._set_nested_value(config, key.split(self.separator), self._convert_value(value))
            else:
                config[key] = self._convert_value(value)
        
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


# Factory function to create a config loader
def create_config_loader(format: Optional[ConfigFormat] = None) -> ConfigLoader:
    """Create a configuration loader.
    
    Args:
        format: Configuration format
        
    Returns:
        Configuration loader
    """
    return StandardConfigLoader()

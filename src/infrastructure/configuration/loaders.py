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


class ConfigLoadError(Exception):
    """Error when loading configuration."""
    pass


class ConfigSaveError(Exception):
    """Error when saving configuration."""
    pass


class JsonLoader:
    """JSON configuration loader."""
    
    def load(self, source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
        """Load JSON configuration.
        
        Args:
            source: JSON file path or dictionary
            
        Returns:
            Configuration dictionary
        
        Raises:
            ConfigLoadError: If failed to load
        """
        if isinstance(source, dict):
            return source
        
        try:
            with open(str(source), 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
            raise ConfigLoadError(f"Failed to load JSON configuration: {e}")
    
    def save(self, config: Dict[str, Any], destination: Union[str, Path]) -> None:
        """Save configuration to JSON file.
        
        Args:
            config: Configuration dictionary
            destination: JSON file path
            
        Raises:
            ConfigSaveError: If failed to save
        """
        try:
            with open(str(destination), 'w') as f:
                json.dump(config, f, indent=2)
        except (OSError, TypeError) as e:
            raise ConfigSaveError(f"Failed to save JSON configuration: {e}")


class YamlLoader:
    """YAML configuration loader."""
    
    def load(self, source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
        """Load YAML configuration.
        
        Args:
            source: YAML file path or dictionary
            
        Returns:
            Configuration dictionary
        
        Raises:
            ConfigLoadError: If failed to load
        """
        if isinstance(source, dict):
            return source
        
        try:
            import yaml
        except ImportError:
            raise ConfigLoadError("PyYAML is not installed. Install it with 'pip install pyyaml'")
        
        try:
            with open(str(source), 'r') as f:
                return yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError, OSError) as e:
            raise ConfigLoadError(f"Failed to load YAML configuration: {e}")
    
    def save(self, config: Dict[str, Any], destination: Union[str, Path]) -> None:
        """Save configuration to YAML file.
        
        Args:
            config: Configuration dictionary
            destination: YAML file path
            
        Raises:
            ConfigSaveError: If failed to save
        """
        try:
            import yaml
        except ImportError:
            raise ConfigSaveError("PyYAML is not installed. Install it with 'pip install pyyaml'")
        
        try:
            with open(str(destination), 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
        except (OSError, yaml.YAMLError) as e:
            raise ConfigSaveError(f"Failed to save YAML configuration: {e}")


class TomlLoader:
    """TOML configuration loader."""
    
    def load(self, source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
        """Load TOML configuration.
        
        Args:
            source: TOML file path or dictionary
            
        Returns:
            Configuration dictionary
        
        Raises:
            ConfigLoadError: If failed to load
        """
        if isinstance(source, dict):
            return source
        
        try:
            import toml
        except ImportError:
            raise ConfigLoadError("toml is not installed. Install it with 'pip install toml'")
        
        try:
            with open(str(source), 'r') as f:
                return toml.load(f)
        except (FileNotFoundError, toml.TomlDecodeError, OSError) as e:
            raise ConfigLoadError(f"Failed to load TOML configuration: {e}")
    
    def save(self, config: Dict[str, Any], destination: Union[str, Path]) -> None:
        """Save configuration to TOML file.
        
        Args:
            config: Configuration dictionary
            destination: TOML file path
            
        Raises:
            ConfigSaveError: If failed to save
        """
        try:
            import toml
        except ImportError:
            raise ConfigSaveError("toml is not installed. Install it with 'pip install toml'")
        
        try:
            with open(str(destination), 'w') as f:
                toml.dump(config, f)
        except (OSError, TypeError) as e:
            raise ConfigSaveError(f"Failed to save TOML configuration: {e}")


class IniLoader:
    """INI configuration loader."""
    
    def load(self, source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
        """Load INI configuration.
        
        Args:
            source: INI file path or dictionary
            
        Returns:
            Configuration dictionary
        
        Raises:
            ConfigLoadError: If failed to load
        """
        if isinstance(source, dict):
            return source
        
        try:
            import configparser
        except ImportError:
            raise ConfigLoadError("configparser is not available")
        
        try:
            config = configparser.ConfigParser()
            config.read(str(source))
            
            # Convert to dictionary
            result = {}
            for section in config.sections():
                result[section] = {}
                for key, value in config[section].items():
                    # Try to convert to appropriate type
                    try:
                        # Try as int
                        result[section][key] = int(value)
                    except ValueError:
                        try:
                            # Try as float
                            result[section][key] = float(value)
                        except ValueError:
                            # Try as boolean
                            if value.lower() in ("true", "yes", "1"):
                                result[section][key] = True
                            elif value.lower() in ("false", "no", "0"):
                                result[section][key] = False
                            else:
                                # Keep as string
                                result[section][key] = value
            
            return result
        except (FileNotFoundError, configparser.Error, OSError) as e:
            raise ConfigLoadError(f"Failed to load INI configuration: {e}")
    
    def save(self, config: Dict[str, Any], destination: Union[str, Path]) -> None:
        """Save configuration to INI file.
        
        Args:
            config: Configuration dictionary
            destination: INI file path
            
        Raises:
            ConfigSaveError: If failed to save
        """
        try:
            import configparser
        except ImportError:
            raise ConfigSaveError("configparser is not available")
        
        try:
            ini_config = configparser.ConfigParser()
            
            # Convert dictionary to configparser format
            for section, section_config in config.items():
                ini_config[section] = {}
                for key, value in section_config.items():
                    ini_config[section][key] = str(value)
            
            with open(str(destination), 'w') as f:
                ini_config.write(f)
        except (OSError, TypeError, configparser.Error) as e:
            raise ConfigSaveError(f"Failed to save INI configuration: {e}")


class EnvLoader:
    """Environment variables configuration loader."""
    
    def __init__(self, prefix: str = ""):
        """Initialize environment variables loader.
        
        Args:
            prefix: Optional prefix for environment variables
        """
        self.prefix = prefix
    
    def load(self, source: Union[str, Path, Dict[str, Any]] = None) -> Dict[str, Any]:
        """Load configuration from environment variables.
        
        Args:
            source: Optional file path (ignored)
            
        Returns:
            Configuration dictionary
        """
        result = {}
        
        # Get all environment variables
        for key, value in os.environ.items():
            # Check if key has prefix
            if self.prefix and not key.startswith(self.prefix):
                continue
            
            # Remove prefix
            if self.prefix:
                clean_key = key[len(self.prefix):]
            else:
                clean_key = key
            
            # Convert value to appropriate type
            try:
                # Try as int
                value = int(value)
            except ValueError:
                try:
                    # Try as float
                    value = float(value)
                except ValueError:
                    # Try as boolean
                    if value.lower() in ("true", "yes", "1"):
                        value = True
                    elif value.lower() in ("false", "no", "0"):
                        value = False
                    # Otherwise, keep as string
            
            # Convert key to nested structure
            # e.g. APP_DATABASE_HOST -> app.database.host
            parts = re.split(r'[_.]', clean_key.lower())
            current = result
            
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                elif not isinstance(current[part], dict):
                    # If the key already exists but is not a dict, convert it
                    current[part] = {"value": current[part]}
                current = current[part]
            
            current[parts[-1]] = value
        
        return result
    
    def save(self, config: Dict[str, Any], destination: Union[str, Path]) -> None:
        """Save configuration to environment file.
        
        Args:
            config: Configuration dictionary
            destination: Environment file path
            
        Raises:
            ConfigSaveError: If failed to save
        """
        try:
            with open(str(destination), 'w') as f:
                # Flatten dictionary
                env_vars = self._flatten_dict(config)
                
                # Write to file
                for key, value in env_vars.items():
                    if self.prefix:
                        key = f"{self.prefix}{key}"
                    f.write(f"{key}={value}\n")
        except OSError as e:
            raise ConfigSaveError(f"Failed to save environment configuration: {e}")
    
    def _flatten_dict(self, config: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
        """Flatten a nested dictionary to environment variables.
        
        Args:
            config: Configuration dictionary
            prefix: Key prefix
            
        Returns:
            Dictionary of environment variables
        """
        result = {}
        
        for key, value in config.items():
            env_key = f"{prefix}{'_' if prefix else ''}{key}".upper()
            
            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                nested = self._flatten_dict(value, env_key)
                result.update(nested)
            else:
                # Convert value to string
                result[env_key] = str(value)
        
        return result


class PythonLoader:
    """Python module configuration loader."""
    
    def load(self, source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
        """Load configuration from Python module.
        
        Args:
            source: Python file path or dictionary
            
        Returns:
            Configuration dictionary
        
        Raises:
            ConfigLoadError: If failed to load
        """
        if isinstance(source, dict):
            return source
        
        try:
            # Load module
            spec = importlib.util.spec_from_file_location("config_module", str(source))
            if spec is None or spec.loader is None:
                raise ConfigLoadError(f"Failed to load Python module: {source}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Extract configuration
            config = {}
            for key in dir(module):
                # Skip private/special attributes
                if key.startswith('_'):
                    continue
                
                value = getattr(module, key)
                
                # Skip functions and classes
                if callable(value) or isinstance(value, type):
                    continue
                
                config[key] = value
            
            return config
        except (FileNotFoundError, ImportError, OSError) as e:
            raise ConfigLoadError(f"Failed to load Python configuration: {e}")
    
    def save(self, config: Dict[str, Any], destination: Union[str, Path]) -> None:
        """Save configuration to Python file.
        
        Args:
            config: Configuration dictionary
            destination: Python file path
            
        Raises:
            ConfigSaveError: If failed to save
        """
        try:
            with open(str(destination), 'w') as f:
                f.write("# Configuration generated by Circle Core\n\n")
                
                for key, value in config.items():
                    if isinstance(value, str):
                        f.write(f"{key} = '{value}'\n")
                    else:
                        f.write(f"{key} = {repr(value)}\n")
        except OSError as e:
            raise ConfigSaveError(f"Failed to save Python configuration: {e}")


class StandardConfigLoader(ConfigLoader):
    """Standard configuration loader supporting multiple formats."""
    
    def __init__(self):
        """Initialize standard configuration loader."""
        self.loaders = {
            ConfigFormat.JSON: JsonLoader(),
            ConfigFormat.YAML: YamlLoader(),
            ConfigFormat.TOML: TomlLoader(),
            ConfigFormat.INI: IniLoader(),
            ConfigFormat.ENV: EnvLoader(),
            ConfigFormat.PYTHON: PythonLoader()
        }
    
    def load(self, source: Union[str, Path, Dict[str, Any]], format: Optional[ConfigFormat] = None) -> Dict[str, Any]:
        """Load configuration from a source.
        
        Args:
            source: Configuration source (file path or dictionary)
            format: Configuration format (auto-detect if None)
            
        Returns:
            Configuration dictionary
        
        Raises:
            ConfigLoadError: If failed to load
        """
        if isinstance(source, dict):
            return source
        
        # Auto-detect format if not specified
        if format is None:
            format = self._detect_format(source)
        
        # Get loader for format
        loader = self.loaders.get(format)
        if loader is None:
            raise ConfigLoadError(f"Unsupported format: {format}")
        
        # Load configuration
        return loader.load(source)
    
    def save(self, config: Dict[str, Any], destination: Union[str, Path], format: ConfigFormat) -> None:
        """Save configuration to a destination.
        
        Args:
            config: Configuration dictionary
            destination: Destination file path
            format: Configuration format
        
        Raises:
            ConfigSaveError: If failed to save
        """
        # Get loader for format
        loader = self.loaders.get(format)
        if loader is None:
            raise ConfigSaveError(f"Unsupported format: {format}")
        
        # Save configuration
        loader.save(config, destination)
    
    def _detect_format(self, source: Union[str, Path]) -> ConfigFormat:
        """Detect configuration format from file extension.
        
        Args:
            source: File path
            
        Returns:
            Detected format
        
        Raises:
            ConfigLoadError: If format could not be detected
        """
        source_str = str(source)
        
        if source_str.endswith((".json", ".json5")):
            return ConfigFormat.JSON
        elif source_str.endswith((".yaml", ".yml")):
            return ConfigFormat.YAML
        elif source_str.endswith(".toml"):
            return ConfigFormat.TOML
        elif source_str.endswith((".ini", ".cfg", ".conf")):
            return ConfigFormat.INI
        elif source_str.endswith((".env", ".envrc")):
            return ConfigFormat.ENV
        elif source_str.endswith((".py", ".pyc")):
            return ConfigFormat.PYTHON
        else:
            raise ConfigLoadError(f"Could not detect format for: {source}")

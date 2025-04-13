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


class DefaultConfigLoader(ConfigLoader):
    """Default implementation of configuration loader.
    
    This loader supports various file formats (JSON, YAML, TOML, INI, ENV, Python).
    """
    
    def __init__(self):
        """Initialize the default configuration loader."""
        self._format_handlers = {
            ConfigFormat.JSON: self._load_json,
            ConfigFormat.YAML: self._load_yaml,
            ConfigFormat.TOML: self._load_toml,
            ConfigFormat.INI: self._load_ini,
            ConfigFormat.ENV: self._load_env,
            ConfigFormat.PYTHON: self._load_python
        }
        
        self._save_handlers = {
            ConfigFormat.JSON: self._save_json,
            ConfigFormat.YAML: self._save_yaml,
            ConfigFormat.TOML: self._save_toml,
            ConfigFormat.INI: self._save_ini,
            ConfigFormat.ENV: self._save_env,
            ConfigFormat.PYTHON: self._save_python
        }
    
    def load(self, source: Union[str, Path, Dict[str, Any]], format: Optional[ConfigFormat] = None) -> Dict[str, Any]:
        """Load configuration from a source.
        
        Args:
            source: Configuration source (file path or dictionary)
            format: Configuration format (auto-detect if None)
            
        Returns:
            Configuration dictionary
            
        Raises:
            ValueError: If format is not supported or cannot be detected
            FileNotFoundError: If source file does not exist
            Exception: If loading fails
        """
        # If source is already a dictionary, return it
        if isinstance(source, dict):
            return source
        
        # Convert to Path object
        if isinstance(source, str):
            source_path = Path(source)
        else:
            source_path = source
        
        # Check if file exists
        if not source_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {source_path}")
        
        # Detect format if not provided
        if format is None:
            format = self._detect_format(source_path)
        
        # Get format handler
        handler = self._format_handlers.get(format)
        if handler is None:
            raise ValueError(f"Unsupported configuration format: {format}")
        
        # Load configuration
        return handler(source_path)
    
    def save(self, config: Dict[str, Any], destination: Union[str, Path], format: ConfigFormat) -> None:
        """Save configuration to a destination.
        
        Args:
            config: Configuration dictionary
            destination: Destination file path
            format: Configuration format
            
        Raises:
            ValueError: If format is not supported
            Exception: If saving fails
        """
        # Convert to Path object
        if isinstance(destination, str):
            dest_path = Path(destination)
        else:
            dest_path = destination
        
        # Create parent directories if they don't exist
        os.makedirs(dest_path.parent, exist_ok=True)
        
        # Get format handler
        handler = self._save_handlers.get(format)
        if handler is None:
            raise ValueError(f"Unsupported configuration format: {format}")
        
        # Save configuration
        handler(config, dest_path)
    
    def _detect_format(self, path: Path) -> ConfigFormat:
        """Detect configuration format from file extension.
        
        Args:
            path: File path
            
        Returns:
            Detected format
            
        Raises:
            ValueError: If format cannot be detected
        """
        suffix = path.suffix.lower()
        
        if suffix == ".json":
            return ConfigFormat.JSON
        elif suffix in (".yaml", ".yml"):
            return ConfigFormat.YAML
        elif suffix == ".toml":
            return ConfigFormat.TOML
        elif suffix == ".ini":
            return ConfigFormat.INI
        elif suffix == ".env":
            return ConfigFormat.ENV
        elif suffix == ".py":
            return ConfigFormat.PYTHON
        else:
            raise ValueError(f"Cannot detect configuration format for file: {path}")
    
    def _load_json(self, path: Path) -> Dict[str, Any]:
        """Load JSON configuration.
        
        Args:
            path: File path
            
        Returns:
            Configuration dictionary
            
        Raises:
            Exception: If loading fails
        """
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML configuration.
        
        Args:
            path: File path
            
        Returns:
            Configuration dictionary
            
        Raises:
            Exception: If loading fails
        """
        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except ImportError:
            raise ImportError("YAML support requires PyYAML package. Install with 'pip install PyYAML'.")
    
    def _load_toml(self, path: Path) -> Dict[str, Any]:
        """Load TOML configuration.
        
        Args:
            path: File path
            
        Returns:
            Configuration dictionary
            
        Raises:
            Exception: If loading fails
        """
        try:
            import toml
            with open(path, "r", encoding="utf-8") as f:
                return toml.load(f)
        except ImportError:
            raise ImportError("TOML support requires toml package. Install with 'pip install toml'.")
    
    def _load_ini(self, path: Path) -> Dict[str, Any]:
        """Load INI configuration.
        
        Args:
            path: File path
            
        Returns:
            Configuration dictionary
            
        Raises:
            Exception: If loading fails
        """
        try:
            import configparser
            parser = configparser.ConfigParser()
            parser.read(path)
            
            result = {}
            for section in parser.sections():
                result[section] = {}
                for key, value in parser[section].items():
                    result[section][key] = self._infer_type(value)
            
            return result
        except ImportError:
            raise ImportError("INI support requires configparser package. Install with 'pip install configparser'.")
    
    def _load_env(self, path: Path) -> Dict[str, Any]:
        """Load environment variables from a .env file.
        
        Args:
            path: File path
            
        Returns:
            Configuration dictionary
            
        Raises:
            Exception: If loading fails
        """
        result = {}
        
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                # Remove comments
                if "#" in line:
                    line = line.split("#", 1)[0].strip()
                
                # Extract key-value pair
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes
                    if value and value[0] == value[-1] and value[0] in ('"', "'"):
                        value = value[1:-1]
                    
                    # Add to result
                    result[key] = self._infer_type(value)
        
        return result
    
    def _load_python(self, path: Path) -> Dict[str, Any]:
        """Load configuration from a Python file.
        
        Args:
            path: File path
            
        Returns:
            Configuration dictionary
            
        Raises:
            Exception: If loading fails
        """
        # Load module
        spec = importlib.util.spec_from_file_location("config_module", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Failed to load Python module: {path}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Extract configuration
        result = {}
        for key in dir(module):
            # Skip private attributes and modules
            if key.startswith("_") or key == "Optional" or key == "Dict" or key == "List":
                continue
            
            # Get attribute
            value = getattr(module, key)
            
            # Skip functions and classes
            if callable(value) or isinstance(value, type):
                continue
            
            # Add to result
            result[key] = value
        
        return result
    
    def _save_json(self, config: Dict[str, Any], path: Path) -> None:
        """Save configuration as JSON.
        
        Args:
            config: Configuration dictionary
            path: Destination file path
            
        Raises:
            Exception: If saving fails
        """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    
    def _save_yaml(self, config: Dict[str, Any], path: Path) -> None:
        """Save configuration as YAML.
        
        Args:
            config: Configuration dictionary
            path: Destination file path
            
        Raises:
            Exception: If saving fails
        """
        try:
            import yaml
            with open(path, "w", encoding="utf-8") as f:
                yaml.safe_dump(config, f, default_flow_style=False)
        except ImportError:
            raise ImportError("YAML support requires PyYAML package. Install with 'pip install PyYAML'.")
    
    def _save_toml(self, config: Dict[str, Any], path: Path) -> None:
        """Save configuration as TOML.
        
        Args:
            config: Configuration dictionary
            path: Destination file path
            
        Raises:
            Exception: If saving fails
        """
        try:
            import toml
            with open(path, "w", encoding="utf-8") as f:
                toml.dump(config, f)
        except ImportError:
            raise ImportError("TOML support requires toml package. Install with 'pip install toml'.")
    
    def _save_ini(self, config: Dict[str, Any], path: Path) -> None:
        """Save configuration as INI.
        
        Args:
            config: Configuration dictionary
            path: Destination file path
            
        Raises:
            Exception: If saving fails
        """
        try:
            import configparser
            parser = configparser.ConfigParser()
            
            for section, section_config in config.items():
                if not isinstance(section_config, dict):
                    # Skip non-dict sections
                    continue
                
                parser[section] = {}
                for key, value in section_config.items():
                    parser[section][key] = str(value)
            
            with open(path, "w", encoding="utf-8") as f:
                parser.write(f)
        except ImportError:
            raise ImportError("INI support requires configparser package. Install with 'pip install configparser'.")
    
    def _save_env(self, config: Dict[str, Any], path: Path) -> None:
        """Save configuration as .env file.
        
        Args:
            config: Configuration dictionary
            path: Destination file path
            
        Raises:
            Exception: If saving fails
        """
        # Flatten the configuration
        flat_config = self._flatten_dict(config)
        
        with open(path, "w", encoding="utf-8") as f:
            for key, value in flat_config.items():
                # Quote values with spaces or special characters
                if isinstance(value, str) and (" " in value or "=" in value or "\n" in value):
                    value = f'"{value}"'
                
                f.write(f"{key}={value}\n")
    
    def _save_python(self, config: Dict[str, Any], path: Path) -> None:
        """Save configuration as Python file.
        
        Args:
            config: Configuration dictionary
            path: Destination file path
            
        Raises:
            Exception: If saving fails
        """
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Generated configuration file\n\n")
            
            for key, value in config.items():
                f.write(f"{key} = {self._python_repr(value)}\n")
    
    def _infer_type(self, value: str) -> Any:
        """Infer the type of a string value.
        
        Args:
            value: String value
            
        Returns:
            Typed value
        """
        # Check for null/None
        if value.lower() in ("null", "none"):
            return None
        
        # Check for boolean
        if value.lower() in ("true", "yes", "y", "on", "1"):
            return True
        if value.lower() in ("false", "no", "n", "off", "0"):
            return False
        
        # Check for integer
        if re.match(r"^-?\d+$", value):
            return int(value)
        
        # Check for float
        if re.match(r"^-?\d+\.\d+$", value):
            return float(value)
        
        # String value
        return value
    
    def _flatten_dict(self, d: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """Flatten a nested dictionary.
        
        Args:
            d: Dictionary to flatten
            prefix: Prefix for keys
            
        Returns:
            Flattened dictionary
        """
        result = {}
        
        for key, value in d.items():
            if prefix:
                new_key = f"{prefix}_{key}"
            else:
                new_key = key
            
            if isinstance(value, dict):
                result.update(self._flatten_dict(value, new_key))
            else:
                result[new_key] = value
        
        return result
    
    def _python_repr(self, value: Any) -> str:
        """Convert a value to its Python representation.
        
        Args:
            value: Value to convert
            
        Returns:
            Python representation
        """
        if value is None:
            return "None"
        elif isinstance(value, (int, float, bool)):
            return str(value)
        elif isinstance(value, str):
            return repr(value)
        elif isinstance(value, (list, tuple, set)):
            items = ", ".join(self._python_repr(item) for item in value)
            if isinstance(value, list):
                return f"[{items}]"
            elif isinstance(value, tuple):
                return f"({items})"
            else:  # set
                return f"{{{items}}}"
        elif isinstance(value, dict):
            items = ", ".join(f"{self._python_repr(k)}: {self._python_repr(v)}" for k, v in value.items())
            return f"{{{items}}}"
        else:
            return repr(value)

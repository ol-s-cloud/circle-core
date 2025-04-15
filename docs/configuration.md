# Circle Core Configuration Module

The Circle Core Configuration Module provides a flexible and secure way to manage application configuration, supporting multiple sources, validation, and environment-specific settings.

## Overview

The configuration system is built around these key components:

- **ConfigManager**: Central component that manages all configuration sources and provides a unified API
- **ConfigProviders**: Interface with different configuration sources (files, environment variables, etc.)
- **ConfigLoaders**: Load and save configuration in different formats (JSON, YAML, TOML, etc.)
- **ConfigSchemas**: Define and validate configuration structure and types
- **Validation**: Ensure configuration values meet requirements and constraints

## Quick Start

### Basic Usage

```python
from circle_core.infrastructure.configuration import get_config, set_config

# Get a configuration value (dot notation for nested keys)
app_name = get_config("app.name")
db_port = get_config("database.port")

# Set a configuration value
set_config("logging.level", "DEBUG")
```

### Setting Up Configuration Sources

```python
from circle_core.infrastructure.configuration import (
    get_config_manager, ConfigSource, ConfigEnvironment
)

# Get the global configuration manager
manager = get_config_manager()

# Set the environment
manager.set_environment(ConfigEnvironment.DEVELOPMENT)

# Register configuration from a file
manager.register_source(
    "config/app.json", ConfigSource.FILE, priority=100
)

# Register environment variables with prefix "MYAPP_"
manager.register_source(
    {"prefix": "MYAPP_", "separator": "__"}, 
    ConfigSource.ENVIRONMENT, 
    priority=200
)

# Register default values
defaults = {
    "app": {
        "name": "MyApp",
        "version": "1.0.0",
        "debug": True
    },
    "database": {
        "host": "localhost",
        "port": 5432
    }
}
manager.register_source(defaults, ConfigSource.DEFAULT, priority=10)

# Load all configuration sources
manager.load()
```

### Validating Configuration with JSON Schema

```python
from circle_core.infrastructure.configuration import (
    get_config_manager, JsonSchema, ValidationLevel
)

# Define a schema
schema = {
    "type": "object",
    "required": ["app", "database"],
    "properties": {
        "app": {
            "type": "object",
            "required": ["name", "version"],
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
                "debug": {"type": "boolean"}
            }
        },
        "database": {
            "type": "object",
            "required": ["host", "port"],
            "properties": {
                "host": {"type": "string"},
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                "username": {"type": "string"},
                "password": {"type": "string"}
            }
        }
    }
}

# Create a schema object
json_schema = JsonSchema(schema)

# Register the schema with the manager
manager = get_config_manager()
manager.register_schema(json_schema)

# Validate the configuration
result = manager.validate(level=ValidationLevel.STRICT)
if not result:
    print("Configuration validation failed:")
    for error in result.errors:
        print(f"- {error}")
```

### Using Dataclass Schemas

```python
from dataclasses import dataclass, field
from typing import Dict, Any
from circle_core.infrastructure.configuration import (
    get_config_manager, DataclassSchema
)

# Define configuration classes
@dataclass
class AppConfig:
    name: str
    version: str
    debug: bool = True

@dataclass
class DatabaseConfig:
    host: str
    port: int
    username: str = ""
    password: str = ""

@dataclass
class RootConfig:
    app: AppConfig
    database: DatabaseConfig
    logging: Dict[str, Any] = field(default_factory=dict)

# Create a schema object
dataclass_schema = DataclassSchema(RootConfig)

# Register the schema with the manager
manager = get_config_manager()
manager.register_schema(dataclass_schema)

# Get a typed configuration object
config_dict = manager.get_all()
typed_config = dataclass_schema.parse(config_dict)

# Now you can use typed access
print(f"App name: {typed_config.app.name}")
print(f"Database port: {typed_config.database.port}")
```

## Configuration Environments

The configuration system supports different environments (development, testing, staging, production), allowing you to have environment-specific settings:

```python
from circle_core.infrastructure.configuration import (
    ConfigEnvironment, create_config_manager
)

# Create a manager for a specific environment
manager = create_config_manager(environment=ConfigEnvironment.PRODUCTION)

# Load different configuration files based on environment
env = manager.get_environment()
manager.register_source(
    f"config/app.{env.value}.json", ConfigSource.FILE, priority=100
)
```

## Using Multiple Configuration Sources

The configuration system supports multiple sources with priority, allowing higher-priority sources to override lower-priority ones:

```python
from circle_core.infrastructure.configuration import (
    get_config_manager, ConfigSource
)

manager = get_config_manager()

# Register sources with different priorities
# (higher numbers mean higher priority)

# Default values (lowest priority)
manager.register_source(
    {"app": {"name": "DefaultApp"}}, 
    ConfigSource.DEFAULT, 
    priority=10
)

# Configuration file (medium priority)
manager.register_source(
    "config/app.json", 
    ConfigSource.FILE, 
    priority=100
)

# Environment variables (highest priority)
manager.register_source(
    {"prefix": "MYAPP_", "separator": "__"}, 
    ConfigSource.ENVIRONMENT, 
    priority=200
)

# Load all sources
manager.load()
```

## Namespaced Configuration

You can organize configuration values into namespaces:

```python
from circle_core.infrastructure.configuration import get_config_manager

manager = get_config_manager()

# Get all values in a namespace
app_config = manager.get_namespace("app")
db_config = manager.get_namespace("database")

# Register a source for a specific namespace
manager.register_source(
    {"host": "db.example.com", "port": 5432}, 
    ConfigSource.MEMORY, 
    priority=100,
    namespace="database"
)
```

## Advanced Features

### Custom Configuration Providers

You can create custom configuration providers by implementing the `ConfigProvider` interface:

```python
from circle_core.infrastructure.configuration import (
    ConfigProvider, get_config_manager, ConfigSource
)

class MyCustomProvider(ConfigProvider):
    def get(self, key, default=None):
        # Implementation
        pass
    
    def set(self, key, value):
        # Implementation
        pass
    
    def has(self, key):
        # Implementation
        pass
    
    def delete(self, key):
        # Implementation
        pass
    
    def get_all(self):
        # Implementation
        pass
    
    def set_many(self, config, prefix=""):
        # Implementation
        pass
    
    def clear(self):
        # Implementation
        pass

# Register your custom provider
manager = get_config_manager()
manager.register_source(
    MyCustomProvider(), ConfigSource.REMOTE, priority=100
)
```

### Custom Validators

You can create custom validators for configuration values:

```python
from circle_core.infrastructure.configuration import (
    range_validator, length_validator, pattern_validator,
    enum_validator, type_validator
)

# Built-in validators
port_validator = range_validator(min_value=1, max_value=65535)
name_validator = length_validator(min_length=3, max_length=50)
email_validator = pattern_validator(r'^[\w\.-]+@[\w\.-]+\.\w+$')
mode_validator = enum_validator(["development", "production", "testing"])
list_validator = type_validator(list)

# Custom validator
def custom_validator(value):
    if not is_valid(value):
        return "Value does not meet custom criteria"
    return None  # No error
```

## Best Practices

1. **Use a layered approach**:
   - Default values (lowest priority)
   - Configuration files (medium priority)
   - Environment variables (highest priority)

2. **Always define schemas** for validation and type checking

3. **Use environment-specific configuration files** when appropriate

4. **Keep secrets out of configuration files**:
   - Use environment variables for secrets
   - Use secret management services for production

5. **Use namespaces** to organize configuration logically

6. **Validate configuration early** in application startup

## Configuration File Formats

The configuration system supports multiple file formats:

- **JSON**: `.json` files
- **YAML**: `.yaml` or `.yml` files (if PyYAML is installed)
- **TOML**: `.toml` files (if toml/tomli is installed)
- **INI**: `.ini` or `.cfg` files
- **ENV**: `.env` files for environment variable definitions
- **Python**: `.py` files with uppercase variables as configuration

## Security Considerations

1. **Never store sensitive information** in plaintext configuration files
2. **Use environment variables or secret management services** for sensitive information
3. **Validate all configuration values** before use
4. **Apply the principle of least privilege** when setting up configuration access
5. **Consider encrypting sensitive configuration files** when necessary

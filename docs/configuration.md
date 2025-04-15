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
                "port": {"type": "integer"},
                "username": {"type": "string"},
                "password": {"type": "string"}
            }
        }
    }
}

# Create a schema validator
json_schema = JsonSchema(schema)

# Register the schema with the manager
get_config_manager().register_schema(json_schema)

# Validate the configuration
result = get_config_manager().validate(level=ValidationLevel.SCHEMA)
if not result:
    print("Configuration validation failed:")
    for error in result.errors:
        print(f"  - {error}")
```

### Using Dataclass Schemas

```python
from dataclasses import dataclass, field
from typing import Dict, Any
from circle_core.infrastructure.configuration import (
    get_config_manager, DataclassSchema
)

# Define configuration structure with dataclasses
@dataclass
class AppConfig:
    name: str
    version: str
    debug: bool = True

@dataclass
class DatabaseConfig:
    host: str
    port: int
    username: str = "default"
    password: str = ""

@dataclass
class RootConfig:
    app: AppConfig
    database: DatabaseConfig
    logging: Dict[str, Any] = field(default_factory=dict)

# Create a schema validator
dataclass_schema = DataclassSchema(RootConfig)

# Register the schema with the manager
get_config_manager().register_schema(dataclass_schema)

# Get typed configuration
config = get_config_manager().get_all()
typed_config = dataclass_schema.parse(config)

# Access strongly-typed configuration
app_name = typed_config.app.name
db_port = typed_config.database.port
```

## Configuration Sources

The module supports multiple configuration sources with different priorities:

1. **File-based configuration**: Load from JSON, YAML, TOML, INI, or other formats
2. **Environment variables**: Access system environment variables
3. **In-memory dictionaries**: Programmatically defined configuration
4. **Default values**: Fallback values when no other source defines a setting
5. **Remote sources**: (Custom implementation) Load from remote APIs or services
6. **Secret stores**: (Custom implementation) Load sensitive values from secure storage

When a configuration value is requested, the manager checks all registered sources in order of priority (higher priority first) until it finds a matching key.

### Configuration Priority

You can set priorities when registering configuration sources:

```python
# Higher priority (200) will override lower priority (100)
manager.register_source(file_path, ConfigSource.FILE, priority=100)
manager.register_source(env_config, ConfigSource.ENVIRONMENT, priority=200)
```

## Environment-specific Configuration

The configuration manager supports different environments:

```python
from circle_core.infrastructure.configuration import (
    get_config_manager, ConfigEnvironment
)

# Set the current environment
get_config_manager().set_environment(ConfigEnvironment.PRODUCTION)

# Check the current environment
current_env = get_config_manager().get_environment()
if current_env == ConfigEnvironment.DEVELOPMENT:
    # Enable development features
    pass
```

Available environments:
- `ConfigEnvironment.DEVELOPMENT`
- `ConfigEnvironment.TESTING`
- `ConfigEnvironment.STAGING`
- `ConfigEnvironment.PRODUCTION`
- `ConfigEnvironment.CUSTOM`

## Configuration Formats

The system supports multiple file formats:

- **JSON**: Most common format
- **YAML**: Requires PyYAML package
- **TOML**: Requires tomli/tomllib package
- **INI**: Simple key-value format
- **ENV**: Environment variable files
- **Python modules**: Python files with uppercase variables

## Advanced Usage

### Namespaced Configuration

You can organize configuration into namespaces:

```python
# Get all values in a specific namespace
db_config = get_config_manager().get_namespace("database")

# Register a source for a specific namespace
manager.register_source(
    {"host": "localhost", "port": 5432},
    ConfigSource.MEMORY,
    priority=100,
    namespace="database"
)
```

### Creating a Custom ConfigProvider

You can create custom providers by implementing the `ConfigProvider` interface:

```python
from circle_core.infrastructure.configuration import ConfigProvider

class MyCustomProvider(ConfigProvider):
    def get(self, key, default=None):
        # Custom implementation
        pass
    
    def set(self, key, value):
        # Custom implementation
        pass
    
    def has(self, key):
        # Custom implementation
        pass
    
    def delete(self, key):
        # Custom implementation
        pass
    
    def get_all(self):
        # Custom implementation
        pass
    
    def set_many(self, config, prefix=""):
        # Custom implementation
        pass
    
    def clear(self):
        # Custom implementation
        pass

# Register custom provider
manager.register_source(
    MyCustomProvider(), ConfigSource.REMOTE, priority=150
)
```

### Custom Validation

```python
from circle_core.infrastructure.configuration import (
    range_validator, length_validator, pattern_validator
)

# Create validators
port_validator = range_validator(min_value=1, max_value=65535)
name_validator = length_validator(min_length=3, max_length=50)
version_validator = pattern_validator(r"^\d+\.\d+\.\d+$")

# Use them in dataclass metadata or custom validators
@dataclass
class AppConfig:
    name: str = field(metadata={"validators": [name_validator]})
    version: str = field(metadata={"validators": [version_validator]})

@dataclass
class DatabaseConfig:
    port: int = field(metadata={"validators": [port_validator]})
```

## Security Considerations

1. **Sensitive Information**: Avoid storing sensitive information like passwords, API keys, and tokens in plain text configuration files. Instead, use environment variables or a secure secrets manager.

2. **Configuration Sources**: Remember that higher priority sources override lower priority ones. Ensure that critical security settings cannot be overridden by less secure sources.

3. **Validation**: Always validate configuration, especially when accepting values from external sources like environment variables or remote APIs.

4. **Audit Logging**: The configuration manager supports an optional audit logger to track configuration changes.

## Integration with Other Components

The configuration system is designed to integrate with other Circle Core components:

- **Security**: Works with encryption and secrets management
- **Audit Logging**: Can log configuration changes for compliance and debugging
- **Storage**: Supports loading and saving configuration from Circle Core storage services

## Best Practices

1. **Centralize Configuration**: Use a single configuration manager instance for the entire application.

2. **Define Schemas**: Always define and validate schemas to catch configuration errors early.

3. **Use Typed Configuration**: Leverage dataclass schemas for strong typing and IDE support.

4. **Layer Configuration**: Use different priority levels for:
   - Default values (lowest priority)
   - Application configuration files
   - Environment-specific overrides
   - Command-line options
   - Environment variables (highest priority)

5. **Namespace Configuration**: Organize configuration into logical namespaces.

6. **Document Configuration**: Include comments and descriptions in schemas to document the purpose of each setting.

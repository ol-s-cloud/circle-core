"""Tests for the ConfigManager class."""

import os
import tempfile
import json
import unittest
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass, field

from src.infrastructure.configuration import (
    ConfigManager, ConfigEnvironment, ConfigSource, ConfigFormat, ValidationLevel,
    StandardConfigManager, DictConfigProvider, FileConfigProvider, EnvironmentConfigProvider,
    JsonSchema, DataclassSchema, ValidationResult, ValidationError,
    create_config_manager
)


class TestConfigManager(unittest.TestCase):
    """Test case for the ConfigManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = StandardConfigManager()
        
        # Sample configuration
        self.sample_config = {
            "app": {
                "name": "TestApp",
                "version": "1.0.0",
                "debug": True
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "username": "test",
                "password": "test123"
            },
            "logging": {
                "level": "INFO",
                "file": "/var/log/app.log"
            }
        }
        
        # Create a temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Clean up temporary directory
        self.temp_dir.cleanup()
    
    def test_register_dict_source(self):
        """Test registering a dictionary source."""
        # Register the source
        self.manager.register_source(
            self.sample_config, ConfigSource.MEMORY, priority=100
        )
        
        # Load the configuration
        self.manager.load()
        
        # Check values
        self.assertEqual(self.manager.get("app.name"), "TestApp")
        self.assertEqual(self.manager.get("database.port"), 5432)
        self.assertEqual(self.manager.get("logging.level"), "INFO")
    
    def test_register_file_source(self):
        """Test registering a file source."""
        # Create a JSON config file
        config_path = Path(self.temp_dir.name) / "config.json"
        with open(config_path, "w") as f:
            json.dump(self.sample_config, f)
        
        # Register the source
        self.manager.register_source(
            config_path, ConfigSource.FILE, priority=100
        )
        
        # Load the configuration
        self.manager.load()
        
        # Check values
        self.assertEqual(self.manager.get("app.name"), "TestApp")
        self.assertEqual(self.manager.get("database.port"), 5432)
        self.assertEqual(self.manager.get("logging.level"), "INFO")
    
    def test_register_environment_source(self):
        """Test registering an environment source."""
        # Set environment variables
        os.environ["TEST_APP_NAME"] = "EnvApp"
        os.environ["TEST_DATABASE_PORT"] = "9999"
        
        # Create and register an environment provider
        provider = EnvironmentConfigProvider(prefix="TEST_", separator="_")
        self.manager.register_source(
            provider, ConfigSource.ENVIRONMENT, priority=100
        )
        
        # Load the configuration
        self.manager.load()
        
        # Check values
        self.assertEqual(self.manager.get("app.name"), "EnvApp")
        self.assertEqual(self.manager.get("database.port"), 9999)
        
        # Clean up environment
        del os.environ["TEST_APP_NAME"]
        del os.environ["TEST_DATABASE_PORT"]
    
    def test_source_priority(self):
        """Test that sources with higher priority override lower priority."""
        # Register a low-priority source
        self.manager.register_source(
            self.sample_config, ConfigSource.MEMORY, priority=10
        )
        
        # Register a high-priority source with different values
        high_priority_config = {
            "app": {
                "name": "HighPriorityApp",
                "version": "2.0.0"
            }
        }
        
        self.manager.register_source(
            high_priority_config, ConfigSource.MEMORY, priority=100
        )
        
        # Load the configuration
        self.manager.load()
        
        # Check that high-priority values are used
        self.assertEqual(self.manager.get("app.name"), "HighPriorityApp")
        self.assertEqual(self.manager.get("app.version"), "2.0.0")
        
        # Check that low-priority values are still available when not overridden
        self.assertEqual(self.manager.get("database.port"), 5432)
    
    def test_get_default_value(self):
        """Test getting a default value for a non-existent key."""
        # Register a source
        self.manager.register_source(
            self.sample_config, ConfigSource.MEMORY, priority=100
        )
        
        # Load the configuration
        self.manager.load()
        
        # Get a non-existent key with a default value
        value = self.manager.get("non_existent_key", "default_value")
        self.assertEqual(value, "default_value")
    
    def test_has_key(self):
        """Test checking if a key exists."""
        # Register a source
        self.manager.register_source(
            self.sample_config, ConfigSource.MEMORY, priority=100
        )
        
        # Load the configuration
        self.manager.load()
        
        # Check existing keys
        self.assertTrue(self.manager.has("app.name"))
        self.assertTrue(self.manager.has("database.port"))
        
        # Check non-existent key
        self.assertFalse(self.manager.has("non_existent_key"))
    
    def test_get_all(self):
        """Test getting all configuration values."""
        # Register a source
        self.manager.register_source(
            self.sample_config, ConfigSource.MEMORY, priority=100
        )
        
        # Load the configuration
        self.manager.load()
        
        # Get all configuration
        all_config = self.manager.get_all()
        
        # Check structure
        self.assertIn("app", all_config)
        self.assertIn("database", all_config)
        self.assertIn("logging", all_config)
        
        # Check specific values
        self.assertEqual(all_config["app"]["name"], "TestApp")
        self.assertEqual(all_config["database"]["port"], 5432)
        self.assertEqual(all_config["logging"]["level"], "INFO")
    
    def test_get_namespace(self):
        """Test getting a configuration namespace."""
        # Register a source
        self.manager.register_source(
            self.sample_config, ConfigSource.MEMORY, priority=100
        )
        
        # Load the configuration
        self.manager.load()
        
        # Get a namespace
        app_config = self.manager.get_namespace("app")
        
        # Check structure
        self.assertIn("name", app_config)
        self.assertIn("version", app_config)
        self.assertIn("debug", app_config)
        
        # Check specific values
        self.assertEqual(app_config["name"], "TestApp")
        self.assertEqual(app_config["version"], "1.0.0")
        self.assertTrue(app_config["debug"])
    
    def test_set_value(self):
        """Test setting a configuration value."""
        # Register a source
        self.manager.register_source(
            self.sample_config, ConfigSource.MEMORY, priority=100
        )
        
        # Load the configuration
        self.manager.load()
        
        # Set a value
        self.manager.set("app.name", "UpdatedApp")
        
        # Check the updated value
        self.assertEqual(self.manager.get("app.name"), "UpdatedApp")
        
        # Set a nested value that doesn't exist yet
        self.manager.set("app.new_value", "NewValue")
        self.assertEqual(self.manager.get("app.new_value"), "NewValue")
        
        # Set a completely new path
        self.manager.set("new_section.key", "Value")
        self.assertEqual(self.manager.get("new_section.key"), "Value")
    
    def test_environment_handling(self):
        """Test environment handling."""
        # Create a manager with a specific environment
        env_manager = StandardConfigManager(environment=ConfigEnvironment.PRODUCTION)
        
        # Check the environment
        self.assertEqual(env_manager.get_environment(), ConfigEnvironment.PRODUCTION)
        
        # Change the environment
        env_manager.set_environment(ConfigEnvironment.TESTING)
        self.assertEqual(env_manager.get_environment(), ConfigEnvironment.TESTING)
    
    def test_schema_validation_json(self):
        """Test validation with a JSON schema."""
        # Create a JSON schema
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
                    "required": ["host", "port", "username", "password"],
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "integer"},
                        "username": {"type": "string"},
                        "password": {"type": "string"}
                    }
                }
            }
        }
        
        json_schema = JsonSchema(schema)
        
        # Register the schema with the manager
        self.manager.register_schema(json_schema)
        
        # Register a valid configuration
        self.manager.register_source(
            self.sample_config, ConfigSource.MEMORY, priority=100
        )
        
        # Load the configuration
        self.manager.load()
        
        # Validate the configuration
        result = self.manager.validate()
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        
        # Create a manager with invalid configuration
        invalid_manager = StandardConfigManager()
        invalid_manager.register_schema(json_schema)
        
        invalid_config = {
            "app": {
                "name": "TestApp",
                # Missing required "version" field
                "debug": "not a boolean"  # Wrong type
            }
        }
        
        invalid_manager.register_source(
            invalid_config, ConfigSource.MEMORY, priority=100
        )
        
        invalid_manager.load()
        
        # Validate the configuration
        invalid_result = invalid_manager.validate()
        self.assertFalse(invalid_result.is_valid)
        self.assertGreater(len(invalid_result.errors), 0)
    
    def test_schema_validation_dataclass(self):
        """Test validation with a dataclass schema."""
        # Create a dataclass schema
        @dataclass
        class AppConfig:
            name: str
            version: str
            debug: bool = True
        
        @dataclass
        class DatabaseConfig:
            host: str
            port: int
            username: str
            password: str
        
        @dataclass
        class RootConfig:
            app: AppConfig
            database: DatabaseConfig
            logging: Dict[str, Any] = field(default_factory=dict)
        
        dataclass_schema = DataclassSchema(RootConfig)
        
        # Register the schema with the manager
        self.manager.register_schema(dataclass_schema)
        
        # Register a valid configuration
        self.manager.register_source(
            self.sample_config, ConfigSource.MEMORY, priority=100
        )
        
        # Load the configuration
        self.manager.load()
        
        # Validate the configuration
        result = self.manager.validate()
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
        
        # Parse the configuration to a typed object
        parsed_config = dataclass_schema.parse(self.sample_config)
        self.assertIsInstance(parsed_config, RootConfig)
        self.assertIsInstance(parsed_config.app, AppConfig)
        self.assertIsInstance(parsed_config.database, DatabaseConfig)
        self.assertEqual(parsed_config.app.name, "TestApp")
        self.assertEqual(parsed_config.database.port, 5432)
    
    def test_create_config_manager_factory(self):
        """Test the create_config_manager factory function."""
        # Create a manager with the factory function
        manager = create_config_manager(
            environment=ConfigEnvironment.STAGING,
            env_prefix="MYAPP_",
            env_separator="__"
        )
        
        # Check the manager type
        self.assertIsInstance(manager, StandardConfigManager)
        
        # Check the environment
        self.assertEqual(manager.get_environment(), ConfigEnvironment.STAGING)
    
    def test_factory_defaults(self):
        """Test that the factory creates a manager with default values."""
        # Create a manager with the factory function
        manager = create_config_manager()
        
        # Check the environment
        self.assertEqual(manager.get_environment(), ConfigEnvironment.DEVELOPMENT)
    
    def test_validation_levels(self):
        """Test different validation levels."""
        # Create a JSON schema
        schema = {
            "type": "object",
            "required": ["app"],
            "properties": {
                "app": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string"}
                    }
                }
            }
        }
        
        json_schema = JsonSchema(schema)
        
        # Register the schema with the manager
        self.manager.register_schema(json_schema)
        
        # Register a valid configuration
        self.manager.register_source(
            {"app": {"name": "TestApp"}}, ConfigSource.MEMORY, priority=100
        )
        
        # Load the configuration
        self.manager.load()
        
        # Test NONE validation level
        none_result = self.manager.validate(level=ValidationLevel.NONE)
        self.assertTrue(none_result.is_valid)
        self.assertEqual(len(none_result.errors), 0)
        
        # Test SCHEMA validation level
        schema_result = self.manager.validate(level=ValidationLevel.SCHEMA)
        self.assertTrue(schema_result.is_valid)
        self.assertEqual(len(schema_result.errors), 0)
        
        # Test STRICT validation level
        strict_result = self.manager.validate(level=ValidationLevel.STRICT)
        self.assertTrue(strict_result.is_valid)
        self.assertEqual(len(strict_result.errors), 0)
    
    def test_multiple_namespaced_sources(self):
        """Test multiple sources with different namespaces."""
        # Register a source for app namespace
        app_config = {"name": "TestApp", "version": "1.0.0"}
        self.manager.register_source(
            app_config, ConfigSource.MEMORY, priority=100, namespace="app"
        )
        
        # Register a source for database namespace
        db_config = {"host": "localhost", "port": 5432}
        self.manager.register_source(
            db_config, ConfigSource.MEMORY, priority=100, namespace="database"
        )
        
        # Load the configuration
        self.manager.load()
        
        # Check values from different namespaces
        self.assertEqual(self.manager.get("app.name"), "TestApp")
        self.assertEqual(self.manager.get("database.port"), 5432)
        
        # Test get_namespace function
        app_namespace = self.manager.get_namespace("app")
        self.assertEqual(app_namespace["name"], "TestApp")
        
        db_namespace = self.manager.get_namespace("database")
        self.assertEqual(db_namespace["port"], 5432)
    
    def test_different_file_formats(self):
        """Test loading configuration from different file formats."""
        # Create a YAML file (if PyYAML is available)
        try:
            import yaml
            yaml_config_path = Path(self.temp_dir.name) / "config.yaml"
            with open(yaml_config_path, "w") as f:
                yaml.dump(self.sample_config, f)
            
            # Create a manager
            yaml_manager = StandardConfigManager()
            
            # Register the YAML file
            yaml_manager.register_source(
                yaml_config_path, ConfigSource.FILE, priority=100
            )
            
            # Load the configuration
            yaml_manager.load()
            
            # Check values
            self.assertEqual(yaml_manager.get("app.name"), "TestApp")
            self.assertEqual(yaml_manager.get("database.port"), 5432)
        except ImportError:
            # Skip if PyYAML is not available
            pass
        
        # Create a JSON file
        json_config_path = Path(self.temp_dir.name) / "config.json"
        with open(json_config_path, "w") as f:
            json.dump(self.sample_config, f)
        
        # Create a manager
        json_manager = StandardConfigManager()
        
        # Register the JSON file
        json_manager.register_source(
            json_config_path, ConfigSource.FILE, priority=100
        )
        
        # Load the configuration
        json_manager.load()
        
        # Check values
        self.assertEqual(json_manager.get("app.name"), "TestApp")
        self.assertEqual(json_manager.get("database.port"), 5432)
    
    def test_chain_provider_ordering(self):
        """Test that the chain provider maintains the correct ordering of providers."""
        # Create several sources with different priorities
        self.manager.register_source(
            {"key": "priority_10"}, ConfigSource.MEMORY, priority=10
        )
        
        self.manager.register_source(
            {"key": "priority_20"}, ConfigSource.MEMORY, priority=20
        )
        
        self.manager.register_source(
            {"key": "priority_5"}, ConfigSource.MEMORY, priority=5
        )
        
        self.manager.register_source(
            {"key": "priority_15"}, ConfigSource.MEMORY, priority=15
        )
        
        # Load the configuration
        self.manager.load()
        
        # The highest priority should win
        self.assertEqual(self.manager.get("key"), "priority_20")
        
        # Add an even higher priority
        self.manager.register_source(
            {"key": "priority_30"}, ConfigSource.MEMORY, priority=30
        )
        
        # The new highest priority should win
        self.manager.load()
        self.assertEqual(self.manager.get("key"), "priority_30")


if __name__ == "__main__":
    unittest.main()

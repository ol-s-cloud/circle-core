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

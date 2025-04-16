#!/usr/bin/env python3
"""
Circle Core Configuration Generator

This script generates environment-specific configuration files for Circle Core deployments.
It supports different environments (development, staging, production) and customization.
"""

import os
import sys
import json
import random
import string
import argparse
from datetime import datetime

# Default configuration templates for different environments
DEFAULT_CONFIGS = {
    "development": {
        "app": {
            "name": "Circle Core",
            "environment": "development",
            "debug": True,
            "log_level": "DEBUG",
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "workers": 1
            }
        },
        "security": {
            "encryption": {
                "algorithm": "AES-GCM",
                "key_rotation_days": 90
            },
            "authentication": {
                "session_timeout_minutes": 60,
                "mfa_enabled": False,
                "password_policy": {
                    "min_length": 8,
                    "require_uppercase": True,
                    "require_lowercase": True,
                    "require_numbers": True,
                    "require_special": True
                }
            },
            "audit": {
                "enabled": True,
                "retention_days": 30
            }
        },
        "storage": {
            "backend": "file",
            "path": "/data/storage",
            "encryption_enabled": True
        },
        "database": {
            "type": "sqlite",
            "path": "/data/circle.db",
            "pool_size": 5
        },
        "cache": {
            "type": "memory",
            "ttl_seconds": 300
        }
    },
    "staging": {
        "app": {
            "name": "Circle Core",
            "environment": "staging",
            "debug": False,
            "log_level": "INFO",
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "workers": 2
            }
        },
        "security": {
            "encryption": {
                "algorithm": "AES-GCM",
                "key_rotation_days": 60
            },
            "authentication": {
                "session_timeout_minutes": 30,
                "mfa_enabled": True,
                "password_policy": {
                    "min_length": 10,
                    "require_uppercase": True,
                    "require_lowercase": True,
                    "require_numbers": True,
                    "require_special": True
                }
            },
            "audit": {
                "enabled": True,
                "retention_days": 90
            }
        },
        "storage": {
            "backend": "file",
            "path": "/data/storage",
            "encryption_enabled": True
        },
        "database": {
            "type": "postgres",
            "host": "postgres",
            "port": 5432,
            "name": "circlecore",
            "user": "circle",
            "pool_size": 10
        },
        "cache": {
            "type": "redis",
            "host": "redis",
            "port": 6379,
            "ttl_seconds": 600
        }
    },
    "production": {
        "app": {
            "name": "Circle Core",
            "environment": "production",
            "debug": False,
            "log_level": "WARNING",
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "workers": 4
            }
        },
        "security": {
            "encryption": {
                "algorithm": "AES-GCM",
                "key_rotation_days": 30
            },
            "authentication": {
                "session_timeout_minutes": 15,
                "mfa_enabled": True,
                "password_policy": {
                    "min_length": 12,
                    "require_uppercase": True,
                    "require_lowercase": True,
                    "require_numbers": True,
                    "require_special": True,
                    "max_age_days": 90
                }
            },
            "audit": {
                "enabled": True,
                "retention_days": 365,
                "immutable": True
            }
        },
        "storage": {
            "backend": "file",
            "path": "/data/storage",
            "encryption_enabled": True,
            "backup": {
                "enabled": True,
                "schedule": "0 2 * * *",  # Daily at 2 AM
                "retention_count": 7
            }
        },
        "database": {
            "type": "postgres",
            "host": "postgres",
            "port": 5432,
            "name": "circlecore",
            "user": "circle",
            "pool_size": 20,
            "ssl_enabled": True,
            "connection_timeout": 30
        },
        "cache": {
            "type": "redis",
            "host": "redis",
            "port": 6379,
            "ttl_seconds": 1200,
            "ssl_enabled": True
        },
        "performance": {
            "request_timeout": 30,
            "max_request_size_mb": 10,
            "rate_limiting": {
                "enabled": True,
                "rate": 100,  # requests per minute
                "burst": 20
            }
        },
        "monitoring": {
            "metrics_enabled": True,
            "health_check_interval": 60,
            "alert_thresholds": {
                "cpu_percent": 80,
                "memory_percent": 80,
                "disk_percent": 85
            }
        }
    }
}

def generate_random_string(length=16):
    """Generate a random string of fixed length"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def generate_config(environment, output_file, custom_config=None):
    """Generate a configuration file for the specified environment"""
    # Get the default config for the environment
    if environment not in DEFAULT_CONFIGS:
        print(f"Error: Unknown environment '{environment}'")
        sys.exit(1)
    
    # Start with the default config
    config = DEFAULT_CONFIGS[environment].copy()
    
    # Add generation metadata
    config["_metadata"] = {
        "generated_at": datetime.now().isoformat(),
        "environment": environment,
        "generator_version": "1.0.0"
    }
    
    # Merge with custom config if provided
    if custom_config:
        try:
            with open(custom_config, 'r') as f:
                custom_data = json.load(f)
            
            # Deep merge the custom config
            def merge_dicts(a, b):
                for key in b:
                    if key in a and isinstance(a[key], dict) and isinstance(b[key], dict):
                        merge_dicts(a[key], b[key])
                    else:
                        a[key] = b[key]
                return a
            
            config = merge_dicts(config, custom_data)
        except Exception as e:
            print(f"Error loading custom config: {str(e)}")
            sys.exit(1)
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Write the configuration to file
    try:
        with open(output_file, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Configuration generated successfully: {output_file}")
    except Exception as e:
        print(f"Error writing configuration: {str(e)}")
        sys.exit(1)

def main():
    """Main function to parse arguments and generate configuration"""
    parser = argparse.ArgumentParser(description='Generate Circle Core configuration')
    parser.add_argument('-e', '--environment', required=True,
                        choices=['development', 'staging', 'production'],
                        help='Target environment')
    parser.add_argument('-o', '--output', required=True,
                        help='Output file path')
    parser.add_argument('-c', '--custom-config', 
                        help='Custom configuration to merge (JSON file)')
    
    args = parser.parse_args()
    
    generate_config(args.environment, args.output, args.custom_config)

if __name__ == '__main__':
    main()

# Circle Core

Core framework and infrastructure for the Circle Core ecosystem. Provides a foundation of security, infrastructure, and development tools for building secure, scalable applications.

## Project Status

[![Project Status](https://img.shields.io/badge/status-active-brightgreen)](PROJECT_STATUS.md)
[![Security Focus](https://img.shields.io/badge/focus-security-blue)](GAP_ANALYSIS.md)
[![Sprint](https://img.shields.io/badge/sprint-2-orange)](SPRINT_STATUS.md)
[![Test Coverage](https://img.shields.io/badge/coverage-92%25-green)](AUDIT_FRAMEWORK.md)

**Project Documentation:**
- [📊 Project Status](PROJECT_STATUS.md) - Overall project progress and component status
- [🔍 Gap Analysis](GAP_ANALYSIS.md) - Detailed comparison of current state vs. target architecture
- [🏃 Sprint Status](SPRINT_STATUS.md) - Current sprint goals, achievements, and metrics
- [🔒 Audit Framework](AUDIT_FRAMEWORK.md) - Testing and audit guidelines for quality assurance

## Overview

Circle Core is a comprehensive platform for building, deploying, and managing secure applications. It provides:

- **Security First**: Built-in security features including encryption, authentication, and audit logging
- **Extensible Architecture**: Designed to be extended for specific projects and platforms
- **Cloud Ready**: Infrastructure components for major cloud providers
- **Developer Friendly**: CLI tools, documentation, and APIs for a smooth developer experience

## Structure

```
├── src/                  # Source code
│   ├── core/             # Core components
│   │   ├── auth/         # Authentication & authorization
│   │   ├── encryption/   # Encryption services
│   │   ├── audit/        # Audit logging
│   │   └── validation/   # Validation services
│   ├── infrastructure/   # Infrastructure components
│   │   ├── storage/      # Storage mechanisms
│   │   ├── registry/     # Package registry
│   │   └── licensing/    # License management
│   └── security/         # Security-specific modules
│       ├── dependency_scanner/ # Dependency scanning
│       ├── secrets_manager/    # Secrets management
│       └── security_monitor/   # Security monitoring
├── tests/                # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── security/         # Security-specific tests
├── docs/                 # Documentation
│   ├── architecture/     # Architecture documentation
│   ├── security/         # Security documentation
│   ├── api/              # API documentation
│   └── guides/           # User and developer guides
└── deployment/           # Deployment configurations
    ├── docker/           # Docker configurations
    └── kubernetes/       # Kubernetes resources
```

## Installation

```bash
# Install the core framework
pip install circle-core

# Install with development dependencies
pip install circle-core[dev]

# Install with test dependencies
pip install circle-core[test]

# Install with documentation dependencies
pip install circle-core[docs]
```

## Key Features

### Security Components

- **Authentication**: Secure user authentication with MFA, Argon2 hashing, and role-based access
- **Encryption**: Data protection with key rotation, multiple algorithms, and envelope encryption
- **Audit Logging**: Tamper-evident logging with cryptographic hash chains and integrity verification
- **Security Scanning**: Automatic scanning for vulnerabilities in dependencies

### Infrastructure Components

- **Storage**: Unified storage interface with transparent encryption and multiple backends
- **Package Registry**: Package management with versioning, validation, and dependency resolution
- **Licensing**: Feature-based license validation and management system
- **Configuration**: Coming soon - Configuration management and validation

## Getting Started

### Security Example

```python
from circle_core.security import dependency_scanner

# Initialize the security scanner
scanner = dependency_scanner.Scanner()

# Scan your project dependencies
results = scanner.scan_requirements_file("requirements.txt")

# Check for vulnerabilities
for result in results:
    if result["vulnerabilities"]:
        print(f"Vulnerabilities found in {result['package']}!")
```

### Storage Example

```python
from circle_core.infrastructure.storage import StorageManager

# Create a storage manager
storage_manager = StorageManager()

# Store an object
metadata = storage_manager.put_object(
    "my_file.txt",
    data="Hello, world!",
    content_type="text/plain"
)

# Retrieve the object
obj = storage_manager.get_object("my_file.txt")
print(obj.data)  # Outputs: Hello, world!
```

### Registry Example

```python
from circle_core.infrastructure.registry import CoreRegistryManager

# Create a registry manager
registry_manager = CoreRegistryManager()
registry_manager.initialize()

# Publish a package
registry_manager.publish_package(
    "example-package",
    "1.0.0",
    package_data,
    package_metadata
)

# Search for packages
results = registry_manager.search_packages("example")

# Download a package
package_data = registry_manager.download_package("example-package", "1.0.0")
```

### Licensing Example

```python
from circle_core.infrastructure.licensing import (
    has_feature, verify_feature, register_license,
    FEATURE_STORAGE, FEATURE_ENCRYPTION
)

# Register a license
with open("license_file.txt", "r") as f:
    license_data = f.read()
register_license(license_data)

# Check if a feature is available
if has_feature(FEATURE_STORAGE):
    print("Storage feature is available")

# Verify feature access (raises exception if not available)
try:
    verify_feature(FEATURE_ENCRYPTION)
    print("Encryption feature is available")
except LicenseFeatureNotAvailableError:
    print("Encryption feature not available in current license")
```

See the [examples directory](docs/examples/) for more detailed examples.

## Documentation

Comprehensive documentation is available in the `docs/` directory.

## Development

```bash
# Clone the repository
git clone https://github.com/ol-s-cloud/circle-core.git
cd circle-core

# Install development dependencies
pip install -e ".[dev,test]"

# Run tests
pytest
```

## Project Documentation

- [Project Status](PROJECT_STATUS.md) - Overall project progress and component status
- [Gap Analysis](GAP_ANALYSIS.md) - Detailed comparison of current state vs. target architecture
- [Sprint Status](SPRINT_STATUS.md) - Current sprint goals, achievements, and metrics
- [Audit Framework](AUDIT_FRAMEWORK.md) - Testing and audit guidelines for quality assurance

## License

Proprietary - All Rights Reserved © Circle Data & IT Solutions Ltd

# Circle Core Framework

Core framework and infrastructure for the Circle Core ecosystem. Provides a foundation of security, infrastructure, and development tools for building secure, scalable applications.

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
pip install circle-core-framework

# Install with development dependencies
pip install circle-core-framework[dev]

# Install with test dependencies
pip install circle-core-framework[test]

# Install with documentation dependencies
pip install circle-core-framework[docs]
```

## Getting Started

```python
from circle_core import security

# Initialize the security scanner
scanner = security.dependency_scanner.Scanner()

# Scan your project dependencies
results = scanner.scan_requirements_file("requirements.txt")

# Check for vulnerabilities
for result in results:
    if result["vulnerabilities"]:
        print(f"Vulnerabilities found in {result['package']}!")
```

## Documentation

Comprehensive documentation is available in the `docs/` directory.

## Development

```bash
# Clone the repository
git clone https://github.com/ol-s-cloud/circle-core-framework.git
cd circle-core-framework

# Install development dependencies
pip install -e ".[dev,test]"

# Run tests
pytest
```

## License

Proprietary - All Rights Reserved © Circle Data & IT Solutions Ltd

# Circle Core Registry Module

The Registry module is a core component of the Circle Core infrastructure that provides package management capabilities. It enables storing, retrieving, and managing packages with proper versioning, validation, and dependency resolution.

## Features

- **Package Storage**: Secure storage of package files with metadata
- **Semantic Versioning**: Full support for semantic versioning and dependency resolution
- **Package Validation**: Verification of package integrity and structure
- **Security Scanning**: Integration with dependency scanner for security vulnerabilities
- **Search Capabilities**: Efficient package discovery with filtering and pagination
- **Audit Logging**: Comprehensive logging of all registry operations
- **Encryption Integration**: Optional encryption of package content

## Architecture

The Registry module follows a modular architecture with clear separation of concerns:

### Components

1. **Registry Manager**: The main entry point that coordinates all registry operations
2. **Metadata Provider**: Handles storage and retrieval of package metadata
3. **Storage Provider**: Manages the physical storage of package files
4. **Versioning Provider**: Handles semantic versioning and dependency resolution
5. **Validation Provider**: Verifies package integrity and security
6. **Search Provider**: Enables efficient package discovery

### Dependencies

- **Storage Module**: For secure storage of packages and metadata
- **Encryption Module**: For encrypting sensitive package content
- **Audit Module**: For logging registry operations
- **Security Module**: For scanning packages for vulnerabilities

## Usage

### Basic Usage

```python
from src.infrastructure.storage import StorageManager
from src.infrastructure.registry.manager import CoreRegistryManager

# Create storage manager
storage_manager = StorageManager()

# Create registry manager
registry_manager = CoreRegistryManager(
    storage_manager=storage_manager
)

# Initialize the registry
registry_manager.initialize()

# Publish a package
registry_manager.publish_package(
    package_name="example-package",
    version="1.0.0",
    package_data=package_bytes,
    metadata=package_metadata
)

# Search for packages
results = registry_manager.search_packages("example")

# Download a package
package_data = registry_manager.download_package("example-package", "1.0.0")
```

See the [registry_usage.py](../../docs/examples/registry_usage.py) example for a more detailed demonstration.

### Advanced Usage

```python
from src.core.encryption import EncryptionService
from src.core.audit import AuditLogger
from src.security.dependency_scanner import DependencyScanner
from src.infrastructure.storage import StorageManager
from src.infrastructure.registry.manager import CoreRegistryManager

# Create dependencies
storage_manager = StorageManager()
encryption_service = EncryptionService()
audit_logger = AuditLogger()
dependency_scanner = DependencyScanner()

# Create registry manager with all dependencies
registry_manager = CoreRegistryManager(
    storage_manager=storage_manager,
    encryption_service=encryption_service,
    audit_logger=audit_logger,
    dependency_scanner=dependency_scanner
)

# Initialize the registry
registry_manager.initialize()

# Use registry manager with full feature set
registry_manager.publish_package(...)
registry_manager.search_packages(...)
registry_manager.download_package(...)
registry_manager.get_package_info(...)
registry_manager.delete_package(...)
registry_manager.resolve_dependency(...)
registry_manager.get_dependency_tree(...)
registry_manager.validate_package(...)
```

## Package Format

The registry works with packages in ZIP format with the following structure:

```
package-name-version.zip
├── metadata.json    (Required - Package metadata)
├── manifest.json    (Required - File list with checksums)
└── [content files]  (Package content)
```

### Metadata Format

The package metadata (metadata.json) must include the following fields:

```json
{
  "name": "package-name",
  "version": "1.0.0",
  "description": "Package description",
  "author": "Author Name",
  "dependencies": {
    "dependency1": ">=1.0.0,<2.0.0",
    "dependency2": "^1.2.3"
  },
  "tags": ["tag1", "tag2"]
}
```

### Manifest Format

The package manifest (manifest.json) must include a list of files with checksums:

```json
{
  "name": "package-name",
  "version": "1.0.0",
  "files": {
    "file1.txt": {
      "hash": "sha256-hash-value"
    },
    "file2.txt": {
      "hash": "sha256-hash-value"
    }
  }
}
```

## Extension Points

The Registry module is designed to be extensible through the implementation of custom providers:

- Custom metadata storage (implement `PackageMetadataProvider`)
- Custom package storage (implement `PackageStorageProvider`)
- Custom versioning logic (implement `PackageVersioningProvider`)
- Custom validation rules (implement `PackageValidationProvider`)
- Custom search algorithms (implement `PackageSearchProvider`)

## Security Considerations

- Package signatures can be verified if encryption service is provided
- Package integrity is verified using file checksums
- Package content can be scanned for security vulnerabilities
- All registry operations are logged for audit purposes
- Package content can be encrypted for sensitive packages

## Performance Considerations

- The registry module is designed for efficient package retrieval
- Search operations use in-memory filtering for small registries
- For larger registries, consider implementing a custom search provider
- Cached metadata improves performance for frequently accessed packages

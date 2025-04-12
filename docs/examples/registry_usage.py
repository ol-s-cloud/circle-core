"""Example usage of the Circle Core Registry.

This example demonstrates how to use the registry module to publish,
search, and download packages.
"""

import os
import json
import zipfile
from io import BytesIO

from src.core.audit import AuditLogger
from src.infrastructure.storage import StorageManager
from src.infrastructure.registry.manager import CoreRegistryManager


def create_sample_package(package_name, version, metadata):
    """Create a sample package file.
    
    Args:
        package_name: Package name
        version: Package version
        metadata: Package metadata
        
    Returns:
        Package data as bytes
    """
    # Create an in-memory zip file
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        # Add metadata.json
        zip_file.writestr("metadata.json", json.dumps(metadata))
        
        # Add manifest.json with file info
        manifest = {
            "name": package_name,
            "version": version,
            "files": {
                "metadata.json": {
                    "hash": "dummy_hash"
                },
                "manifest.json": {
                    "hash": "dummy_hash"
                },
                "README.md": {
                    "hash": "dummy_hash"
                }
            }
        }
        zip_file.writestr("manifest.json", json.dumps(manifest))
        
        # Add a README file
        zip_file.writestr("README.md", f"# {package_name}\n\nVersion: {version}\n\n{metadata.get('description', '')}")
    
    # Get the zip data
    zip_buffer.seek(0)
    return zip_buffer.read()


def main():
    """Run the registry example."""
    print("Circle Core Registry Example")
    print("============================")
    
    # Create registry directory
    registry_dir = os.path.expanduser("~/circle-core-example/registry")
    os.makedirs(registry_dir, exist_ok=True)
    
    print(f"Using registry directory: {registry_dir}")
    
    # Create a storage manager
    storage_manager = StorageManager()
    storage_manager.create_file_system_backend(
        "registry_storage",
        registry_dir
    )
    
    # Create audit logger
    audit_logger = AuditLogger()
    
    # Create the registry manager
    registry_manager = CoreRegistryManager(
        storage_manager=storage_manager,
        storage_backend="registry_storage",
        audit_logger=audit_logger
    )
    
    # Initialize the registry
    print("Initializing registry...")
    registry_manager.initialize()
    
    # Sample package metadata
    package_metadata = {
        "name": "example-package",
        "version": "1.0.0",
        "description": "An example package for demonstrating the registry",
        "author": "Circle Core Team",
        "dependencies": {
            "core-lib": ">=0.5.0"
        },
        "tags": ["example", "demo"]
    }
    
    # Create a sample package
    print("Creating sample package...")
    package_data = create_sample_package(
        "example-package",
        "1.0.0",
        package_metadata
    )
    
    # Publish the package
    print("Publishing package...")
    result = registry_manager.publish_package(
        "example-package",
        "1.0.0",
        package_data,
        package_metadata
    )
    
    if result:
        print("Package published successfully!")
    else:
        print("Failed to publish package.")
        return
    
    # Search for packages
    print("\nSearching for packages with 'example'...")
    search_results = registry_manager.search_packages("example")
    
    print(f"Found {len(search_results)} packages:")
    for package in search_results:
        print(f"- {package['name']} v{package['version']}: {package['description']}")
    
    # Get package versions
    print("\nGetting package versions...")
    versions = registry_manager.get_package_versions("example-package")
    
    print(f"Available versions of example-package: {', '.join(versions)}")
    
    # Get package info
    print("\nGetting package info...")
    info = registry_manager.get_package_info("example-package", "1.0.0")
    
    print("Package info:")
    for key, value in info.items():
        print(f"- {key}: {value}")
    
    # Download the package
    print("\nDownloading package...")
    downloaded_data = registry_manager.download_package("example-package", "1.0.0")
    
    if downloaded_data:
        print(f"Successfully downloaded package ({len(downloaded_data)} bytes)")
        
        # Extract and verify contents
        print("Package contents:")
        with zipfile.ZipFile(BytesIO(downloaded_data)) as zip_file:
            for file_info in zip_file.infolist():
                print(f"- {file_info.filename} ({file_info.file_size} bytes)")
    else:
        print("Failed to download package.")
    
    print("\nRegistry example completed.")


if __name__ == "__main__":
    main()

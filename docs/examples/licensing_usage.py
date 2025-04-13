"""Example usage of the Circle Core licensing module.

This example demonstrates how to use the licensing module to generate,
register, and validate licenses.
"""

import os
import sys
from datetime import timedelta

# Import Circle Core components
from src.infrastructure.licensing import (
    CoreLicenseManager, LicenseType, FeatureCatalog,
    InvalidLicenseError, LicenseExpiredError, LicenseFeatureNotAvailableError,
    verify_feature, has_feature, register_license, get_active_license
)
from src.core.encryption import EncryptionService
from src.core.audit import AuditLogger


def main():
    """Run the licensing example."""
    print("Circle Core Licensing Example")
    print("=============================")
    
    # Create dependencies (optional)
    encryption_service = EncryptionService()
    audit_logger = AuditLogger()
    
    # Create a license manager
    license_manager = CoreLicenseManager(
        encryption_service=encryption_service,
        audit_logger=audit_logger
    )
    
    # ------------------------------------
    # License Generation
    # ------------------------------------
    print("\nGenerating Licenses:")
    print("--------------------")
    
    # Generate a trial license
    print("Generating trial license...")
    trial_license = license_manager.generate_trial_license(
        licensee="Trial User",
        duration=timedelta(days=14)  # 14-day trial
    )
    print(f"  Trial license generated: {trial_license.id}")
    print(f"  Licensee: {trial_license.licensee}")
    print(f"  Type: {trial_license.type.name}")
    print(f"  Expires: {trial_license.expiry_date}")
    print(f"  Features: {len(trial_license.features)}")
    
    # Generate a standard license
    print("\nGenerating standard license...")
    standard_license = license_manager.generate_standard_license(
        licensee="Standard User",
        duration=timedelta(days=365)  # 1-year license
    )
    print(f"  Standard license generated: {standard_license.id}")
    print(f"  Licensee: {standard_license.licensee}")
    print(f"  Type: {standard_license.type.name}")
    print(f"  Expires: {standard_license.expiry_date}")
    print(f"  Features: {len(standard_license.features)}")
    
    # Generate an enterprise license
    print("\nGenerating enterprise license...")
    enterprise_license = license_manager.generate_enterprise_license(
        licensee="Enterprise Corp",
        # No duration - perpetual license
    )
    print(f"  Enterprise license generated: {enterprise_license.id}")
    print(f"  Licensee: {enterprise_license.licensee}")
    print(f"  Type: {enterprise_license.type.name}")
    print(f"  Expires: {enterprise_license.expiry_date}")
    print(f"  Features: {len(enterprise_license.features)}")
    
    # Generate a custom license
    print("\nGenerating custom license...")
    custom_features = {
        FeatureCatalog.FEATURE_STORAGE,
        FeatureCatalog.FEATURE_REGISTRY,
        FeatureCatalog.FEATURE_ENCRYPTION,
        FeatureCatalog.FEATURE_TRADING_BOT,
        FeatureCatalog.FEATURE_MLOPS
    }
    custom_license = license_manager.generate_license(
        licensee="Custom Solutions Ltd",
        license_type=LicenseType.CUSTOM,
        features=custom_features,
        duration=timedelta(days=180),  # 6-month license
        custom_data={
            "organization_id": "ORG123456",
            "contact_email": "admin@customsolutions.example",
            "max_users": 50
        }
    )
    print(f"  Custom license generated: {custom_license.id}")
    print(f"  Licensee: {custom_license.licensee}")
    print(f"  Type: {custom_license.type.name}")
    print(f"  Expires: {custom_license.expiry_date}")
    print(f"  Features: {len(custom_license.features)}")
    print(f"  Custom data: {custom_license.custom_data}")
    
    # ------------------------------------
    # License Serialization
    # ------------------------------------
    print("\nLicense Serialization:")
    print("---------------------")
    
    # Serialize a license
    print("Serializing standard license...")
    license_data = license_manager.save_license(standard_license)
    print(f"  License data: {license_data[:50]}... ({len(license_data)} bytes)")
    
    # ------------------------------------
    # License Registration
    # ------------------------------------
    print("\nLicense Registration:")
    print("--------------------")
    
    # Register a license
    try:
        print("Registering standard license...")
        registered_license = license_manager.register_license(license_data)
        print(f"  License registered: {registered_license.id}")
        
        # Get active license
        active_license = license_manager.get_active_license()
        print(f"  Active license: {active_license.id} ({active_license.type.name})")
    except InvalidLicenseError as e:
        print(f"  Error registering license: {e}")
    
    # ------------------------------------
    # Feature Access
    # ------------------------------------
    print("\nFeature Access:")
    print("--------------")
    
    # Check feature access using direct methods
    print("Checking feature access...")
    features_to_check = [
        FeatureCatalog.FEATURE_STORAGE,
        FeatureCatalog.FEATURE_REGISTRY,
        FeatureCatalog.FEATURE_ENCRYPTION,
        FeatureCatalog.FEATURE_MFA,
        FeatureCatalog.FEATURE_CLOUD_INTEGRATION,
        FeatureCatalog.FEATURE_TRADING_BOT
    ]
    
    for feature in features_to_check:
        feature_name = next((name for name, value in vars(FeatureCatalog).items() 
                             if value == feature and name.startswith('FEATURE_')), feature)
        has_access = license_manager.check_feature_access(feature)
        print(f"  {feature_name}: {'Available' if has_access else 'Not available'}")
    
    # Verify feature access with exceptions
    print("\nVerifying feature access (with exceptions)...")
    for feature in features_to_check:
        feature_name = next((name for name, value in vars(FeatureCatalog).items() 
                             if value == feature and name.startswith('FEATURE_')), feature)
        try:
            license_manager.verify_feature_access(feature)
            print(f"  {feature_name}: Access granted")
        except LicenseFeatureNotAvailableError:
            print(f"  {feature_name}: Access denied (feature not available)")
        except LicenseExpiredError:
            print(f"  {feature_name}: Access denied (license expired)")
        except InvalidLicenseError as e:
            print(f"  {feature_name}: Access denied ({e})")
    
    # ------------------------------------
    # License Management
    # ------------------------------------
    print("\nLicense Management:")
    print("------------------")
    
    # List all licenses
    print("Listing all licenses...")
    licenses = license_manager.list_licenses()
    for license in licenses:
        print(f"  {license.id}: {license.licensee} ({license.type.name})")
    
    # Change active license
    print("\nChanging active license...")
    # Use the enterprise license
    success = license_manager.set_active_license(enterprise_license.id)
    if success:
        # Get the new active license
        active_license = license_manager.get_active_license()
        print(f"  New active license: {active_license.id} ({active_license.type.name})")
        
        # Check feature access with new license
        print("  Checking feature access with new license...")
        for feature in features_to_check:
            feature_name = next((name for name, value in vars(FeatureCatalog).items() 
                                if value == feature and name.startswith('FEATURE_')), feature)
            has_access = license_manager.check_feature_access(feature)
            print(f"    {feature_name}: {'Available' if has_access else 'Not available'}")
    else:
        print("  Failed to change active license")
    
    # ------------------------------------
    # Using the simplified API
    # ------------------------------------
    print("\nUsing the Simplified API:")
    print("-----------------------")
    
    # Get active license
    active = get_active_license()
    print(f"Active license: {active.id} ({active.type.name})")
    
    # Check feature access
    for feature in features_to_check:
        feature_name = next((name for name, value in vars(FeatureCatalog).items() 
                            if value == feature and name.startswith('FEATURE_')), feature)
        access = has_feature(feature)
        print(f"  {feature_name}: {'Available' if access else 'Not available'}")
    
    # Using feature access in code
    print("\nUsing feature access in code:")
    try:
        # Example: Only execute certain code if a feature is available
        if has_feature(FeatureCatalog.FEATURE_STORAGE):
            print("  Storage feature is available - executing storage code...")
            # (storage code would go here)
        
        # Example: Raise an exception if feature is not available
        print("  Verifying MFA feature...")
        verify_feature(FeatureCatalog.FEATURE_MFA)
        print("  MFA feature is available - executing MFA code...")
        # (MFA code would go here)
        
    except LicenseFeatureNotAvailableError as e:
        print(f"  Feature access error: {e}")
    
    print("\nLicensing example completed.")


if __name__ == "__main__":
    main()

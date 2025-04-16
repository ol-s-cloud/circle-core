# Circle Core Changelog

All notable changes to the Circle Core project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial CLI tool architecture design
- Expanded documentation structure with historical tracking
- Architecture Decision Records (ADRs) framework

## [0.2.0] - 2025-04-16

### Added
- Kubernetes deployment resources
  - ConfigMap for application configuration
  - Secret template for sensitive data
  - PVC for persistent storage
  - Ingress for external access
  - Network policies for security
  - Kustomize base configuration
- Deployment validation script with multi-environment support
- Configuration generator script for deployment environments
- Multi-environment deployment script
- Kubernetes security testing framework
- Comprehensive documentation for Kubernetes deployment

### Changed
- Updated audit framework to include Kubernetes security
- Reorganized project documentation with historical tracking
- Improved test coverage for deployment components

### Fixed
- Security vulnerabilities in configuration handling
- Edge cases in validation framework

## [0.1.0] - 2025-04-14

### Added
- Configuration management system
  - Multiple provider support (file, environment, memory)
  - Schema-based validation
  - Environment-specific configuration
- Database security components
  - SQL injection protection
  - Query parameterization
  - Secure connection handling
- Storage service with encryption
  - Multiple backend support
  - Transparent encryption
  - Consistent API
- Package registry
  - Versioning system
  - Package validation
  - Dependency resolution
- License management system
  - Feature-based licensing
  - License validation
  - Revocation support

### Changed
- Enhanced authentication with additional MFA options
- Improved audit logging with tamper-evident records
- Upgraded encryption module with key rotation support

### Fixed
- Race condition in concurrent audit logs
- Memory leak in encryption service
- Permissions issue in storage service

## [0.0.1] - 2025-02-28

### Added
- Initial security foundation
  - Authentication services
  - Encryption mechanisms
  - Audit logging
  - Dependency scanning
  - Secrets management
  - Security monitoring
- Basic API structure
- Core utility functions
- Initial documentation

[Unreleased]: https://github.com/ol-s-cloud/circle-core/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ol-s-cloud/circle-core/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ol-s-cloud/circle-core/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/ol-s-cloud/circle-core/releases/tag/v0.0.1

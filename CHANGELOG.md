# Changelog

All notable changes to the Circle Core Framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Core authentication module with Argon2 password hashing
- Multi-factor authentication with TOTP support and backup codes
- Encryption module with key rotation and multiple algorithms
- Audit logging with tamper-evident hash chains
- Secure log storage with encryption
- Comprehensive unit tests for all components

## [0.1.0] - 2025-04-11

### Added
- Initial repository structure
- Authentication module
- Encryption module
- Audit logging module

### Security
- Implemented secure password hashing with Argon2
- Added account lockout protection
- Implemented key rotation policies
- Created tamper-evident audit logging

# Contributing to Circle Core

Thank you for your interest in contributing to Circle Core! This document provides guidelines and instructions for contributing to make the process smooth for everyone involved.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Security Guidelines](#security-guidelines)
- [Testing Requirements](#testing-requirements)
- [Documentation](#documentation)
- [Community Discussions](#community-discussions)
- [Recognition](#recognition)

## Code of Conduct

Our community is dedicated to providing a harassment-free experience for everyone. We do not tolerate harassment of community members in any form. Please be respectful and constructive in all interactions.

Key principles:
- **Be respectful and inclusive**: Treat everyone with respect regardless of their background or identity.
- **Be constructive**: Provide constructive feedback and focus on what is best for the community.
- **Be collaborative**: Work together effectively and acknowledge the efforts of others.
- **Be mindful of language**: Use inclusive language and avoid offensive terms or expressions.

## Getting Started

### Prerequisites
- Python 3.9+
- Git
- Docker (for integration testing)
- Basic knowledge of security concepts

### Setup for Development
1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/circle-core.git
   cd circle-core
   ```
3. Set up the upstream remote:
   ```bash
   git remote add upstream https://github.com/ol-s-cloud/circle-core.git
   ```
4. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
5. Install development dependencies:
   ```bash
   pip install -e ".[dev,test]"
   ```
6. Verify your setup:
   ```bash
   pytest -xvs tests/
   ```

## Development Workflow

1. **Create a Branch**: Always create a new branch for your work.
   ```bash
   git checkout -b feature/your-feature-name
   ```
   
   Naming convention:
   - `feature/` - for new features
   - `bugfix/` - for bug fixes
   - `docs/` - for documentation changes
   - `test/` - for test additions or changes
   - `refactor/` - for code refactoring
   - `security/` - for security enhancements

2. **Make Changes**: Implement your changes with appropriate tests and documentation.

3. **Follow Code Standards**: Run linters and formatters before committing:
   ```bash
   # Format code
   black .
   
   # Check for linting issues
   flake8 .
   
   # Run static type checking
   mypy .
   ```

4. **Run Tests**: Ensure all tests pass:
   ```bash
   pytest -xvs tests/
   ```

5. **Commit Changes**: Use meaningful commit messages.
   ```bash
   git commit -m "feat: Add support for X"
   ```
   
   We follow [Conventional Commits](https://www.conventionalcommits.org/) format:
   - `feat:` - for new features
   - `fix:` - for bug fixes
   - `docs:` - for documentation changes
   - `test:` - for test additions/changes
   - `refactor:` - for code refactoring
   - `chore:` - for maintenance tasks
   - `security:` - for security enhancements

6. **Update Your Branch**: Keep your branch updated with the upstream main branch.
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

7. **Push Changes**: Push your changes to your fork.
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Create a Pull Request**: Open a PR against the main repository with a clear description of the changes.

## Pull Request Process

1. **PR Title**: Use a clear, descriptive title following the Conventional Commits format.

2. **Description Template**: Fill out the PR template completely, including:
   - Purpose of the change
   - Related issue(s)
   - Testing performed
   - Screenshots (if applicable)
   - Documentation updates

3. **Reviews**: At least one maintainer review is required before merging.

4. **CI Checks**: All CI checks must pass, including:
   - Unit and integration tests
   - Code quality checks
   - Security scans
   - Documentation build

5. **Merge Requirements**:
   - PR must be approved by at least one maintainer
   - All discussions must be resolved
   - All CI checks must pass
   - Branch must be up to date with main

6. **Merge Strategy**: We use squash merging to maintain a clean history.

## Coding Standards

We strive for consistent, high-quality code throughout the project:

### Python Style
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting
- Maximum line length of 100 characters
- Use type hints for all function parameters and return values
- Document all public APIs using docstrings (Google style)

### Security Standards
- No hardcoded secrets or credentials
- All user inputs must be validated
- Parameterized queries for all database operations
- Principle of least privilege for all operations
- No disabled security features or debugging code in PRs

### Testing Standards
- All new features must include tests
- Minimum test coverage of 90% for new code
- Include both positive and negative test cases
- Unit tests for all business logic
- Integration tests for component interactions

## Security Guidelines

Security is our highest priority. Please follow these guidelines:

1. **Report Security Issues Privately**: Do not disclose security vulnerabilities publicly. Email security@example.com instead.

2. **Code Security Practices**:
   - Validate all inputs
   - Use parameterized queries
   - Apply proper error handling
   - Follow the principle of least privilege
   - Keep dependencies updated

3. **Security Review**: All security-related changes undergo additional review by security team members.

4. **Security Testing**: Include specific tests that verify security properties of your code.

## Testing Requirements

We have high standards for testing to ensure quality and prevent regressions:

1. **Test Coverage**: Aim for at least 90% test coverage for new code.

2. **Test Types**:
   - **Unit Tests**: For individual functions and classes
   - **Integration Tests**: For component interactions
   - **Security Tests**: For security-specific functionality
   - **Performance Tests**: For performance-critical paths

3. **Test Structure**:
   - Use descriptive test names that explain what is being tested
   - Follow Arrange-Act-Assert pattern
   - One assertion per test when possible
   - Use fixtures and mocks appropriately

4. **CI Integration**: All tests must pass in CI environment before merging.

## Documentation

Good documentation is essential for the project's usability:

1. **Code Documentation**:
   - Docstrings for all public classes and methods (Google style)
   - Clear comments for complex logic
   - Type hints for all function parameters and return values

2. **Project Documentation**:
   - Update relevant documentation for any feature changes
   - Add examples for new functionality
   - Ensure README is kept up-to-date
   - Consider creating tutorials for significant features

3. **Documentation Testing**: Verify that documentation examples work as expected.

## Community Discussions

We encourage open discussions about features, improvements, and issues:

1. **GitHub Discussions**: Use the Discussions tab for:
   - Ideas for new features
   - Questions about usage
   - Architecture discussions
   - Community announcements

2. **Issue Discussions**: Comment on issues to:
   - Provide additional context
   - Suggest solutions
   - Offer to help implement

3. **Pull Request Reviews**: Engage constructively in PR reviews:
   - Ask clarifying questions
   - Suggest improvements
   - Acknowledge good work
   - Explain reasoning when requesting changes

4. **Community Channels**:
   - Join our Discord server for real-time discussions
   - Subscribe to our mailing list for announcements
   - Follow us on Twitter for updates

## Recognition

We value all contributions, and we're committed to recognizing contributors:

1. **Contributors List**: All contributors are listed in the CONTRIBUTORS.md file.

2. **Acknowledgment**: Significant contributions are highlighted in release notes.

3. **Maintainer Path**: Regular contributors may be invited to become maintainers with additional repository access.

---

Thank you for contributing to Circle Core! Your efforts help make this project better for everyone.

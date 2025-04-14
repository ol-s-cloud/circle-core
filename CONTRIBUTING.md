# Contributing to Circle Core

Thank you for your interest in contributing to Circle Core! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Security Guidelines](#security-guidelines)
- [Documentation](#documentation)
- [Community Discussions](#community-discussions)
- [Issue Reporting](#issue-reporting)

## Code of Conduct

We are committed to providing a friendly, safe, and welcoming environment for all contributors. By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before participating.

## Getting Started

### Prerequisites

- Python 3.9+
- Git
- Docker and docker-compose (for running integration tests)

### Setup

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/circle-core.git
   cd circle-core
   ```
3. Set up the upstream remote:
   ```bash
   git remote add upstream https://github.com/ol-s-cloud/circle-core.git
   ```
4. Install development dependencies:
   ```bash
   pip install -e ".[dev,test]"
   ```
5. Create a branch for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

1. Make sure your branch is up to date with the main branch:
   ```bash
   git checkout main
   git pull upstream main
   git checkout your-branch-name
   git rebase main
   ```

2. Make your changes, following our coding standards.

3. Add tests for your changes.

4. Run the tests to ensure they pass:
   ```bash
   # Run unit tests
   pytest tests/unit

   # Run integration tests
   pytest tests/integration

   # Run security tests
   pytest tests/security

   # Run all tests with coverage
   pytest --cov=circle_core
   ```

5. Update documentation as necessary.

6. Commit your changes using a descriptive commit message following our guidelines.

7. Push your branch to your fork:
   ```bash
   git push origin your-branch-name
   ```

8. Submit a pull request to the main repository.

## Pull Request Process

1. Ensure your PR includes a clear description of the changes and their purpose.

2. Link any related issues in the PR description using GitHub keywords (e.g., "Fixes #123").

3. Make sure all CI checks pass:
   - Tests pass
   - Code style checks pass
   - Security scans pass
   - Documentation is up to date

4. Address any feedback from reviewers promptly.

5. Once your PR is approved by at least one maintainer and passes all checks, it will be merged.

### PR Template

When submitting a PR, please use our PR template, which will help you provide all the necessary information:

```markdown
## Description
[Provide a brief description of the changes in this PR]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Other (please describe):

## Related Issues
[Link any related issues here (e.g., "Fixes #123")]

## How Has This Been Tested?
[Describe the tests that you ran to verify your changes]

## Checklist
- [ ] My code follows the project's coding standards
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] I have updated the documentation accordingly
- [ ] I have added docstrings to new functions and classes
- [ ] I have checked that there aren't other open PRs for the same update/change
- [ ] All new and existing tests pass

## Additional Notes
[Add any additional notes or context here]
```

## Coding Standards

We follow strict coding standards to ensure maintainability and readability:

1. **Style Guide**: We follow PEP 8 and use Black for automatic formatting.

2. **Type Hints**: All new code should include Python type hints.

3. **Docstrings**: All public modules, functions, classes, and methods should have docstrings following the Google style.

4. **Testing**: All new code should be accompanied by unit tests. Security-critical code should also have security tests.

5. **Imports**: Organize imports with isort and follow this order:
   - Standard library
   - Third-party libraries
   - Local modules

6. **Security**: Follow security best practices as outlined in our [Security Guidelines](#security-guidelines).

## Commit Message Guidelines

We follow a structured commit message format to standardize our commit history:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **chore**: Changes to the build process or auxiliary tools

### Scope
The scope should be the name of the module affected (e.g., auth, encryption, storage).

### Subject
- Use the imperative, present tense: "change" not "changed" nor "changes"
- Don't capitalize the first letter
- No dot (.) at the end

### Example
```
feat(auth): add support for OAuth2 authentication

Implement OAuth2 authentication flow with support for popular providers.
The implementation follows RFC6749 and includes proper state validation.

Closes #123
```

## Security Guidelines

Security is a top priority for Circle Core. When contributing code, please follow these guidelines:

1. **Input Validation**: Always validate and sanitize inputs, especially from external sources.

2. **Output Encoding**: Properly encode outputs to prevent injection attacks.

3. **Authentication**: Use the provided authentication mechanisms; don't invent your own.

4. **Secrets Management**: Never hardcode secrets or credentials. Use the Secrets Manager.

5. **Dependency Security**: Only add dependencies that are actively maintained and have no known vulnerabilities.

6. **Error Handling**: Implement proper error handling without leaking sensitive information.

7. **Logging**: Use the audit logging system appropriately, ensuring no sensitive data is logged.

8. **Cryptography**: Use the provided encryption module; never implement custom cryptographic solutions.

9. **Security Review**: All security-critical code will undergo additional security review.

Please refer to our [AUDIT_FRAMEWORK.md](AUDIT_FRAMEWORK.md) for more detailed security requirements.

## Documentation

Good documentation is essential for a successful project:

1. **Code Comments**: Use comments to explain "why" rather than "what" when the code isn't self-explanatory.

2. **Docstrings**: All public APIs should have comprehensive docstrings.

3. **README.md**: Keep the README up to date with the latest project overview.

4. **API Documentation**: Document all public APIs with examples.

5. **Tutorials**: Consider creating tutorials for complex features.

When updating code, please update the relevant documentation as well.

## Community Discussions

We encourage open discussions about features, improvements, and challenges:

1. **GitHub Discussions**: Use GitHub Discussions for broader topics, feature ideas, and general questions.

2. **Issue Comments**: Keep discussions on issues focused on the specific topic of the issue.

3. **PR Reviews**: Provide constructive feedback in PR reviews, with specific suggestions where possible.

4. **Community Calls**: Join our monthly community calls (see the Community section on our website).

## Issue Reporting

If you find a bug or have a feature request:

1. Search existing issues to see if it's already reported.

2. If not, create a new issue using the appropriate template.

3. Provide as much detail as possible, including:
   - Steps to reproduce bugs
   - Expected vs. actual behavior
   - Screenshots or logs (with sensitive information redacted)
   - Environment details (OS, Python version, etc.)

### Security Vulnerabilities

If you discover a security vulnerability, please do NOT open an issue. Instead, send an email to security@circle-data.com. See our [Security Policy](SECURITY.md) for more details.

## Thank You!

Your contributions to Circle Core are greatly appreciated. Together, we're building a secure, robust framework that benefits everyone. Thank you for being part of our community!

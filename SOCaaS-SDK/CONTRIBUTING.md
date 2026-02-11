# Contributing to SOCaaS SDK

Thank you for your interest in contributing to the SOCaaS Python SDK!

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/socaas-sdk.git`
3. Create a virtual environment: `python -m venv venv`
4. Install dependencies: `pip install -e ".[dev]"`

## Development Setup

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black socaas/

# Type checking
mypy socaas/
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Keep line length under 100 characters
- Use meaningful variable and function names
- Add docstrings to all public functions

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Update documentation if needed
6. Submit a pull request

## Reporting Issues

When reporting issues, please include:

- Python version
- SDK version
- Steps to reproduce
- Expected vs actual behavior
- Error messages (with sensitive data redacted)

## Security

**Important**: Never commit credentials or tokens. Use environment variables or credential files that are in `.gitignore`.

If you discover a security vulnerability, please report it privately rather than opening a public issue.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

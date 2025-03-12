# DCAgent Development Guide

## Build/Run Commands
```
poetry install                      # Install dependencies
poetry run python -m dcagent.main   # Run the application
poetry run pytest                   # Run all tests
poetry run pytest tests/test_file.py::test_function  # Run single test
poetry run black .                  # Format code
poetry run isort .                  # Sort imports
poetry run mypy .                   # Type checking
poetry run flake8                   # Lint code
```

## Code Style Guidelines
- **Imports:** Use `from typing import` for type annotations; group stdlib, third-party, and local imports
- **Typing:** Use type annotations for all function parameters and return values
- **Naming:** Use snake_case for variables/functions, PascalCase for classes, UPPER_CASE for constants
- **Error Handling:** Use try/except blocks with specific exceptions; log errors with appropriate level
- **Documentation:** Use docstrings for all classes and non-trivial functions
- **Function Structure:** Keep functions focused on a single responsibility
- **Blockchain Interaction:** Always validate transactions and handle gas optimization properly
- **Config:** Store configuration in dcagent/config.py; use environment variables for secrets
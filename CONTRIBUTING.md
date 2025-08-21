# Contributing to TokenForge

Thank you for considering contributing to TokenForge! This document provides guidelines and instructions for contributing to this project.

## Code of Conduct

Please be respectful and considerate of others when contributing to this project. We aim to foster an inclusive and welcoming community.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with the following information:
- A clear, descriptive title
- Steps to reproduce the bug
- Expected behavior
- Actual behavior
- Environment information (OS, Go version, Python version, etc.)

### Suggesting Features

Feature suggestions are welcome! Please create an issue with:
- A clear, descriptive title
- A detailed description of the proposed feature
- Any relevant context or examples

### Pull Requests

1. Fork the repository
2. Create a new branch from `main`
3. Make your changes
4. Run tests to ensure your changes don't break existing functionality
5. Submit a pull request

### Pull Request Guidelines

- Follow the existing code style
- Include tests for new functionality
- Update documentation as needed
- Keep pull requests focused on a single concern
- Reference any related issues

## Development Setup

### Prerequisites

- Go 1.19+
- Python 3.9+
- Docker and Docker Compose
- Kubernetes cluster (for full testing)

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/TokenForge.git
cd TokenForge
```

2. Start the development environment:
```bash
make dev
```

3. Run the API server:
```bash
make run-api
```

## Testing

Run tests with:
```bash
./scripts/test_api_local.sh
```

For more comprehensive testing with Docker:
```bash
./scripts/comprehensive_test.sh
```

## Code Style

- Go: Follow the [Go Code Review Comments](https://github.com/golang/go/wiki/CodeReviewComments)
- Python: Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)

## License

By contributing to TokenForge, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).

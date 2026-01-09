# Contributing to Nansen Twitter Sentiment Monitor

Thank you for your interest in contributing to the Nansen Twitter Sentiment Monitor! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing Requirements](#testing-requirements)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)
- [Project Structure](#project-structure)
- [Adding New Features](#adding-new-features)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow:

- **Be respectful**: Treat everyone with respect and kindness
- **Be collaborative**: Work together to find the best solutions
- **Be professional**: Keep discussions focused and constructive
- **Be inclusive**: Welcome contributors of all backgrounds and experience levels

## How to Contribute

There are many ways to contribute to this project:

1. **Report bugs** - Help us identify and fix issues
2. **Suggest features** - Share ideas for improvements
3. **Write code** - Implement new features or fix bugs
4. **Improve documentation** - Make guides clearer and more comprehensive
5. **Write tests** - Increase test coverage and robustness
6. **Review pull requests** - Provide feedback on proposed changes

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- Access to X API, Claude API, and Slack (for testing)

### Setup Steps

1. **Fork the repository**
   ```bash
   # Click "Fork" on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/nansen-twitter-sentiment-monitor.git
   cd nansen-twitter-sentiment-monitor
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If available
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your test credentials
   ```

5. **Verify installation**
   ```bash
   python -m pytest tests/ -v
   ```

## Development Workflow

### 1. Create a Branch

Always create a new branch for your work:

```bash
# Update your fork
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

Branch naming conventions:
- `feature/feature-name` - New features
- `fix/bug-name` - Bug fixes
- `docs/description` - Documentation updates
- `test/description` - Test improvements
- `refactor/description` - Code refactoring

### 2. Make Changes

- Write clean, readable code
- Follow the code style guidelines (see below)
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test class
python -m pytest tests/test_suite.py::TestTwitterClient -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Check code style
black --check src/ tests/
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "Brief description of changes"
```

See [Commit Message Guidelines](#commit-message-guidelines) for formatting.

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Code Style Guidelines

### Python Style (PEP 8)

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: Maximum 100 characters (not 79)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Use double quotes for strings (not single)
- **Imports**: Group in order: standard library, third-party, local

### Code Formatting

We use [Black](https://black.readthedocs.io/) for automatic code formatting:

```bash
# Format all code
black src/ tests/

# Check formatting without changes
black --check src/ tests/
```

### Type Hints

All functions should include type hints:

```python
def search_mentions(self, hours: int = 24) -> List[Dict[str, Any]]:
    """Search for mentions in the specified time window."""
    pass
```

### Docstrings

Use Google-style docstrings for all public functions and classes:

```python
def analyze_sentiment(self, tweets: List[Dict]) -> List[Dict]:
    """Analyze sentiment of tweets using Claude AI.

    Args:
        tweets: List of tweet dictionaries with required fields

    Returns:
        List of analyzed tweets with sentiment data

    Raises:
        ValueError: If tweets list is empty
        APIError: If Claude API call fails
    """
    pass
```

### Naming Conventions

- **Functions and variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_leading_underscore`

### Code Organization

- Keep functions focused and single-purpose
- Maximum function length: ~50 lines
- Use meaningful variable names (no single letters except in loops)
- Add comments for complex logic only (code should be self-documenting)

### Example Good Code

```python
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """Analyzes tweet sentiment using Claude AI."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        """Initialize analyzer with API credentials.

        Args:
            api_key: Anthropic API key
            model: Claude model identifier
        """
        self.api_key = api_key
        self.model = model
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate configuration parameters."""
        if not self.api_key:
            raise ValueError("API key is required")
        logger.info(f"Initialized SentimentAnalyzer with model: {self.model}")
```

## Testing Requirements

### Test Coverage

- All new features must include tests
- Target: >80% code coverage
- Test both success and failure cases
- Include edge cases and boundary conditions

### Test Structure

```python
import unittest
from unittest.mock import Mock, patch

class TestNewFeature(unittest.TestCase):
    """Test suite for new feature."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_data = {"key": "value"}

    def tearDown(self):
        """Clean up after tests."""
        pass

    def test_basic_functionality(self):
        """Test basic feature behavior."""
        result = function_under_test(self.test_data)
        self.assertEqual(result, expected_value)

    def test_error_handling(self):
        """Test error handling."""
        with self.assertRaises(ValueError):
            function_under_test(invalid_data)
```

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_suite.py -v

# Specific test class
python -m pytest tests/test_suite.py::TestTwitterClient -v

# Specific test method
python -m pytest tests/test_suite.py::TestTwitterClient::test_initialization -v

# With coverage report
python -m pytest tests/ --cov=src --cov-report=html

# Show print statements
python -m pytest tests/ -s

# Stop on first failure
python -m pytest tests/ -x
```

### Mock External APIs

Always mock external API calls in tests:

```python
@patch('twitter_client.tweepy.Client')
def test_fetch_tweets(self, mock_client):
    """Test tweet fetching with mocked API."""
    mock_response = Mock()
    mock_response.data = [mock_tweet1, mock_tweet2]
    mock_client.return_value.search_recent_tweets.return_value = mock_response

    result = client.search_mentions(hours=24)
    self.assertEqual(len(result), 2)
```

## Commit Message Guidelines

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **test**: Test additions or modifications
- **refactor**: Code refactoring
- **style**: Code style changes (formatting, no logic change)
- **perf**: Performance improvements
- **chore**: Build process or tooling changes

### Examples

```bash
feat(analyzer): add multi-language sentiment support

Implement support for analyzing tweets in Spanish, French, and German.
Uses language detection before analysis and applies language-specific
sentiment models.

Closes #123
```

```bash
fix(twitter): handle rate limit errors correctly

Previously, rate limit errors caused the entire workflow to fail.
Now implements exponential backoff and retries up to 3 times.

Fixes #456
```

```bash
docs(readme): update API cost calculations

Update cost estimates based on current Claude API pricing and
add examples of monthly costs for different usage patterns.
```

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages follow guidelines
- [ ] Branch is up to date with main

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
Describe how you tested your changes

## Checklist
- [ ] Tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No breaking changes (or documented)

## Related Issues
Closes #123
Related to #456
```

### Review Process

1. **Automated checks**: All CI/CD checks must pass
2. **Code review**: At least one maintainer review required
3. **Testing**: Reviewer may test changes locally
4. **Approval**: Maintainer approves and merges

### After Merge

- Delete your branch (done automatically on GitHub)
- Update your local repository:
  ```bash
  git checkout main
  git pull upstream main
  ```

## Project Structure

Understanding the project structure helps you find where to make changes:

```
nansen-twitter-sentiment-monitor/
├── src/                          # Main source code
│   ├── twitter_client.py         # X API integration
│   ├── sentiment_analyzer.py     # Claude AI analysis
│   ├── aggregator.py             # Data aggregation
│   ├── slack_notifier.py         # Slack notifications
│   └── utils.py                  # Helper functions
├── config/                       # Configuration files
│   └── config.yaml               # Main configuration
├── tests/                        # Test suite
│   ├── test_suite.py             # All tests
│   ├── test_data/                # Sample data
│   └── README.md                 # Test documentation
├── .github/workflows/            # GitHub Actions
│   └── daily-sentiment.yml       # Automated workflow
├── main.py                       # Main orchestration script
└── requirements.txt              # Python dependencies
```

## Adding New Features

### Feature Development Checklist

1. **Planning**
   - [ ] Create GitHub issue describing the feature
   - [ ] Discuss approach with maintainers
   - [ ] Design API/interface

2. **Implementation**
   - [ ] Create feature branch
   - [ ] Write implementation code
   - [ ] Add type hints and docstrings
   - [ ] Handle errors appropriately

3. **Testing**
   - [ ] Write unit tests
   - [ ] Write integration tests if needed
   - [ ] Ensure >80% coverage
   - [ ] Test edge cases

4. **Documentation**
   - [ ] Update relevant README sections
   - [ ] Add docstrings to all functions
   - [ ] Update CHANGELOG.md
   - [ ] Add usage examples

5. **Review**
   - [ ] Self-review code
   - [ ] Run all tests locally
   - [ ] Create pull request
   - [ ] Address review feedback

### Example: Adding a New Sentiment Theme

```python
# 1. Update config/config.yaml
positive_themes:
  - mobile_adoption
  - roi_confirmation
  - new_theme_name  # Add here

# 2. Update prompt in sentiment_analyzer.py
POSITIVE_THEMES = """
- mobile_adoption: Users adopting Nansen Mobile
- roi_confirmation: Users confirming ROI/value
- new_theme_name: Description of new theme
"""

# 3. Add test in tests/test_suite.py
def test_new_theme_extraction(self):
    """Test extraction of new theme."""
    tweets = [{"text": "Example tweet about new theme"}]
    result = analyzer.analyze(tweets)
    self.assertIn("new_theme_name", result[0]["themes"])

# 4. Update documentation in README.md
```

## Reporting Bugs

### Before Reporting

- Check existing issues to avoid duplicates
- Verify the bug exists in the latest version
- Collect relevant information (logs, screenshots, etc.)

### Bug Report Template

```markdown
**Description**
Clear description of the bug

**To Reproduce**
1. Step 1
2. Step 2
3. Step 3

**Expected Behavior**
What should happen

**Actual Behavior**
What actually happens

**Environment**
- OS: [e.g., macOS 14.0]
- Python version: [e.g., 3.11.5]
- Project version: [e.g., 1.0.0]

**Logs**
```
Paste relevant logs here
```

**Additional Context**
Any other relevant information
```

## Suggesting Enhancements

### Enhancement Proposal Template

```markdown
**Problem**
What problem does this solve?

**Proposed Solution**
Detailed description of the enhancement

**Alternatives Considered**
Other approaches you've thought about

**Implementation Notes**
Technical details, if applicable

**Breaking Changes**
Will this break existing functionality?

**Additional Context**
Mockups, examples, references, etc.
```

## Questions?

If you have questions about contributing:

1. Check existing documentation (README.md, this file)
2. Search existing GitHub issues
3. Create a new issue with the "question" label
4. Reach out to maintainers

## Recognition

Contributors will be recognized in:
- GitHub contributors list
- Release notes for significant contributions
- README.md acknowledgments section

Thank you for contributing to Nansen Twitter Sentiment Monitor!

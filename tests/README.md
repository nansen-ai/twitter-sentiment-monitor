# Test Suite Documentation

Comprehensive test suite for Nansen Twitter Sentiment Monitor.

## Test Coverage

### 1. Unit Tests

**TestTwitterClient** (6 tests)
- Initialization and configuration
- Keyword extraction from tweets
- Credential validation (success/failure)
- Search query formatting

**TestSentimentAnalyzer** (7 tests)
- Initialization with API key
- Tweet formatting for prompts
- JSON response parsing (valid JSON, markdown fences)
- Analysis validation with defaults
- Cost calculation accuracy
- Error handling and retries

**TestAggregator** (8 tests)
- Sentiment score calculation
- Theme grouping
- Product mention counting
- Negative phrase extraction
- Empty tweet list handling
- Full report generation
- Tweet count validation

**TestSlackNotifier** (8 tests)
- Message formatting (summary and detailed)
- Tweet list Slack link formatting
- Webhook posting (success/failure)
- Team alert triggering
- Report validation
- Error notifications

**TestUtils** (11 tests)
- Number formatting (K/M/B)
- Cost calculation
- Text truncation at word boundaries
- Text sanitization
- Twitter URL building
- Spam detection (various patterns)
- Engagement rate calculation

### 2. Integration Tests

**TestFullWorkflow** (2 tests)
- Complete pipeline (Twitter → Claude → Aggregation → Slack)
- Empty tweets handling
- Error recovery

## Running Tests

### Run All Tests
```bash
# Using pytest (recommended)
python -m pytest tests/ -v

# Using unittest
python tests/test_suite.py

# With coverage
python -m pytest tests/ -v --cov=src --cov-report=html
```

### Run Specific Test Class
```bash
python -m pytest tests/test_suite.py::TestTwitterClient -v
python -m pytest tests/test_suite.py::TestSentimentAnalyzer -v
```

### Run Specific Test
```bash
python -m pytest tests/test_suite.py::TestUtils::test_format_number_thousands -v
```

## Test Data

### Mock Data Generators

**generate_mock_tweets(n=20)**
- Creates realistic tweet data
- Mix of positive, negative, neutral sentiments
- Includes edge cases (airdrop speculation, violations)
- All required fields included

**generate_mock_analyzed_tweets(n=20)**
- Creates fully analyzed tweet structures
- Complete analysis fields
- Diverse strategic categories
- Cost data included

### Sample Files

**tests/test_data/sample_tweets.json**
- 3 representative tweets
- Used for integration testing
- Covers positive, negative, neutral cases

## Test Requirements

Install test dependencies:
```bash
pip install pytest pytest-cov pytest-mock
```

Or from requirements.txt:
```bash
pip install -r requirements.txt
```

## Test Structure

```
tests/
├── __init__.py              # Package initialization
├── test_suite.py            # Main test suite (50+ tests)
├── test_data/              # Test data files
│   └── sample_tweets.json  # Sample tweet data
└── README.md               # This file
```

## Mocking Strategy

### External APIs
- **Twitter API**: Mock `tweepy.Client` responses
- **Claude API**: Mock `Anthropic` client responses
- **Slack API**: Mock `requests.post` for webhooks

### File Operations
- Use temporary directories for file I/O tests
- Mock environment variables with `os.environ`

### Example Mock
```python
@patch('twitter_client.tweepy.Client')
def test_fetch_tweets(self, mock_client):
    mock_response = Mock()
    mock_response.data = [mock_tweet1, mock_tweet2]
    mock_client.return_value.search_recent_tweets.return_value = mock_response

    result = client.search_mentions(hours=24)
    assert len(result) == 2
```

## Test Coverage Goals

Target: >80% code coverage

Current coverage:
- TwitterClient: ~85%
- SentimentAnalyzer: ~80%
- Aggregator: ~90%
- SlackNotifier: ~75%
- Utils: ~95%

Run coverage report:
```bash
python -m pytest tests/ --cov=src --cov-report=term-missing
```

## CI/CD Integration

Tests run automatically on:
- Push to main branch
- Pull requests
- Manual workflow dispatch

See `.github/workflows/daily-sentiment.yml` for configuration.

## Adding New Tests

### 1. Create Test Class
```python
class TestNewFeature(unittest.TestCase):
    def setUp(self):
        # Setup test fixtures
        pass

    def test_feature_behavior(self):
        # Test specific behavior
        self.assertEqual(expected, actual)
```

### 2. Add to Test Suite
```python
suite.addTests(loader.loadTestsFromTestCase(TestNewFeature))
```

### 3. Run Tests
```bash
python -m pytest tests/test_suite.py::TestNewFeature -v
```

## Common Test Patterns

### Test API Call
```python
@patch('module.external_api')
def test_api_call(self, mock_api):
    mock_api.return_value = expected_response
    result = function_under_test()
    self.assertEqual(result, expected)
```

### Test Exception Handling
```python
def test_error_handling(self):
    with self.assertRaises(ValueError):
        function_that_should_fail()
```

### Test File Operations
```python
def test_save_load(self):
    data = {'key': 'value'}
    save_json(data, 'test.json')
    loaded = load_json('test.json')
    self.assertEqual(data, loaded)
```

## Debugging Tests

### Verbose Output
```bash
python -m pytest tests/ -vv
```

### Show Print Statements
```bash
python -m pytest tests/ -s
```

### Run Last Failed
```bash
python -m pytest tests/ --lf
```

### Debug with pdb
```python
def test_debug(self):
    import pdb; pdb.set_trace()
    # Test code here
```

## Test Best Practices

1. **Isolation**: Each test should be independent
2. **Clarity**: Test names should describe what they test
3. **Completeness**: Test both success and failure cases
4. **Speed**: Keep tests fast by mocking external calls
5. **Maintainability**: Use setup/teardown for common fixtures

## Continuous Improvement

- Add tests when fixing bugs
- Update tests when changing features
- Review test coverage regularly
- Refactor tests to reduce duplication

## Support

For questions or issues with tests:
1. Check test output for specific failure
2. Review mock data generators
3. Verify external dependencies are mocked
4. Check environment variable setup

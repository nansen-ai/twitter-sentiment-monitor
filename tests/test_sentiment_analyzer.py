"""Tests for sentiment analyzer."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sentiment_analyzer import SentimentAnalyzer


@pytest.fixture
def sentiment_analyzer():
    """Create a sentiment analyzer instance for testing."""
    return SentimentAnalyzer(api_key="test_api_key")


@pytest.fixture
def sample_tweet():
    """Create a sample tweet for testing."""
    return {
        "id": "123456789",
        "text": "Bitcoin is revolutionizing finance! Great news for crypto adoption.",
        "author_username": "cryptoenthusiast",
        "author_id": "user123",
        "created_at": "2025-01-09T12:00:00Z"
    }


@pytest.fixture
def mock_claude_response():
    """Create mock Claude API response."""
    mock_content = Mock()
    mock_content.text = """SENTIMENT: positive
SCORE: 0.8
CONFIDENCE: 0.9
REASONING: The tweet expresses strong optimism about Bitcoin and cryptocurrency adoption."""

    mock_message = Mock()
    mock_message.content = [mock_content]

    return mock_message


class TestSentimentAnalyzer:
    """Test cases for SentimentAnalyzer."""

    def test_initialization(self, sentiment_analyzer):
        """Test analyzer initialization."""
        assert sentiment_analyzer.client is not None
        assert sentiment_analyzer.model == "claude-3-5-sonnet-20241022"

    def test_build_sentiment_prompt(self, sentiment_analyzer, sample_tweet):
        """Test prompt building."""
        prompt = sentiment_analyzer._build_sentiment_prompt(sample_tweet["text"])

        assert sample_tweet["text"] in prompt
        assert "SENTIMENT:" in prompt
        assert "SCORE:" in prompt
        assert "CONFIDENCE:" in prompt

    def test_parse_sentiment_response_positive(self, sentiment_analyzer):
        """Test parsing positive sentiment response."""
        response = """SENTIMENT: positive
SCORE: 0.75
CONFIDENCE: 0.85
REASONING: Very optimistic tone about crypto"""

        result = sentiment_analyzer._parse_sentiment_response(response)

        assert result["sentiment"] == "positive"
        assert result["score"] == 0.75
        assert result["confidence"] == 0.85
        assert "optimistic" in result["reasoning"].lower()

    def test_parse_sentiment_response_negative(self, sentiment_analyzer):
        """Test parsing negative sentiment response."""
        response = """SENTIMENT: negative
SCORE: -0.6
CONFIDENCE: 0.8
REASONING: Expresses concern about market crash"""

        result = sentiment_analyzer._parse_sentiment_response(response)

        assert result["sentiment"] == "negative"
        assert result["score"] == -0.6
        assert result["confidence"] == 0.8

    def test_parse_sentiment_response_neutral(self, sentiment_analyzer):
        """Test parsing neutral sentiment response."""
        response = """SENTIMENT: neutral
SCORE: 0.0
CONFIDENCE: 0.7
REASONING: Factual statement without clear sentiment"""

        result = sentiment_analyzer._parse_sentiment_response(response)

        assert result["sentiment"] == "neutral"
        assert result["score"] == 0.0

    def test_parse_sentiment_response_score_clamping(self, sentiment_analyzer):
        """Test that scores are clamped to [-1, 1] range."""
        response = """SENTIMENT: positive
SCORE: 1.5
CONFIDENCE: 0.9
REASONING: Test"""

        result = sentiment_analyzer._parse_sentiment_response(response)

        assert result["score"] == 1.0  # Clamped to max

        response_negative = """SENTIMENT: negative
SCORE: -1.5
CONFIDENCE: 0.9
REASONING: Test"""

        result_negative = sentiment_analyzer._parse_sentiment_response(response_negative)

        assert result_negative["score"] == -1.0  # Clamped to min

    @patch("sentiment_analyzer.Anthropic")
    def test_analyze_tweet_success(self, mock_anthropic, sentiment_analyzer, sample_tweet, mock_claude_response):
        """Test successful tweet analysis."""
        sentiment_analyzer.client.messages.create = Mock(return_value=mock_claude_response)

        result = sentiment_analyzer.analyze_tweet(sample_tweet)

        assert result["sentiment"] == "positive"
        assert result["score"] == 0.8
        assert result["confidence"] == 0.9
        assert result["tweet_id"] == sample_tweet["id"]
        assert result["author"] == sample_tweet["author_username"]

    @patch("sentiment_analyzer.Anthropic")
    def test_analyze_tweet_api_error(self, mock_anthropic, sentiment_analyzer, sample_tweet):
        """Test tweet analysis with API error."""
        sentiment_analyzer.client.messages.create = Mock(side_effect=Exception("API Error"))

        result = sentiment_analyzer.analyze_tweet(sample_tweet)

        assert result["sentiment"] == "neutral"
        assert result["score"] == 0.0
        assert "error" in result

    def test_analyze_batch(self, sentiment_analyzer, sample_tweet):
        """Test batch analysis."""
        tweets = [sample_tweet, {**sample_tweet, "id": "987654321"}]

        with patch.object(sentiment_analyzer, "analyze_tweet") as mock_analyze:
            mock_analyze.return_value = {
                "sentiment": "positive",
                "score": 0.7,
                "confidence": 0.8
            }

            results = sentiment_analyzer.analyze_batch(tweets)

            assert len(results) == 2
            assert mock_analyze.call_count == 2

    def test_get_aggregate_sentiment_empty(self, sentiment_analyzer):
        """Test aggregate sentiment with empty results."""
        aggregate = sentiment_analyzer.get_aggregate_sentiment([])

        assert aggregate["average_score"] == 0.0
        assert aggregate["total_count"] == 0
        assert aggregate["positive_count"] == 0

    def test_get_aggregate_sentiment_mixed(self, sentiment_analyzer):
        """Test aggregate sentiment with mixed results."""
        results = [
            {"sentiment": "positive", "score": 0.8, "confidence": 0.9},
            {"sentiment": "negative", "score": -0.6, "confidence": 0.8},
            {"sentiment": "neutral", "score": 0.0, "confidence": 0.7},
            {"sentiment": "positive", "score": 0.4, "confidence": 0.6},
        ]

        aggregate = sentiment_analyzer.get_aggregate_sentiment(results)

        assert aggregate["total_count"] == 4
        assert aggregate["positive_count"] == 2
        assert aggregate["negative_count"] == 1
        assert aggregate["neutral_count"] == 1
        assert aggregate["average_score"] == pytest.approx(0.15, rel=0.01)

    def test_get_aggregate_sentiment_with_errors(self, sentiment_analyzer):
        """Test aggregate sentiment with some errors."""
        results = [
            {"sentiment": "positive", "score": 0.8, "confidence": 0.9},
            {"sentiment": "negative", "score": -0.6, "confidence": 0.8, "error": "API timeout"},
            {"sentiment": "neutral", "score": 0.0, "confidence": 0.7},
        ]

        aggregate = sentiment_analyzer.get_aggregate_sentiment(results)

        assert aggregate["total_count"] == 3
        assert aggregate["error_count"] == 1
        # Error entries should be excluded from score calculation
        assert aggregate["positive_count"] == 1
        assert aggregate["negative_count"] == 0  # Error entry not counted
        assert aggregate["neutral_count"] == 1

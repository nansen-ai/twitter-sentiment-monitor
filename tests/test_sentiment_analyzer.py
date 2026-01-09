"""Tests for sentiment analyzer."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestSentimentAnalyzer:
    """Test cases for SentimentAnalyzer."""

    @patch("sentiment_analyzer.Anthropic")
    def test_initialization(self, mock_anthropic):
        """Test analyzer initialization."""
        from sentiment_analyzer import SentimentAnalyzer

        analyzer = SentimentAnalyzer(api_key="test_api_key")

        assert analyzer.client is not None
        assert analyzer.model == "claude-sonnet-4-5-20250929"
        assert analyzer.api_key == "test_api_key"

    @patch("sentiment_analyzer.Anthropic")
    def test_initialization_missing_api_key(self, mock_anthropic):
        """Test analyzer initialization fails without API key."""
        from sentiment_analyzer import SentimentAnalyzer

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="API key not provided"):
                SentimentAnalyzer(api_key=None)

    @patch("sentiment_analyzer.Anthropic")
    def test_format_tweets_for_prompt(self, mock_anthropic):
        """Test formatting tweets for the prompt."""
        from sentiment_analyzer import SentimentAnalyzer

        analyzer = SentimentAnalyzer(api_key="test_api_key")

        tweets = [
            {
                "tweet_id": "123",
                "text": "Nansen is great!",
                "author_username": "user1",
                "engagement": {
                    "total": 100,
                    "likes": 50,
                    "retweets": 30,
                    "replies": 20,
                },
                "author_followers": 1000,
            },
            {
                "tweet_id": "456",
                "text": "Love the mobile app",
                "author_username": "user2",
                "engagement": {"total": 50, "likes": 25, "retweets": 15, "replies": 10},
                "author_followers": 500,
            },
        ]

        formatted = analyzer._format_tweets_for_prompt(tweets)

        # Check for tweet numbering format (Tweet 1:, Tweet 2:)
        assert "Tweet 1:" in formatted
        assert "Tweet 2:" in formatted
        assert "Nansen is great!" in formatted
        assert "user1" in formatted

    @patch("sentiment_analyzer.Anthropic")
    def test_calculate_cost(self, mock_anthropic):
        """Test cost calculation."""
        from sentiment_analyzer import SentimentAnalyzer

        analyzer = SentimentAnalyzer(api_key="test_api_key")

        # Test with known values
        # Input: $3/MTok, Output: $15/MTok
        cost = analyzer._calculate_cost(1000, 1000)

        # 1000 input tokens = $0.003, 1000 output tokens = $0.015
        expected = (1000 / 1_000_000 * 3.0) + (1000 / 1_000_000 * 15.0)
        assert cost == pytest.approx(expected, rel=0.01)

    @patch("sentiment_analyzer.Anthropic")
    def test_validate_analysis_valid(self, mock_anthropic):
        """Test validation of a valid analysis result."""
        from sentiment_analyzer import SentimentAnalyzer

        analyzer = SentimentAnalyzer(api_key="test_api_key")

        tweet = {"tweet_id": "123", "text": "Test tweet"}
        analysis = {
            "sentiment": "POSITIVE",
            "confidence": 85,
            "intent": "PRAISE",
            "urgency": "LOW",
            "product_mentions": ["nansen_mobile"],
            "themes": ["mobile_adoption"],
            "negative_patterns": [],
            "critical_keywords": [],
            "strategic_category": "STRATEGIC_WIN",
            "competitive_mentions": [],
            "is_viral": False,
            "is_influencer": False,
            "actionable": False,
            "summary": "User praising the mobile app",
        }

        result = analyzer._validate_analysis(analysis, tweet)

        assert result["sentiment"] == "POSITIVE"
        assert result["confidence"] == 85
        assert result["intent"] == "PRAISE"

    @patch("sentiment_analyzer.Anthropic")
    def test_validate_analysis_invalid_sentiment(self, mock_anthropic):
        """Test validation corrects invalid sentiment."""
        from sentiment_analyzer import SentimentAnalyzer

        analyzer = SentimentAnalyzer(api_key="test_api_key")

        tweet = {"tweet_id": "123", "text": "Test tweet"}
        analysis = {
            "sentiment": "INVALID_SENTIMENT",
            "confidence": 85,
            "intent": "PRAISE",
            "urgency": "LOW",
            "product_mentions": [],
            "themes": [],
            "negative_patterns": [],
            "critical_keywords": [],
            "strategic_category": "NEUTRAL_MENTION",
            "competitive_mentions": [],
            "summary": "Test",
        }

        result = analyzer._validate_analysis(analysis, tweet)

        # Should default to NEUTRAL for invalid sentiment
        assert result["sentiment"] == "NEUTRAL"

    @patch("sentiment_analyzer.Anthropic")
    def test_validate_analysis_clamps_confidence(self, mock_anthropic):
        """Test validation clamps confidence to valid range."""
        from sentiment_analyzer import SentimentAnalyzer

        analyzer = SentimentAnalyzer(api_key="test_api_key")

        tweet = {"tweet_id": "123", "text": "Test tweet"}
        analysis = {
            "sentiment": "POSITIVE",
            "confidence": 150,  # Invalid - should be clamped to 100
            "intent": "PRAISE",
            "urgency": "LOW",
            "product_mentions": [],
            "themes": [],
            "negative_patterns": [],
            "critical_keywords": [],
            "strategic_category": "NEUTRAL_MENTION",
            "competitive_mentions": [],
            "summary": "Test",
        }

        result = analyzer._validate_analysis(analysis, tweet)

        assert result["confidence"] == 100

    @patch("sentiment_analyzer.Anthropic")
    def test_parse_response_valid_json(self, mock_anthropic):
        """Test parsing valid JSON response."""
        from sentiment_analyzer import SentimentAnalyzer

        analyzer = SentimentAnalyzer(api_key="test_api_key")

        response_text = json.dumps(
            [
                {
                    "tweet_id": "123",
                    "sentiment": "POSITIVE",
                    "confidence": 0.85,
                    "primary_intent": "PRAISE",
                    "urgency_level": "LOW",
                    "products_mentioned": ["nansen_mobile"],
                    "positive_themes": ["mobile_adoption"],
                    "negative_themes": [],
                    "strategic_category": "STRATEGIC_WIN",
                    "key_phrases": ["great app"],
                    "summary": "User praising the mobile app",
                }
            ]
        )

        result = analyzer._parse_response(response_text)

        assert len(result) == 1
        assert result[0]["tweet_id"] == "123"
        assert result[0]["sentiment"] == "POSITIVE"

    @patch("sentiment_analyzer.Anthropic")
    def test_parse_response_with_code_block(self, mock_anthropic):
        """Test parsing JSON response wrapped in code block."""
        from sentiment_analyzer import SentimentAnalyzer

        analyzer = SentimentAnalyzer(api_key="test_api_key")

        response_text = """```json
[
    {
        "tweet_id": "123",
        "sentiment": "POSITIVE",
        "confidence": 0.85,
        "primary_intent": "PRAISE",
        "urgency_level": "LOW",
        "products_mentioned": [],
        "positive_themes": [],
        "negative_themes": [],
        "strategic_category": "STRATEGIC_WIN",
        "key_phrases": [],
        "summary": "Test"
    }
]
```"""

        result = analyzer._parse_response(response_text)

        assert len(result) == 1
        assert result[0]["sentiment"] == "POSITIVE"

    @patch("sentiment_analyzer.Anthropic")
    def test_cache_operations(self, mock_anthropic):
        """Test cache loading and saving."""
        from sentiment_analyzer import SentimentAnalyzer
        import tempfile
        import os

        analyzer = SentimentAnalyzer(api_key="test_api_key")

        # Use temp file for cache
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp.write("{}")
            tmp_path = tmp.name

        try:
            analyzer.cache_file = Path(tmp_path)

            # Test loading empty cache
            cache = analyzer._load_cache()
            assert cache == {}

            # Test saving cache
            test_cache = {"tweet_123": {"sentiment": "POSITIVE"}}
            analyzer._save_cache(test_cache)

            # Test loading saved cache
            loaded_cache = analyzer._load_cache()
            assert "tweet_123" in loaded_cache
        finally:
            os.unlink(tmp_path)

    @patch("sentiment_analyzer.Anthropic")
    def test_is_cache_valid(self, mock_anthropic):
        """Test cache validity checking."""
        from sentiment_analyzer import SentimentAnalyzer
        from datetime import datetime, timedelta

        analyzer = SentimentAnalyzer(api_key="test_api_key")

        # Recent cache entry - should be valid
        recent_entry = {"cached_at": datetime.now().isoformat()}
        assert analyzer._is_cache_valid(recent_entry, max_days=7) is True

        # Old cache entry - should be invalid
        old_date = datetime.now() - timedelta(days=10)
        old_entry = {"cached_at": old_date.isoformat()}
        assert analyzer._is_cache_valid(old_entry, max_days=7) is False

        # Entry without cached_at - should be invalid
        no_date_entry = {}
        assert analyzer._is_cache_valid(no_date_entry, max_days=7) is False

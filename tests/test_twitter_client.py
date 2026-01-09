"""Tests for Twitter client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from twitter_client import TwitterClient


@pytest.fixture
def twitter_client():
    """Create a Twitter client instance for testing."""
    return TwitterClient(bearer_token="test_token")


@pytest.fixture
def mock_tweet_response():
    """Create mock tweet response."""
    mock_tweet = Mock()
    mock_tweet.id = "123456789"
    mock_tweet.text = "Bitcoin is going to the moon! #crypto"
    mock_tweet.author_id = "user123"
    mock_tweet.created_at = "2025-01-09T12:00:00Z"
    mock_tweet.public_metrics = {"like_count": 100, "retweet_count": 50}

    mock_user = Mock()
    mock_user.id = "user123"
    mock_user.username = "cryptotrader"
    mock_user.name = "Crypto Trader"

    return mock_tweet, mock_user


class TestTwitterClient:
    """Test cases for TwitterClient."""

    def test_initialization(self, twitter_client):
        """Test client initialization."""
        assert twitter_client.client is not None

    def test_build_search_query_keywords_only(self, twitter_client):
        """Test building search query with keywords only."""
        keywords = ["Bitcoin", "Ethereum"]
        accounts = []

        query = twitter_client.build_search_query(keywords, accounts)

        assert "Bitcoin" in query
        assert "Ethereum" in query
        assert "-is:retweet" in query
        assert "lang:en" in query

    def test_build_search_query_accounts_only(self, twitter_client):
        """Test building search query with accounts only."""
        keywords = []
        accounts = ["VitalikButerin", "cz_binance"]

        query = twitter_client.build_search_query(keywords, accounts)

        assert "from:VitalikButerin" in query
        assert "from:cz_binance" in query
        assert "-is:retweet" in query

    def test_build_search_query_combined(self, twitter_client):
        """Test building search query with keywords and accounts."""
        keywords = ["Bitcoin"]
        accounts = ["VitalikButerin"]

        query = twitter_client.build_search_query(keywords, accounts)

        assert "Bitcoin" in query
        assert "from:VitalikButerin" in query

    @patch("twitter_client.tweepy.Client")
    def test_search_recent_tweets_success(self, mock_tweepy_client, twitter_client, mock_tweet_response):
        """Test successful tweet search."""
        mock_tweet, mock_user = mock_tweet_response

        mock_response = Mock()
        mock_response.data = [mock_tweet]
        mock_response.includes = {"users": [mock_user]}

        twitter_client.client.search_recent_tweets = Mock(return_value=mock_response)

        tweets = twitter_client.search_recent_tweets("Bitcoin", max_results=10)

        assert len(tweets) == 1
        assert tweets[0]["id"] == "123456789"
        assert tweets[0]["author_username"] == "cryptotrader"
        assert "Bitcoin" in tweets[0]["text"] or "moon" in tweets[0]["text"]

    @patch("twitter_client.tweepy.Client")
    def test_search_recent_tweets_no_results(self, mock_tweepy_client, twitter_client):
        """Test tweet search with no results."""
        mock_response = Mock()
        mock_response.data = None

        twitter_client.client.search_recent_tweets = Mock(return_value=mock_response)

        tweets = twitter_client.search_recent_tweets("NonexistentKeyword")

        assert len(tweets) == 0

    @patch("twitter_client.tweepy.Client")
    def test_search_recent_tweets_with_since_id(self, mock_tweepy_client, twitter_client):
        """Test tweet search with since_id parameter."""
        mock_response = Mock()
        mock_response.data = []

        twitter_client.client.search_recent_tweets = Mock(return_value=mock_response)

        twitter_client.search_recent_tweets("Bitcoin", since_id="123456")

        call_args = twitter_client.client.search_recent_tweets.call_args
        assert call_args[1]["since_id"] == "123456"

    @patch("twitter_client.tweepy.Client")
    def test_get_user_tweets_success(self, mock_tweepy_client, twitter_client, mock_tweet_response):
        """Test successful user tweet retrieval."""
        mock_tweet, mock_user = mock_tweet_response

        # Mock get_user response
        user_response = Mock()
        user_response.data = mock_user
        twitter_client.client.get_user = Mock(return_value=user_response)

        # Mock get_users_tweets response
        tweets_response = Mock()
        tweets_response.data = [mock_tweet]
        twitter_client.client.get_users_tweets = Mock(return_value=tweets_response)

        tweets = twitter_client.get_user_tweets("cryptotrader")

        assert len(tweets) == 1
        assert tweets[0]["author_username"] == "cryptotrader"

    @patch("twitter_client.tweepy.Client")
    def test_get_user_tweets_user_not_found(self, mock_tweepy_client, twitter_client):
        """Test user tweet retrieval when user doesn't exist."""
        user_response = Mock()
        user_response.data = None
        twitter_client.client.get_user = Mock(return_value=user_response)

        tweets = twitter_client.get_user_tweets("nonexistentuser")

        assert len(tweets) == 0

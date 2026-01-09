"""Tests for Twitter client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestTwitterClient:
    """Test cases for TwitterClient."""

    @patch("twitter_client.tweepy.Client")
    def test_initialization(self, mock_tweepy_client):
        """Test client initialization."""
        from twitter_client import TwitterClient

        # Mock the get_user call for credential validation
        mock_client_instance = Mock()
        mock_response = Mock()
        mock_response.data = Mock()
        mock_response.data.username = "X"
        mock_client_instance.get_user.return_value = mock_response
        mock_tweepy_client.return_value = mock_client_instance

        client = TwitterClient(bearer_token="test_token")

        assert client.client is not None
        assert client.bearer_token == "test_token"

    @patch("twitter_client.tweepy.Client")
    def test_initialization_missing_token(self, mock_tweepy_client):
        """Test client initialization fails without bearer token."""
        from twitter_client import TwitterClient

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="Bearer token not provided"):
                TwitterClient(bearer_token=None)

    @patch("twitter_client.tweepy.Client")
    def test_validate_credentials_success(self, mock_tweepy_client):
        """Test successful credential validation."""
        from twitter_client import TwitterClient

        mock_client_instance = Mock()
        mock_response = Mock()
        mock_response.data = Mock()
        mock_response.data.username = "X"
        mock_client_instance.get_user.return_value = mock_response
        mock_tweepy_client.return_value = mock_client_instance

        client = TwitterClient(bearer_token="test_token")

        assert client.validate_credentials() is True

    @patch("twitter_client.tweepy.Client")
    def test_validate_credentials_failure(self, mock_tweepy_client):
        """Test failed credential validation."""
        from twitter_client import TwitterClient
        import tweepy

        mock_client_instance = Mock()
        # First call succeeds (for __init__), second call fails
        mock_response_success = Mock()
        mock_response_success.data = Mock()
        mock_response_fail = Mock()
        mock_response_fail.data = None

        mock_client_instance.get_user.side_effect = [
            mock_response_success,
            mock_response_fail,
        ]
        mock_tweepy_client.return_value = mock_client_instance

        client = TwitterClient(bearer_token="test_token")

        # Second call should return False
        assert client.validate_credentials() is False

    @patch("twitter_client.tweepy.Client")
    def test_extract_keywords(self, mock_tweepy_client):
        """Test keyword extraction from tweet text."""
        from twitter_client import TwitterClient

        mock_client_instance = Mock()
        mock_response = Mock()
        mock_response.data = Mock()
        mock_client_instance.get_user.return_value = mock_response
        mock_tweepy_client.return_value = mock_client_instance

        client = TwitterClient(bearer_token="test_token")

        # Test with Nansen mention
        keywords = client._extract_keywords("@nansen_ai is great for trading!")
        assert "nansen_ai" in keywords
        assert "trading" in keywords

        # Test with nansen text
        keywords = client._extract_keywords("Nansen mobile app is awesome")
        assert "nansen_ai" in keywords
        assert "mobile" in keywords
        assert "app" in keywords

        # Test with multiple keywords
        keywords = client._extract_keywords("Trading points and mobile features")
        assert "trading" in keywords
        assert "points" in keywords
        assert "mobile" in keywords

    @patch("twitter_client.tweepy.Client")
    def test_search_mentions_success(self, mock_tweepy_client):
        """Test successful tweet search."""
        from twitter_client import TwitterClient

        # Setup mock client
        mock_client_instance = Mock()

        # Mock get_user for credential validation
        mock_user_response = Mock()
        mock_user_response.data = Mock()
        mock_user_response.data.username = "X"
        mock_client_instance.get_user.return_value = mock_user_response

        # Mock search response
        mock_tweet = Mock()
        mock_tweet.id = "123456789"
        mock_tweet.text = "@nansen_ai is amazing for trading!"
        mock_tweet.author_id = "user123"
        mock_tweet.created_at = Mock()
        mock_tweet.created_at.isoformat.return_value = "2025-01-09T12:00:00"
        mock_tweet.public_metrics = {
            "like_count": 100,
            "retweet_count": 50,
            "reply_count": 10,
            "quote_count": 5,
        }

        mock_author = Mock()
        mock_author.id = "user123"
        mock_author.username = "cryptotrader"
        mock_author.name = "Crypto Trader"
        mock_author.verified = True
        mock_author.public_metrics = {"followers_count": 10000}

        mock_search_response = Mock()
        mock_search_response.data = [mock_tweet]
        mock_search_response.includes = {"users": [mock_author]}
        mock_search_response.meta = {}

        mock_client_instance.search_recent_tweets.return_value = mock_search_response
        mock_tweepy_client.return_value = mock_client_instance

        client = TwitterClient(bearer_token="test_token")
        tweets = client.search_mentions(hours=24)

        assert len(tweets) == 1
        assert tweets[0]["tweet_id"] == "123456789"
        assert tweets[0]["author_username"] == "cryptotrader"
        assert tweets[0]["engagement"]["likes"] == 100
        assert tweets[0]["is_verified"] is True

    @patch("twitter_client.tweepy.Client")
    def test_search_mentions_no_results(self, mock_tweepy_client):
        """Test tweet search with no results."""
        from twitter_client import TwitterClient

        mock_client_instance = Mock()

        # Mock get_user for credential validation
        mock_user_response = Mock()
        mock_user_response.data = Mock()
        mock_client_instance.get_user.return_value = mock_user_response

        # Mock empty search response
        mock_search_response = Mock()
        mock_search_response.data = None

        mock_client_instance.search_recent_tweets.return_value = mock_search_response
        mock_tweepy_client.return_value = mock_client_instance

        client = TwitterClient(bearer_token="test_token")
        tweets = client.search_mentions(hours=1)

        assert len(tweets) == 0

    @patch("twitter_client.tweepy.Client")
    def test_search_mentions_pagination(self, mock_tweepy_client):
        """Test tweet search with pagination."""
        from twitter_client import TwitterClient

        mock_client_instance = Mock()

        # Mock get_user for credential validation
        mock_user_response = Mock()
        mock_user_response.data = Mock()
        mock_client_instance.get_user.return_value = mock_user_response

        # Create mock tweets
        def create_mock_tweet(tweet_id):
            mock_tweet = Mock()
            mock_tweet.id = tweet_id
            mock_tweet.text = f"Tweet {tweet_id}"
            mock_tweet.author_id = "user123"
            mock_tweet.created_at = Mock()
            mock_tweet.created_at.isoformat.return_value = "2025-01-09T12:00:00"
            mock_tweet.public_metrics = {
                "like_count": 10,
                "retweet_count": 5,
                "reply_count": 2,
                "quote_count": 1,
            }
            return mock_tweet

        mock_author = Mock()
        mock_author.id = "user123"
        mock_author.username = "testuser"
        mock_author.name = "Test User"
        mock_author.verified = False
        mock_author.public_metrics = {"followers_count": 100}

        # First page response
        mock_response1 = Mock()
        mock_response1.data = [create_mock_tweet("1"), create_mock_tweet("2")]
        mock_response1.includes = {"users": [mock_author]}
        mock_response1.meta = {"next_token": "token123"}

        # Second page response (no more pages)
        mock_response2 = Mock()
        mock_response2.data = [create_mock_tweet("3")]
        mock_response2.includes = {"users": [mock_author]}
        mock_response2.meta = {}

        mock_client_instance.search_recent_tweets.side_effect = [
            mock_response1,
            mock_response2,
        ]
        mock_tweepy_client.return_value = mock_client_instance

        client = TwitterClient(bearer_token="test_token")
        tweets = client.search_mentions(hours=24)

        assert len(tweets) == 3
        assert mock_client_instance.search_recent_tweets.call_count == 2

    @patch("twitter_client.tweepy.Client")
    def test_search_mentions_rate_limit_handled(self, mock_tweepy_client):
        """Test that rate limit errors are handled gracefully."""
        from twitter_client import TwitterClient
        import tweepy

        mock_client_instance = Mock()

        # Mock get_user for credential validation
        mock_user_response = Mock()
        mock_user_response.data = Mock()
        mock_client_instance.get_user.return_value = mock_user_response

        # Mock rate limit error with proper Response object
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"detail": "Too Many Requests"}
        mock_client_instance.search_recent_tweets.side_effect = tweepy.TooManyRequests(
            mock_response
        )
        mock_tweepy_client.return_value = mock_client_instance

        client = TwitterClient(bearer_token="test_token")

        # Should return empty list after retries, not raise exception
        with patch("time.sleep"):  # Skip actual sleep
            tweets = client.search_mentions(hours=1)

        assert tweets == []

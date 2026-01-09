"""Tests for alert manager."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from alert_manager import AlertManager


@pytest.fixture
def alert_config():
    """Create alert configuration for testing."""
    return {
        "average_score_threshold": 0.5,
        "negative_score_threshold": -0.7,
        "positive_score_threshold": 0.7,
        "min_confidence_for_alerts": 0.7,
    }


@pytest.fixture
def alert_manager(alert_config):
    """Create an alert manager instance for testing."""
    return AlertManager(
        slack_webhook_url="https://hooks.slack.com/test", alert_config=alert_config
    )


@pytest.fixture
def sample_sentiment_results():
    """Create sample sentiment results."""
    return [
        {
            "tweet_id": "123",
            "tweet_text": "Bitcoin is amazing!",
            "author": "user1",
            "sentiment": "positive",
            "score": 0.8,
            "confidence": 0.9,
        },
        {
            "tweet_id": "124",
            "tweet_text": "Crypto market looking good",
            "author": "user2",
            "sentiment": "positive",
            "score": 0.6,
            "confidence": 0.8,
        },
        {
            "tweet_id": "125",
            "tweet_text": "Market crash incoming",
            "author": "user3",
            "sentiment": "negative",
            "score": -0.8,
            "confidence": 0.85,
        },
    ]


@pytest.fixture
def sample_aggregate():
    """Create sample aggregate metrics."""
    return {
        "average_score": 0.6,
        "positive_count": 5,
        "negative_count": 2,
        "neutral_count": 1,
        "total_count": 8,
    }


class TestAlertManager:
    """Test cases for AlertManager."""

    def test_initialization(self, alert_manager):
        """Test alert manager initialization."""
        assert alert_manager.slack_client is not None
        assert alert_manager.alert_config is not None
        assert len(alert_manager.alert_history) == 0

    def test_initialization_without_slack(self, alert_config):
        """Test initialization without Slack webhook."""
        manager = AlertManager(slack_webhook_url=None, alert_config=alert_config)
        assert manager.slack_client is None

    def test_create_aggregate_alert_positive(self, alert_manager):
        """Test creating aggregate alert for positive sentiment."""
        aggregate = {
            "average_score": 0.7,
            "positive_count": 10,
            "negative_count": 2,
            "neutral_count": 3,
            "total_count": 15,
        }

        alert = alert_manager._create_aggregate_alert(aggregate)

        assert alert["type"] == "aggregate_sentiment"
        assert "positive" in alert["message"]
        assert "📈" in alert["message"]
        assert alert["data"]["Total Tweets"] == 15

    def test_create_aggregate_alert_negative(self, alert_manager):
        """Test creating aggregate alert for negative sentiment."""
        aggregate = {
            "average_score": -0.6,
            "positive_count": 2,
            "negative_count": 10,
            "neutral_count": 3,
            "total_count": 15,
        }

        alert = alert_manager._create_aggregate_alert(aggregate)

        assert alert["type"] == "aggregate_sentiment"
        assert "negative" in alert["message"]
        assert "📉" in alert["message"]

    def test_create_tweet_alert_positive(self, alert_manager):
        """Test creating alert for positive tweet."""
        result = {
            "tweet_id": "123",
            "tweet_text": "Bitcoin is going to the moon!",
            "author": "cryptotrader",
            "sentiment": "positive",
            "score": 0.9,
            "confidence": 0.95,
        }

        alert = alert_manager._create_tweet_alert(result, "positive")

        assert alert["type"] == "high_positive_tweet"
        assert "🔥" in alert["message"]
        assert "@cryptotrader" in alert["message"]
        assert alert["data"]["Score"] == "0.90"

    def test_create_tweet_alert_negative(self, alert_manager):
        """Test creating alert for negative tweet."""
        result = {
            "tweet_id": "456",
            "tweet_text": "Market crash is imminent!",
            "author": "bearishtrader",
            "sentiment": "negative",
            "score": -0.85,
            "confidence": 0.9,
        }

        alert = alert_manager._create_tweet_alert(result, "negative")

        assert alert["type"] == "high_negative_tweet"
        assert "⚠️" in alert["message"]
        assert "@bearishtrader" in alert["message"]

    def test_format_slack_message(self, alert_manager):
        """Test formatting alert as Slack message."""
        alert = {
            "type": "test_alert",
            "message": "Test alert message",
            "data": {"Score": "0.8", "Confidence": "0.9"},
        }

        blocks = alert_manager._format_slack_message(alert)

        assert len(blocks) >= 3  # header, section, divider
        assert blocks[0]["type"] == "header"
        assert blocks[1]["type"] == "section"
        assert "Test alert message" in blocks[1]["text"]["text"]

    def test_check_and_send_alerts_high_average(
        self, alert_manager, sample_sentiment_results
    ):
        """Test alert triggering on high average score."""
        aggregate = {
            "average_score": 0.6,  # Above threshold of 0.5
            "positive_count": 2,
            "negative_count": 1,
            "neutral_count": 0,
            "total_count": 3,
        }

        with patch.object(alert_manager, "send_alert") as mock_send:
            alert_manager.check_and_send_alerts(sample_sentiment_results, aggregate)
            # Should send at least aggregate alert
            assert mock_send.call_count >= 1

    def test_check_and_send_alerts_extreme_tweets(self, alert_manager):
        """Test alert triggering on extreme sentiment tweets."""
        results = [
            {
                "tweet_id": "999",
                "tweet_text": "HUGE crash incoming!",
                "author": "bear",
                "sentiment": "negative",
                "score": -0.9,
                "confidence": 0.95,
            }
        ]

        aggregate = {
            "average_score": -0.9,
            "positive_count": 0,
            "negative_count": 1,
            "neutral_count": 0,
            "total_count": 1,
        }

        with patch.object(alert_manager, "send_alert") as mock_send:
            alert_manager.check_and_send_alerts(results, aggregate)
            # Should send both aggregate and individual tweet alerts
            assert mock_send.call_count >= 2

    @patch("alert_manager.WebhookClient")
    def test_send_slack_alert_success(self, mock_webhook_client, alert_manager):
        """Test successful Slack alert sending."""
        mock_response = Mock()
        mock_response.status_code = 200
        alert_manager.slack_client.send = Mock(return_value=mock_response)

        alert = {"type": "test", "message": "Test message", "data": {}}

        result = alert_manager._send_slack_alert(alert)

        assert result is True
        assert alert_manager.slack_client.send.called

    @patch("alert_manager.WebhookClient")
    def test_send_slack_alert_failure(self, mock_webhook_client, alert_manager):
        """Test failed Slack alert sending."""
        mock_response = Mock()
        mock_response.status_code = 500
        alert_manager.slack_client.send = Mock(return_value=mock_response)

        alert = {"type": "test", "message": "Test message", "data": {}}

        result = alert_manager._send_slack_alert(alert)

        assert result is False

    def test_get_alert_history(self, alert_manager):
        """Test retrieving alert history."""
        # Add some alerts
        for i in range(15):
            alert_manager.alert_history.append(
                {
                    "type": f"test_{i}",
                    "message": f"Test message {i}",
                    "timestamp": f"2025-01-09T{i:02d}:00:00Z",
                }
            )

        history = alert_manager.get_alert_history(limit=5)

        assert len(history) == 5
        # Should return most recent
        assert "test_14" in history[-1]["type"]

    def test_clear_alert_history(self, alert_manager):
        """Test clearing alert history."""
        alert_manager.alert_history.append({"type": "test", "message": "test"})
        assert len(alert_manager.alert_history) > 0

        alert_manager.clear_alert_history()

        assert len(alert_manager.alert_history) == 0

    def test_send_alert_without_slack(self, alert_config):
        """Test sending alert when no Slack is configured."""
        manager = AlertManager(slack_webhook_url=None, alert_config=alert_config)

        alert = {"type": "test", "message": "test", "data": {}}

        result = manager.send_alert(alert)

        assert result is False
        # But alert should still be logged in history
        assert len(manager.alert_history) == 1

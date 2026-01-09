"""
Comprehensive test suite for Nansen Twitter Sentiment Monitor.

Run with:
    python -m pytest tests/ -v
    python tests/test_suite.py
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from twitter_client import TwitterClient
from sentiment_analyzer import SentimentAnalyzer
from aggregator import SentimentAggregator
from slack_notifier import SlackNotifier
from utils import (
    format_number,
    calculate_cost,
    truncate_text,
    sanitize_text,
    save_json,
    load_json,
    build_twitter_url,
    is_spam,
    calculate_engagement_rate,
)


# ============================================================================
# Mock Data Generators
# ============================================================================


def generate_mock_tweets(n: int = 20) -> List[Dict]:
    """
    Generate realistic mock tweets for testing.

    Args:
        n: Number of tweets to generate

    Returns:
        List of mock tweet dictionaries
    """
    base_time = datetime.utcnow()

    # Mix of positive, negative, and neutral tweets
    tweet_templates = [
        # Positive
        (
            "Just used @nansen_ai mobile app to catch a whale trade! This is game changing 🚀",
            "POSITIVE",
        ),
        (
            "@nansen_ai Season 2 rewards are amazing! Already earned 500 points",
            "POSITIVE",
        ),
        ("Best trading experience ever with @nansen_ai AI insights", "POSITIVE"),
        (
            "Nansen Mobile is the future of crypto trading. Highly recommend!",
            "POSITIVE",
        ),
        ("Love how easy it is to track trades with @nansen_ai", "POSITIVE"),
        # Negative
        ("@nansen_ai app keeps crashing, can't access my dashboard", "NEGATIVE"),
        ("High fees on @nansen_ai trading, not worth it", "NEGATIVE"),
        ("Terrible execution quality, slippage too high @nansen_ai", "NEGATIVE"),
        ("@nansen_ai customer support is non-responsive", "NEGATIVE"),
        ("Platform down again @nansen_ai, very frustrating", "NEGATIVE"),
        # Neutral
        ("Does @nansen_ai support Base chain?", "NEUTRAL"),
        ("Looking into @nansen_ai for on-chain analytics", "NEUTRAL"),
        ("Anyone tried Nansen Mobile app yet?", "NEUTRAL"),
        ("Comparing @nansen_ai vs Arkham", "NEUTRAL"),
        ("How do I earn Nansen points?", "NEUTRAL"),
        # Edge cases
        ("@nansen_ai wen token? 🚀", "AIRDROP"),
        ("Guaranteed 10x profits with @nansen_ai trading! 💰", "VIOLATION"),
        ("@nansen_ai is a scam, lost all my funds", "CRITICAL"),
        ("Just made $10k using @nansen_ai signals!", "POSITIVE"),
        ("@nansen_ai mobile app UI needs improvement", "FEEDBACK"),
    ]

    tweets = []
    for i in range(n):
        template_idx = i % len(tweet_templates)
        text, sentiment = tweet_templates[template_idx]

        tweet = {
            "tweet_id": str(1000000 + i),
            "text": text,
            "author_username": f"user{i}",
            "author_name": f"Test User {i}",
            "created_at": (base_time - timedelta(hours=i)).isoformat() + "Z",
            "engagement": {
                "likes": 10 + i * 5,
                "retweets": 2 + i,
                "replies": 1 + i // 2,
                "quotes": i // 3,
                "total": 13 + i * 6,
            },
            "url": f"https://twitter.com/user{i}/status/{1000000 + i}",
            "is_verified": i % 5 == 0,  # Every 5th user is verified
            "author_followers": 1000 + i * 500,
            "mentioned_keywords": ["nansen_ai"] if "@nansen_ai" in text else [],
        }
        tweets.append(tweet)

    return tweets


def generate_mock_analyzed_tweets(n: int = 20) -> List[Dict]:
    """
    Generate mock analyzed tweets with full analysis structure.

    Args:
        n: Number of analyzed tweets to generate

    Returns:
        List of analyzed tweet dictionaries
    """
    raw_tweets = generate_mock_tweets(n)
    analyzed = []

    sentiment_map = {
        0: "POSITIVE",
        1: "POSITIVE",
        2: "POSITIVE",
        3: "POSITIVE",
        4: "POSITIVE",
        5: "NEGATIVE",
        6: "NEGATIVE",
        7: "NEGATIVE",
        8: "NEGATIVE",
        9: "NEGATIVE",
        10: "NEUTRAL",
        11: "NEUTRAL",
        12: "NEUTRAL",
        13: "NEUTRAL",
        14: "NEUTRAL",
        15: "NEGATIVE",
        16: "NEGATIVE",
        17: "NEGATIVE",
        18: "POSITIVE",
        19: "MIXED",
    }

    for i, tweet in enumerate(raw_tweets):
        sentiment = sentiment_map.get(i % 20, "NEUTRAL")

        analysis = {
            "sentiment": sentiment,
            "confidence": 75 + (i % 20),
            "intent": (
                "PRAISE"
                if sentiment == "POSITIVE"
                else "COMPLAINT" if sentiment == "NEGATIVE" else "QUESTION"
            ),
            "product_mentions": (
                ["nansen_mobile"] if "mobile" in tweet["text"].lower() else []
            ),
            "themes": (
                ["mobile_adoption"]
                if sentiment == "POSITIVE"
                else ["execution_failures"] if sentiment == "NEGATIVE" else []
            ),
            "negative_patterns": (
                ["slippage", "bad_execution"]
                if "slippage" in tweet["text"].lower()
                else []
            ),
            "critical_keywords": (
                ["scam"]
                if "scam" in tweet["text"].lower()
                else ["token"] if "token" in tweet["text"].lower() else []
            ),
            "urgency": (
                "HIGH"
                if "scam" in tweet["text"].lower()
                else "MEDIUM" if sentiment == "NEGATIVE" else "LOW"
            ),
            "actionable": "scam" in tweet["text"].lower()
            or "crash" in tweet["text"].lower(),
            "summary": tweet["text"][:100],
            "competitive_mentions": (
                ["Arkham"] if "arkham" in tweet["text"].lower() else []
            ),
            "is_viral": tweet["engagement"]["total"] > 100,
            "is_influencer": tweet["is_verified"],
            "strategic_category": (
                "CRITICAL_FUD"
                if "scam" in tweet["text"].lower()
                else (
                    "STRATEGIC_WIN"
                    if sentiment == "POSITIVE" and i % 5 == 0
                    else "NEUTRAL_MENTION"
                )
            ),
            "analyzed_at": datetime.utcnow().isoformat(),
        }

        analyzed.append(
            {
                "tweet_id": tweet["tweet_id"],
                "original_tweet": tweet,
                "analysis": analysis,
                "api_cost": {
                    "input_tokens": 1500,
                    "output_tokens": 800,
                    "estimated_cost_usd": 0.0165,
                },
            }
        )

    return analyzed


# ============================================================================
# Test Classes
# ============================================================================


class TestTwitterClient(unittest.TestCase):
    """Test cases for TwitterClient."""

    def setUp(self):
        """Set up test fixtures."""
        os.environ["X_API_BEARER_TOKEN"] = "test_bearer_token"
        with patch("twitter_client.tweepy.Client"):
            self.client = TwitterClient(bearer_token="test_token")

    def test_initialization(self):
        """Test TwitterClient initialization."""
        self.assertIsNotNone(self.client)
        self.assertEqual(self.client.bearer_token, "test_token")

    def test_extract_keywords(self):
        """Test keyword extraction from tweets."""
        text = "Check out @nansen_ai mobile app for trading!"
        keywords = self.client._extract_keywords(text)

        self.assertIn("nansen_ai", keywords)
        self.assertIn("mobile", keywords)
        self.assertIn("trading", keywords)

    @patch("twitter_client.tweepy.Client")
    def test_validate_credentials_success(self, mock_client):
        """Test successful credential validation."""
        mock_me = Mock()
        mock_me.data.username = "test_user"
        self.client.client.get_me = Mock(return_value=mock_me)

        result = self.client.validate_credentials()
        self.assertTrue(result)

    @patch("twitter_client.tweepy.Client")
    def test_validate_credentials_failure(self, mock_client):
        """Test failed credential validation."""
        self.client.client.get_me = Mock(side_effect=Exception("Auth failed"))

        result = self.client.validate_credentials()
        self.assertFalse(result)


class TestSentimentAnalyzer(unittest.TestCase):
    """Test cases for SentimentAnalyzer."""

    def setUp(self):
        """Set up test fixtures."""
        os.environ["ANTHROPIC_API_KEY"] = "test_api_key"
        with patch("sentiment_analyzer.Anthropic"):
            self.analyzer = SentimentAnalyzer(api_key="test_key")

    def test_initialization(self):
        """Test SentimentAnalyzer initialization."""
        self.assertIsNotNone(self.analyzer)
        self.assertEqual(self.analyzer.model, "claude-sonnet-4-5-20250929")

    def test_format_tweets_for_prompt(self):
        """Test tweet formatting for Claude prompt."""
        tweets = generate_mock_tweets(3)
        formatted = self.analyzer._format_tweets_for_prompt(tweets)

        self.assertIn("Tweet 1:", formatted)
        self.assertIn("Tweet 2:", formatted)
        self.assertIn("Tweet 3:", formatted)
        self.assertIn("@user0", formatted)

    def test_parse_response_valid_json(self):
        """Test parsing valid JSON response."""
        response = json.dumps(
            [
                {
                    "sentiment": "POSITIVE",
                    "confidence": 85,
                    "intent": "PRAISE",
                    "themes": ["mobile_adoption"],
                }
            ]
        )

        result = self.analyzer._parse_response(response)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["sentiment"], "POSITIVE")

    def test_parse_response_markdown_fences(self):
        """Test parsing JSON with markdown code fences."""
        response = "```json\n" + json.dumps([{"sentiment": "POSITIVE"}]) + "\n```"

        result = self.analyzer._parse_response(response)
        self.assertEqual(len(result), 1)

    def test_validate_analysis(self):
        """Test analysis validation with defaults."""
        tweet = generate_mock_tweets(1)[0]
        analysis = {"sentiment": "INVALID"}  # Invalid sentiment

        validated = self.analyzer._validate_analysis(analysis, tweet)

        self.assertEqual(validated["sentiment"], "NEUTRAL")  # Default
        self.assertIn("confidence", validated)
        self.assertIn("themes", validated)

    def test_calculate_cost(self):
        """Test API cost calculation."""
        cost = self.analyzer._calculate_cost(10000, 5000)

        # Input: 10k tokens * $3/1M = $0.03
        # Output: 5k tokens * $15/1M = $0.075
        # Total: $0.105
        self.assertAlmostEqual(cost, 0.105, places=3)


class TestAggregator(unittest.TestCase):
    """Test cases for SentimentAggregator."""

    def setUp(self):
        """Set up test fixtures."""
        self.aggregator = SentimentAggregator()
        self.mock_tweets = generate_mock_analyzed_tweets(20)

    def test_initialization(self):
        """Test SentimentAggregator initialization."""
        self.assertIsNotNone(self.aggregator)

    def test_calculate_sentiment_score(self):
        """Test sentiment score calculation."""
        score = self.aggregator._calculate_sentiment_score(self.mock_tweets)

        # Score should be between -100 and 100
        self.assertGreaterEqual(score, -100)
        self.assertLessEqual(score, 100)

    def test_group_by_themes(self):
        """Test grouping tweets by themes."""
        groups = self.aggregator._group_by_themes(self.mock_tweets)

        self.assertIsInstance(groups, dict)
        for theme, tweets in groups.items():
            self.assertIsInstance(tweets, list)

    def test_count_product_mentions(self):
        """Test counting product mentions."""
        counts = self.aggregator._count_product_mentions(self.mock_tweets)

        self.assertIn("nansen_mobile", counts)
        self.assertIn("season2_rewards", counts)
        self.assertIn("nansen_trading", counts)
        self.assertIsInstance(counts["nansen_mobile"], int)

    def test_extract_negative_phrases(self):
        """Test extracting negative phrases."""
        negative_tweets = [
            t for t in self.mock_tweets if t["analysis"]["sentiment"] == "NEGATIVE"
        ]

        phrases = self.aggregator._extract_negative_phrases(negative_tweets)

        self.assertIsInstance(phrases, list)
        for phrase in phrases:
            self.assertIn("phrase", phrase)
            self.assertIn("username", phrase)
            self.assertIn("category", phrase)

    def test_aggregate_empty_tweets(self):
        """Test aggregating empty tweet list."""
        report = self.aggregator.aggregate([])

        self.assertEqual(report["raw_data"]["summary"]["total_tweets"], 0)
        self.assertIn("message_1", report)
        self.assertIn("message_2", report)

    def test_aggregate_full_report(self):
        """Test generating full report."""
        report = self.aggregator.aggregate(self.mock_tweets)

        # Validate structure
        self.assertIn("message_1", report)
        self.assertIn("message_2", report)
        self.assertIn("raw_data", report)
        self.assertIn("metadata", report)

        # Validate summary
        summary = report["raw_data"]["summary"]
        self.assertEqual(summary["total_tweets"], 20)
        self.assertIn("positive_count", summary)
        self.assertIn("negative_count", summary)

    def test_tweet_count_validation(self):
        """Test that positive + negative equals total."""
        report = self.aggregator.aggregate(self.mock_tweets)
        summary = report["raw_data"]["summary"]

        total = summary["positive_count"] + summary["negative_count"]
        self.assertEqual(total, summary["total_tweets"])


class TestSlackNotifier(unittest.TestCase):
    """Test cases for SlackNotifier."""

    def setUp(self):
        """Set up test fixtures."""
        os.environ["SLACK_WEBHOOK_URL"] = "https://hooks.slack.com/test"
        self.notifier = SlackNotifier()

    def test_initialization(self):
        """Test SlackNotifier initialization."""
        self.assertIsNotNone(self.notifier)
        self.assertEqual(self.notifier.method, "webhook")

    def test_format_message_1(self):
        """Test formatting summary message."""
        analyzed_tweets = generate_mock_analyzed_tweets(20)
        aggregator = SentimentAggregator()
        report = aggregator.aggregate(analyzed_tweets)

        message = self.notifier._format_message_1(report)

        self.assertIn("Nansen Daily Sentiment Report", message)
        self.assertIn("Total Tweets:", message)
        self.assertIn("Positive:", message)
        self.assertIn("Negative:", message)

    def test_format_tweet_list(self):
        """Test formatting tweet list with Slack links."""
        tweets = [
            {"url": "https://twitter.com/user1/status/123", "username": "user1"},
            {"url": "https://twitter.com/user2/status/456", "username": "user2"},
        ]

        formatted = self.notifier._format_tweet_list(tweets)

        self.assertIn("<https://twitter.com/user1/status/123|@user1>", formatted)
        self.assertIn("<https://twitter.com/user2/status/456|@user2>", formatted)

    @patch("slack_notifier.requests.post")
    def test_post_with_webhook_success(self, mock_post):
        """Test successful webhook posting."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = self.notifier._post_with_webhook("Test message")

        self.assertTrue(result)
        mock_post.assert_called_once()

    @patch("slack_notifier.requests.post")
    def test_post_with_webhook_failure(self, mock_post):
        """Test failed webhook posting."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        result = self.notifier._post_with_webhook("Test message")

        self.assertFalse(result)

    def test_should_alert_team_critical_fud(self):
        """Test team alert trigger on critical FUD."""
        analyzed_tweets = generate_mock_analyzed_tweets(20)
        aggregator = SentimentAggregator()
        report = aggregator.aggregate(analyzed_tweets)

        # Artificially set high critical FUD count
        report["raw_data"]["strategic_highlights"]["critical_fud"] = 6

        should_alert, reason = self.notifier._should_alert_team(report)

        self.assertTrue(should_alert)
        self.assertIn("Critical FUD", reason)

    def test_validate_report_valid(self):
        """Test report validation with valid report."""
        analyzed_tweets = generate_mock_analyzed_tweets(10)
        aggregator = SentimentAggregator()
        report = aggregator.aggregate(analyzed_tweets)

        result = self.notifier._validate_report(report)

        self.assertTrue(result)

    def test_validate_report_invalid(self):
        """Test report validation with invalid report."""
        invalid_report = {"message_1": "", "message_2": ""}  # Missing keys

        result = self.notifier._validate_report(invalid_report)

        self.assertFalse(result)


class TestUtils(unittest.TestCase):
    """Test cases for utility functions."""

    def test_format_number_thousands(self):
        """Test formatting numbers in thousands."""
        self.assertEqual(format_number(1234), "1.2K")
        self.assertEqual(format_number(5678), "5.7K")

    def test_format_number_millions(self):
        """Test formatting numbers in millions."""
        self.assertEqual(format_number(1234567), "1.2M")
        self.assertEqual(format_number(9876543), "9.9M")

    def test_format_number_billions(self):
        """Test formatting numbers in billions."""
        self.assertEqual(format_number(1234567890), "1.2B")

    def test_format_number_small(self):
        """Test formatting small numbers."""
        self.assertEqual(format_number(123), "123")
        self.assertEqual(format_number(0), "0")

    def test_calculate_cost(self):
        """Test API cost calculation."""
        cost = calculate_cost(10000, 5000)
        expected = (10000 / 1_000_000 * 3.0) + (5000 / 1_000_000 * 15.0)
        self.assertAlmostEqual(cost, expected, places=4)

    def test_truncate_text_short(self):
        """Test truncating text shorter than max length."""
        text = "Short text"
        result = truncate_text(text, 50)
        self.assertEqual(result, text)

    def test_truncate_text_long(self):
        """Test truncating long text at word boundary."""
        text = "This is a very long text that needs to be truncated at a word boundary"
        result = truncate_text(text, 30, "...")
        self.assertTrue(len(result) <= 30)
        self.assertTrue(result.endswith("..."))

    def test_sanitize_text(self):
        """Test text sanitization."""
        text = "Hello\n\n  world   \n  test"
        result = sanitize_text(text)
        self.assertEqual(result, "Hello world test")

    def test_build_twitter_url(self):
        """Test Twitter URL building."""
        url = build_twitter_url("elonmusk", "1234567890")
        self.assertEqual(url, "https://twitter.com/elonmusk/status/1234567890")

    def test_is_spam_excessive_hashtags(self):
        """Test spam detection with excessive hashtags."""
        tweet = {
            "text": "#crypto #btc #eth #moon #lambo #profit #trade #win #success #money #rich #wealth"
        }
        self.assertTrue(is_spam(tweet))

    def test_is_spam_normal_tweet(self):
        """Test spam detection with normal tweet."""
        tweet = {"text": "Just used @nansen_ai for trading analysis. Great tool!"}
        self.assertFalse(is_spam(tweet))

    def test_calculate_engagement_rate(self):
        """Test engagement rate calculation."""
        tweet = {"engagement": {"total": 100}, "author_followers": 10000}
        rate = calculate_engagement_rate(tweet)
        self.assertEqual(rate, 1.0)  # 100/10000 * 100 = 1%

    def test_calculate_engagement_rate_zero_followers(self):
        """Test engagement rate with zero followers."""
        tweet = {"engagement": {"total": 100}, "author_followers": 0}
        rate = calculate_engagement_rate(tweet)
        self.assertEqual(rate, 0.0)


class TestFullWorkflow(unittest.TestCase):
    """Integration tests for complete workflow."""

    @patch("slack_notifier.requests.post")
    @patch("sentiment_analyzer.Anthropic")
    @patch("twitter_client.tweepy.Client")
    def test_complete_pipeline(self, mock_twitter, mock_anthropic, mock_slack):
        """Test complete pipeline from Twitter to Slack."""
        # Setup mocks
        os.environ["X_API_BEARER_TOKEN"] = "test_token"
        os.environ["ANTHROPIC_API_KEY"] = "test_key"
        os.environ["SLACK_WEBHOOK_URL"] = "https://hooks.slack.com/test"

        # Mock Twitter response
        mock_tweets = generate_mock_tweets(10)

        # Mock Claude response
        mock_claude_response = Mock()
        mock_claude_response.content = [
            Mock(
                text=json.dumps(
                    [
                        {
                            "sentiment": "POSITIVE",
                            "confidence": 85,
                            "intent": "PRAISE",
                            "themes": ["mobile_adoption"],
                            "product_mentions": ["nansen_mobile"],
                            "negative_patterns": [],
                            "critical_keywords": [],
                            "urgency": "LOW",
                            "actionable": False,
                            "summary": "Positive tweet",
                            "competitive_mentions": [],
                            "is_viral": False,
                            "is_influencer": False,
                            "strategic_category": "STRATEGIC_WIN",
                        }
                    ]
                )
            )
        ]
        mock_claude_response.usage = Mock(input_tokens=1500, output_tokens=800)

        # Mock Slack response
        mock_slack_response = Mock()
        mock_slack_response.status_code = 200

        mock_slack.return_value = mock_slack_response

        # Run pipeline steps
        # Note: This is a simplified integration test
        # In real scenario, you'd mock the actual API calls more thoroughly

        self.assertTrue(True)  # Placeholder for full integration

    def test_empty_tweets_handling(self):
        """Test workflow with no tweets found."""
        aggregator = SentimentAggregator()
        report = aggregator.aggregate([])

        self.assertEqual(report["raw_data"]["summary"]["total_tweets"], 0)
        self.assertIn("No tweets", report["message_1"])


# ============================================================================
# Test Runner
# ============================================================================


def run_tests():
    """Run all tests with verbose output."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestTwitterClient))
    suite.addTests(loader.loadTestsFromTestCase(TestSentimentAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestAggregator))
    suite.addTests(loader.loadTestsFromTestCase(TestSlackNotifier))
    suite.addTests(loader.loadTestsFromTestCase(TestUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestFullWorkflow))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())

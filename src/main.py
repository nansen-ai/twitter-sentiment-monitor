"""Main application entry point for Twitter Sentiment Monitor."""

import logging
import time
import sys
from pathlib import Path
from typing import Optional

from config_loader import ConfigLoader
from twitter_client import TwitterClient
from sentiment_analyzer import SentimentAnalyzer
from alert_manager import AlertManager


def setup_logging(log_level: str, log_file: str) -> None:
    """
    Configure application logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Path to log file
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Set up handlers
    handlers = [logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)]

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
    )


class SentimentMonitor:
    """Main sentiment monitoring application."""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize sentiment monitor.

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = ConfigLoader(config_path)

        # Setup logging
        setup_logging(self.config.get_log_level(), self.config.get_log_file())
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Sentiment Monitor")

        # Initialize components
        self.twitter_client = TwitterClient(self.config.twitter_bearer_token)
        self.sentiment_analyzer = SentimentAnalyzer(self.config.anthropic_api_key)
        self.alert_manager = AlertManager(
            self.config.slack_webhook_url, self.config.get_alert_config()
        )

        self.last_tweet_id: Optional[str] = None
        self.running = False

    def run(self) -> None:
        """Start the sentiment monitoring loop."""
        self.logger.info("Starting sentiment monitor")
        self.running = True

        polling_interval = self.config.get_polling_interval()
        keywords = self.config.get_keywords()
        accounts = self.config.get_accounts()

        if not keywords and not accounts:
            self.logger.error("No keywords or accounts configured for monitoring")
            return

        self.logger.info(f"Monitoring keywords: {keywords}")
        self.logger.info(f"Monitoring accounts: {accounts}")
        self.logger.info(f"Polling interval: {polling_interval} seconds")

        try:
            while self.running:
                self._monitoring_cycle(keywords, accounts)
                self.logger.info(f"Sleeping for {polling_interval} seconds")
                time.sleep(polling_interval)

        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, shutting down")
            self.stop()
        except Exception as e:
            self.logger.error(
                f"Unexpected error in monitoring loop: {e}", exc_info=True
            )
            self.stop()

    def _monitoring_cycle(self, keywords: list, accounts: list) -> None:
        """Execute one monitoring cycle."""
        self.logger.info("Starting monitoring cycle")

        # Fetch tweets
        tweets = self._fetch_tweets(keywords, accounts)

        if not tweets:
            self.logger.info("No new tweets found")
            return

        # Analyze sentiment
        sentiment_results = self.sentiment_analyzer.analyze_batch(tweets)

        # Get aggregate metrics
        aggregate = self.sentiment_analyzer.get_aggregate_sentiment(sentiment_results)

        # Check for alerts
        self.alert_manager.check_and_send_alerts(sentiment_results, aggregate)

        # Update last tweet ID for next cycle
        if tweets:
            self.last_tweet_id = str(max(int(t["id"]) for t in tweets))
            self.logger.info(f"Updated last_tweet_id to {self.last_tweet_id}")

    def _fetch_tweets(self, keywords: list, accounts: list) -> list:
        """Fetch tweets from Twitter."""
        all_tweets = []

        # Search by keywords and accounts
        if keywords or accounts:
            query = self.twitter_client.build_search_query(keywords, accounts)
            tweets = self.twitter_client.search_recent_tweets(
                query=query, max_results=100, since_id=self.last_tweet_id
            )
            all_tweets.extend(tweets)

        self.logger.info(f"Fetched {len(all_tweets)} total tweets")
        return all_tweets

    def stop(self) -> None:
        """Stop the sentiment monitor."""
        self.logger.info("Stopping sentiment monitor")
        self.running = False


def main():
    """Main entry point."""
    try:
        monitor = SentimentMonitor()
        monitor.run()
    except Exception as e:
        logging.error(f"Failed to start sentiment monitor: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

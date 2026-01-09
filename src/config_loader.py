"""Configuration loader for sentiment monitor."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv


class ConfigLoader:
    """Loads and manages configuration from YAML and environment variables."""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize the configuration loader.

        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = Path(config_path)
        load_dotenv()
        self.config = self._load_yaml_config()
        self._validate_config()

    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def _validate_config(self) -> None:
        """Validate required configuration parameters."""
        required_env_vars = [
            "TWITTER_BEARER_TOKEN",
            "ANTHROPIC_API_KEY",
        ]

        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def get_twitter_config(self) -> Dict[str, Any]:
        """Get Twitter monitoring configuration."""
        return self.config.get("twitter", {})

    def get_sentiment_config(self) -> Dict[str, Any]:
        """Get sentiment analysis configuration."""
        return self.config.get("sentiment", {})

    def get_alert_config(self) -> Dict[str, Any]:
        """Get alert configuration."""
        return self.config.get("alerts", {})

    def get_keywords(self) -> List[str]:
        """Get list of keywords to monitor."""
        return self.config.get("twitter", {}).get("keywords", [])

    def get_accounts(self) -> List[str]:
        """Get list of accounts to monitor."""
        return self.config.get("twitter", {}).get("accounts", [])

    def get_polling_interval(self) -> int:
        """Get polling interval in seconds."""
        return int(os.getenv("POLLING_INTERVAL", 300))

    def get_log_level(self) -> str:
        """Get logging level."""
        return os.getenv("LOG_LEVEL", "INFO")

    def get_log_file(self) -> str:
        """Get log file path."""
        return os.getenv("LOG_FILE", "logs/sentiment_monitor.log")

    @property
    def twitter_bearer_token(self) -> str:
        """Get Twitter bearer token."""
        return os.getenv("TWITTER_BEARER_TOKEN", "")

    @property
    def anthropic_api_key(self) -> str:
        """Get Anthropic API key."""
        return os.getenv("ANTHROPIC_API_KEY", "")

    @property
    def slack_webhook_url(self) -> str:
        """Get Slack webhook URL."""
        return os.getenv("SLACK_WEBHOOK_URL", "")

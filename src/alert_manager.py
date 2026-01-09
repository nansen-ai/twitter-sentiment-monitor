"""Alert manager for sending notifications."""

import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from slack_sdk.webhook import WebhookClient


logger = logging.getLogger(__name__)


class AlertManager:
    """Manages alerts and notifications for sentiment changes."""

    def __init__(self, slack_webhook_url: Optional[str] = None, alert_config: Optional[Dict[str, Any]] = None):
        """
        Initialize alert manager.

        Args:
            slack_webhook_url: Slack webhook URL for sending alerts
            alert_config: Configuration for alert thresholds and behavior
        """
        self.slack_webhook_url = slack_webhook_url
        self.slack_client = WebhookClient(slack_webhook_url) if slack_webhook_url else None
        self.alert_config = alert_config or {}
        self.alert_history: List[Dict[str, Any]] = []
        logger.info("Alert manager initialized")

    def check_and_send_alerts(
        self,
        sentiment_results: List[Dict[str, Any]],
        aggregate: Dict[str, Any]
    ) -> None:
        """
        Check sentiment results and send alerts if thresholds are met.

        Args:
            sentiment_results: List of individual sentiment analysis results
            aggregate: Aggregate sentiment metrics
        """
        alerts = []

        # Check average score threshold
        avg_threshold = self.alert_config.get("average_score_threshold", 0.5)
        if abs(aggregate["average_score"]) >= avg_threshold:
            alerts.append(self._create_aggregate_alert(aggregate))

        # Check for highly negative tweets
        negative_threshold = self.alert_config.get("negative_score_threshold", -0.7)
        for result in sentiment_results:
            if result.get("score", 0) <= negative_threshold and result.get("confidence", 0) >= 0.7:
                alerts.append(self._create_tweet_alert(result, "negative"))

        # Check for highly positive tweets
        positive_threshold = self.alert_config.get("positive_score_threshold", 0.7)
        for result in sentiment_results:
            if result.get("score", 0) >= positive_threshold and result.get("confidence", 0) >= 0.7:
                alerts.append(self._create_tweet_alert(result, "positive"))

        # Send alerts
        for alert in alerts:
            self.send_alert(alert)

    def send_alert(self, alert: Dict[str, Any]) -> bool:
        """
        Send an alert via configured channels.

        Args:
            alert: Alert dictionary with type, message, and data

        Returns:
            True if alert was sent successfully
        """
        logger.info(f"Sending alert: {alert['type']}")

        # Log alert
        self.alert_history.append({
            **alert,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Send to Slack if configured
        if self.slack_client:
            return self._send_slack_alert(alert)

        logger.warning("No alert channels configured")
        return False

    def _send_slack_alert(self, alert: Dict[str, Any]) -> bool:
        """Send alert to Slack."""
        try:
            message = self._format_slack_message(alert)
            response = self.slack_client.send(
                text=alert["message"],
                blocks=message
            )

            if response.status_code == 200:
                logger.info("Slack alert sent successfully")
                return True
            else:
                logger.error(f"Failed to send Slack alert: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")
            return False

    def _format_slack_message(self, alert: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format alert as Slack blocks."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Sentiment Alert: {alert['type'].upper()}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": alert["message"]
                }
            }
        ]

        # Add data fields
        if alert.get("data"):
            fields = []
            for key, value in alert["data"].items():
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*{key}:*\n{value}"
                })

            if fields:
                blocks.append({
                    "type": "section",
                    "fields": fields
                })

        # Add divider
        blocks.append({"type": "divider"})

        return blocks

    def _create_aggregate_alert(self, aggregate: Dict[str, Any]) -> Dict[str, Any]:
        """Create alert for aggregate sentiment."""
        sentiment = "positive" if aggregate["average_score"] > 0 else "negative"
        emoji = "📈" if sentiment == "positive" else "📉"

        return {
            "type": "aggregate_sentiment",
            "message": (
                f"{emoji} Significant {sentiment} sentiment detected\n"
                f"Average score: {aggregate['average_score']:.2f}"
            ),
            "data": {
                "Total Tweets": aggregate["total_count"],
                "Positive": aggregate["positive_count"],
                "Negative": aggregate["negative_count"],
                "Neutral": aggregate["neutral_count"],
                "Avg Score": f"{aggregate['average_score']:.2f}",
            }
        }

    def _create_tweet_alert(self, result: Dict[str, Any], alert_type: str) -> Dict[str, Any]:
        """Create alert for individual tweet."""
        emoji = "🔥" if alert_type == "positive" else "⚠️"

        return {
            "type": f"high_{alert_type}_tweet",
            "message": (
                f"{emoji} Highly {alert_type} tweet detected\n"
                f"*Author:* @{result['author']}\n"
                f"*Tweet:* {result['tweet_text'][:200]}..."
            ),
            "data": {
                "Score": f"{result['score']:.2f}",
                "Confidence": f"{result['confidence']:.2f}",
                "Sentiment": result["sentiment"],
                "Tweet ID": result["tweet_id"],
            }
        }

    def get_alert_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent alert history.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of recent alerts
        """
        return self.alert_history[-limit:]

    def clear_alert_history(self) -> None:
        """Clear alert history."""
        self.alert_history = []
        logger.info("Alert history cleared")

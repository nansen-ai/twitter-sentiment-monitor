"""Slack notification system for sentiment reports with threading and rich formatting."""

import os
import json
import logging
import time
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


# Configure logging
logger = logging.getLogger(__name__)

# Constants
MAX_MESSAGE_LENGTH = 40000
MAX_RETRIES = 3
RETRY_BACKOFF = [1, 2, 4]

EMOJI_MAP = {
    "positive": "💚",
    "negative": "❌",
    "neutral": "⚪",
    "improving": "↗️",
    "stable": "→",
    "declining": "↘️",
}


class SlackNotifier:
    """Sends comprehensive sentiment reports to Slack with threading and rich formatting."""

    def __init__(self):
        """
        Initialize Slack notifier with credentials from environment.

        Supports both webhook URL and bot token authentication methods.

        Environment Variables:
            SLACK_WEBHOOK_URL: Slack incoming webhook URL (method 1)
            SLACK_BOT_TOKEN: Slack bot token (method 2)
            SLACK_CHANNEL_ID: Channel ID for bot token method
            SLACK_MENTION_USER_ID: User ID to mention for critical alerts
        """
        self.method, self.client = self._initialize_client()
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.channel_id = os.getenv("SLACK_CHANNEL_ID")
        self.mention_user_id = os.getenv("SLACK_MENTION_USER_ID")

        logger.info(f"SlackNotifier initialized with method: {self.method}")

    def _initialize_client(self) -> Tuple[str, Optional[WebClient]]:
        """
        Initialize Slack client based on available credentials.

        Returns:
            Tuple of (method, client) where method is "webhook" or "bot"
        """
        # Check for webhook URL
        if os.getenv("SLACK_WEBHOOK_URL"):
            logger.info("Using Slack Webhook URL for notifications")
            return ("webhook", None)

        # Check for bot token
        bot_token = os.getenv("SLACK_BOT_TOKEN")
        if bot_token:
            logger.info("Using Slack Bot Token for notifications")
            client = WebClient(token=bot_token)
            return ("bot", client)

        logger.warning("No Slack credentials found. Notifications will be disabled.")
        return ("none", None)

    def send_report(self, report: Dict) -> bool:
        """
        Send complete sentiment report to Slack with threading.

        Posts message_1 (summary) as main message, then message_2 (detailed analysis)
        as a threaded reply. Handles conditional alerts for critical issues.

        Args:
            report: Report dictionary from SentimentAggregator

        Returns:
            True if successfully sent, False otherwise

        Example:
            >>> notifier = SlackNotifier()
            >>> success = notifier.send_report(report)
            >>> if success:
            ...     print("Report sent to Slack!")
        """
        if self.method == "none":
            logger.warning("No Slack credentials configured. Skipping notification.")
            return False

        # Validate report
        if not self._validate_report(report):
            logger.error("Report validation failed. Cannot send to Slack.")
            return False

        try:
            # Format messages
            message_1 = self._format_message_1(report)
            message_2 = self._format_message_2(report)

            logger.info(
                f"Sending report to Slack (Message 1: {len(message_1)} chars, Message 2: {len(message_2)} chars)"
            )

            # Check for urgent alerts
            should_alert, alert_reason = self._should_alert_team(report)
            if should_alert and self.mention_user_id:
                message_1 = self._add_team_mention(message_1, alert_reason)

            # Post messages with threading
            success = self._post_threaded_messages(message_1, message_2)

            if success:
                logger.info("✓ Report successfully sent to Slack")
            else:
                logger.error("✗ Failed to send report to Slack")

            return success

        except Exception as e:
            logger.error(f"Error sending report to Slack: {e}", exc_info=True)
            return False

    def send_empty_report(self, hours: int) -> bool:
        """
        Send notification when no tweets are found.

        Args:
            hours: Number of hours that were searched

        Returns:
            True if sent successfully
        """
        message = f"""📊 Nansen Daily Sentiment Report
━━━━━━━━━━
📅 {datetime.utcnow().strftime('%b %d, %Y')}

ℹ️ No tweets found in the last {hours} hours matching search criteria.

This could mean:
• Low mention volume during this period
• All tweets filtered out (retweets, spam, etc.)
• API rate limits or connectivity issues

Report will resume when new tweets are detected."""

        try:
            if self.method == "webhook":
                return self._post_with_webhook(message)
            elif self.method == "bot":
                result = self._post_with_bot(message)
                return result is not None
            return False

        except Exception as e:
            logger.error(f"Error sending empty report: {e}")
            return False

    def send_error_notification(self, error: str) -> bool:
        """
        Send simple error notification to Slack.

        Args:
            error: Error message to send

        Returns:
            True if sent successfully
        """
        message = f"""🚨 Nansen Sentiment Monitor Error
━━━━━━━━━━
⚠️ An error occurred during sentiment analysis:

```
{error}
```

Timestamp: {datetime.utcnow().isoformat()}

Please check logs for more details."""

        try:
            if self.method == "webhook":
                return self._post_with_webhook(message)
            elif self.method == "bot":
                result = self._post_with_bot(message)
                return result is not None
            return False

        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
            return False

    def _format_message_1(self, report: Dict) -> str:
        """
        Format summary message (Message 1).

        Args:
            report: Report dictionary

        Returns:
            Formatted Slack message
        """
        summary = report["raw_data"]["summary"]
        metadata = report["metadata"]
        strategic = report["raw_data"]["strategic_highlights"]

        total = summary["total_tweets"]
        pos_count = summary["positive_count"]
        neg_count = summary["negative_count"]
        pos_pct = summary["positive_pct"]
        neg_pct = summary["negative_pct"]
        score = summary["sentiment_score"]

        # Determine trend emoji
        if score >= 60:
            trend_emoji = EMOJI_MAP["improving"]
        elif score >= 40:
            trend_emoji = EMOJI_MAP["stable"]
        else:
            trend_emoji = EMOJI_MAP["declining"]

        message = f"""📊 Nansen Daily Sentiment Report
━━━━━━━━━━
📅 {metadata['date_range']}
Total Tweets: {total}
💚 Positive: {pos_count} ({pos_pct:.0f}%)
❌ Negative: {neg_count} ({neg_pct:.0f}%)

Overall Sentiment: {score:.0f}/100 {trend_emoji}"""

        # Add conditional urgent alert
        critical_fud = strategic.get("critical_fud", 0)
        affiliate_violations = strategic.get("affiliate_violations", 0)

        if critical_fud > 5 or affiliate_violations > 0:
            alert_count = critical_fud + affiliate_violations
            message += (
                f"\n\n⚠️ {alert_count} critical issues detected - see thread for details"
            )

        return message

    def _format_message_2(self, report: Dict) -> str:
        """
        Format detailed analysis message (Message 2).

        Args:
            report: Report dictionary

        Returns:
            Formatted Slack message with all sections
        """
        raw_data = report["raw_data"]
        metadata = report["metadata"]

        sections = []

        # Section 1: Product Mentions
        sections.append("📱 KEY PRODUCT MENTIONS")
        sections.append("━━━━━━━━━━━━━━━━━━━━")
        product_mentions = raw_data["product_mentions"]
        sections.append(
            f"• Nansen Mobile: {product_mentions.get('nansen_mobile', 0)} tweets"
        )
        sections.append(
            f"• Season 2 / Rewards: {product_mentions.get('season2_rewards', 0)} tweets"
        )
        sections.append(
            f"• Nansen Trading: {product_mentions.get('nansen_trading', 0)} tweets"
        )
        sections.append(
            f"• AI Insights: {product_mentions.get('ai_insights', 0)} tweets"
        )
        sections.append(
            f"• Nansen Points: {product_mentions.get('nansen_points', 0)} tweets"
        )
        sections.append("")

        # Section 2: Positive Sentiments
        sections.append("━━━━━━━━━━━━━━━━━━━━")
        sections.append("✅ TLDR POSITIVE SENTIMENTS")
        positive_themes = self._format_positive_themes(
            raw_data.get("positive_themes", [])
        )
        sections.append(positive_themes)
        sections.append("")

        # Section 3: Negative Sentiments
        sections.append("━━━━━━━━━━━━━━━━━━━━")
        sections.append("⚠️ TLDR NEGATIVE SENTIMENTS")
        negative_themes = self._format_negative_themes(
            raw_data.get("negative_themes", [])
        )
        sections.append(negative_themes)
        sections.append("")

        # Section 4: Strategic Highlights
        strategic = raw_data["strategic_highlights"]
        if any(strategic.values()):
            sections.append("━━━━━━━━━━━━━━━━━━━━")
            sections.append("🎯 STRATEGIC HIGHLIGHTS")
            sections.append(f"• {strategic.get('strategic_wins', 0)} Strategic Wins 🎉")
            sections.append(
                f"• {strategic.get('adoption_signals', 0)} Adoption Signals 📈"
            )
            sections.append(
                f"• {strategic.get('influencer_mentions', 0)} Influencer Mentions 👤"
            )

            if strategic.get("critical_fud", 0) > 0:
                sections.append(f"• ⚠️ {strategic['critical_fud']} Critical FUD alerts")
            if strategic.get("affiliate_violations", 0) > 0:
                sections.append(
                    f"• 🚨 {strategic['affiliate_violations']} Affiliate Violations"
                )

            sections.append("")

        # Section 5: Full Positive Tweet List
        sections.append("━━━━━━━━━━━━━━━━━━━━")
        positive_tweets = raw_data.get("all_positive_tweets", [])
        sections.append(f"✅ Positive tweets (Total: {len(positive_tweets)})")
        if positive_tweets:
            sections.append(self._format_tweet_list(positive_tweets))
        else:
            sections.append("None")
        sections.append("")

        # Section 6: Full Negative Tweet List
        sections.append("━━━━━━━━━━━━━━━━━━━━")
        negative_tweets = raw_data.get("all_negative_tweets", [])
        sections.append(f"⚠️ Negative tweets (Total: {len(negative_tweets)})")
        if negative_tweets:
            sections.append(self._format_tweet_list(negative_tweets))
        else:
            sections.append("None")
        sections.append("")

        # Section 7: Negative Phrase Analysis
        sections.append("━━━━━━━━━━━━━━━━━━━━")
        sections.append("🚨 NEGATIVE PHRASE ANALYSIS")
        phrase_analysis = self._format_negative_phrase_analysis(
            raw_data.get("negative_phrase_analysis", [])
        )
        sections.append(phrase_analysis)
        sections.append("")

        # Footer
        sections.append("━━━━━━━━━━━━━━━━━━━━")
        timestamp = datetime.fromisoformat(metadata["generated_at"]).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
        cost = metadata.get("total_api_cost", 0.0)
        sections.append(f"📊 Generated at {timestamp} | Cost: ${cost:.4f}")

        message = "\n".join(sections)

        # Truncate if too long
        if len(message) > MAX_MESSAGE_LENGTH:
            logger.warning(
                f"Message 2 exceeds max length ({len(message)} chars), truncating..."
            )
            message = (
                message[: MAX_MESSAGE_LENGTH - 100] + "\n\n... (truncated for length)"
            )

        return message

    def _format_positive_themes(self, themes: List[Dict]) -> str:
        """
        Format positive themes section.

        Args:
            themes: List of positive theme dictionaries

        Returns:
            Formatted string
        """
        if not themes:
            return "No significant positive sentiments this period."

        lines = []
        for theme_data in themes:
            description = theme_data["description"]
            examples = theme_data.get("example_tweets", [])

            # Format examples
            example_links = []
            for ex in examples[:3]:  # Limit to 3 examples
                url = ex["url"]
                username = ex["username"]
                example_links.append(f"<{url}|@{username}>")

            examples_str = " ".join(example_links) if example_links else "No examples"
            lines.append(f"• {description}")
            lines.append(f"  Examples: {examples_str}")

        return "\n".join(lines)

    def _format_negative_themes(self, themes: List[Dict]) -> str:
        """
        Format negative themes section.

        Args:
            themes: List of negative theme dictionaries

        Returns:
            Formatted string
        """
        if not themes:
            return "No significant negative sentiments this period."

        lines = []
        for theme_data in themes:
            description = theme_data["description"]
            urgency = theme_data.get("urgency", "LOW")
            examples = theme_data.get("example_tweets", [])

            # Add urgency indicator
            urgency_emoji = (
                "🚨" if urgency == "HIGH" else "⚠️" if urgency == "MEDIUM" else "ℹ️"
            )

            # Format examples
            example_links = []
            for ex in examples[:3]:
                url = ex["url"]
                username = ex["username"]
                example_links.append(f"<{url}|@{username}>")

            examples_str = " ".join(example_links) if example_links else "No examples"
            lines.append(f"• {urgency_emoji} {description}")
            lines.append(f"  Examples: {examples_str}")

        return "\n".join(lines)

    def _format_tweet_list(self, tweets: List[Dict]) -> str:
        """
        Format list of tweets with Slack-style links.

        Args:
            tweets: List of tweet dictionaries

        Returns:
            Formatted string with all tweets
        """
        lines = []
        for tweet in tweets:
            url = tweet["url"]
            username = tweet["username"]
            lines.append(f"• <{url}|@{username}>")

        return "\n".join(lines)

    def _format_negative_phrase_analysis(self, phrases: List[Dict]) -> str:
        """
        Format negative phrase analysis section.

        Args:
            phrases: List of phrase dictionaries

        Returns:
            Formatted string
        """
        if not phrases:
            return "No qualifying negative phrases detected in this period."

        lines = []
        for item in phrases:
            phrase = item["phrase"]
            username = item["username"]
            category = item["category"]
            url = item["url"]

            lines.append(f'• Phrase: "{phrase}"')
            lines.append(f"  Handle: @{username}")
            lines.append(f"  Theme: {category}")
            lines.append(f"  URL: <{url}|@{username}>")
            lines.append("")

        return "\n".join(lines)

    def _post_threaded_messages(self, message_1: str, message_2: str) -> bool:
        """
        Post main message and threaded reply.

        Args:
            message_1: Summary message (main post)
            message_2: Detailed analysis (threaded reply)

        Returns:
            True if both messages posted successfully
        """
        try:
            if self.method == "webhook":
                # Webhooks don't support threading, post separately
                logger.info(
                    "Webhook doesn't support threading, posting messages separately"
                )
                result_1 = self._post_with_webhook(message_1)
                time.sleep(1)  # Small delay between messages
                result_2 = self._post_with_webhook(message_2)
                return result_1 and result_2

            elif self.method == "bot":
                # Post main message
                logger.info("Posting main message...")
                result_1 = self._post_with_bot(message_1)

                if not result_1:
                    logger.error("Failed to post main message")
                    return False

                # Get thread timestamp
                thread_ts = result_1.get("ts")
                logger.info(f"Main message posted with ts: {thread_ts}")

                # Small delay before threaded reply
                time.sleep(0.5)

                # Post threaded reply
                logger.info("Posting threaded reply...")
                result_2 = self._post_with_bot(message_2, thread_ts=thread_ts)

                if not result_2:
                    logger.error("Failed to post threaded reply")
                    return False

                thread_url = f"https://slack.com/archives/{self.channel_id}/p{thread_ts.replace('.', '')}"
                logger.info(f"✓ Messages posted successfully. Thread: {thread_url}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error posting threaded messages: {e}")
            # Fallback: Try posting separately
            logger.info("Attempting fallback: posting messages separately")
            try:
                (
                    self._post_with_webhook(message_1)
                    if self.method == "webhook"
                    else self._post_with_bot(message_1)
                )
                time.sleep(1)
                (
                    self._post_with_webhook(message_2)
                    if self.method == "webhook"
                    else self._post_with_bot(message_2)
                )
                return True
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                return False

    def _post_with_webhook(self, message: str) -> bool:
        """
        Post message using webhook URL with retry logic.

        Args:
            message: Message text to post

        Returns:
            True if posted successfully
        """
        if not self.webhook_url:
            logger.error("No webhook URL configured")
            return False

        payload = {"text": message}

        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(self.webhook_url, json=payload, timeout=10)

                if response.status_code == 200:
                    logger.debug(f"Webhook post successful (attempt {attempt + 1})")
                    return True
                elif response.status_code == 429:
                    # Rate limited
                    retry_after = int(
                        response.headers.get("Retry-After", RETRY_BACKOFF[attempt])
                    )
                    logger.warning(f"Rate limited. Retrying after {retry_after}s...")
                    time.sleep(retry_after)
                else:
                    logger.error(
                        f"Webhook post failed: {response.status_code} - {response.text}"
                    )
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_BACKOFF[attempt])
                    else:
                        return False

            except requests.RequestException as e:
                logger.error(
                    f"Network error posting to webhook (attempt {attempt + 1}): {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BACKOFF[attempt])
                else:
                    return False

        return False

    def _post_with_bot(
        self, message: str, thread_ts: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Post message using bot token with retry logic.

        Args:
            message: Message text to post
            thread_ts: Thread timestamp for threaded replies

        Returns:
            Response dictionary if successful, None otherwise
        """
        if not self.client or not self.channel_id:
            logger.error("Bot client or channel ID not configured")
            return None

        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.chat_postMessage(
                    channel=self.channel_id,
                    text=message,
                    thread_ts=thread_ts,
                    unfurl_links=False,
                    unfurl_media=False,
                )

                if response["ok"]:
                    logger.debug(f"Bot post successful (attempt {attempt + 1})")
                    return response
                else:
                    logger.error(f"Bot post failed: {response.get('error')}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_BACKOFF[attempt])
                    else:
                        return None

            except SlackApiError as e:
                error_code = e.response["error"]

                if error_code == "ratelimited":
                    retry_after = int(
                        e.response.headers.get("Retry-After", RETRY_BACKOFF[attempt])
                    )
                    logger.warning(f"Rate limited. Retrying after {retry_after}s...")
                    time.sleep(retry_after)
                else:
                    logger.error(
                        f"Slack API error (attempt {attempt + 1}): {error_code}"
                    )
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_BACKOFF[attempt])
                    else:
                        return None

            except Exception as e:
                logger.error(
                    f"Unexpected error posting with bot (attempt {attempt + 1}): {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BACKOFF[attempt])
                else:
                    return None

        return None

    def _should_alert_team(self, report: Dict) -> Tuple[bool, str]:
        """
        Determine if team should be alerted about critical issues.

        Args:
            report: Report dictionary

        Returns:
            Tuple of (should_alert, reason)
        """
        strategic = report["raw_data"]["strategic_highlights"]
        negative_tweets = report["raw_data"].get("all_negative_tweets", [])

        # Check critical FUD count
        critical_fud = strategic.get("critical_fud", 0)
        if critical_fud > 5:
            return (True, f"{critical_fud} Critical FUD alerts detected")

        # Check affiliate violations
        affiliate_violations = strategic.get("affiliate_violations", 0)
        if affiliate_violations > 0:
            return (True, f"{affiliate_violations} Affiliate violations found")

        # Check for scam accusations from influencers
        for tweet in negative_tweets:
            themes = tweet.get("themes", [])
            if "scam_accusations" in themes:
                # Check original tweet data for influencer status
                # This would need to be passed through in the raw_data structure
                return (True, "Scam accusations detected")

        # Check for viral negative tweets (high engagement)
        for tweet in negative_tweets:
            if tweet.get("engagement", 0) > 100:
                return (True, "Viral negative tweet detected")

        return (False, "")

    def _add_team_mention(self, message: str, reason: str) -> str:
        """
        Add team mention to message for critical alerts.

        Args:
            message: Original message
            reason: Reason for alert

        Returns:
            Message with team mention
        """
        mention = f"\n\n⚠️ <@{self.mention_user_id}> Urgent: {reason}"
        return message + mention

    def _validate_report(self, report: Dict) -> bool:
        """
        Validate report structure before sending.

        Args:
            report: Report dictionary

        Returns:
            True if valid
        """
        required_keys = ["message_1", "message_2", "raw_data", "metadata"]

        for key in required_keys:
            if key not in report:
                logger.error(f"Missing required key in report: {key}")
                return False

        # Check messages are non-empty
        if not report["message_1"] or not report["message_2"]:
            logger.error("Empty messages in report")
            return False

        # Check raw_data structure
        if "summary" not in report["raw_data"]:
            logger.error("Missing summary in raw_data")
            return False

        return True

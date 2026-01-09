"""Comprehensive sentiment data aggregation and report generation for Nansen."""

import json
import logging
import time
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from pathlib import Path


# Configure logging
logger = logging.getLogger(__name__)

# Theme descriptions for natural language
THEME_DESCRIPTIONS = {
    # Positive
    "mobile_as_future": "Users highlighting mobile app as revolutionary for crypto trading",
    "mobile_adoption": "New users downloading and onboarding to Nansen Mobile",
    "competitive_advantage": "Comparing Nansen favorably against competitors",
    "season2_engagement": "High engagement with Season 2 points and rewards",
    "roi_confirmation": "Users confirming profitable trades and platform value",
    "trading_execution_praise": "Positive feedback on execution quality and speed",
    "ai_insights_praise": "Praise for AI signal accuracy and helpfulness",
    "points_earning_success": "Successfully earning points through staking and trading",
    "seamless_experience": "Easy onboarding and smooth user experience",
    "trust_security": "Platform reliability and security praise",
    "mobile_app_praise": "Positive feedback on mobile app UX and performance",
    # Negative
    "airdrop_expectations": "Speculation about Nansen token or airdrop farming",
    "scam_accusations": "Fraud, scam, or rugpull accusations",
    "execution_failures": "Complaints about slippage, bad fills, or execution quality",
    "subscription_revolt": "Cancellations or pricing complaints",
    "fee_complaints": "Concerns about high or hidden fees",
    "guaranteed_returns_claims": "Affiliate violation: Users claiming guaranteed profits",
    "financial_advice_claims": "Affiliate violation: Financial advice or trade recommendations",
    "platform_failures": "Technical issues, downtime, or login problems",
    "ai_signal_failures": "Inaccurate or contradictory AI recommendations",
    "mobile_app_bugs": "Crashes and technical issues with mobile app",
    "season2_complaints": "Issues with Season 2 points system",
    "points_earning_issues": "Problems with staking or trading rewards",
    "competitive_disadvantage": "Comparisons showing Nansen worse than alternatives",
    "speed_price_guarantees": "Affiliate violation: Unrealistic execution claims",
}

# Theme to category mapping for negative phrase analysis
THEME_CATEGORY_MAPPING = {
    "airdrop_expectations": "[AIRDROP]",
    "scam_accusations": "[SCAM]",
    "rugpull": "[SCAM]",
    "execution_failures": "[EXECUTION]",
    "slippage": "[EXECUTION]",
    "front_running": "[EXECUTION]",
    "subscription_revolt": "[SUBSCRIPTIONS]",
    "too_expensive": "[SUBSCRIPTIONS]",
    "ai_signal_failures": "[AI-INSIGHTS]",
    "platform_failures": "[PLATFORM]",
    "fee_complaints": "[FEES]",
    "guaranteed_returns_claims": "[AFFILIATE-VIOLATION]",
    "financial_advice_claims": "[AFFILIATE-VIOLATION]",
    "speed_price_guarantees": "[AFFILIATE-VIOLATION]",
    "mobile_app_bugs": "[MOBILE]",
    "season2_complaints": "[SEASON2]",
    "points_earning_issues": "[POINTS]",
}


class SentimentAggregator:
    """Aggregates sentiment analysis results and generates comprehensive reports."""

    def __init__(self):
        """Initialize sentiment aggregator."""
        self.reports_dir = Path("logs")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        logger.info("SentimentAggregator initialized")

    def aggregate(self, analyzed_tweets: List[Dict]) -> Dict:
        """
        Aggregate analyzed tweets and generate comprehensive report.

        Args:
            analyzed_tweets: List of analyzed tweet dictionaries from SentimentAnalyzer

        Returns:
            Dictionary with message_1 (summary), message_2 (detailed), raw_data, and metadata

        Example:
            >>> aggregator = SentimentAggregator()
            >>> report = aggregator.aggregate(analyzed_tweets)
            >>> print(report['message_1'])  # Summary statistics
            >>> print(report['message_2'])  # Detailed analysis
        """
        start_time = time.time()
        logger.info(f"Starting aggregation of {len(analyzed_tweets)} tweets")

        if not analyzed_tweets:
            logger.warning("No tweets to analyze")
            return self._generate_empty_report()

        # Calculate summary statistics
        total_tweets = len(analyzed_tweets)
        positive_tweets = [
            t for t in analyzed_tweets if t["analysis"]["sentiment"] != "NEGATIVE"
        ]
        negative_tweets = [
            t for t in analyzed_tweets if t["analysis"]["sentiment"] == "NEGATIVE"
        ]

        positive_count = len(positive_tweets)
        negative_count = len(negative_tweets)
        positive_pct = (positive_count / total_tweets * 100) if total_tweets > 0 else 0
        negative_pct = (negative_count / total_tweets * 100) if total_tweets > 0 else 0

        logger.info(
            f"Found {positive_count} positive, {negative_count} negative tweets"
        )

        # Validate counts
        if not self._validate_tweet_counts(
            positive_count, negative_count, total_tweets
        ):
            logger.error(
                f"Tweet count mismatch! Positive: {positive_count}, Negative: {negative_count}, Total: {total_tweets}"
            )

        # Calculate sentiment score
        sentiment_score = self._calculate_sentiment_score(analyzed_tweets)

        # Determine trend (compare with historical if available)
        trend = self._determine_trend(sentiment_score, [])

        # Count product mentions
        product_mentions = self._count_product_mentions(analyzed_tweets)

        # Group by themes
        positive_theme_groups = self._group_by_themes(positive_tweets)
        negative_theme_groups = self._group_by_themes(negative_tweets)

        # Get top themes
        top_positive_themes = self._get_top_themes(positive_theme_groups, n=5)
        top_negative_themes = self._get_top_themes(negative_theme_groups, n=5)

        # Count strategic categories
        strategic_highlights = self._count_strategic_categories(analyzed_tweets)

        # Extract negative phrases
        negative_phrases = self._extract_negative_phrases(negative_tweets)

        # Log strategic alerts
        if (
            strategic_highlights["strategic_wins"] > 0
            or strategic_highlights["critical_fud"] > 0
        ):
            logger.info(
                f"🎯 {strategic_highlights['strategic_wins']} Strategic Wins | "
                f"⚠️ {strategic_highlights['critical_fud']} Critical FUDs | "
                f"🚨 {strategic_highlights['affiliate_violations']} Affiliate Violations"
            )

        # Generate messages
        message_1 = self._generate_message_1(
            total_tweets,
            positive_count,
            negative_count,
            positive_pct,
            negative_pct,
            sentiment_score,
            trend,
        )

        message_2 = self._generate_message_2(
            product_mentions,
            top_positive_themes,
            top_negative_themes,
            strategic_highlights,
            positive_tweets,
            negative_tweets,
            negative_phrases,
            positive_theme_groups,
            negative_theme_groups,
        )

        # Build raw data structure
        raw_data = {
            "summary": {
                "total_tweets": total_tweets,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "positive_pct": round(positive_pct, 1),
                "negative_pct": round(negative_pct, 1),
                "sentiment_score": round(sentiment_score, 1),
                "trend": trend,
            },
            "product_mentions": product_mentions,
            "positive_themes": [
                {
                    "theme": theme,
                    "count": count,
                    "description": self._format_theme_description(
                        theme, positive_theme_groups[theme]
                    ),
                    "example_tweets": [
                        {
                            "url": t["original_tweet"]["url"],
                            "username": t["original_tweet"]["author_username"],
                            "text": t["original_tweet"]["text"],
                        }
                        for t in positive_theme_groups[theme][:3]
                    ],
                }
                for theme, count in top_positive_themes
            ],
            "negative_themes": [
                {
                    "theme": theme,
                    "count": count,
                    "description": self._format_theme_description(
                        theme, negative_theme_groups[theme]
                    ),
                    "example_tweets": [
                        {
                            "url": t["original_tweet"]["url"],
                            "username": t["original_tweet"]["author_username"],
                            "text": t["original_tweet"]["text"],
                            "urgency": t["analysis"].get("urgency", "LOW"),
                        }
                        for t in negative_theme_groups[theme][:3]
                    ],
                    "urgency": self._get_theme_urgency(negative_theme_groups[theme]),
                }
                for theme, count in top_negative_themes
            ],
            "strategic_highlights": strategic_highlights,
            "negative_phrase_analysis": negative_phrases,
            "all_positive_tweets": [
                {
                    "url": t["original_tweet"]["url"],
                    "username": t["original_tweet"]["author_username"],
                    "text": t["original_tweet"]["text"],
                    "engagement": t["original_tweet"]
                    .get("engagement", {})
                    .get("total", 0),
                }
                for t in positive_tweets
            ],
            "all_negative_tweets": [
                {
                    "url": t["original_tweet"]["url"],
                    "username": t["original_tweet"]["author_username"],
                    "text": t["original_tweet"]["text"],
                    "themes": t["analysis"].get("themes", []),
                    "urgency": t["analysis"].get("urgency", "LOW"),
                }
                for t in negative_tweets
            ],
        }

        # Calculate metadata
        duration = time.time() - start_time
        metadata = {
            "generated_at": datetime.utcnow().isoformat(),
            "date_range": datetime.utcnow().strftime("%b %d, %Y"),
            "analysis_duration": round(duration, 2),
            "tweets_analyzed": total_tweets,
            "cache_hits": 0,  # This would be passed from analyzer
            "total_api_cost": 0.0,  # This would be passed from analyzer
        }

        # Validate report
        report = {
            "message_1": message_1,
            "message_2": message_2,
            "raw_data": raw_data,
            "metadata": metadata,
        }

        if self._validate_report(report, analyzed_tweets):
            logger.info("✓ Report validation passed - all tweets accounted for")
        else:
            logger.warning("⚠️ Report validation found issues")

        logger.info(f"Aggregation complete in {duration:.2f}s")
        return report

    def _generate_message_1(
        self,
        total: int,
        positive: int,
        negative: int,
        pos_pct: float,
        neg_pct: float,
        score: float,
        trend: str,
    ) -> str:
        """Generate summary message (Message 1)."""
        trend_emoji = {"IMPROVING": "↗️", "DECLINING": "↘️", "STABLE": "→"}.get(
            trend, "→"
        )

        return f"""📊 Nansen Daily Sentiment Report
----------
Total Tweets: {total}
• Positive: {positive} ({pos_pct:.0f}%)
• Negative: {negative} ({neg_pct:.0f}%)

Overall Sentiment Score: {score:.0f}/100 {trend_emoji}"""

    def _generate_message_2(
        self,
        product_mentions: Dict,
        top_positive: List[Tuple],
        top_negative: List[Tuple],
        strategic: Dict,
        positive_tweets: List,
        negative_tweets: List,
        negative_phrases: List,
        positive_groups: Dict,
        negative_groups: Dict,
    ) -> str:
        """Generate detailed analysis message (Message 2)."""
        sections = []

        # Section 1: Product Mentions
        sections.append("📱 KEY PRODUCT MENTIONS")
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
        sections.append("✅ TLDR positive sentiments")
        if top_positive:
            for theme, count in top_positive:
                description = self._format_theme_description(
                    theme, positive_groups.get(theme, [])
                )
                examples = self._get_example_tweets(positive_groups.get(theme, []), n=3)
                sections.append(f"• {description} (e.g., {examples})")
        else:
            sections.append("No significant positive sentiments this period.")
        sections.append("")

        # Section 3: Negative Sentiments
        sections.append("⚠️ TLDR negative sentiments")
        if top_negative:
            for theme, count in top_negative:
                description = self._format_theme_description(
                    theme, negative_groups.get(theme, [])
                )
                examples = self._get_example_tweets(negative_groups.get(theme, []), n=3)
                sections.append(f"• {description} (e.g., {examples})")
        else:
            sections.append("No significant negative sentiments this period.")
        sections.append("")

        # Section 4: Strategic Highlights
        if any(strategic.values()):
            sections.append("🎯 STRATEGIC HIGHLIGHTS")
            if strategic["strategic_wins"] > 0:
                sections.append(
                    f"• {strategic['strategic_wins']} Strategic Wins detected"
                )
            if strategic["adoption_signals"] > 0:
                sections.append(f"• {strategic['adoption_signals']} Adoption Signals")
            if strategic["influencer_mentions"] > 0:
                sections.append(
                    f"• {strategic['influencer_mentions']} Influencer Mentions"
                )
            if strategic["critical_fud"] > 0:
                sections.append(f"• ⚠️ {strategic['critical_fud']} Critical FUD alerts")
            if strategic["affiliate_violations"] > 0:
                sections.append(
                    f"• 🚨 {strategic['affiliate_violations']} Affiliate Violations"
                )
            sections.append("")

        # Section 5: Full Tweet Lists
        sections.append("=====")
        sections.append("")
        sections.append(f"✅ Positive tweets (Total: {len(positive_tweets)})")
        for tweet in positive_tweets:
            url = tweet["original_tweet"]["url"]
            username = tweet["original_tweet"]["author_username"]
            sections.append(f"• <{url}|@{username}>")
        sections.append("")

        sections.append(f"⚠️ Negative tweets (Total: {len(negative_tweets)})")
        if negative_tweets:
            for tweet in negative_tweets:
                url = tweet["original_tweet"]["url"]
                username = tweet["original_tweet"]["author_username"]
                sections.append(f"• <{url}|@{username}>")
        else:
            sections.append("None")
        sections.append("")

        # Section 6: Negative Phrase Analysis
        sections.append("⸻")
        sections.append("")
        sections.append("🚨 NEGATIVE PHRASE ANALYSIS")
        sections.append("")

        if negative_phrases:
            for item in negative_phrases:
                sections.append(f"• Phrase: \"{item['phrase']}\"")
                sections.append(f"  Handle: @{item['username']}")
                sections.append(f"  Theme: {item['category']}")
                sections.append(f"  URL: <{item['url']}|@{item['username']}>")
                sections.append("")
        else:
            sections.append("No qualifying negative phrases detected in this period.")

        return "\n".join(sections)

    def _calculate_sentiment_score(self, tweets: List[Dict]) -> float:
        """
        Calculate weighted sentiment score.

        Args:
            tweets: List of analyzed tweets

        Returns:
            Sentiment score from -100 to +100
        """
        if not tweets:
            return 0.0

        total_weighted_score = 0.0
        total_weight = 0.0

        for tweet in tweets:
            sentiment = tweet["analysis"]["sentiment"]
            confidence = tweet["analysis"]["confidence"] / 100.0  # Normalize to 0-1

            # Assign base score
            if sentiment == "POSITIVE":
                base_score = 1.0
            elif sentiment == "NEGATIVE":
                base_score = -1.0
            else:  # NEUTRAL or MIXED
                base_score = 0.0

            # Weight by confidence
            weighted_score = base_score * confidence
            total_weighted_score += weighted_score
            total_weight += confidence

        # Calculate average and scale to -100 to +100
        if total_weight > 0:
            avg_score = total_weighted_score / total_weight
            return avg_score * 100
        return 0.0

    def _group_by_themes(self, tweets: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group tweets by themes.

        Args:
            tweets: List of analyzed tweets

        Returns:
            Dictionary mapping theme to list of tweets
        """
        groups = {}

        for tweet in tweets:
            themes = tweet["analysis"].get("themes", [])
            if not themes:
                themes = ["general"]  # Default theme

            for theme in themes:
                if theme not in groups:
                    groups[theme] = []
                groups[theme].append(tweet)

        return groups

    def _get_top_themes(self, theme_groups: Dict, n: int = 5) -> List[Tuple[str, int]]:
        """
        Get top N themes by tweet count.

        Args:
            theme_groups: Dictionary mapping theme to tweets
            n: Number of top themes to return

        Returns:
            List of (theme, count) tuples sorted by count
        """
        theme_counts = [(theme, len(tweets)) for theme, tweets in theme_groups.items()]
        theme_counts.sort(key=lambda x: x[1], reverse=True)
        return theme_counts[:n]

    def _format_theme_description(self, theme: str, tweets: List[Dict]) -> str:
        """
        Generate natural language description for theme.

        Args:
            theme: Theme name
            tweets: List of tweets with this theme

        Returns:
            Human-readable description
        """
        # Use predefined description if available
        if theme in THEME_DESCRIPTIONS:
            return THEME_DESCRIPTIONS[theme]

        # Fallback: Capitalize and humanize
        return theme.replace("_", " ").title()

    def _get_example_tweets(self, tweets: List[Dict], n: int = 3) -> str:
        """
        Get formatted example tweet URLs.

        Args:
            tweets: List of tweets
            n: Number of examples to include

        Returns:
            Formatted string with Slack-style links
        """
        # Sort by engagement or influencer status
        sorted_tweets = sorted(
            tweets,
            key=lambda t: (
                t["analysis"].get("is_influencer", False),
                t["original_tweet"].get("engagement", {}).get("total", 0),
            ),
            reverse=True,
        )

        examples = []
        for tweet in sorted_tweets[:n]:
            url = tweet["original_tweet"]["url"]
            username = tweet["original_tweet"]["author_username"]
            examples.append(f"<{url}|@{username}>")

        return " ".join(examples) if examples else "No examples available"

    def _count_product_mentions(self, tweets: List[Dict]) -> Dict[str, int]:
        """
        Count occurrences of each product mention.

        Args:
            tweets: List of analyzed tweets

        Returns:
            Dictionary mapping product to count
        """
        counts = {
            "nansen_mobile": 0,
            "season2_rewards": 0,
            "nansen_trading": 0,
            "ai_insights": 0,
            "nansen_points": 0,
        }

        for tweet in tweets:
            products = tweet["analysis"].get("product_mentions", [])
            for product in products:
                if product in counts:
                    counts[product] += 1

        return counts

    def _count_strategic_categories(self, tweets: List[Dict]) -> Dict[str, int]:
        """
        Count tweets by strategic category.

        Args:
            tweets: List of analyzed tweets

        Returns:
            Dictionary with strategic category counts
        """
        counts = {
            "strategic_wins": 0,
            "adoption_signals": 0,
            "critical_fud": 0,
            "affiliate_violations": 0,
            "influencer_mentions": 0,
        }

        for tweet in tweets:
            category = tweet["analysis"].get("strategic_category", "")

            if category == "STRATEGIC_WIN":
                counts["strategic_wins"] += 1
            elif category == "ADOPTION_SIGNAL":
                counts["adoption_signals"] += 1
            elif category == "CRITICAL_FUD":
                counts["critical_fud"] += 1
            elif category == "AFFILIATE_VIOLATION":
                counts["affiliate_violations"] += 1

            # Count influencers separately
            if tweet["analysis"].get("is_influencer", False):
                counts["influencer_mentions"] += 1

        return counts

    def _extract_negative_phrases(self, tweets: List[Dict]) -> List[Dict]:
        """
        Extract negative phrases for detailed analysis.

        Args:
            tweets: List of negative tweets

        Returns:
            List of dictionaries with phrase, username, theme, URL
        """
        phrases = []

        for tweet in tweets:
            critical_keywords = tweet["analysis"].get("critical_keywords", [])
            negative_patterns = tweet["analysis"].get("negative_patterns", [])
            themes = tweet["analysis"].get("themes", [])

            # Get primary theme for categorization
            primary_theme = themes[0] if themes else "unknown"
            category = self._map_theme_to_category(primary_theme, negative_patterns)

            # Extract from critical keywords
            for keyword in critical_keywords:
                phrases.append(
                    {
                        "phrase": keyword,
                        "username": tweet["original_tweet"]["author_username"],
                        "theme": primary_theme,
                        "category": category,
                        "url": tweet["original_tweet"]["url"],
                        "urgency": tweet["analysis"].get("urgency", "LOW"),
                    }
                )

        # Sort by urgency (HIGH first)
        urgency_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        phrases.sort(key=lambda x: urgency_order.get(x["urgency"], 3))

        return phrases

    def _map_theme_to_category(self, theme: str, patterns: List[str]) -> str:
        """
        Map theme to category label for negative phrase analysis.

        Args:
            theme: Theme name
            patterns: List of negative patterns

        Returns:
            Category label like [AIRDROP], [SCAM], etc.
        """
        # Check patterns first (more specific)
        for pattern in patterns:
            if pattern in THEME_CATEGORY_MAPPING:
                return THEME_CATEGORY_MAPPING[pattern]

        # Fall back to theme mapping
        if theme in THEME_CATEGORY_MAPPING:
            return THEME_CATEGORY_MAPPING[theme]

        return "[GENERAL]"

    def _get_theme_urgency(self, tweets: List[Dict]) -> str:
        """
        Determine overall urgency level for a theme.

        Args:
            tweets: List of tweets with this theme

        Returns:
            Urgency level: HIGH, MEDIUM, or LOW
        """
        urgency_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

        for tweet in tweets:
            urgency = tweet["analysis"].get("urgency", "LOW")
            if urgency in urgency_counts:
                urgency_counts[urgency] += 1

        # Return highest urgency level found
        if urgency_counts["HIGH"] > 0:
            return "HIGH"
        elif urgency_counts["MEDIUM"] > 0:
            return "MEDIUM"
        return "LOW"

    def _determine_trend(
        self, current_score: float, historical_scores: List[float]
    ) -> str:
        """
        Determine trend direction based on historical data.

        Args:
            current_score: Current sentiment score
            historical_scores: List of previous scores

        Returns:
            Trend direction: IMPROVING, DECLINING, or STABLE
        """
        if not historical_scores:
            return "STABLE"

        avg_historical = sum(historical_scores) / len(historical_scores)
        diff = current_score - avg_historical

        if diff > 10:
            return "IMPROVING"
        elif diff < -10:
            return "DECLINING"
        return "STABLE"

    def _validate_tweet_counts(self, positive: int, negative: int, total: int) -> bool:
        """
        Validate that tweet counts match.

        Args:
            positive: Number of positive tweets
            negative: Number of negative tweets
            total: Total number of tweets

        Returns:
            True if counts are valid
        """
        if positive + negative != total:
            logger.warning(
                f"Tweet count mismatch: positive ({positive}) + negative ({negative}) "
                f"!= total ({total})"
            )
            return False
        return True

    def _validate_report(self, report: Dict, tweets: List[Dict]) -> bool:
        """
        Validate report completeness and accuracy.

        Args:
            report: Generated report dictionary
            tweets: Original analyzed tweets

        Returns:
            True if validation passes
        """
        try:
            raw_data = report["raw_data"]

            # Validate tweet counts
            total = raw_data["summary"]["total_tweets"]
            positive = raw_data["summary"]["positive_count"]
            negative = raw_data["summary"]["negative_count"]

            if not self._validate_tweet_counts(positive, negative, total):
                return False

            # Validate all tweets appear in lists
            positive_urls = {t["url"] for t in raw_data["all_positive_tweets"]}
            negative_urls = {t["url"] for t in raw_data["all_negative_tweets"]}
            all_urls = positive_urls | negative_urls

            original_urls = {t["original_tweet"]["url"] for t in tweets}

            if len(all_urls) != len(original_urls):
                logger.warning(
                    f"URL count mismatch: {len(all_urls)} in report, "
                    f"{len(original_urls)} in original tweets"
                )
                return False

            # Validate URL format
            for tweet in (
                raw_data["all_positive_tweets"] + raw_data["all_negative_tweets"]
            ):
                if "http" not in tweet["url"]:
                    logger.warning(f"Invalid URL format: {tweet['url']}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False

    def _generate_empty_report(self) -> Dict:
        """Generate report for empty tweet list."""
        return {
            "message_1": "📊 Nansen Daily Sentiment Report\n----------\nNo tweets to analyze",
            "message_2": "No tweets available for analysis.",
            "raw_data": {
                "summary": {
                    "total_tweets": 0,
                    "positive_count": 0,
                    "negative_count": 0,
                    "positive_pct": 0.0,
                    "negative_pct": 0.0,
                    "sentiment_score": 0.0,
                    "trend": "STABLE",
                },
                "product_mentions": {},
                "positive_themes": [],
                "negative_themes": [],
                "strategic_highlights": {},
                "negative_phrase_analysis": [],
                "all_positive_tweets": [],
                "all_negative_tweets": [],
            },
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "date_range": datetime.utcnow().strftime("%b %d, %Y"),
                "analysis_duration": 0.0,
                "tweets_analyzed": 0,
                "cache_hits": 0,
                "total_api_cost": 0.0,
            },
        }

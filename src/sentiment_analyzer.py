"""Comprehensive Claude API sentiment analysis for Nansen brand monitoring."""

import os
import json
import logging
import time
import re
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
from anthropic import Anthropic


# Configure logging
logger = logging.getLogger(__name__)

# Constants for validation
SENTIMENTS = ["POSITIVE", "NEGATIVE", "NEUTRAL", "MIXED"]
INTENTS = [
    "PRAISE", "FEATURE_REQUEST", "COMPLAINT", "QUESTION", "GENERAL_MENTION",
    "COMPETITIVE_COMPARISON", "AIRDROP_FUD", "SCAM_ACCUSATION",
    "SUBSCRIPTION_COMPLAINT", "EXECUTION_COMPLAINT", "AFFILIATE_VIOLATION", "SPAM"
]
PRODUCTS = [
    "nansen_mobile", "season2_rewards", "nansen_trading", "ai_insights", "nansen_points"
]
URGENCY_LEVELS = ["LOW", "MEDIUM", "HIGH"]
STRATEGIC_CATEGORIES = [
    "STRATEGIC_WIN", "ADOPTION_SIGNAL", "CRITICAL_FUD", "AFFILIATE_VIOLATION",
    "EXECUTION_ISSUE", "ROUTINE_NEGATIVE", "NEUTRAL_MENTION"
]

# Pricing for Claude Sonnet 4.5 (per million tokens)
SONNET_4_5_INPUT_PRICE = 3.0  # $3/MTok
SONNET_4_5_OUTPUT_PRICE = 15.0  # $15/MTok


class SentimentAnalyzer:
    """Comprehensive sentiment analyzer for Nansen brand monitoring across all products."""

    SYSTEM_PROMPT = """You are an expert social media sentiment analysis agent for Nansen brand monitoring. Nansen is a blockchain analytics and trading platform with multiple products:

PRODUCTS:
1. Nansen Mobile - iOS/Android app for on-the-go analytics and trading
2. Season 2 Rewards - Loyalty program with NXP points, leaderboards, staking rewards
3. Nansen Trading - Agentic onchain execution with AI-powered routing
4. AI Insights - AI-driven signals, trade recommendations, market analysis
5. Nansen Points - Reward system for staking tokens and making spot trades

COMPETITIVE LANDSCAPE:
- Competitors: Arkham, Dune Analytics, Etherscan, 0x, 1inch, Uniswap

CRITICAL FUD PATTERNS:
- Airdrop farming accusations
- Scam/fraud/rugpull claims
- Execution failures (slippage, front-running, bad fills)
- Fee complaints and misrepresentation
- Guaranteed returns promises (affiliate violation)
- Financial advice claims (affiliate violation)
- Subscription pricing complaints
- Platform reliability issues

Your mission: Identify strategic wins, adoption signals, and critical reputation risks across all products."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize sentiment analyzer with Anthropic API.

        Args:
            api_key: Anthropic API key. If not provided, reads from ANTHROPIC_API_KEY env var.

        Raises:
            ValueError: If API key is not provided or empty
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            error_msg = "Anthropic API key not provided. Set ANTHROPIC_API_KEY environment variable."
            logger.error(error_msg)
            raise ValueError(error_msg)

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-5-20250929"
        self.cache_file = Path("logs/sentiment_cache.json")
        self.total_cost = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

        # Ensure cache directory exists
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"SentimentAnalyzer initialized with model: {self.model}")

    def analyze_tweets(
        self,
        tweets: List[Dict],
        batch_size: int = 15,
        use_cache: bool = True
    ) -> List[Dict]:
        """
        Analyze sentiment for a list of tweets with comprehensive multi-product analysis.

        Args:
            tweets: List of tweet dictionaries from TwitterClient
            batch_size: Number of tweets to process per API call (default: 15)
            use_cache: Whether to use cached results (default: True)

        Returns:
            List of analyzed tweet dictionaries with sentiment, intent, themes, and strategic categorization

        Example:
            >>> analyzer = SentimentAnalyzer()
            >>> tweets = [{"tweet_id": "123", "text": "Love Nansen Mobile!", ...}]
            >>> results = analyzer.analyze_tweets(tweets)
            >>> print(results[0]['analysis']['sentiment'])
            'POSITIVE'
        """
        if not tweets:
            logger.warning("No tweets provided for analysis")
            return []

        logger.info(f"Starting analysis of {len(tweets)} tweets in batches of {batch_size}")

        # Load cache if enabled
        cache = self._load_cache() if use_cache else {}
        cache_hits = 0

        # Separate cached and uncached tweets
        uncached_tweets = []
        results = []

        for tweet in tweets:
            tweet_id = tweet.get('tweet_id')
            if use_cache and tweet_id in cache and self._is_cache_valid(cache[tweet_id]):
                # Use cached result
                cached_analysis = cache[tweet_id]['analysis']
                results.append({
                    'tweet_id': tweet_id,
                    'original_tweet': tweet,
                    'analysis': cached_analysis,
                    'api_cost': {'input_tokens': 0, 'output_tokens': 0, 'estimated_cost_usd': 0.0}
                })
                cache_hits += 1
            else:
                uncached_tweets.append(tweet)

        if cache_hits > 0:
            saved_cost = cache_hits * 0.015  # Rough estimate per tweet
            logger.info(f"✓ Cache hits: {cache_hits} tweets (saved ~${saved_cost:.2f})")

        if not uncached_tweets:
            logger.info("All tweets found in cache")
            return results

        # Process uncached tweets in batches
        num_batches = (len(uncached_tweets) + batch_size - 1) // batch_size
        logger.info(f"Processing {len(uncached_tweets)} uncached tweets in {num_batches} batches")

        batch_results = []
        strategic_wins = 0
        critical_fuds = 0
        affiliate_violations = 0

        for i in range(0, len(uncached_tweets), batch_size):
            batch = uncached_tweets[i:i + batch_size]
            batch_num = (i // batch_size) + 1

            logger.info(f"Analyzing batch {batch_num}/{num_batches} ({len(batch)} tweets)...")

            batch_analysis = self._analyze_batch(batch)

            if batch_analysis:
                batch_results.extend(batch_analysis)

                # Update cache
                if use_cache:
                    for result in batch_analysis:
                        cache[result['tweet_id']] = {
                            'analysis': result['analysis'],
                            'cached_at': datetime.utcnow().isoformat()
                        }

                # Track strategic alerts
                for result in batch_analysis:
                    category = result['analysis'].get('strategic_category')
                    if category == 'STRATEGIC_WIN':
                        strategic_wins += 1
                        logger.info(
                            f"🎯 STRATEGIC_WIN detected: "
                            f"@{result['original_tweet'].get('author_username')} - "
                            f"{result['analysis'].get('summary', '')[:50]}..."
                        )
                    elif category == 'CRITICAL_FUD':
                        critical_fuds += 1
                        logger.warning(
                            f"⚠️ CRITICAL_FUD: "
                            f"@{result['original_tweet'].get('author_username')} - "
                            f"{result['analysis'].get('summary', '')[:50]}..."
                        )
                    elif category == 'AFFILIATE_VIOLATION':
                        affiliate_violations += 1
                        logger.warning(
                            f"🚨 AFFILIATE_VIOLATION: "
                            f"@{result['original_tweet'].get('author_username')} - "
                            f"{result['analysis'].get('summary', '')[:50]}..."
                        )

            # Small delay between batches
            if batch_num < num_batches:
                time.sleep(1)

        # Combine cached and new results
        results.extend(batch_results)

        # Save updated cache
        if use_cache and batch_results:
            self._save_cache(cache)
            self._clean_old_cache()

        # Log summary
        logger.info(f"\n{'='*60}")
        logger.info(f"Analysis Complete:")
        logger.info(f"  Total tweets analyzed: {len(results)}")
        logger.info(f"  Total cost: ${self.total_cost:.4f}")
        logger.info(f"  Total tokens: {self.total_input_tokens:,} in / {self.total_output_tokens:,} out")
        logger.info(f"  Strategic Wins: {strategic_wins}")
        logger.info(f"  Critical FUDs: {critical_fuds}")
        logger.info(f"  Affiliate Violations: {affiliate_violations}")
        logger.info(f"{'='*60}\n")

        return results

    def _analyze_batch(self, tweets: List[Dict]) -> List[Dict]:
        """
        Analyze a batch of tweets using Claude API.

        Args:
            tweets: List of tweet dictionaries

        Returns:
            List of analyzed results with all fields
        """
        formatted_tweets = self._format_tweets_for_prompt(tweets)
        user_prompt = self._build_user_prompt(len(tweets), formatted_tweets)

        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8192,
                    temperature=0.15,
                    system=self.SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}]
                )

                # Extract tokens and calculate cost
                input_tokens = response.usage.input_tokens
                output_tokens = response.usage.output_tokens
                cost = self._calculate_cost(input_tokens, output_tokens)

                self.total_input_tokens += input_tokens
                self.total_output_tokens += output_tokens
                self.total_cost += cost

                logger.info(
                    f"✅ Batch analyzed: {input_tokens:,} input tokens, "
                    f"{output_tokens:,} output tokens (${cost:.4f})"
                )

                # Parse response
                analyses = self._parse_response(response.content[0].text)

                # Validate and merge with original tweets
                results = []
                for i, tweet in enumerate(tweets):
                    analysis = analyses[i] if i < len(analyses) else {}
                    validated_analysis = self._validate_analysis(analysis, tweet)

                    results.append({
                        'tweet_id': tweet.get('tweet_id'),
                        'original_tweet': tweet,
                        'analysis': {
                            **validated_analysis,
                            'analyzed_at': datetime.utcnow().isoformat()
                        },
                        'api_cost': {
                            'input_tokens': input_tokens // len(tweets),
                            'output_tokens': output_tokens // len(tweets),
                            'estimated_cost_usd': cost / len(tweets)
                        }
                    })

                return results

            except Exception as e:
                retry_count += 1
                error_type = type(e).__name__

                # Check for rate limit (429)
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    wait_time = min(2 ** retry_count, 60)  # Exponential backoff, max 60s
                    logger.warning(
                        f"⏳ Rate limit exceeded. Retry {retry_count}/{max_retries}. "
                        f"Waiting {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue

                # Check for server errors (500, 502, 503)
                if any(code in str(e) for code in ["500", "502", "503"]):
                    wait_time = 2 ** retry_count  # Exponential backoff
                    logger.warning(
                        f"⏳ Server error ({error_type}). Retry {retry_count}/{max_retries}. "
                        f"Waiting {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue

                # Check for auth errors (401, 403) - don't retry
                if any(code in str(e) for code in ["401", "403"]):
                    logger.error(f"✗ Authentication error: {e}")
                    return []

                # Other errors - retry with backoff
                wait_time = 2 ** retry_count
                logger.warning(
                    f"⚠️ Error analyzing batch ({error_type}): {e}. "
                    f"Retry {retry_count}/{max_retries}. Waiting {wait_time}s..."
                )
                time.sleep(wait_time)

        logger.error(f"✗ Max retries ({max_retries}) exceeded for batch. Skipping.")
        return []

    def _build_user_prompt(self, batch_size: int, formatted_tweets: str) -> str:
        """Build comprehensive user prompt for batch analysis."""
        return f"""Analyze these {batch_size} tweets for Nansen brand monitoring across ALL products.

For EACH tweet, provide detailed multi-product classification:

=== CORE SENTIMENT ===
1. sentiment: POSITIVE, NEGATIVE, NEUTRAL, MIXED
2. confidence: 0-100

=== INTENT CLASSIFICATION ===
3. intent: Choose ONE primary intent:
   - PRAISE
   - FEATURE_REQUEST
   - COMPLAINT
   - QUESTION
   - GENERAL_MENTION
   - COMPETITIVE_COMPARISON
   - AIRDROP_FUD
   - SCAM_ACCUSATION
   - SUBSCRIPTION_COMPLAINT
   - EXECUTION_COMPLAINT
   - AFFILIATE_VIOLATION (guaranteed returns, financial advice, unrealistic claims)
   - SPAM

=== PRODUCT MENTIONS ===
4. product_mentions: Array of products mentioned (can be multiple):
   - "nansen_mobile" - Keywords: mobile app, ios, android, app store, play store, mobile UI, on the go, mobile alerts, mobile trading
   - "season2_rewards" - Keywords: season 2, S2, points, rewards, NXP, leaderboard, loyalty program, point farming, season rewards
   - "nansen_trading" - Keywords: nansen trading, trade on nansen, agentic trading, onchain execution, swap, exchange
   - "ai_insights" - Keywords: AI signals, AI-powered, AI insights, AI recommendations, AI analysis, smart execution
   - "nansen_points" - Keywords: staking rewards, trading rewards, earn points, point multiplier, spot trade rewards, stake tokens

=== THEMATIC ANALYSIS ===
5. themes: Array of themes (can include multiple). Choose from:

   POSITIVE STRATEGIC THEMES:
   - "mobile_as_future" - Revolutionary mobile trading
   - "mobile_adoption" - First-time users, app downloads
   - "competitive_advantage" - Better than competitors
   - "season2_engagement" - Love for S2 points/rewards
   - "roi_confirmation" - Profitable trades, value confirmation
   - "mobile_app_praise" - Positive UX/performance
   - "trading_execution_praise" - Great fills, routing, speed
   - "ai_insights_praise" - Accurate signals, helpful AI
   - "points_earning_success" - Successfully earning/staking points
   - "seamless_experience" - Easy onboarding, smooth UX
   - "trust_security" - Platform reliability, security praise

   NEGATIVE CRITICAL THEMES:
   - "airdrop_expectations" - Token/airdrop speculation
   - "scam_accusations" - Fraud/rugpull/ponzi claims
   - "subscription_revolt" - Cancellations, too expensive
   - "execution_failures" - Slippage, failed trades, bad fills, delays
   - "fee_complaints" - High fees, hidden fees, fee misrepresentation
   - "guaranteed_returns_claims" - Affiliate violation: profit promises
   - "financial_advice_claims" - Affiliate violation: buy/sell recommendations
   - "speed_price_guarantees" - Affiliate violation: unrealistic execution claims
   - "platform_failures" - Downtime, login issues, data errors
   - "ai_signal_failures" - Wrong signals, contradictory AI advice
   - "mobile_app_bugs" - Crashes, technical issues
   - "season2_complaints" - Points system issues
   - "points_earning_issues" - Problems with staking/trading rewards
   - "competitive_disadvantage" - Worse than alternatives

=== CRITICAL NEGATIVE PATTERNS (DETAILED DETECTION) ===
6. negative_patterns: Array of specific violations found (for negative tweets only):

   EXECUTION ISSUES:
   - "bad_execution" - terrible execution, poor fills
   - "slippage" - slippage complaints
   - "front_running" - front-run accusations
   - "failed_trades" - failed tx, trade failures
   - "execution_delays" - slow execution
   - "wrong_routing" - suboptimal routes, bad prices

   FEE ISSUES:
   - "high_fees" - fees too expensive
   - "hidden_fees" - undisclosed fees
   - "fee_misrepresentation" - unclear fee structure

   AFFILIATE VIOLATIONS:
   - "guaranteed_profits" - risk-free, guaranteed returns
   - "financial_advice" - buy/sell recommendations
   - "guaranteed_speed" - instant execution always, zero slippage guaranteed
   - "guaranteed_pricing" - best price guaranteed always

   TOKEN/AIRDROP:
   - "token_speculation" - wen token, nansen token
   - "airdrop_farming" - farming for airdrop
   - "airdrop_promises" - promised airdrop

   SCAM/FRAUD:
   - "scam_accusation" - nansen scam, fraud, ponzi
   - "rugpull" - rug pull accusations
   - "manipulation" - price manipulation, AI front-running

   PLATFORM:
   - "platform_down" - service outages
   - "login_issues" - can't access
   - "data_errors" - wrong data, contradictory signals

   SUBSCRIPTION:
   - "too_expensive" - pricing complaints
   - "not_worth_it" - value concerns
   - "canceling" - unsubscribing

=== CRITICAL KEYWORDS ===
7. critical_keywords: Array of exact concerning phrases found (for negative tweets):
   - Extract phrases matching: airdrop, farm, farming, token, TGE, scam, rugpull, ponzi, fraud, slippage, front-run, guaranteed profits, financial advice

=== URGENCY & ACTIONABILITY ===
8. urgency: LOW, MEDIUM, HIGH
   - HIGH: Scam accusations, platform failures preventing use, viral negative, affiliate violations
   - MEDIUM: Execution failures, fee complaints, subscription cancellations
   - LOW: Feature requests, minor bugs, general questions

9. actionable: true/false
   - true: Requires immediate team response (scam claims, platform failures, affiliate violations, viral negative)
   - false: Routine monitoring

=== ADDITIONAL CONTEXT ===
10. summary: One clear sentence capturing the tweet's essence
11. competitive_mentions: Array of competitors mentioned (Arkham, Dune, Etherscan, 1inch, 0x, Uniswap, etc.)
12. is_viral: true/false (engagement > 100 OR author followers > 10k)
13. is_influencer: true/false (author followers > 50k OR verified account)

=== STRATEGIC CATEGORIZATION ===
14. strategic_category: Executive-level classification:
   - "STRATEGIC_WIN" - Major validation, viral praise, competitive advantage
   - "ADOPTION_SIGNAL" - New users, app downloads, first trades
   - "CRITICAL_FUD" - Scam accusations, platform failures, viral negative
   - "AFFILIATE_VIOLATION" - Guaranteed returns, financial advice, unrealistic claims
   - "EXECUTION_ISSUE" - Trading quality problems
   - "ROUTINE_NEGATIVE" - Minor complaints
   - "NEUTRAL_MENTION" - Generic reference

=== OUTPUT FORMAT ===
Respond with ONLY a valid JSON array containing one object per tweet with ALL fields above.

Example structure:
[
  {{
    "tweet_number": 1,
    "sentiment": "NEGATIVE",
    "confidence": 85,
    "intent": "EXECUTION_COMPLAINT",
    "product_mentions": ["nansen_trading"],
    "themes": ["execution_failures", "slippage"],
    "negative_patterns": ["slippage", "bad_execution"],
    "critical_keywords": ["slippage", "terrible execution"],
    "urgency": "MEDIUM",
    "actionable": true,
    "summary": "User complaining about high slippage on Nansen Trading execution",
    "competitive_mentions": [],
    "is_viral": false,
    "is_influencer": false,
    "strategic_category": "EXECUTION_ISSUE"
  }}
]

Tweets to analyze:
{formatted_tweets}

NO MARKDOWN. PURE JSON ARRAY ONLY."""

    def _format_tweets_for_prompt(self, tweets: List[Dict]) -> str:
        """
        Format tweets for Claude prompt with clear structure.

        Args:
            tweets: List of tweet dictionaries

        Returns:
            Formatted string with all tweet details
        """
        formatted = []

        for i, tweet in enumerate(tweets, 1):
            engagement = tweet.get('engagement', {})
            total_engagement = engagement.get('total', 0)
            followers = tweet.get('author_followers', 0)
            verified_badge = "✓" if tweet.get('is_verified', False) else ""

            formatted.append(f"""Tweet {i}:
Text: {tweet.get('text', '')}
Author: @{tweet.get('author_username', 'unknown')} ({followers:,} followers) {verified_badge}
Engagement: {engagement.get('likes', 0)} likes, {engagement.get('retweets', 0)} RTs, {engagement.get('replies', 0)} replies (Total: {total_engagement})
URL: {tweet.get('url', '')}
Created: {tweet.get('created_at', '')}
""")

        return "\n".join(formatted)

    def _parse_response(self, response_text: str) -> List[Dict]:
        """
        Parse Claude's JSON response with robust validation.

        Args:
            response_text: Raw response text from Claude

        Returns:
            List of analysis dictionaries
        """
        try:
            # Strip markdown fences if present
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
                cleaned = re.sub(r'\n?```$', '', cleaned)

            # Parse JSON
            analyses = json.loads(cleaned)

            if not isinstance(analyses, list):
                logger.warning("Response is not a list, wrapping in list")
                analyses = [analyses]

            logger.debug(f"Successfully parsed {len(analyses)} analyses")
            return analyses

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text[:500]}...")
            return []

    def _validate_analysis(self, analysis: Dict, tweet: Dict) -> Dict:
        """
        Validate and apply defaults to analysis results.

        Args:
            analysis: Raw analysis dictionary from Claude
            tweet: Original tweet dictionary

        Returns:
            Validated analysis dictionary with all required fields
        """
        # Default values
        defaults = {
            'sentiment': 'NEUTRAL',
            'confidence': 50,
            'intent': 'GENERAL_MENTION',
            'product_mentions': [],
            'themes': [],
            'negative_patterns': [],
            'critical_keywords': [],
            'urgency': 'LOW',
            'actionable': False,
            'summary': tweet.get('text', '')[:100] + ('...' if len(tweet.get('text', '')) > 100 else ''),
            'competitive_mentions': [],
            'is_viral': False,
            'is_influencer': False,
            'strategic_category': 'NEUTRAL_MENTION'
        }

        # Merge with defaults
        validated = {**defaults, **analysis}

        # Validate sentiment
        if validated['sentiment'] not in SENTIMENTS:
            logger.warning(f"Invalid sentiment: {validated['sentiment']}, defaulting to NEUTRAL")
            validated['sentiment'] = 'NEUTRAL'

        # Validate intent
        if validated['intent'] not in INTENTS:
            logger.warning(f"Invalid intent: {validated['intent']}, defaulting to GENERAL_MENTION")
            validated['intent'] = 'GENERAL_MENTION'

        # Validate strategic_category
        if validated['strategic_category'] not in STRATEGIC_CATEGORIES:
            logger.warning(f"Invalid strategic_category: {validated['strategic_category']}, defaulting to NEUTRAL_MENTION")
            validated['strategic_category'] = 'NEUTRAL_MENTION'

        # Validate urgency
        if validated['urgency'] not in URGENCY_LEVELS:
            logger.warning(f"Invalid urgency: {validated['urgency']}, defaulting to LOW")
            validated['urgency'] = 'LOW'

        # Ensure arrays are lists
        for field in ['product_mentions', 'themes', 'negative_patterns', 'critical_keywords', 'competitive_mentions']:
            if not isinstance(validated[field], list):
                validated[field] = []

        # Ensure booleans
        validated['actionable'] = bool(validated['actionable'])
        validated['is_viral'] = bool(validated['is_viral'])
        validated['is_influencer'] = bool(validated['is_influencer'])

        # Ensure confidence is int between 0-100
        try:
            validated['confidence'] = max(0, min(100, int(validated['confidence'])))
        except (ValueError, TypeError):
            validated['confidence'] = 50

        return validated

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate API cost for token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * SONNET_4_5_INPUT_PRICE
        output_cost = (output_tokens / 1_000_000) * SONNET_4_5_OUTPUT_PRICE
        return input_cost + output_cost

    def _load_cache(self) -> Dict:
        """Load sentiment cache from file."""
        if not self.cache_file.exists():
            return {}

        try:
            with open(self.cache_file, 'r') as f:
                cache = json.load(f)
            logger.debug(f"Loaded {len(cache)} items from cache")
            return cache
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            return {}

    def _save_cache(self, cache: Dict) -> None:
        """Save sentiment cache to file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
            logger.debug(f"Saved {len(cache)} items to cache")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def _is_cache_valid(self, cache_item: Dict, max_days: int = 7) -> bool:
        """
        Check if cached item is still valid.

        Args:
            cache_item: Cached item dictionary
            max_days: Maximum age in days (default: 7)

        Returns:
            True if cache is valid, False otherwise
        """
        try:
            cached_at = datetime.fromisoformat(cache_item.get('cached_at', ''))
            age = datetime.utcnow() - cached_at
            return age.days < max_days
        except Exception:
            return False

    def _clean_old_cache(self, max_days: int = 30) -> None:
        """
        Remove cache entries older than max_days.

        Args:
            max_days: Maximum age in days (default: 30)
        """
        try:
            cache = self._load_cache()
            original_size = len(cache)

            # Filter out old entries
            cleaned_cache = {
                tweet_id: item
                for tweet_id, item in cache.items()
                if self._is_cache_valid(item, max_days)
            }

            removed = original_size - len(cleaned_cache)
            if removed > 0:
                self._save_cache(cleaned_cache)
                logger.info(f"Cleaned {removed} old cache entries (>{max_days} days)")

        except Exception as e:
            logger.error(f"Failed to clean cache: {e}")

"""Twitter API v2 client for fetching tweets mentioning Nansen."""

import os
import logging
import time
import tweepy
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta


# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TwitterClient:
    """Client for interacting with Twitter/X API v2."""

    # Keywords to search for in tweets
    SEARCH_KEYWORDS = ["points", "point", "trade", "trading", "mobile", "app"]

    def __init__(self, bearer_token: Optional[str] = None):
        """
        Initialize Twitter client with bearer token authentication.

        Args:
            bearer_token: X API bearer token. If not provided, reads from X_API_BEARER_TOKEN env var.

        Raises:
            ValueError: If bearer token is not provided or empty
        """
        self.bearer_token = bearer_token or os.getenv("X_API_BEARER_TOKEN")

        if not self.bearer_token:
            error_msg = "Bearer token not provided. Set X_API_BEARER_TOKEN environment variable."
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Initialize tweepy client with rate limit handling
        self.client = tweepy.Client(
            bearer_token=self.bearer_token,
            wait_on_rate_limit=True
        )

        logger.info("Twitter client initialized")

        # Validate credentials on initialization
        if not self.validate_credentials():
            raise ValueError("Failed to validate Twitter API credentials")

    def validate_credentials(self) -> bool:
        """
        Validate Twitter API credentials by attempting a simple API call.

        Note: Bearer Token (App-only auth) cannot use get_me() - that requires User Context.
        Instead, we validate by looking up a known user (Twitter's official account).

        Returns:
            bool: True if credentials are valid, False otherwise
        """
        try:
            logger.info("Validating Twitter API credentials...")
            # Use get_user to validate Bearer Token (works with App-only auth)
            # Looking up X's official account as a simple validation
            response = self.client.get_user(username="X")

            if response and response.data:
                logger.info("✓ Bearer Token authentication successful")
                return True
            else:
                logger.error("✗ Authentication failed: No data returned")
                return False

        except tweepy.Unauthorized as e:
            logger.error(f"✗ 401 Unauthorized: Invalid Bearer Token - {e}")
            return False
        except tweepy.Forbidden as e:
            logger.error(f"✗ 403 Forbidden: Token lacks required permissions - {e}")
            return False
        except tweepy.TweepyException as e:
            logger.error(f"✗ Authentication failed: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ Unexpected error during authentication: {e}")
            return False

    def search_mentions(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Search for tweets mentioning Nansen or related keywords.

        Search query: "(@nansen_ai OR points OR point OR trade OR trading OR mobile OR app) -from:nansen_ai -is:retweet"

        Args:
            hours: Number of hours to look back (default: 24)

        Returns:
            List of tweet dictionaries with structured data including engagement metrics
        """
        # Calculate start time in ISO 8601 format
        start_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"

        # Build search query
        query = "(@nansen_ai OR points OR point OR trade OR trading OR mobile OR app) -from:nansen_ai -is:retweet"

        logger.info(f"Starting tweet search for last {hours} hours")
        logger.info(f"Search query: {query}")
        logger.info(f"Start time: {start_time}")

        all_tweets = []
        next_token = None
        page = 1
        max_retries = 3

        try:
            while True:
                retry_count = 0
                success = False

                while retry_count < max_retries and not success:
                    try:
                        logger.info(f"Fetching page {page}..." + (f" (token: {next_token[:20]}...)" if next_token else ""))

                        # Use Recent Search (Pro plan - last 7 days)
                        response = self.client.search_recent_tweets(
                            query=query,
                            start_time=start_time,
                            max_results=100,
                            tweet_fields=['id', 'text', 'author_id', 'created_at', 'public_metrics', 'entities', 'conversation_id'],
                            expansions=['author_id'],
                            user_fields=['username', 'name', 'verified', 'public_metrics'],
                            next_token=next_token
                        )
                        logger.debug("Using search_recent_tweets (Pro plan - last 7 days)")

                        success = True

                    except tweepy.TooManyRequests as e:
                        logger.warning(f"⏳ 429 Rate limit exceeded, waiting before retry {retry_count + 1}/{max_retries}...")
                        retry_count += 1
                        if retry_count < max_retries:
                            wait_time = min(2 ** retry_count * 60, 900)  # Exponential backoff, max 15 min
                            logger.info(f"Waiting {wait_time} seconds before retry...")
                            time.sleep(wait_time)
                        else:
                            logger.error("Max retries reached for rate limit. Returning collected tweets.")
                            return all_tweets

                    except tweepy.Unauthorized as e:
                        logger.error(f"✗ 401 Unauthorized: Invalid Bearer Token - {e}")
                        return all_tweets

                    except tweepy.Forbidden as e:
                        logger.error(f"✗ 403 Forbidden: Token lacks required permissions - {e}")
                        return all_tweets

                    except (tweepy.TweepyException, Exception) as e:
                        logger.warning(f"Transient error: {e}. Retry {retry_count + 1}/{max_retries}")
                        retry_count += 1
                        if retry_count < max_retries:
                            wait_time = 2 ** retry_count  # Exponential backoff
                            time.sleep(wait_time)
                        else:
                            logger.error(f"Max retries reached. Error: {e}")
                            return all_tweets

                # Process response
                if not response.data:
                    logger.info("No more tweets found")
                    break

                # Build user lookup dictionary
                users = {}
                if response.includes and 'users' in response.includes:
                    users = {user.id: user for user in response.includes['users']}

                # Process tweets
                page_tweets = []
                for tweet in response.data:
                    author = users.get(tweet.author_id)

                    if not author:
                        logger.warning(f"Author data missing for tweet {tweet.id}")
                        continue

                    # Extract engagement metrics
                    metrics = tweet.public_metrics if hasattr(tweet, 'public_metrics') else {}
                    likes = metrics.get('like_count', 0)
                    retweets = metrics.get('retweet_count', 0)
                    replies = metrics.get('reply_count', 0)
                    quotes = metrics.get('quote_count', 0)

                    # Get author metrics
                    author_metrics = author.public_metrics if hasattr(author, 'public_metrics') else {}
                    author_followers = author_metrics.get('followers_count', 0)

                    # Check for verification (API v2 format)
                    is_verified = getattr(author, 'verified', False)

                    # Extract matched keywords
                    mentioned_keywords = self._extract_keywords(tweet.text)

                    tweet_data = {
                        'tweet_id': str(tweet.id),
                        'text': tweet.text,
                        'author_username': author.username,
                        'author_name': author.name,
                        'created_at': tweet.created_at.isoformat() if hasattr(tweet, 'created_at') and tweet.created_at else None,
                        'engagement': {
                            'likes': likes,
                            'retweets': retweets,
                            'replies': replies,
                            'quotes': quotes,
                            'total': likes + retweets + replies + quotes
                        },
                        'url': f"https://twitter.com/{author.username}/status/{tweet.id}",
                        'is_verified': is_verified,
                        'author_followers': author_followers,
                        'mentioned_keywords': mentioned_keywords
                    }

                    page_tweets.append(tweet_data)

                all_tweets.extend(page_tweets)
                logger.info(f"✓ Page {page}: Retrieved {len(page_tweets)} tweets (Total: {len(all_tweets)})")

                # Check for pagination
                next_token = response.meta.get('next_token') if hasattr(response, 'meta') else None

                if not next_token:
                    logger.info("No more pages available")
                    break

                page += 1

                # Small delay between requests to be respectful
                time.sleep(0.5)

        except Exception as e:
            logger.error(f"Unexpected error in search_mentions: {e}", exc_info=True)

        logger.info(f"✓ Search complete. Total tweets collected: {len(all_tweets)}")
        return all_tweets

    def _extract_keywords(self, tweet_text: str) -> List[str]:
        """
        Extract which keywords from the search query are mentioned in the tweet.

        Args:
            tweet_text: The text content of the tweet

        Returns:
            List of matched keywords found in the tweet
        """
        tweet_lower = tweet_text.lower()
        matched = []

        # Check for @nansen_ai mention
        if '@nansen_ai' in tweet_lower or 'nansen' in tweet_lower:
            matched.append('nansen_ai')

        # Check for other keywords
        for keyword in self.SEARCH_KEYWORDS:
            if keyword.lower() in tweet_lower:
                matched.append(keyword)

        return list(set(matched))  # Remove duplicates

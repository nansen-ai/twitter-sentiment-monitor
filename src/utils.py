"""Comprehensive helper functions and utilities for the sentiment monitoring project."""

import os
import json
import logging
import re
import yaml
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv


# Configure logging
logger = logging.getLogger(__name__)

# Validation constants
ALLOWED_SENTIMENTS = ["POSITIVE", "NEGATIVE", "NEUTRAL", "MIXED"]
ALLOWED_INTENTS = [
    "PRAISE",
    "FEATURE_REQUEST",
    "COMPLAINT",
    "QUESTION",
    "GENERAL_MENTION",
    "COMPETITIVE_COMPARISON",
    "AIRDROP_FUD",
    "SCAM_ACCUSATION",
    "SUBSCRIPTION_COMPLAINT",
    "EXECUTION_COMPLAINT",
    "AFFILIATE_VIOLATION",
    "SPAM",
]
ALLOWED_PRODUCTS = [
    "nansen_mobile",
    "season2_rewards",
    "nansen_trading",
    "ai_insights",
    "nansen_points",
]
ALLOWED_URGENCY = ["LOW", "MEDIUM", "HIGH"]

# Regex patterns
URL_PATTERN = re.compile(r"https?://\S+")
MENTION_PATTERN = re.compile(r"@\w+")
HASHTAG_PATTERN = re.compile(r"#\w+")


# ============================================================================
# Configuration Loading
# ============================================================================


def load_config(config_path: str = "config/config.yaml") -> Dict:
    """
    Load YAML configuration file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML

    Example:
        >>> config = load_config('config/config.yaml')
        >>> print(config['twitter']['keywords'])
        ['Bitcoin', 'Ethereum']
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    try:
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        # Validate required sections
        required_sections = ["twitter", "sentiment", "alerts"]
        missing = [section for section in required_sections if section not in config]

        if missing:
            raise ValueError(f"Missing required config sections: {', '.join(missing)}")

        logger.info(f"✓ Configuration loaded from {config_path}")
        return config

    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in config file: {e}")


def load_env() -> bool:
    """
    Load environment variables from .env file and validate required variables.

    Returns:
        True if all required variables are present

    Raises:
        ValueError: If required environment variables are missing

    Example:
        >>> if load_env():
        ...     print("Environment configured correctly")
    """
    # Load .env file
    load_dotenv()

    # Required variables
    required_vars = {
        "X_API_BEARER_TOKEN": "Twitter/X API bearer token",
        "ANTHROPIC_API_KEY": "Anthropic Claude API key",
    }

    # At least one Slack method required
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
    slack_bot = os.getenv("SLACK_BOT_TOKEN")

    missing = []
    present = []

    # Check required variables
    for var, description in required_vars.items():
        if os.getenv(var):
            present.append(var)
            logger.debug(f"✓ {var} is set")
        else:
            missing.append(f"{var} ({description})")

    # Check Slack credentials
    if not slack_webhook and not slack_bot:
        missing.append(
            "SLACK_WEBHOOK_URL or SLACK_BOT_TOKEN (Slack notification credentials)"
        )
    else:
        if slack_webhook:
            present.append("SLACK_WEBHOOK_URL")
            logger.debug("✓ SLACK_WEBHOOK_URL is set")
        if slack_bot:
            present.append("SLACK_BOT_TOKEN")
            logger.debug("✓ SLACK_BOT_TOKEN is set")

    if missing:
        error_msg = "Missing required environment variables:\n" + "\n".join(
            f"  - {var}" for var in missing
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(f"✓ Environment configured: {len(present)} variables loaded")
    return True


# ============================================================================
# Logging Setup
# ============================================================================


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    Configure Python logging with console and optional file handlers.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file

    Example:
        >>> setup_logging('DEBUG', 'logs/app.log')
        >>> logger.info("Application started")
    """
    # Get log level
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set level
    root_logger.setLevel(level)

    # Format
    log_format = "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        ensure_directory(os.path.dirname(log_file))
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        logger.info(f"Logging to file: {log_file}")

    logger.info(f"Logging configured at {log_level} level")


# ============================================================================
# Cost Calculation
# ============================================================================


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """
    Calculate Claude Sonnet 4.5 API cost.

    Pricing: Input $3/MTok, Output $15/MTok

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in USD with 4 decimal places

    Example:
        >>> cost = calculate_cost(10000, 5000)
        >>> print(f"${cost:.4f}")
        $0.1050
    """
    input_cost = (input_tokens / 1_000_000) * 3.0
    output_cost = (output_tokens / 1_000_000) * 15.0
    return round(input_cost + output_cost, 4)


# ============================================================================
# Text Processing
# ============================================================================


def sanitize_text(text: str) -> str:
    """
    Remove extra whitespace and newlines from text.

    Args:
        text: Input text

    Returns:
        Sanitized text

    Example:
        >>> sanitize_text("Hello\\n\\n  world   !")
        'Hello world !'
    """
    # Replace newlines with spaces
    text = text.replace("\n", " ").replace("\r", " ")
    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)
    # Strip leading/trailing spaces
    return text.strip()


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Smart truncation at word boundaries.

    Args:
        text: Input text
        max_length: Maximum length including suffix
        suffix: Suffix to add if truncated (default: '...')

    Returns:
        Truncated text with suffix if needed

    Example:
        >>> truncate_text("The quick brown fox jumps", 15)
        'The quick...'
    """
    if len(text) <= max_length:
        return text

    # Account for suffix length
    truncate_at = max_length - len(suffix)

    if truncate_at <= 0:
        return suffix

    # Find last space before truncate point
    truncated = text[:truncate_at]
    last_space = truncated.rfind(" ")

    if last_space > 0:
        truncated = truncated[:last_space]

    return truncated + suffix


def remove_urls(text: str) -> str:
    """
    Remove HTTP/HTTPS URLs from text.

    Args:
        text: Input text

    Returns:
        Text with URLs removed

    Example:
        >>> remove_urls("Check out https://example.com for more info")
        'Check out  for more info'
    """
    return URL_PATTERN.sub("", text)


# ============================================================================
# Number Formatting
# ============================================================================


def format_number(num: int) -> str:
    """
    Format large numbers with K/M/B suffixes.

    Args:
        num: Number to format

    Returns:
        Formatted string with 1 decimal place

    Example:
        >>> format_number(1234)
        '1.2K'
        >>> format_number(1234567)
        '1.2M'
        >>> format_number(1234567890)
        '1.2B'
    """
    if num < 1000:
        return str(num)
    elif num < 1_000_000:
        return f"{num / 1000:.1f}K"
    elif num < 1_000_000_000:
        return f"{num / 1_000_000:.1f}M"
    else:
        return f"{num / 1_000_000_000:.1f}B"


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """
    Format value as percentage.

    Args:
        value: Value between 0 and 1 (or any float)
        decimal_places: Number of decimal places (default: 1)

    Returns:
        Formatted percentage string

    Example:
        >>> format_percentage(0.456)
        '45.6%'
        >>> format_percentage(1.25, 2)
        '125.00%'
    """
    percentage = value * 100
    return f"{percentage:.{decimal_places}f}%"


# ============================================================================
# Date/Time Utilities
# ============================================================================


def parse_twitter_timestamp(timestamp: str) -> str:
    """
    Convert Twitter ISO timestamp to readable format.

    Args:
        timestamp: ISO 8601 timestamp from Twitter

    Returns:
        Human-readable timestamp

    Example:
        >>> parse_twitter_timestamp("2025-01-09T14:30:45.000Z")
        'Jan 09, 2025 at 2:30 PM UTC'
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y at %-I:%M %p UTC")
    except Exception as e:
        logger.warning(f"Failed to parse timestamp '{timestamp}': {e}")
        return timestamp


def get_time_range_string(hours: int) -> str:
    """
    Generate human-readable time range string.

    Args:
        hours: Number of hours

    Returns:
        Human-readable string

    Example:
        >>> get_time_range_string(24)
        'Last 24 hours'
        >>> get_time_range_string(168)
        'Last 7 days'
    """
    if hours < 24:
        return f"Last {hours} hours"
    elif hours == 24:
        return "Last 24 hours"
    elif hours % 24 == 0:
        days = hours // 24
        return f"Last {days} {'day' if days == 1 else 'days'}"
    else:
        return f"Last {hours} hours"


def get_datetime_range(hours: int) -> Tuple[datetime, datetime]:
    """
    Get datetime range for given hours back from now.

    Args:
        hours: Number of hours to look back

    Returns:
        Tuple of (start_time, end_time) in UTC

    Example:
        >>> start, end = get_datetime_range(24)
        >>> print(f"From {start} to {end}")
    """
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    return (start_time, end_time)


# ============================================================================
# Data Validation
# ============================================================================


def is_spam(tweet: Dict) -> bool:
    """
    Basic spam detection heuristics.

    Checks for:
    - Too many hashtags (>10)
    - Too many mentions (>5)
    - Excessive URLs (>3)
    - Repeated characters (5+ in a row)
    - Excessive caps (>70% uppercase)

    Args:
        tweet: Tweet dictionary

    Returns:
        True if likely spam

    Example:
        >>> tweet = {'text': 'BUY NOW!!!! #crypto #btc #eth ...'}
        >>> is_spam(tweet)
        True
    """
    text = tweet.get("text", "")

    # Count hashtags
    hashtags = len(HASHTAG_PATTERN.findall(text))
    if hashtags > 10:
        return True

    # Count mentions
    mentions = len(MENTION_PATTERN.findall(text))
    if mentions > 5:
        return True

    # Count URLs
    urls = len(URL_PATTERN.findall(text))
    if urls > 3:
        return True

    # Check for repeated characters (5+ in a row)
    if re.search(r"(.)\1{4,}", text):
        return True

    # Check for excessive caps (>70% uppercase)
    letters = [c for c in text if c.isalpha()]
    if letters:
        caps_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        if caps_ratio > 0.7 and len(letters) > 10:
            return True

    return False


def validate_tweet_structure(tweet: Dict) -> bool:
    """
    Validate tweet has required fields.

    Required fields: tweet_id, text, author_username, created_at, engagement

    Args:
        tweet: Tweet dictionary

    Returns:
        True if valid structure

    Example:
        >>> tweet = {'tweet_id': '123', 'text': 'Hello', 'author_username': 'user', ...}
        >>> validate_tweet_structure(tweet)
        True
    """
    required_fields = [
        "tweet_id",
        "text",
        "author_username",
        "created_at",
        "engagement",
    ]

    for field in required_fields:
        if field not in tweet:
            logger.warning(f"Missing required field in tweet: {field}")
            return False

    # Validate engagement is dict
    if not isinstance(tweet["engagement"], dict):
        logger.warning("engagement field must be a dictionary")
        return False

    return True


# ============================================================================
# Engagement Calculations
# ============================================================================


def calculate_engagement_rate(tweet: Dict) -> float:
    """
    Calculate engagement rate as percentage of followers.

    Formula: (total_engagement / author_followers) * 100

    Args:
        tweet: Tweet dictionary

    Returns:
        Engagement rate percentage

    Example:
        >>> tweet = {'engagement': {'total': 100}, 'author_followers': 10000}
        >>> calculate_engagement_rate(tweet)
        1.0
    """
    total_engagement = tweet.get("engagement", {}).get("total", 0)
    followers = tweet.get("author_followers", 0)

    if followers == 0:
        return 0.0

    return round((total_engagement / followers) * 100, 2)


def calculate_total_engagement(tweet: Dict) -> int:
    """
    Calculate total engagement from all metrics.

    Sum: likes + retweets + replies + quotes

    Args:
        tweet: Tweet dictionary

    Returns:
        Total engagement count

    Example:
        >>> tweet = {'engagement': {'likes': 10, 'retweets': 5, 'replies': 3, 'quotes': 2}}
        >>> calculate_total_engagement(tweet)
        20
    """
    engagement = tweet.get("engagement", {})
    return (
        engagement.get("likes", 0)
        + engagement.get("retweets", 0)
        + engagement.get("replies", 0)
        + engagement.get("quotes", 0)
    )


# ============================================================================
# File Operations
# ============================================================================


def save_json(data: Dict, filepath: str, pretty: bool = True) -> None:
    """
    Save dictionary to JSON file.

    Args:
        data: Dictionary to save
        filepath: Path to save to
        pretty: Pretty print with indent=2 (default: True)

    Example:
        >>> save_json({'key': 'value'}, 'data.json')
    """
    try:
        # Create parent directories
        ensure_directory(os.path.dirname(filepath))

        # Write JSON
        with open(filepath, "w") as f:
            if pretty:
                json.dump(data, f, indent=2)
            else:
                json.dump(data, f)

        logger.debug(f"Saved JSON to {filepath}")

    except Exception as e:
        logger.error(f"Failed to save JSON to {filepath}: {e}")
        raise


def load_json(filepath: str) -> Dict:
    """
    Load JSON from file.

    Args:
        filepath: Path to JSON file

    Returns:
        Dictionary or empty dict if file doesn't exist

    Example:
        >>> data = load_json('data.json')
        >>> print(data.get('key'))
    """
    if not os.path.exists(filepath):
        logger.debug(f"File does not exist: {filepath}, returning empty dict")
        return {}

    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Failed to load JSON from {filepath}: {e}")
        return {}


def ensure_directory(directory: str) -> None:
    """
    Create directory if it doesn't exist.

    Args:
        directory: Directory path

    Example:
        >>> ensure_directory('logs/reports')
    """
    if directory:
        Path(directory).mkdir(parents=True, exist_ok=True)


# ============================================================================
# Cleanup Utilities
# ============================================================================


def cleanup_old_files(directory: str, days: int, pattern: str = "*") -> int:
    """
    Remove files older than specified days.

    Args:
        directory: Directory to clean
        days: Age threshold in days
        pattern: Glob pattern (default: '*')

    Returns:
        Number of files removed

    Example:
        >>> removed = cleanup_old_files('logs', 30, '*.log')
        >>> print(f"Removed {removed} old log files")
    """
    if not os.path.exists(directory):
        logger.warning(f"Directory does not exist: {directory}")
        return 0

    dir_path = Path(directory)
    removed = 0

    for filepath in dir_path.glob(pattern):
        # Skip .gitkeep files
        if filepath.name == ".gitkeep":
            continue

        # Skip directories
        if filepath.is_dir():
            continue

        # Check age
        age = get_file_age_days(str(filepath))
        if age > days:
            try:
                filepath.unlink()
                logger.info(f"Removed old file: {filepath} (age: {age} days)")
                removed += 1
            except Exception as e:
                logger.error(f"Failed to remove {filepath}: {e}")

    logger.info(f"Cleaned up {removed} files older than {days} days from {directory}")
    return removed


def get_file_age_days(filepath: str) -> int:
    """
    Get file age in days.

    Args:
        filepath: Path to file

    Returns:
        Age in days

    Example:
        >>> age = get_file_age_days('data.json')
        >>> print(f"File is {age} days old")
    """
    try:
        mtime = os.path.getmtime(filepath)
        age_seconds = time.time() - mtime
        return int(age_seconds / 86400)  # Convert to days
    except Exception as e:
        logger.error(f"Failed to get age of {filepath}: {e}")
        return 0


# ============================================================================
# URL Helpers
# ============================================================================


def build_twitter_url(username: str, tweet_id: str) -> str:
    """
    Build Twitter URL from username and tweet ID.

    Args:
        username: Twitter username (without @)
        tweet_id: Tweet ID

    Returns:
        Full Twitter URL

    Example:
        >>> build_twitter_url('elonmusk', '1234567890')
        'https://twitter.com/elonmusk/status/1234567890'
    """
    return f"https://twitter.com/{username}/status/{tweet_id}"


def build_slack_link(url: str, text: str) -> str:
    """
    Build Slack link format.

    Args:
        url: URL to link to
        text: Link text

    Returns:
        Slack-formatted link

    Example:
        >>> build_slack_link('https://twitter.com/user/status/123', '@user')
        '<https://twitter.com/user/status/123|@user>'
    """
    return f"<{url}|{text}>"


# ============================================================================
# Statistics Helpers
# ============================================================================


def calculate_average(numbers: List[float]) -> float:
    """
    Calculate average of numbers.

    Args:
        numbers: List of numbers

    Returns:
        Average or 0 if empty list

    Example:
        >>> calculate_average([1, 2, 3, 4, 5])
        3.0
    """
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


def calculate_median(numbers: List[float]) -> float:
    """
    Calculate median value.

    Args:
        numbers: List of numbers

    Returns:
        Median value

    Example:
        >>> calculate_median([1, 2, 3, 4, 5])
        3.0
    """
    if not numbers:
        return 0.0

    sorted_nums = sorted(numbers)
    n = len(sorted_nums)

    if n % 2 == 0:
        # Even number: average of two middle values
        return (sorted_nums[n // 2 - 1] + sorted_nums[n // 2]) / 2
    else:
        # Odd number: middle value
        return sorted_nums[n // 2]


def calculate_weighted_average(values: List[float], weights: List[float]) -> float:
    """
    Calculate weighted average.

    Args:
        values: List of values
        weights: List of weights (must match length of values)

    Returns:
        Weighted average

    Raises:
        ValueError: If lengths don't match

    Example:
        >>> calculate_weighted_average([80, 90, 70], [0.5, 0.3, 0.2])
        81.0
    """
    if len(values) != len(weights):
        raise ValueError(
            f"Length mismatch: {len(values)} values, {len(weights)} weights"
        )

    if not values:
        return 0.0

    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0

    weighted_sum = sum(v * w for v, w in zip(values, weights))
    return weighted_sum / total_weight


# ============================================================================
# Data Structure Helpers
# ============================================================================


def safe_get(dictionary: Dict, key: str, default: Any = None) -> Any:
    """
    Safely get nested dictionary values with dot notation.

    Args:
        dictionary: Dictionary to search
        key: Key in dot notation (e.g., "analysis.sentiment")
        default: Default value if key not found

    Returns:
        Value or default

    Example:
        >>> data = {'analysis': {'sentiment': 'POSITIVE'}}
        >>> safe_get(data, 'analysis.sentiment')
        'POSITIVE'
        >>> safe_get(data, 'analysis.missing', 'N/A')
        'N/A'
    """
    keys = key.split(".")
    value = dictionary

    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default

    return value


def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """
    Deep merge two dictionaries.

    dict2 values override dict1 on conflicts.

    Args:
        dict1: Base dictionary
        dict2: Override dictionary

    Returns:
        Merged dictionary

    Example:
        >>> d1 = {'a': 1, 'b': {'c': 2}}
        >>> d2 = {'b': {'d': 3}, 'e': 4}
        >>> merge_dicts(d1, d2)
        {'a': 1, 'b': {'c': 2, 'd': 3}, 'e': 4}
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


# ============================================================================
# Import time module for file age calculation
# ============================================================================

import time

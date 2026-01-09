#!/usr/bin/env python3
"""
Nansen Twitter Sentiment Monitor - Main Orchestration Script

This script coordinates the complete sentiment analysis workflow:
1. Fetch tweets from X API
2. Analyze sentiment with Claude AI
3. Aggregate results and generate reports
4. Send notifications to Slack
5. Cleanup old data

Usage:
    python main.py                    # Run with default settings (last 24 hours)
    python main.py --hours 48         # Analyze last 48 hours
    python main.py --dry-run          # Test without sending to Slack
    python main.py --verbose          # Enable debug logging
    python main.py --no-cache         # Disable sentiment cache
"""

import sys
import os
import json
import time
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from twitter_client import TwitterClient
from sentiment_analyzer import SentimentAnalyzer
from aggregator import SentimentAggregator
from slack_notifier import SlackNotifier
from utils import (
    load_env, load_config, setup_logging, save_json,
    get_time_range_string, cleanup_old_files, ensure_directory
)


# Configure logger
logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='Nansen Twitter Sentiment Monitor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Run with defaults (last 24 hours)
  %(prog)s --hours 48               Analyze last 48 hours
  %(prog)s --dry-run                Test without Slack notification
  %(prog)s --verbose                Enable debug logging
  %(prog)s --no-cache               Disable sentiment cache
  %(prog)s --config custom.yaml    Use custom config file
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test mode - analyze tweets but do not send to Slack'
    )

    parser.add_argument(
        '--hours',
        type=float,
        default=24,
        help='Hours to look back for tweets (default: 24, supports decimals like 0.5 for 30 mins)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Custom output file path for report JSON'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose debug logging'
    )

    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable sentiment cache (re-analyze all tweets)'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config/config.yaml',
        help='Path to configuration file (default: config/config.yaml)'
    )

    return parser.parse_args()


def main() -> int:
    """
    Main workflow orchestration.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    # Parse command-line arguments
    args = parse_arguments()

    # Setup logging
    log_level = 'DEBUG' if args.verbose else os.getenv('LOG_LEVEL', 'INFO')
    log_file = os.getenv('LOG_FILE', 'logs/sentiment_monitor.log')
    setup_logging(log_level, log_file)

    # Start timer
    start_time = time.time()

    # Ensure logs directory exists
    ensure_directory('logs')

    logger.info("=" * 60)
    logger.info("Starting Nansen Twitter Sentiment Monitor")
    logger.info("=" * 60)
    logger.info(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"⏰ Time range: {get_time_range_string(args.hours)}")
    logger.info(f"🏃 Mode: {'DRY RUN' if args.dry_run else 'PRODUCTION'}")
    logger.info(f"💾 Cache: {'DISABLED' if args.no_cache else 'ENABLED'}")
    logger.info("=" * 60)

    try:
        # ====================================================================
        # STEP 1: Validate Environment
        # ====================================================================
        logger.info("Step 1: Validating environment and configuration...")

        # Load environment variables
        try:
            if not load_env():
                logger.error("❌ Environment validation failed")
                return 1
            logger.info("✅ Environment variables loaded")
        except ValueError as e:
            logger.error(f"❌ Environment validation failed: {e}")
            return 1

        # Load configuration
        try:
            config = load_config(args.config)
            logger.info(f"✅ Loaded config from {args.config}")
        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            return 1

        # ====================================================================
        # STEP 2: Initialize Clients
        # ====================================================================
        logger.info("")
        logger.info("Step 2: Initializing API clients...")

        # Initialize Twitter client
        try:
            twitter_client = TwitterClient()
            logger.info("✅ Twitter client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Twitter client: {e}")
            return 1

        # Initialize sentiment analyzer
        try:
            sentiment_analyzer = SentimentAnalyzer()
            logger.info("✅ Sentiment analyzer initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize sentiment analyzer: {e}")
            return 1

        # Initialize aggregator
        try:
            aggregator = SentimentAggregator()
            logger.info("✅ Aggregator initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize aggregator: {e}")
            return 1

        # Initialize Slack notifier
        try:
            slack_notifier = SlackNotifier()
            logger.info("✅ Slack notifier initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Slack notifier: {e}")
            return 1

        # ====================================================================
        # STEP 3: Fetch Tweets
        # ====================================================================
        logger.info("")
        logger.info(f"Step 3: Fetching tweets (last {args.hours} hours)...")

        try:
            tweets = twitter_client.search_mentions(hours=args.hours)
            logger.info(f"✅ Found {len(tweets)} tweets")
        except Exception as e:
            logger.error(f"❌ Failed to fetch tweets: {e}")
            logger.error("Check your Twitter API credentials and rate limits")
            return 1

        # Handle empty results
        if len(tweets) == 0:
            logger.warning("⚠️ No tweets found in time range")
            if not args.dry_run:
                logger.info("Sending empty report notification to Slack...")
                slack_notifier.send_empty_report(args.hours)
            logger.info("=" * 60)
            logger.info("✅ Workflow completed (no tweets to analyze)")
            logger.info("=" * 60)
            return 0

        # Save raw tweets
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        raw_file = f'logs/tweets_raw_{timestamp}.json'
        try:
            save_json(tweets, raw_file)
            logger.info(f"💾 Saved raw tweets to {raw_file}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save raw tweets: {e}")

        # ====================================================================
        # STEP 4: Analyze Sentiment
        # ====================================================================
        logger.info("")
        logger.info(f"Step 4: Analyzing sentiment ({len(tweets)} tweets)...")
        logger.info("⏳ This may take a few minutes depending on tweet count...")

        try:
            analyzed_tweets = sentiment_analyzer.analyze_tweets(
                tweets,
                batch_size=config.get('claude', {}).get('batch_size', 15),
                use_cache=not args.no_cache
            )
            logger.info(f"✅ Analysis complete")
        except Exception as e:
            logger.error(f"❌ Sentiment analysis failed: {e}")
            logger.error("Check your Anthropic API key and rate limits")
            return 1

        # Calculate total API cost
        total_cost = sum(
            t.get('api_cost', {}).get('estimated_cost_usd', 0)
            for t in analyzed_tweets
        )
        logger.info(f"💰 Total Claude API cost: ${total_cost:.4f}")

        # Check cost limit
        max_cost = config.get('claude', {}).get('cost_limits', {}).get('max_per_run_usd', 5.0)
        if total_cost > max_cost:
            logger.warning(
                f"⚠️ Cost ${total_cost:.4f} exceeds configured limit ${max_cost:.2f}"
            )

        # Save analyzed tweets
        analyzed_file = f'logs/tweets_analyzed_{timestamp}.json'
        try:
            save_json(analyzed_tweets, analyzed_file)
            logger.info(f"💾 Saved analyzed tweets to {analyzed_file}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save analyzed tweets: {e}")

        # ====================================================================
        # STEP 5: Aggregate Results
        # ====================================================================
        logger.info("")
        logger.info("Step 5: Aggregating results and generating report...")

        try:
            report = aggregator.aggregate(analyzed_tweets)
            logger.info("✅ Report generated")
        except Exception as e:
            logger.error(f"❌ Aggregation failed: {e}")
            return 1

        # Update metadata
        report['metadata']['analysis_duration'] = round(time.time() - start_time, 2)
        report['metadata']['total_api_cost'] = total_cost
        report['metadata']['tweets_analyzed'] = len(tweets)
        report['metadata']['date_range'] = get_time_range_string(args.hours)

        # Log summary statistics
        summary = report['raw_data']['summary']
        logger.info("")
        logger.info("📊 REPORT SUMMARY")
        logger.info("-" * 60)
        logger.info(
            f"Total Tweets: {summary['total_tweets']} | "
            f"Positive: {summary['positive_count']} ({summary['positive_pct']:.1f}%) | "
            f"Negative: {summary['negative_count']} ({summary['negative_pct']:.1f}%)"
        )
        logger.info(f"Sentiment Score: {summary['sentiment_score']:.1f}/100")

        # Log strategic highlights
        highlights = report['raw_data']['strategic_highlights']
        logger.info("-" * 60)
        logger.info(
            f"🎯 Strategic Wins: {highlights['strategic_wins']} | "
            f"📈 Adoption Signals: {highlights['adoption_signals']} | "
            f"👤 Influencer Mentions: {highlights['influencer_mentions']}"
        )

        if highlights['critical_fud'] > 0:
            logger.warning(f"⚠️ Critical FUD: {highlights['critical_fud']}")

        if highlights['affiliate_violations'] > 0:
            logger.warning(f"🚨 Affiliate Violations: {highlights['affiliate_violations']}")

        logger.info("-" * 60)

        # Save report
        report_file = args.output or f'logs/report_{datetime.now().strftime("%Y-%m-%d")}.json'
        try:
            save_json(report, report_file)
            logger.info(f"💾 Saved report to {report_file}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save report: {e}")

        # ====================================================================
        # STEP 6: Send to Slack
        # ====================================================================
        logger.info("")

        if args.dry_run:
            logger.info("🏃 DRY RUN MODE - Skipping Slack notification")
            logger.info("=" * 60)
            logger.info("📊 REPORT PREVIEW (Message 1 - Summary):")
            logger.info("=" * 60)
            print("\n" + report['message_1'] + "\n")
            logger.info("=" * 60)
            logger.info("ℹ️ Message 2 (Detailed Analysis) available in: " + report_file)
            logger.info("=" * 60)
        else:
            logger.info("Step 6: Sending report to Slack...")
            try:
                success = slack_notifier.send_report(report)
                if success:
                    logger.info("✅ Report sent to Slack successfully")
                else:
                    logger.error("❌ Failed to send report to Slack")
                    return 1
            except Exception as e:
                logger.error(f"❌ Slack notification failed: {e}")
                try:
                    # Try to send error notification
                    slack_notifier.send_error_notification(str(e))
                except Exception:
                    pass
                return 1

        # ====================================================================
        # STEP 7: Cleanup Old Files
        # ====================================================================
        logger.info("")
        logger.info("Step 7: Cleaning up old logs...")

        try:
            # Clean old log files
            logs_retention = config.get('retention', {}).get('logs_days', 30)
            cleanup_old_files('logs', logs_retention, pattern='*.log')

            # Clean old tweet files
            cleanup_old_files('logs', logs_retention, pattern='tweets_*.json')

            # Keep reports longer
            report_retention = config.get('retention', {}).get('reports_days', 90)
            cleanup_old_files('logs', report_retention, pattern='report_*.json')

            logger.info("✅ Cleanup complete")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup failed: {e}")

        # ====================================================================
        # FINAL SUMMARY
        # ====================================================================
        duration = time.time() - start_time

        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ WORKFLOW COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info(f"⏱️  Duration: {duration:.2f} seconds")
        logger.info(f"📊 Analyzed: {len(tweets)} tweets")
        logger.info(f"💰 API Cost: ${total_cost:.4f}")
        logger.info(f"📝 Sentiment Score: {summary['sentiment_score']:.1f}/100")
        logger.info(f"🎯 Strategic Wins: {highlights['strategic_wins']}")

        if highlights['critical_fud'] > 0:
            logger.warning(f"⚠️ Critical FUD: {highlights['critical_fud']}")

        if highlights['affiliate_violations'] > 0:
            logger.warning(f"🚨 Affiliate Violations: {highlights['affiliate_violations']}")

        logger.info("=" * 60)

        return 0

    except KeyboardInterrupt:
        logger.info("")
        logger.warning("⚠️ Workflow interrupted by user (Ctrl+C)")
        logger.info("=" * 60)
        return 1

    except Exception as e:
        logger.error("")
        logger.error("=" * 60)
        logger.error("❌ FATAL ERROR")
        logger.error("=" * 60)
        logger.error(f"Error: {e}", exc_info=True)
        logger.error("=" * 60)

        # Try to send error notification to Slack
        if not args.dry_run:
            try:
                slack_notifier = SlackNotifier()
                slack_notifier.send_error_notification(str(e))
                logger.info("Error notification sent to Slack")
            except Exception as slack_error:
                logger.error(f"Failed to send error notification: {slack_error}")

        return 1


if __name__ == '__main__':
    sys.exit(main())

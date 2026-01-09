# 🐦 Nansen Twitter Sentiment Monitor

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://img.shields.io/badge/tests-50%2B%20passing-brightgreen.svg)](tests/)

**Automated real-time sentiment analysis for Nansen brand monitoring across Twitter/X**

Monitor mentions of Nansen products, analyze sentiment using AI, and get comprehensive daily reports delivered to Slack—all fully automated.

---

## 📋 Overview

The Nansen Twitter Sentiment Monitor is an automated system that:

- **Monitors** Twitter/X mentions of Nansen products 24/7
- **Analyzes** sentiment using Claude Sonnet 4.5 AI
- **Detects** critical FUD, affiliate violations, and strategic wins
- **Reports** comprehensive insights to Slack daily
- **Tracks** 5 Nansen products: Mobile, Season 2, Trading, AI Insights, Points

Perfect for brand monitoring, competitive intelligence, and customer sentiment tracking.

---

## ✨ Features

### 🤖 **Automated Daily Monitoring**
- Runs automatically via GitHub Actions at 9 AM UTC
- No manual intervention required
- Configurable schedule (hourly, daily, weekly)

### 🧠 **AI-Powered Analysis**
- Uses Claude Sonnet 4.5 for accurate sentiment detection
- Multi-product classification across 5 Nansen offerings
- Intent recognition (praise, complaint, question, etc.)
- Theme extraction (mobile adoption, execution quality, etc.)

### 📱 **Multi-Product Tracking**
1. **Nansen Mobile** - iOS/Android app mentions
2. **Season 2 Rewards** - Points, leaderboards, staking
3. **Nansen Trading** - Agentic execution, swaps
4. **AI Insights** - Signals, recommendations
5. **Nansen Points** - Earning and staking rewards

### 🚨 **Critical FUD Detection**
- Scam accusations and fraud claims
- Airdrop farming speculation
- Affiliate violations (guaranteed returns, financial advice)
- Platform failures and execution issues
- Automatic team alerts for urgent issues

### 💬 **Rich Slack Reports**
- Two-message format: Summary + Detailed thread
- Product mention breakdown
- Top positive/negative themes with examples
- Strategic highlights (wins, FUD, violations)
- Complete tweet lists with clickable links
- Negative phrase analysis with categorization

### 💰 **Cost Tracking & Management**
- Real-time API cost calculation
- Configurable cost limits ($5 max default)
- Caching to reduce duplicate analysis
- Typical cost: $0.20-0.50 per run

### 🎯 **Strategic Intelligence**
- Identifies strategic wins (viral praise, competitive advantage)
- Tracks adoption signals (new users, downloads)
- Monitors influencer mentions (>50k followers)
- Flags affiliate violations automatically

### 📊 **Historical Tracking**
- 90-day report archive
- Sentiment trend analysis
- Product mention tracking over time
- Exportable JSON reports

### ⚡ **Fast & Efficient**
- Completes in under 5 minutes
- Batch processing for efficiency
- Smart caching reduces costs
- Automatic retry on failures

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      GitHub Actions Workflow                     │
│                   (Runs daily at 9:00 AM UTC)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Twitter/X API  │
                    │  search_mentions│
                    │  (last 24 hours)│
                    └────────┬────────┘
                             │ Raw Tweets
                             ▼
                    ┌─────────────────┐
                    │   Claude AI     │
                    │  Sentiment      │
                    │  Analyzer       │
                    └────────┬────────┘
                             │ Analyzed Tweets
                             ▼
                    ┌─────────────────┐
                    │   Aggregator    │
                    │  Generate       │
                    │  Report         │
                    └────────┬────────┘
                             │ Report
                             ▼
                    ┌─────────────────┐
                    │  Slack Notifier │
                    │  Post Summary + │
                    │  Threaded Reply │
                    └─────────────────┘
```

**Workflow:**
1. GitHub Actions triggers workflow (scheduled or manual)
2. Fetch last 24 hours of tweets matching Nansen keywords
3. Analyze sentiment in batches of 15 tweets
4. Aggregate results and generate comprehensive report
5. Post summary to Slack with detailed analysis in thread
6. Archive report and cleanup old logs

---

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/nansen-twitter-sentiment-monitor.git
cd nansen-twitter-sentiment-monitor
```

### 2. Install Dependencies
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 3. Setup Credentials
```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys
nano .env
```

Add your credentials:
```env
X_API_BEARER_TOKEN=your_twitter_bearer_token
ANTHROPIC_API_KEY=your_claude_api_key
SLACK_WEBHOOK_URL=your_slack_webhook_url
```

### 4. Test Locally
```bash
# Dry run (no Slack notification)
python main.py --dry-run --verbose

# View report preview
cat logs/report_$(date +%Y-%m-%d).json | jq
```

### 5. Deploy to GitHub Actions
```bash
# Push to GitHub
git push origin main

# Add secrets in repo settings
# Settings → Secrets and variables → Actions → New secret

# Enable GitHub Actions
# Actions tab → Enable workflows

# Test with manual trigger
# Actions → Daily Sentiment Analysis → Run workflow
```

---

## 🔧 Detailed Setup

### Prerequisites

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **X API Enterprise Account** - For full archive search (or Free tier for recent tweets)
- **Anthropic API Key** - For Claude AI
- **Slack Workspace** - With webhook or bot permissions

### Get API Credentials

#### 1. X (Twitter) API

1. Go to [developer.twitter.com/portal](https://developer.twitter.com/portal)
2. Create a new app or use existing
3. Generate Bearer Token
4. Copy token (starts with `AAAAAAAAAAAAAAAAAAAAAxxxxxx`)

**Access Tiers:**
- **Free**: 500k tweets/month, recent search (last 7 days)
- **Basic**: $100/month, 10k tweets/month
- **Enterprise**: Custom pricing, full archive access

#### 2. Anthropic API

1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Sign up or log in
3. Generate API key
4. Copy key (starts with `sk-ant-api03-xxxxxx`)

**Pricing:** $3/MTok input, $15/MTok output (~$0.20-0.50 per run)

#### 3. Slack Webhook

**Method 1: Webhook (Recommended)**
1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Create New App → From scratch
3. Activate "Incoming Webhooks"
4. Add New Webhook to Workspace
5. Select channel (#marketing-alerts)
6. Copy Webhook URL

**Method 2: Bot Token (For threading)**
1. Create app at api.slack.com/apps
2. OAuth & Permissions → Add scopes: `chat:write`, `chat:write.public`
3. Install App to Workspace
4. Copy Bot User OAuth Token (starts with `xoxb-`)
5. Get Channel ID: Right-click channel → View details → Copy ID

### Configure Environment

Create `.env` file:
```env
# Required
X_API_BEARER_TOKEN=AAAAAAAAAxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxx
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx

# Optional
SLACK_MENTION_USER_ID=U1234567890  # For urgent alerts
LOG_LEVEL=INFO
```

### Customize Configuration

Edit `config/config.yaml`:

```yaml
twitter:
  search_keywords:
    - "@nansen_ai"
    - "nansen mobile"
    - "season 2"
    - "points"
    - "trading"

sentiment:
  thresholds:
    high_engagement: 100
    influencer_followers: 50000
    critical_fud_count: 5

slack:
  mention_on_urgent: true
  use_threading: true

claude:
  batch_size: 15
  cost_limits:
    max_per_run_usd: 5.0
```

### Test Locally

```bash
# Basic test (dry run)
python main.py --dry-run

# With verbose logging
python main.py --dry-run --verbose

# Analyze last 48 hours
python main.py --hours 48 --dry-run

# Save to custom location
python main.py --output reports/test.json --dry-run

# Disable caching
python main.py --no-cache --dry-run
```

### Deploy to GitHub Actions

1. **Push Code**
```bash
git add .
git commit -m "Deploy sentiment monitor"
git push origin main
```

2. **Add Secrets**
```
Repository Settings → Secrets and variables → Actions → New repository secret
```

Add these secrets:
- `X_API_BEARER_TOKEN`
- `ANTHROPIC_API_KEY`
- `SLACK_WEBHOOK_URL`
- `SLACK_MENTION_USER_ID` (optional)

3. **Enable Actions**
```
Actions tab → Enable workflows
```

4. **Test Manually**
```
Actions → Daily Sentiment Analysis → Run workflow
```

5. **Monitor**
```
Actions tab → View run logs
Download artifacts for detailed reports
```

---

## 📖 Usage Examples

### Run Analysis
```bash
# Last 24 hours (default)
python main.py

# Last 7 days
python main.py --hours 168

# Custom time range
python main.py --hours 72 --verbose
```

### Testing
```bash
# Dry run (no Slack)
python main.py --dry-run

# With verbose logging
python main.py --verbose --dry-run

# Disable cache
python main.py --no-cache
```

### Custom Output
```bash
# Save to specific file
python main.py --output reports/weekly_$(date +%Y-%m-%d).json

# Custom config
python main.py --config config/production.yaml
```

### View Results
```bash
# View latest report
cat logs/report_$(date +%Y-%m-%d).json | jq

# Summary statistics
cat logs/report_$(date +%Y-%m-%d).json | jq '.raw_data.summary'

# Strategic highlights
cat logs/report_$(date +%Y-%m-%d).json | jq '.raw_data.strategic_highlights'
```

---

## ⚙️ Configuration

### Modify Schedule

Edit `.github/workflows/daily-sentiment.yml`:

```yaml
on:
  schedule:
    # Daily at 9 AM UTC
    - cron: '0 9 * * *'

    # Every 6 hours
    # - cron: '0 */6 * * *'

    # Twice daily (9 AM and 5 PM UTC)
    # - cron: '0 9,17 * * *'

    # Weekdays only
    # - cron: '0 9 * * 1-5'
```

Use [crontab.guru](https://crontab.guru/) to validate cron expressions.

### Change Keywords

Edit `config/config.yaml`:

```yaml
twitter:
  search_keywords:
    - "@nansen_ai"
    - "nansen mobile"
    - "your custom keywords"
```

### Adjust Cost Limits

Edit `config/config.yaml`:

```yaml
claude:
  cost_limits:
    max_per_run_usd: 5.0      # Stop if exceeded
    warn_threshold_usd: 2.0   # Log warning
```

Or set environment variable:
```bash
MAX_COST_PER_RUN=3.0 python main.py
```

---

## 💰 API Costs

### Per Run (100-150 tweets)

| Service | Cost | Notes |
|---------|------|-------|
| X API | **$0** | Free tier: 500k/month |
| Claude API | **$0.20-0.50** | ~25-35k tokens |
| Slack API | **$0** | Free webhooks |
| GitHub Actions | **$0** | 2,000 min/month free |
| **Total** | **~$0.30** | Typical run |

### Monthly Cost (Daily Runs)

- **30 runs × $0.30 = ~$9/month**
- Range: $6-15/month depending on tweet volume

### Cost Optimization

1. **Enable Caching**
   - Reduces API calls by 30-50%
   - 7-day cache validity

2. **Adjust Batch Size**
   ```yaml
   claude:
     batch_size: 15  # Higher = more efficient
   ```

3. **Set Cost Limits**
   ```yaml
   claude:
     cost_limits:
       max_per_run_usd: 2.0  # Lower for testing
   ```

4. **Reduce Frequency**
   - Change from daily to 2x/week
   - Only run on weekdays

---

## 🐛 Troubleshooting

### Authentication Failed

**Error:** `Bearer token not provided` or `Invalid API key`

**Solutions:**
1. Verify token in `.env` or GitHub Secrets
2. Check for extra spaces or quotes
3. Regenerate token if expired
4. Ensure token has correct permissions

```bash
# Test Twitter auth
python -c "from src.twitter_client import TwitterClient; TwitterClient().validate_credentials()"

# Test Claude auth
python -c "from src.sentiment_analyzer import SentimentAnalyzer; SentimentAnalyzer()"
```

### No Tweets Found

**Error:** `No tweets found in time range`

**Solutions:**
1. Check search keywords are relevant
2. Verify time range (use `--hours` flag)
3. Ensure Twitter API tier supports search
4. Check if keywords have recent mentions

```bash
# Test with broader time range
python main.py --hours 168 --dry-run  # Last 7 days

# Check raw tweets
cat logs/tweets_raw_*.json | jq length
```

### Slack Messages Not Appearing

**Error:** `Failed to send report to Slack`

**Solutions:**
1. Verify webhook URL is correct
2. Check webhook hasn't been deleted
3. Ensure bot has permissions (if using bot token)
4. Test webhook manually:

```bash
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test message from Nansen Sentiment Monitor"}'
```

### GitHub Actions Failing

**Error:** Workflow fails in Actions tab

**Solutions:**
1. Check secrets are added correctly
2. View detailed logs in Actions tab
3. Verify requirements.txt is up to date
4. Check for API rate limits

```bash
# Test locally first
python main.py --verbose

# Check workflow syntax
gh workflow view daily-sentiment.yml
```

### High API Costs

**Issue:** Costs exceeding budget

**Solutions:**
1. Enable caching: Set `use_cache=True`
2. Reduce batch frequency
3. Lower `max_total_tweets` in config
4. Set strict cost limits

```yaml
twitter:
  max_total_tweets: 100  # Reduce from 500

claude:
  cost_limits:
    max_per_run_usd: 1.0  # Strict limit
```

---

## 📂 Project Structure

```
nansen-twitter-sentiment-monitor/
├── 📄 main.py                      # Main orchestration script
├── 📁 src/                         # Source code
│   ├── twitter_client.py           # X API integration
│   ├── sentiment_analyzer.py       # Claude AI analysis
│   ├── aggregator.py               # Report generation
│   ├── slack_notifier.py           # Slack integration
│   └── utils.py                    # Helper functions
├── 📁 config/                      # Configuration
│   ├── config.yaml                 # Main settings
│   └── .gitkeep
├── 📁 tests/                       # Test suite
│   ├── test_suite.py               # 50+ unit tests
│   ├── test_data/                  # Sample data
│   └── README.md                   # Test documentation
├── 📁 logs/                        # Generated logs
│   ├── sentiment_monitor.log       # Application logs
│   ├── tweets_raw_*.json          # Raw tweet data
│   ├── tweets_analyzed_*.json     # Analyzed results
│   └── report_*.json              # Daily reports
├── 📁 .github/workflows/           # CI/CD
│   └── daily-sentiment.yml         # GitHub Actions workflow
├── 📄 requirements.txt             # Python dependencies
├── 📄 .env.example                 # Environment template
├── 📄 .gitignore                   # Git ignore rules
├── 📄 LICENSE                      # MIT License
├── 📄 README.md                    # This file
├── 📄 CHANGELOG.md                 # Version history
└── 📄 CONTRIBUTING.md              # Contribution guide
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

### How to Contribute

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Add tests** (required for new features)
5. **Run tests**
   ```bash
   python -m pytest tests/ -v
   ```
6. **Commit changes**
   ```bash
   git commit -m "Add amazing feature"
   ```
7. **Push to branch**
   ```bash
   git push origin feature/amazing-feature
   ```
8. **Open Pull Request**

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Built for** [Nansen](https://nansen.ai) - Blockchain analytics platform
- **Powered by** [Claude Sonnet 4.5](https://www.anthropic.com/claude) - AI sentiment analysis
- **Uses** [X API v2](https://developer.twitter.com/) - Real-time tweet data
- **Integrates** [Slack API](https://api.slack.com/) - Team notifications

---

## 📞 Support

### Get Help

- 📖 **Documentation**: Read this README thoroughly
- 🐛 **Bug Reports**: [Open an issue](https://github.com/yourusername/nansen-twitter-sentiment-monitor/issues)
- 💬 **Questions**: [GitHub Discussions](https://github.com/yourusername/nansen-twitter-sentiment-monitor/discussions)
- 📧 **Contact**: your-email@example.com

### Useful Resources

- [X API Documentation](https://developer.twitter.com/en/docs/twitter-api)
- [Claude API Documentation](https://docs.anthropic.com/claude/reference)
- [Slack API Documentation](https://api.slack.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

<div align="center">

**⭐ Star this repo if you find it useful!**

Made with ❤️ for the Nansen community

</div>

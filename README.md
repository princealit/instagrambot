# Instagram Demographic Filter & Outreach Bot

Automated Instagram outreach tool that scrapes profiles, filters by inferred demographics, and performs personalized outreach (liking posts + sending DMs).

## Features

- **Profile Scraping** (via Apify)
  - By hashtags
  - By search queries
  - From followers of specific accounts
  - By location

- **Demographic Inference**
  - Gender detection from names (using gender-guesser)
  - Gender detection from bio keywords
  - Age inference from bio text patterns
  - Optional AI-enhanced analysis (OpenAI)

- **Automated Outreach**
  - Like recent posts (configurable count)
  - Send personalized DMs
  - Rate limiting and safety delays
  - Session persistence

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd instagrambot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Fill in your credentials:
```env
# Required
APIFY_API_TOKEN=your_apify_token
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password

# Optional (for AI-enhanced demographic inference)
OPENAI_API_KEY=your_openai_key
```

3. Check your configuration:
```bash
python main.py config-check
```

## Usage

### 1. Hashtag Campaign
Target users posting with specific hashtags:

```bash
python main.py hashtag \
  --tags "entrepreneur,business,startup" \
  --gender male \
  --age-min 40 \
  --age-max 60 \
  --message "Hey {name}! Love your content. Would love to connect!" \
  --max 10 \
  --dry-run  # Remove to actually perform actions
```

### 2. Follower Campaign
Target followers of competitor/similar accounts:

```bash
python main.py followers \
  --accounts "garyvee,taborster" \
  --gender male \
  --age-min 40 \
  --age-max 60 \
  --message "Hey {name}! Saw you follow some great accounts..." \
  --max 10
```

### 3. Search Campaign
Target users matching a search query:

```bash
python main.py search \
  --query "business coach" \
  --gender male \
  --age-min 40 \
  --message "Hey {name}!" \
  --max 10
```

### 4. Analyze Profiles (No Outreach)
Test demographic inference without performing any actions:

```bash
python main.py analyze \
  --usernames "user1,user2,user3" \
  --gender male \
  --age-min 40
```

## How Demographic Inference Works

Since Instagram doesn't expose age/gender data, we **infer** demographics from available signals:

### Gender Detection
1. **Name Analysis**: Uses the `gender-guesser` library to detect gender from first names
2. **Bio Keywords**: Scans for keywords like "dad", "father", "husband" (male) or "mom", "mother", "wife" (female)
3. **AI Analysis**: Optional GPT-powered analysis for ambiguous cases

### Age Detection
Scans bio for patterns like:
- "25 years old", "25 y/o"
- "Born 1985"
- "40th birthday"
- "Age: 45"

### Confidence Scores
Each inference includes a confidence score (0-1). You can set `--confidence` to filter by minimum confidence.

## Safety Features

- **Rate Limiting**: Configurable delays between actions
- **Session Persistence**: Reuses sessions to avoid repeated logins
- **Dry Run Mode**: Test without performing actual Instagram actions
- **Gradual Actions**: Likes posts before sending DMs to appear natural

## Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `MAX_PROFILES_PER_RUN` | 50 | Max profiles to scrape per run |
| `MAX_LIKES_PER_HOUR` | 30 | Rate limit for likes |
| `MAX_DMS_PER_HOUR` | 10 | Rate limit for DMs |
| `MIN_DELAY_BETWEEN_ACTIONS` | 30 | Min seconds between actions |
| `MAX_DELAY_BETWEEN_ACTIONS` | 90 | Max seconds between actions |

## Important Notes

⚠️ **Terms of Service**: This tool uses unofficial Instagram automation which may violate Instagram's ToS. Use responsibly and at your own risk.

⚠️ **Account Safety**: Aggressive automation can lead to account restrictions or bans. Use conservative settings and monitor your account.

⚠️ **Privacy**: Be mindful of privacy regulations (GDPR, etc.) when collecting and using user data.

## Project Structure

```
instagrambot/
├── main.py                 # CLI entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Example configuration
├── src/
│   ├── bot.py             # Main orchestration
│   ├── models/
│   │   └── profile.py     # Data models
│   ├── scrapers/
│   │   └── apify_scraper.py  # Apify integration
│   ├── filters/
│   │   └── demographic_filter.py  # Demographic inference
│   └── actions/
│       └── instagram_client.py    # Instagram automation
```

## License

MIT

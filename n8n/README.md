# n8n Instagram Demographic Outreach Workflow

This n8n workflow automates Instagram outreach by:
1. Finding accounts with your target audience demographics
2. Getting followers who follow 750+ people (active users)
3. Filtering by public profiles only
4. Inferring demographics (gender/age) from name & bio
5. Liking 3 recent posts
6. Sending a personalized DM

## Workflow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Config    │────▶│  Scrape     │────▶│   Scrape    │
│  Settings   │     │  Accounts   │     │  Followers  │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Send     │◀────│  Like 3     │◀────│   Filter    │
│     DM      │     │   Posts     │     │Demographics │
└─────────────┘     └─────────────┘     └─────────────┘
```

## Setup Instructions

### 1. Import Workflow to n8n

1. Open your n8n instance
2. Go to Workflows → Import
3. Select `instagram_demographic_outreach.json`
4. The workflow will be imported

### 2. Set Up Apify Credentials

1. Create an Apify account at https://apify.com
2. Get your API token from Settings → Integrations
3. In n8n, go to Settings → Credentials
4. Create new "Header Auth" credential:
   - Name: `Apify API Token`
   - Header Name: `Authorization`
   - Header Value: `Bearer YOUR_APIFY_TOKEN`

### 3. Run the API Server

The workflow needs a local API server to perform Instagram actions:

```bash
# In the instagrambot directory
pip install -r requirements.txt

# Set up your .env file
cp .env.example .env
# Edit .env with your Instagram credentials

# Start the server
python api_server.py
```

The server runs on `http://localhost:5000`

### 4. Configure the Workflow

Edit the "Configuration" node to set:

| Setting | Description | Example |
|---------|-------------|---------|
| `target_accounts` | Accounts to scrape followers from | `garyvee,taborster` |
| `target_gender` | Gender to target | `male` |
| `target_age_min` | Minimum age | `40` |
| `target_age_max` | Maximum age | `60` |
| `target_country` | Target country | `United States` |
| `min_following` | Min people they follow | `750` |
| `max_followers_to_process` | Limit per run | `50` |
| `dm_message` | Message template | `Hey {name}!` |

### 5. Run the Workflow

Click "Execute Workflow" or set up a schedule trigger.

## How Demographics Work

Since Instagram doesn't provide age/gender data, we **infer** it:

### Gender Detection
- From first name (using a database of common names)
- From bio keywords: "dad", "father", "husband" → male
- From bio keywords: "mom", "mother", "wife" → female

### Age Detection
- From bio patterns: "45 years old", "born 1980"
- From birthday mentions

## Customization

### Change Target Demographics

Edit the "5. Filter by Demographics" node conditions:
- Modify gender matching
- Add age range checks
- Adjust confidence thresholds

### Adjust Rate Limits

Edit the delay nodes:
- "Random Delay (30-90s)" - between actions
- "Delay Before Next (60-120s)" - between users

### Add More Filters

Add code nodes to filter by:
- Follower/following ratio
- Bio keywords
- Account age
- Post frequency

## Troubleshooting

### "Rate Limited" Errors

- Increase delays between actions
- Reduce `max_followers_to_process`
- Wait a few hours before running again

### Instagram Challenge Required

- Log in to Instagram manually
- Complete any verification
- Restart the API server

### Apify Errors

- Check your API token
- Verify you have enough Apify credits
- Check Apify dashboard for run status

## Cost Estimate

| Service | Cost |
|---------|------|
| Apify Profile Scraper | ~$0.02 per profile |
| Apify Instagram Scraper | ~$0.01 per result |
| n8n | Free (self-hosted) |

For 50 followers per run: ~$1-2 in Apify costs

## Legal Disclaimer

This automation may violate Instagram's Terms of Service. Use at your own risk:
- Keep volumes low
- Don't spam
- Personalize messages
- Respect user privacy

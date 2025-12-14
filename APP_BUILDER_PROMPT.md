# Instagram Outreach SaaS App - Full Specification

## COPY THIS ENTIRE PROMPT INTO REPLIT AI OR SIMILAR APP BUILDER

---

## App Overview

Build a web app called "InstaReach" - an Instagram outreach automation tool where users can:
1. Connect their Instagram account
2. Select target demographics (location, gender, age)
3. Write a custom outreach message
4. Automatically find and message matching Instagram users

**Pricing Model:**
- FREE: 10 messages per week
- PRO ($9.99/week): 100 messages per week

---

## Tech Stack

- **Frontend:** React + TailwindCSS
- **Backend:** Node.js + Express (or Python + FastAPI)
- **Database:** PostgreSQL (use Supabase for easy setup)
- **Auth:** Supabase Auth (Google + Email login)
- **Payments:** Stripe (subscriptions)
- **Instagram API:** Apify for scraping + instagrapi for actions
- **Queue:** Bull/Redis for background jobs

---

## Database Schema

```sql
-- Users table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  instagram_username TEXT,
  instagram_connected BOOLEAN DEFAULT FALSE,
  subscription_status TEXT DEFAULT 'free', -- 'free', 'pro', 'cancelled'
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  messages_sent_this_week INT DEFAULT 0,
  week_reset_at TIMESTAMP DEFAULT NOW()
);

-- Campaigns table
CREATE TABLE campaigns (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id),
  name TEXT NOT NULL,
  status TEXT DEFAULT 'draft', -- 'draft', 'running', 'paused', 'completed'
  target_location TEXT, -- e.g., "California, USA"
  target_gender TEXT, -- 'male', 'female', 'any'
  target_age_min INT,
  target_age_max INT,
  message_template TEXT NOT NULL,
  source_accounts TEXT[], -- accounts to scrape followers from
  created_at TIMESTAMP DEFAULT NOW()
);

-- Outreach log
CREATE TABLE outreach_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  campaign_id UUID REFERENCES campaigns(id),
  user_id UUID REFERENCES users(id),
  target_username TEXT NOT NULL,
  target_full_name TEXT,
  inferred_gender TEXT,
  inferred_age_range TEXT,
  photos_liked INT DEFAULT 0,
  dm_sent BOOLEAN DEFAULT FALSE,
  dm_message TEXT,
  status TEXT DEFAULT 'pending', -- 'pending', 'completed', 'failed'
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Message templates (suggestions)
CREATE TABLE message_templates (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  category TEXT, -- 'business', 'networking', 'sales', etc.
  template TEXT NOT NULL,
  is_default BOOLEAN DEFAULT FALSE
);
```

---

## API Endpoints

### Auth
```
POST /api/auth/signup - Create account
POST /api/auth/login - Login
POST /api/auth/logout - Logout
GET  /api/auth/me - Get current user
```

### Instagram Connection
```
POST /api/instagram/connect - Connect Instagram account
  Body: { username, password }
  - Validates credentials
  - Stores encrypted session
  - Returns success/challenge_required

POST /api/instagram/verify-challenge - Handle 2FA
  Body: { code }

GET  /api/instagram/status - Check connection status
POST /api/instagram/disconnect - Disconnect account
```

### Campaigns
```
GET    /api/campaigns - List user's campaigns
POST   /api/campaigns - Create campaign
GET    /api/campaigns/:id - Get campaign details
PUT    /api/campaigns/:id - Update campaign
DELETE /api/campaigns/:id - Delete campaign
POST   /api/campaigns/:id/start - Start campaign
POST   /api/campaigns/:id/pause - Pause campaign
GET    /api/campaigns/:id/results - Get outreach results
```

### Usage & Billing
```
GET  /api/usage - Get current usage stats
  Response: { messages_sent: 5, limit: 10, resets_at: "2024-01-07" }

POST /api/billing/create-checkout - Create Stripe checkout session
POST /api/billing/webhook - Stripe webhook handler
GET  /api/billing/subscription - Get subscription status
POST /api/billing/cancel - Cancel subscription
```

### Message Templates
```
GET /api/templates - Get suggested message templates
```

---

## Frontend Pages

### 1. Landing Page (`/`)
```
┌─────────────────────────────────────────────────────────────┐
│  🚀 InstaReach                              [Login] [Signup]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│     Grow Your Instagram With Targeted Outreach              │
│     ─────────────────────────────────────────               │
│     Find your ideal customers and connect automatically     │
│                                                             │
│     ✓ Target by location, age, gender                       │
│     ✓ Like posts + Send personalized DMs                    │
│     ✓ 10 FREE messages per week                             │
│                                                             │
│              [Get Started Free →]                           │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Pricing                                                    │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ FREE            │  │ PRO $9.99/week  │                   │
│  │ 10 msgs/week    │  │ 100 msgs/week   │                   │
│  │ 1 campaign      │  │ Unlimited camps │                   │
│  │ Basic targeting │  │ Advanced target │                   │
│  │ [Start Free]    │  │ [Upgrade Now]   │                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### 2. Dashboard (`/dashboard`)
```
┌─────────────────────────────────────────────────────────────┐
│  InstaReach    [Dashboard] [Campaigns] [Settings]  [@user]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Welcome back, John!                                        │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ Messages Sent    │  │ Subscription     │                 │
│  │ 5 / 10           │  │ FREE Plan        │                 │
│  │ ████████░░ 50%   │  │ [Upgrade to Pro] │                 │
│  │ Resets in 3 days │  │                  │                 │
│  └──────────────────┘  └──────────────────┘                 │
│                                                             │
│  Instagram: @yourhandle ✓ Connected                         │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Active Campaigns                                     │   │
│  │ ┌────────────────────────────────────────────────┐   │   │
│  │ │ 🎯 Business Owners CA    [Running] [Pause]     │   │   │
│  │ │    12/50 contacted • 3 replies                 │   │   │
│  │ └────────────────────────────────────────────────┘   │   │
│  │                                                      │   │
│  │ [+ New Campaign]                                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3. New Campaign (`/campaigns/new`)
```
┌─────────────────────────────────────────────────────────────┐
│  Create New Campaign                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Step 1: Target Audience                                    │
│  ───────────────────────                                    │
│                                                             │
│  Location:  [California, USA          ▼]                    │
│                                                             │
│  Gender:    (•) Male  ( ) Female  ( ) Any                   │
│                                                             │
│  Age Range: [40] to [60]                                    │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Step 2: Source Accounts                                    │
│  ───────────────────────                                    │
│  Find followers from these accounts:                        │
│                                                             │
│  [@garyvee        ] [+ Add]                                 │
│  • @garyvee                                                 │
│  • @gaborster                                               │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Step 3: Your Message                                       │
│  ───────────────────────                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Hey {name}! I came across your profile and loved    │    │
│  │ your content. I help business owners like yourself  │    │
│  │ grow their online presence. Would love to connect!  │    │
│  └─────────────────────────────────────────────────────┘    │
│  Variables: {name} {username}                               │
│                                                             │
│  💡 Suggested templates:                                    │
│  • "Hey {name}! Love your content..."                       │
│  • "Hi {name}, I noticed we're in the same industry..."     │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Actions per contact:                                       │
│  [✓] Like 3 recent photos                                   │
│  [✓] Send DM                                                │
│                                                             │
│              [Cancel]  [Create & Start Campaign]            │
└─────────────────────────────────────────────────────────────┘
```

### 4. Campaign Results (`/campaigns/:id`)
```
┌─────────────────────────────────────────────────────────────┐
│  Campaign: Business Owners CA                    [Running]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Progress: 12/50 contacts    ████████░░░░░░░░░ 24%          │
│                                                             │
│  Stats:                                                     │
│  • DMs Sent: 12                                             │
│  • Photos Liked: 36                                         │
│  • Replies Received: 3 (25%)                                │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Contact Log                                        │    │
│  ├─────────────────────────────────────────────────────┤    │
│  │ @john_smith    Male 45-50   ✓ Liked ✓ DM   2h ago  │    │
│  │ @mike_jones    Male 52-58   ✓ Liked ✓ DM   3h ago  │    │
│  │ @david_wilson  Male 41-45   ✓ Liked ✓ DM   4h ago  │    │
│  │ ...                                                │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│              [Pause Campaign]  [Export CSV]                 │
└─────────────────────────────────────────────────────────────┘
```

### 5. Connect Instagram (`/settings/instagram`)
```
┌─────────────────────────────────────────────────────────────┐
│  Connect Instagram Account                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ⚠️ We never store your password. We use secure session    │
│     tokens that you can revoke at any time.                 │
│                                                             │
│  Username: [@________________]                              │
│  Password: [________________]                               │
│                                                             │
│  [Connect Account]                                          │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  🔒 Security Note:                                          │
│  • Your credentials are encrypted                           │
│  • We use the same login method as the Instagram app        │
│  • You may receive a login notification from Instagram      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Business Logic

### Weekly Usage Reset
```javascript
// Run this as a cron job every Monday at midnight
async function resetWeeklyUsage() {
  await db.query(`
    UPDATE users
    SET messages_sent_this_week = 0,
        week_reset_at = NOW()
    WHERE week_reset_at < NOW() - INTERVAL '7 days'
  `);
}
```

### Check Usage Limit
```javascript
async function canSendMessage(userId) {
  const user = await getUser(userId);
  const limit = user.subscription_status === 'pro' ? 100 : 10;
  return user.messages_sent_this_week < limit;
}

async function incrementUsage(userId) {
  await db.query(`
    UPDATE users
    SET messages_sent_this_week = messages_sent_this_week + 1
    WHERE id = $1
  `, [userId]);
}
```

### Demographic Inference (Key Algorithm)
```javascript
// Infer gender from first name
const maleNames = ['james','john','robert','michael','william','david',...];
const femaleNames = ['mary','patricia','jennifer','linda','elizabeth',...];

function inferGender(fullName, bio) {
  const firstName = fullName.split(' ')[0].toLowerCase();

  // Check name
  if (maleNames.includes(firstName)) return { gender: 'male', confidence: 0.85 };
  if (femaleNames.includes(firstName)) return { gender: 'female', confidence: 0.85 };

  // Check bio keywords
  const bioLower = bio.toLowerCase();
  const maleKeywords = ['dad', 'father', 'husband', 'he/him', 'businessman'];
  const femaleKeywords = ['mom', 'mother', 'wife', 'she/her', 'businesswoman'];

  if (maleKeywords.some(k => bioLower.includes(k))) {
    return { gender: 'male', confidence: 0.9 };
  }
  if (femaleKeywords.some(k => bioLower.includes(k))) {
    return { gender: 'female', confidence: 0.9 };
  }

  return { gender: 'unknown', confidence: 0 };
}

// Infer age from bio
function inferAge(bio) {
  // Pattern: "45 years old", "45 y/o"
  const ageMatch = bio.match(/(\d{1,2})\s*(?:years?\s*old|y\/?o|yrs)/i);
  if (ageMatch) {
    const age = parseInt(ageMatch[1]);
    if (age >= 18 && age <= 100) {
      return { min: age - 2, max: age + 2, confidence: 0.85 };
    }
  }

  // Pattern: "born 1980"
  const birthMatch = bio.match(/born\s*(?:in\s*)?(19|20)(\d{2})/i);
  if (birthMatch) {
    const birthYear = parseInt(birthMatch[1] + birthMatch[2]);
    const age = new Date().getFullYear() - birthYear;
    return { min: age - 1, max: age + 1, confidence: 0.9 };
  }

  return null;
}
```

### Campaign Worker (Background Job)
```javascript
async function processCampaign(campaignId) {
  const campaign = await getCampaign(campaignId);
  const user = await getUser(campaign.user_id);

  // Check if user can still send
  if (!await canSendMessage(user.id)) {
    await pauseCampaign(campaignId, 'Usage limit reached');
    return;
  }

  // 1. Scrape followers from source accounts (via Apify)
  const followers = await scrapeFollowers(campaign.source_accounts);

  // 2. Filter by criteria
  const qualified = followers.filter(f => {
    // Must follow 750+ people (active user)
    if (f.following_count < 750) return false;
    // Must be public
    if (f.is_private) return false;

    // Check demographics
    const gender = inferGender(f.full_name, f.biography);
    if (campaign.target_gender !== 'any' && gender.gender !== campaign.target_gender) {
      return false;
    }

    // Age check if specified
    if (campaign.target_age_min || campaign.target_age_max) {
      const age = inferAge(f.biography);
      if (!age) return false;
      if (campaign.target_age_min && age.max < campaign.target_age_min) return false;
      if (campaign.target_age_max && age.min > campaign.target_age_max) return false;
    }

    return true;
  });

  // 3. Process each qualified follower
  for (const target of qualified) {
    if (!await canSendMessage(user.id)) break;

    try {
      // Like 3 posts
      await likeRecentPosts(target.username, 3);
      await randomDelay(30, 60);

      // Send DM
      const message = personalizeMessage(campaign.message_template, target);
      await sendDM(target.username, message);

      // Log success
      await logOutreach(campaign.id, target, 'completed', message);
      await incrementUsage(user.id);

      // Wait before next
      await randomDelay(60, 120);

    } catch (error) {
      await logOutreach(campaign.id, target, 'failed', null, error.message);
    }
  }
}
```

---

## Stripe Integration

### Create Checkout Session
```javascript
app.post('/api/billing/create-checkout', async (req, res) => {
  const user = req.user;

  const session = await stripe.checkout.sessions.create({
    customer_email: user.email,
    payment_method_types: ['card'],
    line_items: [{
      price: 'price_XXXXX', // Your $9.99/week price ID
      quantity: 1,
    }],
    mode: 'subscription',
    success_url: 'https://yourapp.com/dashboard?upgraded=true',
    cancel_url: 'https://yourapp.com/dashboard',
    metadata: { user_id: user.id },
  });

  res.json({ url: session.url });
});
```

### Webhook Handler
```javascript
app.post('/api/billing/webhook', async (req, res) => {
  const event = stripe.webhooks.constructEvent(
    req.body,
    req.headers['stripe-signature'],
    process.env.STRIPE_WEBHOOK_SECRET
  );

  switch (event.type) {
    case 'checkout.session.completed':
      const session = event.data.object;
      await db.query(`
        UPDATE users
        SET subscription_status = 'pro',
            stripe_customer_id = $1,
            stripe_subscription_id = $2
        WHERE id = $3
      `, [session.customer, session.subscription, session.metadata.user_id]);
      break;

    case 'customer.subscription.deleted':
      const sub = event.data.object;
      await db.query(`
        UPDATE users
        SET subscription_status = 'cancelled'
        WHERE stripe_subscription_id = $1
      `, [sub.id]);
      break;
  }

  res.json({ received: true });
});
```

---

## Environment Variables Needed

```env
# Database
DATABASE_URL=postgresql://...

# Supabase (if using)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_KEY=xxx

# Stripe
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_ID=price_xxx

# Apify (for scraping)
APIFY_API_TOKEN=xxx

# App
APP_URL=https://yourapp.com
JWT_SECRET=xxx
```

---

## Suggested Message Templates (Seed Data)

```sql
INSERT INTO message_templates (category, template, is_default) VALUES
('business', 'Hey {name}! I came across your profile and love what you''re building. I help entrepreneurs scale their businesses - would love to connect!', true),
('networking', 'Hi {name}! I noticed we''re in similar spaces. Always looking to connect with like-minded people. Let''s chat!', false),
('sales', 'Hey {name}! Quick question - are you currently looking for ways to [benefit]? I might be able to help.', false),
('coaching', 'Hi {name}! I love your content. I work with professionals like yourself to [achieve goal]. Open to a quick chat?', false),
('real_estate', 'Hey {name}! I noticed you''re in [location]. I specialize in helping people find their dream homes here. Let me know if I can ever help!', false);
```

---

## Security Considerations

1. **Never store Instagram passwords in plain text** - Use encrypted session tokens
2. **Rate limit all API endpoints** - Prevent abuse
3. **Validate all user inputs** - Prevent XSS/SQL injection
4. **Use HTTPS everywhere**
5. **Implement proper CORS**
6. **Add request logging for debugging**

---

## Launch Checklist

- [ ] Set up Supabase project + database
- [ ] Create Stripe account + products
- [ ] Get Apify API key
- [ ] Deploy backend to Railway/Render
- [ ] Deploy frontend to Vercel
- [ ] Set up custom domain
- [ ] Test full flow end-to-end
- [ ] Add error monitoring (Sentry)
- [ ] Add analytics (Mixpanel/Amplitude)

---

## One-Line Summary for AI Builder

> Build a React + Node.js SaaS app for Instagram outreach automation. Users connect their Instagram, set target demographics (location, gender, age 40-60), write a custom message, and the app automatically finds matching users, likes 3 of their photos, and sends a DM. Free tier: 10 messages/week. Pro tier ($9.99/week via Stripe): 100 messages/week. Use Supabase for auth + database, Apify for Instagram scraping.

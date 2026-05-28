# Anthropic API Key Setup Guide

## 1. Create an Anthropic Account

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Click **Sign Up** and complete email verification

## 2. Generate an API Key

1. Log in and click **API Keys** in the left menu
2. Click the **Create Key** button
3. Enter a key name (e.g., `clickeye-dev`)
4. Copy the generated key immediately — **it cannot be viewed again**

Generated key format: `sk-ant-api03-...`

## 3. Configure .env

```
ANTHROPIC_API_KEY=sk-ant-api03-paste-your-key-here
```

## 4. Billing Setup (Required)

You must add a payment method to use the API.

1. Click **Billing** in the left menu
2. Click **Add payment method** and register a card
3. Recommended: set a monthly limit under the **Usage Limits** tab (e.g., $20)

## Pricing

- Claude Sonnet 4: $3 / 1M input tokens, $15 / 1M output tokens
- Claude Haiku 4: $0.25 / 1M input tokens, $1.25 / 1M output tokens
- Typical cost during early development: $5–20 / month

## Troubleshooting

- `401 Unauthorized`: Verify the key is correct and not expired
- `429 Too Many Requests`: Check your plan limits or retry after a short wait
- `402 Payment Required`: Billing setup is needed

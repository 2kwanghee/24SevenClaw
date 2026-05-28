# Linear API Key & Team ID Setup Guide

## 1. Create a Linear Account

1. Go to [linear.app](https://linear.app)
2. Click **Sign Up** and register with email or Google
3. Create a workspace (team)

## 2. Generate a Personal API Key

1. Click your profile in the top-right corner → **Settings**
2. Click the **API** section in the left menu
3. Under **Personal API keys**, click **Create key**
4. Enter a name (e.g., `clickeye-agent`)
5. Copy the generated key immediately — **it cannot be viewed again**

Generated key format: `lin_api_...`

## 3. Configure .env

```
LINEAR_API_KEY=lin_api_paste-your-key-here
LINEAR_TEAM_ID=paste-your-team-id-here
```

## 4. Find Your Team ID

### Method A: From the URL
Navigate to your team in the Linear app. The URL looks like:
```
https://linear.app/{workspace}/team/{TEAM-ID}/issues
```
The `{TEAM-ID}` part is your team identifier (e.g., `MYTEAM`).

### Method B: Via the API
```bash
curl -H "Authorization: lin_api_your-key-here" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ teams { nodes { id name key } } }"}' \
  https://api.linear.app/graphql
```
The `id` value in the response is your team UUID.

## 5. AI Team Integration

Once connected to ClickEye AI Team:
- Session created → Linear issue auto-created (status: Backlog, awaiting review)
- Subtask completed → Linear issue status auto-updated
- Merge completed → Linear issue moved to Done

## Troubleshooting

- `401`: Check API key (must include `lin_api_` prefix)
- `404`: Wrong team ID — re-check team list via the API
- Permission error: Confirm you are a member of the team

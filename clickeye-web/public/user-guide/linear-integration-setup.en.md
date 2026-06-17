---
title: Linear Integration Setup
description: A step-by-step guide covering Linear API key registration, webhook setup, and the DayQueued flow.
order: 5
---

# Linear Integration Setup

Set up the complete flow in which subtasks created by ClickEye's AI Team are automatically registered as Linear issues, and when an issue's status changes to `Queued`, your local Claude Code automatically starts development.

---

## Overall Flow

```
[ClickEye AI Team] Generate AI draft
         │ → Auto-register Linear issues
         ▼
[Linear] Issue status → changed to Queued
         │
         ▼
[Local PC] Webhook received or polling
         │
         ▼
[Claude Code] Run automatic development pipeline
```

---

## Step 1 — Issue a Linear API Key

1. Go to [https://linear.app/settings/api](https://linear.app/settings/api)
2. Click **Personal API keys → Create key**
3. Enter a name (e.g., `ClickEye`)
4. Permissions: **Full access** or at minimum `issues:write`
5. Copy the issued key (`lin_api_...`)

---

## Step 2 — Find Your Linear Team ID

You need your Linear **Team ID**. Find it using one of these methods:

- Linear app → Right-click your team name in the left sidebar → **Copy Team ID**
- Or find it in the URL: `https://linear.app/{workspace}/team/{TEAM_ID}/issues`

---

## Step 3 — Save It on the ClickEye Settings Page

1. Go to [ClickEye Settings → Linear](https://app.24sevenclaw.com/settings/linear)
2. Enter the following fields:

| Field | Description | Required |
|------|------|------|
| Linear API Key | `lin_api_...` format | ✅ |
| Team ID | The UUID of the team where issues will be created | ✅ |
| Webhook Secret | A random string used for HMAC signature verification | ⬜ |
| Tunnel URL | The public URL of your local webhook server | ⬜ |

3. Click **Save**

> **Security tip**: For the Webhook Secret, use a strong random string generated with `openssl rand -hex 32`.

> **When you save a Tunnel URL**: The server automatically registers a webhook in your Linear workspace.

---

## Step 4 — Select the Linear Skill in the Wizard (When Generating the ZIP)

If you select the **Linear** skill in Step 5 (Agents & Skills) of the 7-Step wizard, the ZIP will include the Linear integration scripts.

After extracting the ZIP, the following values are needed in the `.env` file:

```bash
LINEAR_API_KEY=lin_api_xxxxxxxxxxxx
LINEAR_TEAM_ID=your-team-uuid
WEBHOOK_SECRET=your-webhook-secret
TUNNEL_PROVIDER=cloudflare   # cloudflare | ngrok | polling
```

---

## Step 5 — Choose a Real-Time Tracking Method

### Method A: Cloudflare Tunnel (Recommended)

Free and provides a static URL.

```bash
bash scripts/setup-tunnel.sh
```

When you run the script:
1. `cloudflared` is installed automatically (Homebrew / apt / snap)
2. The tunnel starts and a `https://xxxx.trycloudflare.com` URL is issued
3. `WEBHOOK_PUBLIC_URL` in `.env` is updated automatically

Save the issued URL in the **Tunnel URL** field on the [ClickEye settings page](https://app.24sevenclaw.com/settings/linear).

> ⚠️ Closing this terminal window terminates the tunnel. To run it in the background: `nohup bash scripts/setup-tunnel.sh &`

### Method B: ngrok

```bash
TUNNEL_PROVIDER=ngrok bash scripts/setup-tunnel.sh
```

- Free plan: The URL changes on each restart. When the URL changes, you must re-save it on the settings page
- Paid fixed URL: Set `NGROK_AUTH_TOKEN` in `.env` to authenticate automatically

### Method C: 30-Second Polling (Without a Tunnel)

Polls Linear every 30 seconds without a webhook. Suitable for environments where setting up a tunnel is difficult.

```bash
python scripts/linear_watcher.py
```

To run it in the background:

```bash
python scripts/linear_watcher.py &
```

---

## Step 6 — Start the Local Webhook Server (Cloudflare/ngrok Methods)

Run this in a new terminal:

```bash
bash scripts/start-webhook.sh
```

Health check:

```bash
curl http://localhost:9876/health
# {"status":"ok","port":9876}
```

---

## Step 7 — Verify the DayQueued Flow

Once all setup is complete, automatic development is triggered by the following flow:

1. ClickEye AI Team → Click **Generate AI Draft**
2. Issues are automatically registered in Linear (e.g., `24S-123`)
3. In Linear, change the issue status to **Queued** (or `DayQueued`, `NightQueued`)
4. The pipeline runs automatically in your local environment:

   - **Webhook mode**: Check the `start-webhook.sh` terminal
     ```
     [ClickEye] Linear webhook received: issue 24S-123 → Queued
     [ClickEye] Automatic development pipeline triggered
     ```
   - **Polling mode**: Check the `linear_watcher.py` terminal
     ```
     [watcher] Issue found: 24S-123 (Queued) → running pipeline
     ```

---

## Troubleshooting

| Symptom | Cause | Solution |
|------|------|----------|
| "Linear credentials not found" banner | API key not saved | Save the API key on the settings page |
| Linear issue creation fails | Expired API key or insufficient permissions | Issue a new key and re-save |
| No webhook received | Tunnel URL mismatch | Re-save the current Tunnel URL on the settings page |
| Signature verification failed (401) | Webhook Secret mismatch | Verify that the Secret in `.env` matches the settings page |
| `cloudflared` installation fails | Internet connection or permission issue | [Manual installation guide](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) |
| ngrok URL changed | Free plan restart | Re-save the new URL on the settings page or use a paid plan |
| Polling doesn't detect issues | `LINEAR_TEAM_ID` error | Verify in Linear that the TEAM_ID in `.env` is correct |

---

## Security Checklist

- [ ] Is your Linear API key only in `.env` and not committed to Git? (Check `.gitignore`)
- [ ] Is the Webhook Secret strong enough? (`openssl rand -hex 32` recommended)
- [ ] Does `start-webhook.sh` only listen on localhost? (Port 9876 does not need external exposure)
- [ ] Do the Cloudflare/ngrok tunnels expose only port 9876?

---

## Related Guides

- [7-Step Solution Wizard](/guide/wizard-7-step) — Selecting the Linear skill in the wizard
- [AI Team Management](/guide/ai-team-management) — Generating AI drafts and checking Linear issues

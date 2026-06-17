---
title: 7-Step Solution Wizard
description: A guide to the inputs, examples, and common mistakes for each step of the 7-Step wizard.
order: 3
---

# How to Use the 7-Step Solution Wizard

The ClickEye wizard consists of 10 screens in total, 2 of which are handled automatically by AI. The user directly enters or selects on 8 of these screens.

---

## Overall Flow

```
Step 1. Enter company information
   ↓ (click Next)
[AI Automatic] Generate solution prototypes (~30s)
   ↓
Step 2. Select a prototype
   ↓ (click Next)
[AI Automatic] PM recommendation analysis (~10s)
   ↓
Step 3. Select a PM
   ↓
Step 4. Review PM configuration
   ↓
Step 5. Configure agents & skills
   ↓
Step 6. Select a platform
   ↓
Step 7. Enter environment variables
   ↓
Step 8. Final review & project creation
```

---

## Step 1 — Company Information & Solution Requirements

In this step, the AI gathers your company context and requirements so it can design a solution.

### Input Fields

| Field | Required | Limit | Description |
|------|------|------|------|
| Company Name | ✅ | 200 characters | Company or team name |
| Company Size | ✅ | Select | Startup (1–10) / Small business (11–50) / SMB (51–200) / Mid-size (201–1,000) / Enterprise (1,000+) |
| Industry | ✅ | Select | IT, Finance/Fintech, E-commerce, Healthcare, Education, Manufacturing, Logistics, Marketing, Gaming, Other |
| Tech Stack | ⬜ | Multi-select | Python, TypeScript, React, Next.js, FastAPI, Docker, etc. (multiple selections allowed) |
| Core Product/Service | ✅ | 500 characters | The product or service your company currently sells or operates |
| Business Type | ✅ | Select | B2B / B2C / B2B2C / Internal tool |
| Company Description | ⬜ | 1,000 characters | Additional context such as team composition, development maturity, and current problems |
| Solution Description | ✅ | Min. 50 / Max. 2,000 characters | **The field the AI relies on most** |

### Writing Examples

**How to write a good Solution Description:**

```
✅ Good example:
We want to automate the customer inquiries we currently manage in Excel.
Our sales team of 8 handles over 100 inquiries a day. We'd like automatic replies to
repetitive questions, and a Slack notification for urgent cases.
Integration with our CRM would be even better.

❌ Bad example:
We need AI automation.
```

### Common Mistakes

- **Writing the solution description too briefly**: If it is under the 50-character minimum, the Next button stays disabled. Describe your specific workflow and the outcomes you want.
- **Leaving the tech stack unselected**: You can proceed without selecting one, but choosing the technologies your team currently uses helps the AI design a more suitable solution.
- **Skipping the company description**: It is not a required field, but noting your team size, current technical level, and constraints produces a far more accurate prototype.

---

## [AI Automatic] Solution Prototype Generation

When you click Next, the AI automatically generates 3 solution prototypes. This takes about 30 seconds. No user input is required on this screen.

---

## Step 2 — Prototype Selection

Choose the one of the 3 AI-generated solution candidates that best matches your project direction.

### How to Read a Card

Each prototype card displays the following information:

- **Name**: The solution's name
- **Type**: SaaS / REST API / Full-stack / Internal tool / MVP / Custom
- **Description**: An overview of the solution

### Common Mistakes

- **Choosing "the one that looks most expensive"**: A complex solution isn't always better. Choose the one that matches your team size and technical level.
- **If you don't like any of them**: Go back to the previous step, write your solution requirements in more detail, and regenerate.

---

## [AI Automatic] PM Recommendation Analysis

After you select a prototype, the AI analyzes a list of PMs (Project Manager AIs) optimized for that solution. This takes about 10 seconds.

---

## Step 3 — PM Selection

From the list of PMs recommended by the AI, choose the PM AI that will lead your project.

### How to Read a PM Card

| Field | Description |
|------|------|
| Avatar & Name | PM profile |
| Domain | The PM's area of expertise |
| Match Rate (%) | Fit with the selected prototype |
| Recommendation Reason | The basis for the AI's analysis |
| Success Rate / Completed Projects / Average Rating | Performance metrics |

### Common Mistakes

- **Choosing based on match rate alone**: Also check whether the domain matches your project's industry.
- **Proceeding without a selection**: Selecting a PM is required. If none is selected, the Next button is disabled.

---

## Step 4 — PM Configuration Review

In this step, you review which sub-agents and skills make up your selected PM. You can simply review and move on without making any changes.

---

## Step 5 — Agent & Skill Configuration

Default agents are pre-selected based on the PM configuration. You can add or remove them as needed.

### Agents

Each AI agent handles a specific role (writing code, testing, documentation, etc.). We recommend keeping the default selections.

### Integration Skills (Optional)

Skills are integration features for connecting to external services.

| Skill | Description | Additional Setup Required |
|------|------|--------------|
| linear | Linear issue tracking integration | ✅ LINEAR_API_KEY, LINEAR_TEAM_ID |
| slack | Sending Slack notifications | ✅ SLACK_WEBHOOK_URL |
| github | Automatic GitHub PR creation | ✅ GITHUB_TOKEN |

> **When selecting the Linear skill**: `LINEAR_API_KEY` and `LINEAR_TEAM_ID` are added as required fields in Step 7 (Environment Variables). See the [Linear Integration Setup Guide](/guide/linear-integration-setup).

### Common Mistakes

- **Adding skills you don't need**: Adding a skill also makes its API key a required input. Don't add skills for services you won't use.

---

## Step 6 — Platform Selection

Select the AI agent platform that will run your downloaded ZIP.

| Platform | Recommended For | Notes |
|--------|----------|------|
| **Claude Code** ⭐ | Most users | Anthropic's AI coding agent; best supported |
| Gemini CLI | Users in the Google ecosystem | Based on Google Gemini |
| Cursor | Those who prefer an AI code editor | A VS Code-based editor |
| Codex | OpenAI users | Based on OpenAI Codex |

### Common Mistakes

- **Selecting Claude Code without an ANTHROPIC_API_KEY**: If you select Claude Code, you must enter your Anthropic API key in Step 7. Get one in advance at [console.anthropic.com](https://console.anthropic.com).

---

## Step 7 — Environment Variable Configuration

Enter the API keys and environment variables needed to run your solution. The values entered here are saved to the `.env` file inside the ZIP.

### Required API Keys

| Key | Required | Where to Get It |
|----|----------|-------|
| `ANTHROPIC_API_KEY` | Always required | [console.anthropic.com](https://console.anthropic.com) |
| `LINEAR_API_KEY` | When the Linear skill is selected | [linear.app/settings/api](https://linear.app/settings/api) |
| `LINEAR_TEAM_ID` | When the Linear skill is selected | Found in your Linear team URL |

### When the Linear Skill Is Selected — Real-Time Tracking Methods

| Method | Cost | Characteristics | Recommended For |
|------|------|------|----------|
| **Cloudflare Tunnel** ⭐ | Free | Static URL, requires the terminal to stay open | Most users |
| ngrok | Paid $8/mo (fixed) / Free (temporary) | URL changes on restart (free plan) | Users with an ngrok account |
| 30-second polling | Free | No webhook needed, up to 30-second delay | When setting up a tunnel is difficult |

### How to Add Environment Variables

1. In the **Add Environment Variable** section at the bottom of the screen, enter the key name (`KEY_NAME`) and value.
2. Click the **+** button or press Enter.
3. If you want to enter a value later, extract the ZIP and edit the `.env` file directly.

### Common Mistakes

- **Proceeding without entering `ANTHROPIC_API_KEY`**: You can move to the next step even when a required key is unset, but an error will occur when you run the ZIP. **Always enter it before proceeding.**
- **Sharing the ZIP file**: The `.env` file contains your actual keys. Do not share the ZIP file with others.
- **Choosing the Cloudflare method on the ngrok free plan**: The URL changes on restart, invalidating the webhook. You would have to re-save the URL on the ClickEye settings page.

---

## Step 8 — Final Review & Project Creation

This shows a summary of all the settings you have entered so far. If everything looks correct, click the **Create Project** button.

### Items to Review

- Company name / Business type / Core product
- Selected prototype name & type
- Selected PM
- Agent & skill list
- Platform
- Number of configured environment variables

### After Project Creation

1. A ZIP file download button is displayed.
2. Extract the ZIP and launch your selected platform (Claude Code, etc.).
3. AI development begins.

---

## Frequently Asked Questions

**Q. If I go back to a previous step, does the AI regenerate?**
A. The prototype is regenerated only when you change the company information (Step 1). The other steps do not regenerate even if you go back.

**Q. What happens if I close the wizard partway through?**
A. Your inputs are preserved as long as the browser session is maintained. If you close the browser completely, you'll have to start over from the beginning.

**Q. What files are in the generated ZIP?**
A. It includes the configuration files for your selected platform (`.claude/`, `.gemini/`, etc.), `.env`, `CLAUDE.md`, `README.md`, and more.

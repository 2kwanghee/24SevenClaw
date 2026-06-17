---
title: AI Team Management
description: A guide to requesting work, generating AI drafts, and syncing with Linear from the AI Team dashboard.
order: 4
---

# AI Team Management

The AI Team dashboard is a 3-tier system for orchestrating your project's AI agent team.

---

## How to Access the Dashboard

1. ClickEye web → Select a project from the project list
2. Project detail page → Click **AI Team** in the left sidebar or top tabs
3. URL: `/projects/{projectId}/ai-team`

---

## Understanding the 3-Tier Structure

| Tier | Responsible Party | Role |
|------|-------|------|
| **Tier 1 — Human** | User | Requests work, approves phases, makes final decisions |
| **Tier 2 — PM AI** | AI | Breaks down work, generates drafts, coordinates reviews, runs the 10-phase pipeline |
| **Tier 3 — AI Team** | AI agents | Executes subtasks in parallel |

---

## Requesting Your First Task

If there are no sessions, a **Request Your First Task** button appears in the center of the screen.

1. Click **Request Your First Task** (or **New Task Request** in the header)
2. Enter the task title and description in the modal
3. Click **Create** → A session is created in the `requested` state

### Managing Multiple Sessions

You can switch between sessions using the top tabs. Each tab shows the session title and current phase.

---

## Phase Flow

| Phase | Description | User Action |
|------|------|-----------|
| requested | Task requested | — |
| decomposed | Subtasks decomposed | — |
| assigned | Assigned to PM | Click the **Generate AI Draft** button |
| drafting | AI draft in progress | — |
| reviewing | Under review | — |
| integrating | Integrating | — |
| validating | Validating | Click the **Approve** button |
| approved | Approved | — |
| transitioning | Transitioning | — |
| completed | Completed | — |

---

## Generating an AI Draft

Once the session phase reaches `assigned`, the **Generate AI Draft** button becomes enabled.

1. Click the **Generate AI Draft** button
2. The AI automatically runs two tasks in order:
   - ① Generates subtask drafts (breaking the work into smaller units)
   - ② Automatically registers Linear issues (if Linear credentials are saved)

### The Screen After Generating an AI Draft

- **Review Rounds**: The drafts written by the AI are displayed
- **Linear Sync Hint**: The list of registered Linear issues is displayed

---

## Linear Sync Hint

When AI draft generation succeeds, the "Linear Sync" panel appears.

### On Successful Automatic Issue Registration

```
✓ Linear issues created: 24S-123, 24S-124, 24S-125
```

You can find the registered issue IDs (e.g., `24S-123`) in Linear.

### When Linear Credentials Are Not Saved

```
Linear credentials not found. Save your API key in settings →
```

In this case, refer to the [Linear Integration Setup Guide](/guide/linear-integration-setup) and save your API key first.

---

## Role Assignment (Reviewing Subtasks)

In the AI Team section (Tier 3), review each subtask card.

Each subtask card displays the following information:

- **Role**: The responsible agent's role (e.g., backend, frontend, devops)
- **Title**: The subtask name
- **Draft Summary**: A work overview written by the AI

Subtasks refresh automatically every 30 seconds.

---

## Final Approval

When the PM AI finishes the work and reaches the `validating` phase, the **Approve** button becomes enabled.

1. Review the AI draft content in the review rounds.
2. If everything looks correct, click the **Approve** button.
3. The session transitions in the order `approved` → `completed`.

---

## Risk Flags

If a potential problem is detected in a session, a risk flag is displayed at the top.

| Flag | Meaning |
|-------|------|
| High Complexity | The scope of work is too broad |
| Dependency Conflict | A dependency issue between subtasks |
| Key Not Set | A required API key is missing |

---

## Refresh and Real-Time Updates

- **Refresh** button: Manually updates the session list and current session summary.
- **AI Team section**: Refreshes automatically every 30 seconds.

---

## Frequently Asked Questions

**Q. What happens if I click Generate AI Draft multiple times?**
A. If a draft already exists, it is not overwritten. The button is enabled only in the `assigned` phase.

**Q. Linear issue registration failed — how do I retry?**
A. Save your API key on the [settings page](/settings/linear), then refresh the AI Team page. Issue registration is retried when you generate an AI draft.

**Q. Can I delete a session?**
A. The current UI does not provide a session deletion feature. You can add new sessions at any time.

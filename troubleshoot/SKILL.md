---
name: troubleshoot
description: >
  Diagnose and fix common WA Monitor issues step by step. Use when: "something is broken", "not working", "getting an error", "fix this", "troubleshoot", "QR code not showing", "no Slack alerts", "webhook not working", "WhatsApp keeps disconnecting", "messages not appearing in dashboard", "SLA alerts not firing", "app is down", "Railway deploy failed", "can't connect WhatsApp", "help something went wrong", "debug", "error in logs", "can't add groups", "groups not loading", "add group button not working", "role not saving", "manager field not showing".
allowed-tools:
  - mcp__workspace__bash
---

# Troubleshoot

Diagnose and fix WA Monitor issues using a structured approach.

Before starting, read `references/error-patterns.md` — it contains all known error patterns with diagnostic commands and fixes.

---

## Step 1: Understand the problem

Ask the user: "What were you trying to do, and what happened instead?"

Keep it to one question. The answer tells you which error pattern to apply.

Map their description to a pattern in `references/error-patterns.md`:

| Symptom keywords | Pattern |
|-----------------|---------|
| QR, scan, code not showing | QR_NOT_SHOWING |
| connected but messages missing | MESSAGES_NOT_CAPTURED |
| no Slack, no alert, no DM | SLACK_ALERTS_NOT_FIRING |
| 401, invalid API key, database error | SUPABASE_AUTH_FAILURE |
| disconnects, logs out, re-scan every time | SESSION_NOT_PERSISTING |
| crash, deploy failed, keeps restarting | APP_CRASH_ON_STARTUP |
| SLA, breach alert missing | SLA_ALERTS_NOT_FIRING |
| add group button, groups not loading in dashboard, modal empty | GROUPS_LOAD_FAILED |
| role not saving, manager fields not appearing, reportees lost | ROLE_NOT_SAVED |

If the symptom doesn't match any pattern, ask the user to check Railway → their Node.js service → **Logs** tab and copy any red error lines.

---

## Step 2: Run diagnostics

Ask if they have access to Railway logs. If yes, ask them to share any red lines.

Run the diagnostic command for the matched pattern from `references/error-patterns.md` using `mcp__workspace__bash`.

You will need credentials — ask for only what is required for the specific diagnostic. If Supabase URL/key were given earlier in the conversation, use them.

---

## Step 3: Apply the fix

Follow the fix steps for the matched pattern. Explain each step in plain language — tell the user what they are doing and why.

For fixes that require browser actions (Railway dashboard, Slack app settings):
- Give numbered step-by-step instructions
- Tell them exactly where to click
- Tell them what they should see after each step

For fixes that can be verified programmatically, run the verification command from `references/error-patterns.md`.

---

## Step 4: Verify the fix

After applying the fix, re-run the diagnostic check. Confirm whether the issue is resolved.

If resolved → tell the user what was wrong and confirm it is now fixed.

If not resolved after 2 fix attempts → escalate:
- Ask the user to share the full content of Railway → Node.js service → Logs (last 50 lines)
- Analyse the logs carefully for clues not covered by the standard patterns
- If still unresolved, suggest they open a support thread and share: app URL, error screenshot, and the fix attempts made

---

## Step 5: Prevent recurrence

After fixing, briefly explain what caused the issue and how to avoid it in future. Keep it to 1–2 sentences in plain language.

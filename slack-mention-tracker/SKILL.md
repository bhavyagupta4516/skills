---
name: slack-mention-tracker
description: Automatically track and summarize Slack mentions in working hours. Sends you a DM every 3 hours (10am, 1pm, 4pm IST) with accumulated mentions, thread replies, and context. Marks threads as "done" with a green tick (✅) emoji on your message to weed them out. Mentions outside working hours (6pm-10am) roll into the first 10am alert. Use this skill whenever you want to set up mention tracking, check your accumulated Slack mentions, or configure the alert schedule. Works with Cowork for scheduled automation.
---

# Slack Mention Tracker

A Slack automation skill that helps you stay on top of mentions and thread activity without constant interruptions.

## What It Does

- **Tracks mentions** across all Slack channels you're in
- **Sends DM alerts** every 3 hours during working hours (10am, 1pm, 4pm IST)
- **Accumulates mentions** since the last alert in each batch
- **Marks threads complete** by adding ✅ to your message in that thread (auto-weeds for next 3 hours)
- **Buffers off-hours mentions** and includes them in the first 10am alert
- **Prevents duplicates** within a thread after first alert (unless ✅ is removed)

---

## Scope: What Gets Tracked

✅ **Direct mentions** (`@username`)  
✅ **Thread replies** that mention you  
✅ **Threaded conversations** where you're mentioned in replies (not just top-level)  
❌ **Reactions** to your messages (not tracked)  
❌ **Quotes/references** without explicit mentions (not tracked)  

---

## How It Works

### 1. **Detection Phase** (Every 3 hours + continuous)

The bot monitors all channels you're a member of and logs:
- **Direct mentions:** `@yourname` in any message or thread
- **Thread replies:** Any reply in a thread where you were mentioned
- **Timestamp:** When the mention occurred
- **Message context:** Full text of the mentioning message
- **Channel:** Where the mention happened
- **Thread link:** Slack permalink to the specific message

### 2. **Filtering Phase** (Before each alert)

Before sending an alert, the bot checks:
- ✅ **Green tick status:** Has the user reacted with ✅ to any of their messages in this thread in the last 3 hours?
  - If yes → **Weed out** the entire thread from this alert batch
  - If no → **Include** the thread
- **Duplicate prevention:** If the thread was already alerted on in the previous batch AND no new mentions, skip it
- **First mention in thread:** Track which threads you've already been notified about in this cycle

### 3. **Buffering Phase** (Off-hours)

- Mentions between 6pm and 10am IST are **stored but not alerted**
- They accumulate and are **included in the first 10am alert**
- After the 10am alert, the buffer clears for the next cycle

### 4. **Alert Format** (DM to you, every 3 hours)

```
📌 Slack Mentions Summary — [Time Window]

* Date: May 28, 2026 2:15 PM
* Channel: #engineering
* Context: "@bhavya can you review this PR? It's pretty urgent"
* Link: https://slack.com/archives/C123456/p1234567890

* Date: May 28, 2026 2:45 PM
* Channel: #product
* Context: "Jumping on this thread with @bhavya — thoughts on the deadline shift?"
* Link: https://slack.com/archives/C789012/p9876543210

[Add ✅ to your message in any thread above to mark it complete. It'll be auto-weeded from future alerts for 3 hours.]
```

---

## Using Green Tick to Weed Out

**Goal:** Mark a thread as "handled" so you don't get re-alerted about it.

### Steps:
1. Read the mention in the alert DM
2. Click the thread link to open it in Slack
3. **Find your message** (or any message you own) in that thread
4. **Add the ✅ (green check) emoji reaction** to it
5. Next alert cycle: That thread will be **automatically filtered out** for the next 3 hours
6. After 3 hours, if new mentions appear, they'll be tracked again

### What "Entire Thread" Means:
- If the thread contains multiple mentions of you, adding ✅ to *one of your messages* weeds the entire thread
- All future mentions in that thread in the current 3-hour window are ignored
- New mentions in that thread after 3 hours will be tracked again

---

## Setup & Configuration

### Prerequisites:
- Access to **all Slack channels** (or at least the ones you want tracked)
- A **Slack bot token** with permissions:
  - `channels:read` — List all channels
  - `groups:read` — Read private channels
  - `users:read` — Identify users
  - `chat:read` — Read message content
  - `reactions:read` — Check for ✅ reactions
  - `chat:write` — Send DM alerts

### Running the Bot:

#### Option 1: Cowork (Recommended for Automation)
Use Cowork to schedule the bot to run at:
- 10:00 AM IST
- 1:00 PM IST
- 4:00 PM IST

This ensures you get alerts on time without manual intervention.

```bash
# Run via Cowork scheduler
claude-cowork schedule-job \
  --name "Slack Mention Tracker" \
  --times "10:00 IST, 13:00 IST, 16:00 IST" \
  --job-script mention-tracker.py
```

#### Option 2: Manual Check
Run the script on-demand whenever you want:
```bash
python mention-tracker.py --check
```

---

## Edge Cases & Behavior

| Scenario | Behavior |
|----------|----------|
| **Multiple mentions in same thread** | Only alerted once per 3-hour window; subsequent mentions ignored |
| **New mention after you ✅'d** | Ignored for 3 hours; tracked again after the window |
| **Mention at 9:45pm** | Buffered and included in 10am alert next day |
| **Mention at 6:15pm** | Buffered until next working window |
| **Thread with no new mentions** | Not included in alert even if you received it before |
| **Someone replies to your old message** | Tracked as a new mention if they @mention you |
| **You mention yourself** | Not tracked (would be too meta) |

---

## State Management

The bot maintains minimal state:
- **Weeded threads:** Thread IDs with ✅ reactions (expires after 3 hours)
- **Alerted threads:** Which threads you've already been notified about this cycle
- **Buffer:** Off-hours mentions (cleared at 10am)

All state is time-windowed and automatically cleaned up.

---

## Troubleshooting

**Q: I added ✅ but the thread still appears in the next alert**
- ✅ may not have been detected. Try clicking your message again and checking the reaction is there.
- It's been >3 hours since you added it — state has reset.

**Q: I'm getting alerts outside 10am-6pm**
- This shouldn't happen. Check your timezone is set to IST.
- Cowork job schedule may be off.

**Q: Some mentions aren't showing up**
- The bot may not have access to that channel. Check permissions.
- The message may not contain an explicit @mention or thread reply.

**Q: Can I change the alert times?**
- Yes! Update the Cowork schedule or pass a config flag:
```bash
python mention-tracker.py --times "9:00,12:00,15:00,18:00"
```

---

## Future Enhancements

- Slack rich message formatting (thread previews, participant list)
- Custom keywords beyond mentions (e.g., track specific channel activity)
- Weekly digest summary
- Integration with calendar (skip alerts during meetings)

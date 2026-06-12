---
name: linkedin-engagement-reminder
description: >
  Reminds the LimeChat Slack team to engage with company LinkedIn posts shared in #general.
  Detects messages containing LinkedIn post URLs (linkedin.com/posts/), checks the total
  reaction count on the Slack message, and DMs every workspace member individually if the
  count is below a user-specified threshold. Skips the person who posted the link.
  Only runs within working hours (9 AM–6 PM IST, Mon–Fri).

  Use this skill EVERY TIME someone says: "run LinkedIn reminder", "check LinkedIn engagement",
  "remind team about LinkedIn post", "send LinkedIn reminders", "nudge team on LinkedIn",
  "who hasn't engaged with LinkedIn", "run the LinkedIn bot", or any request to follow up on
  LinkedIn post engagement in Slack. Also use when setting up recurring LinkedIn reminders.
---

# LinkedIn Engagement Reminder

Scans #general for LinkedIn posts, checks total Slack reaction counts, and DMs the whole
team individually if engagement is below target — privately, no public call-outs.

---

## Configuration

| Setting         | Value                                              |
|-----------------|----------------------------------------------------|
| Watch channel   | #general (`CTB0M279U`)                             |
| URL pattern     | Must contain `linkedin.com` AND `/posts/`          |
| Remind window   | Last 2 working days                                |
| Working hours   | 9:00 AM – 6:00 PM IST (UTC+5:30), Mon–Fri         |
| Stop condition  | Total reaction count ≥ user-specified threshold    |
| Reminder style  | Individual DM to each workspace member             |
| Skip            | The user who originally posted the link in Slack   |

---

## Execution Steps

### Step 0 — Ask for Engagement Threshold
At the start of every run, ask:

> "What's the reaction target for today? (How many total reactions on the Slack post before we stop reminding?)"

Wait for the user's number. Store as `ENGAGEMENT_THRESHOLD`. Do not proceed without it.

---

### Step 1 — Working Hours Gate
Compute current IST time (UTC+5:30).
- If outside 9 AM–6 PM IST **or** it is Saturday/Sunday → stop and respond:
  > "⏰ Outside working hours (9 AM–6 PM IST, Mon–Fri). No reminders sent."

---

### Step 2 — Find LinkedIn Posts in #general
Use `slack_search_public_and_private` with:
```
query: "in:<#CTB0M279U> linkedin.com/posts/"
sort: timestamp
sort_dir: desc
```

For each result extract:
- `message_ts` — Slack message timestamp
- `poster_user_id` — user who shared the link
- `linkedin_url` — the full LinkedIn URL
- `posted_at` — message datetime

**Filter:** Keep only messages from the last 2 working days (skip weekends when counting back).

If no posts found → respond:
> "📭 No LinkedIn posts found in #general in the last 2 working days. Nothing to do!"

---

### Step 3 — Check Reaction Count Per Post
For each post, use `slack_read_thread` with the post's `message_ts` to fetch the parent message.

Read the `reactions` field and sum **all** reaction counts across every emoji type.
Store as `total_reactions` for that post.

**Decision:**
- If `total_reactions >= ENGAGEMENT_THRESHOLD` → skip this post, log:
  > "✅ [linkedin_url] — Target reached ({total_reactions} reactions). No reminders sent."
- If `total_reactions < ENGAGEMENT_THRESHOLD` → proceed to Step 4 for this post.

---

### Step 4 — Get All Active Workspace Members
Use `slack_search_users` with a broad query to get all workspace members.

Keep only users where:
- `is_bot = false`
- `deleted / deactivated = false`

Store as `all_member_ids`.

---

### Step 5 — Send Individual DMs
For each post that needs reminders, DM every member in `all_member_ids` **except** `poster_user_id`.

Use `slack_send_message` with the member's `user_id` as the channel. Message:

```
Hey [first_name] 👋

Just a quick nudge — we shared a LinkedIn post and your support really helps us grow! 🚀

🔗 [linkedin_url]

Takes 10 seconds — a like or comment goes a long way. 🙌

_(React to the post in #general once you've engaged so we can track team support!)_
```

Replace `[first_name]` with the user's Slack display first name.
Replace `[linkedin_url]` with the actual LinkedIn URL.

---

### Step 6 — Summary Report
After all DMs are sent, output:

```
✅ LinkedIn Reminder Run Complete

Threshold set: [N] reactions
────────────────────────────
Post 1: [linkedin_url]
  Current reactions: X  |  Target: N
  Status: Reminders sent / Target already reached
  DMs sent to: Y members

Post 2: [linkedin_url]  (if applicable)
  ...
────────────────────────────
Total DMs sent this run: Z
```

---

## Edge Cases

| Situation | Behaviour |
|---|---|
| Multiple posts in the 2-day window | Run Steps 3–5 independently per post |
| Post has zero reactions | `total_reactions = 0`, remind everyone |
| Post has no reactions field | Treat as zero reactions — remind everyone |
| Poster is a bot or deactivated account | Skip in member list; also safe to skip DM to poster |
| User's first name unavailable | Fall back to their Slack display name |
| Same user posted multiple LinkedIn links | Skip them as poster for each post they shared |

---

## Scheduling (Recurring Use)

This skill is designed to be triggered every 2 hours during working hours:
- **Run times:** ~9 AM, 11 AM, 1 PM, 3 PM, 5 PM IST
- **Coverage:** Posts from the last 2 working days
- **Self-gating:** The working hours check in Step 1 makes it safe to call on any schedule

To automate, set up a Cowork schedule that calls:
> "Run the LinkedIn engagement reminder skill"

The skill will ask for the threshold at the start of each run, then proceed automatically.

---

## Tools Required
- **Slack MCP** — `slack_search_public_and_private`, `slack_read_thread`, `slack_send_message`, `slack_search_users`
- Channel: #general (`CTB0M279U`)

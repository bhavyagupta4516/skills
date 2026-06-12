# Slack Mention Tracker Skill

Automatically track and summarize Slack mentions during working hours with smart filtering and weeding.

## What It Does

- **Tracks mentions** across all Slack channels you're in
- **Sends DM alerts** every 3 hours (10am, 1pm, 4pm IST) with accumulated mentions
- **Filters duplicates** within a thread per cycle
- **Weed threads** by adding ✅ emoji (auto-filters for next 3 hours)
- **Buffers off-hours** mentions and includes them in the 10am alert

## Components

### `mention_tracker.py`
Core logic with these classes:

- **MentionTrackerState**: Manages persistent state (JSON file)
- **MentionExtractor**: Parses Slack search results
- **MentionFilter**: Applies filtering rules (weeded, duplicates)
- **WorkingHoursManager**: Handles IST timezone logic
- **AlertFormatter**: Formats DMs
- **MentionTracker**: Orchestrates the flow

### `cowork_integration.py`
Wrapper that integrates with Cowork's Slack MCP connectors

### `test_mention_tracker.py`
Comprehensive test suite (all passing ✅)

## Setup Instructions

### 1. Prerequisites

```bash
pip install pytz --break-system-packages
```

### 2. Get Your Slack User ID

Find it in Slack:
1. Click your profile photo
2. Click "Profile"
3. Click the three dots → "Copy user ID"
4. It looks like: `U064S0G74L9`

### 3. Configure Cowork Scheduler

Create a scheduled job that calls the script every 3 hours:

```bash
cowork schedule-job \
  --name "Slack Mention Tracker" \
  --schedule "0 10,13,16 * * *" \
  --command "python /path/to/mention_tracker.py --user-id YOUR_USER_ID"
```

Or with the Cowork integration:

```bash
cowork schedule-job \
  --name "Slack Mention Tracker" \
  --schedule "0 10,13,16 * * *" \
  --command "python /path/to/cowork_integration.py --user-id YOUR_USER_ID"
```

### 4. Test It

Dry run (see what would be sent):

```bash
python mention_tracker.py --user-id YOUR_USER_ID --dry-run
```

## Usage

### During Working Hours

The script runs automatically at 10am, 1pm, 4pm IST. You'll receive a DM like:

```
📌 Slack Mentions Summary — 2:15 PM

1. #engineering
Date: May 28, 2026 2:15 PM
From: @john
Message: Can you review this PR? It's urgent
Link: https://slack.com/archives/C123456/p1234567890

2. #product
Date: May 28, 2026 2:45 PM
From: @jane
Message: @bhavya thoughts on deadline?
Link: https://slack.com/archives/C789012/p9876543210

━━━━━━━━━━━━━━━━━━━━━━
Add ✅ to your message in any thread above to mark it complete.
It'll be auto-weeded from future alerts for 3 hours.
```

### Marking Threads as "Done"

1. Click the thread link in the DM
2. Find your message in that thread
3. React with ✅ (green check emoji)
4. Next alert cycle: thread is filtered out

## State Management

State is stored in `/tmp/mention_tracker_state.json`:

```json
{
  "last_alert_cycle": "2026-05-28T10:00:00+05:30",
  "weeded_threads": {
    "C123:p456": "2026-05-28T13:30:00+05:30"
  },
  "alerted_threads_this_cycle": [
    "C123:p456",
    "C789:p012"
  ],
  "buffer": [],
  "cycle_start": "2026-05-28T10:00:00+05:30"
}
```

**Important:** State resets every 3 hours. Weeded threads expire after 3 hours and are tracked again.

## Filtering Rules

| Condition | Result |
|-----------|--------|
| Thread has ✅ in last 3 hours | Filtered out |
| Already alerted about thread this cycle | Filtered out |
| First time mention in thread | Included |
| Mention outside 10am-6pm | Buffered for 10am alert |

## Running Tests

```bash
python test_mention_tracker.py
```

All tests should pass ✅

## Troubleshooting

**Q: I'm not getting alerts**
- Check if you're running within working hours (10am-6pm IST)
- Verify Cowork scheduler is running
- Run: `python mention_tracker.py --user-id YOUR_USER_ID --dry-run`

**Q: I added ✅ but still got mentioned in the thread**
- ✅ must be on YOUR message (not someone else's)
- It expires after 3 hours

**Q: Getting duplicate alerts**
- This shouldn't happen. Check if state file is being persisted correctly.
- Verify: `cat /tmp/mention_tracker_state.json`

**Q: My timezone is wrong**
- State uses IST (Asia/Kolkata) hardcoded
- To change: Edit `IST = pytz.timezone('Asia/Kolkata')` in script

## Architecture Notes

- **Idempotent**: Safe to run multiple times without duplicate alerts
- **Stateful**: Minimal state in JSON (no database needed)
- **Timezone-aware**: All times in IST
- **Slack-native**: Uses Slack search API for efficiency
- **Cowork-integrated**: Designed for scheduled execution

## Next Steps

1. Save your user ID somewhere safe
2. Configure Cowork scheduler
3. Test with `--dry-run` first
4. Verify DM is sent at next alert time

## Support

For issues or enhancements, check the state file and test suite first.

---
name: meeting-recap-automation
description: Automate meeting recap workflow by fetching tl;dv notes and updating Google Calendar event descriptions with AI-generated summaries, decisions, and action items. Use when generating meeting recaps, capturing action items from recorded meetings, batch-updating calendar events, or reviewing meeting summaries. Triggers on "create meeting recaps", "generate today's meeting summaries", "update meetings with notes", "recap my meetings", "show meeting notes". Uses Google Calendar MCP to list/update events, Slack MCP for DM approvals, and tl;dv API for highlights.
compatibility:
  - Google Calendar MCP (list and update events)
  - Slack MCP (send DMs and get approvals)
  - tl;dv API (fetch highlights and transcripts)
  - TLDV_TOKEN environment variable
---

# Meeting Recap Automation Skill

Automatically capture meeting notes from tl;dv, review them via Slack, and update your Google Calendar event descriptions with AI-generated summaries, decisions, and action items.

## Workflow Overview

```
1. Fetch today's calendar events (Google Calendar MCP)
   ↓
2. Check tl;dv for recorded meetings matching calendar events
   ↓
3. Extract AI-generated notes, highlights, topics, decisions, action items
   ↓
4. Send Slack DM with summary + ask for approval (Slack MCP)
   ↓
5. On approval: Update Google Calendar event description (Google Calendar MCP)
   ↓
6. Handle edge cases: missing recordings, ad-hoc meetings, manual input
```

---

## How to Use This Skill

### Prerequisites

1. **Google Calendar MCP** - Connected and authorized
2. **Slack MCP** - Connected with DM permissions
3. **tl;dv API Token** - Set as `TLDV_TOKEN` environment variable
4. **Plan Type** - tl;dv Business/Pro/Enterprise (Free plans don't have API access)

### Quick Start

```
"Recap today's meetings"
"Generate meeting summaries for [date]"
"Update calendar with meeting notes"
"Show me the action items from today's meetings"
```

---

## Integration Points

### Google Calendar MCP Usage

**List today's events:**
```
Use Google Calendar MCP to:
- Query primary calendar for today's events
- Extract: event ID, title, start/end times, attendees, description
```

**Update event descriptions:**
```
Use Google Calendar MCP to:
- PATCH event with new description containing recap
- Keep original attendees/times intact
- Add timestamp and tl;dv link
```

### Slack MCP Usage

**Send approval request:**
```
Use Slack MCP to:
- Send DM to authenticated user
- Include formatted meeting recap
- Add interactive buttons: [Approve] [Edit] [Skip]
```

**Collect user response:**
```
Wait for user to:
- Approve recap and update calendar
- Edit recap with custom notes
- Skip if no tl;dv recording found
```

### tl;dv API Integration

**Fetch meetings:**
```bash
GET https://pasta.tldv.io/v1alpha1/meetings?pageSize=50
Headers: x-api-key: $TLDV_TOKEN
```

**Extract highlights:**
```bash
GET https://pasta.tldv.io/v1alpha1/meetings/{meeting_id}/highlights
Headers: x-api-key: $TLDV_TOKEN
```

**Get transcript (if needed):**
```bash
GET https://pasta.tldv.io/v1alpha1/meetings/{meeting_id}/transcript
Headers: x-api-key: $TLDV_TOKEN
```

---

## Step-by-Step Implementation

### Phase 1: Fetch Data

**1A. Get Calendar Events (Google Calendar MCP)**
- Query today's events
- Extract meeting titles, times, attendees
- Return as structured JSON

**1B. Get tl;dv Meetings (tl;dv API)**
- Fetch all meetings from today using TLDV_TOKEN
- Filter by date
- Extract: id, name, happenedAt, duration, organizer

### Phase 2: Match & Extract

**2A. Match Calendar to tl;dv**
- For each calendar event, find matching tl;dv recording:
  * Title similarity (fuzzy match)
  * Time proximity (within ±5 minutes)
- Flag unmatched recordings as ad-hoc meetings

**2B. Extract Notes (tl;dv API)**
For each matched meeting:
- `GET /highlights` → AI topics and summaries
- `GET /transcript` → Parse for action items, decisions
- Compile into structured format:
  ```json
  {
    "summary": "AI-generated summary",
    "topics": [
      {"title": "Topic 1", "summary": "..."},
      {"title": "Topic 2", "summary": "..."}
    ],
    "decisions": ["Decision 1", "Decision 2"],
    "action_items": ["Action 1", "Action 2"]
  }
  ```

### Phase 3: Review & Approve

**3A. Format Slack Message (Slack MCP)**
```
📋 **Meeting Recap: [Meeting Title]**
⏱️ Duration: [45 min]

**Summary**
[AI-generated summary]

**Topics Discussed**
• Topic 1: [summary]
• Topic 2: [summary]

**Decisions Made**
☑️ Decision 1
☑️ Decision 2

**Action Items**
→ Action 1 (Owner: Name)
→ Action 2 (Owner: Name)

---
✅ Ready to update calendar? [Yes] [Edit] [Skip]
```

**3B. Send DM & Collect Response (Slack MCP)**
- Send formatted message to user
- Wait for response via interactive buttons
- On [Edit]: Ask user for custom notes
- On [Skip]: Move to next meeting

### Phase 4: Update & Finalize

**4A. Update Calendar (Google Calendar MCP)**
On user approval:
- Format description with recap:
  ```
  **Meeting Summary**
  [AI-generated summary]
  
  **Topics Discussed**
  • Topic 1
  • Topic 2
  
  **Key Decisions**
  ☑️ Decision 1
  ☑️ Decision 2
  
  **Action Items**
  → Action 1 (Owner)
  → Action 2 (Owner)
  
  ---
  *Updated by Meeting Recap Automation*
  *Recorded on tl;dv: [link]*
  ```
- PATCH event with new description

**4B. Confirm (Slack MCP)**
- Send confirmation DM: "✅ Updated [Meeting Name]"
- Provide link to calendar event

### Phase 5: Handle Edge Cases

**Case A: Calendar event but no tl;dv recording**
```
Slack DM:
"📹 No recording found for [Meeting] in tl;dv.
Did you attend? [Yes, add notes] [No, skip]"

If "Yes, add notes":
  → Ask user to provide brief summary
  → Update calendar with user-provided recap

If "No, skip":
  → Skip this event
```

**Case B: tl;dv recording but no calendar event (ad-hoc meeting)**
```
Slack DM:
"🎬 Found a recording: [Meeting Name] (45 min)
Did you attend this? [Yes] [No]"

If "Yes":
  → Create recap as drafted recap email
  → Optionally add to calendar

If "No":
  → Skip
```

**Case C: Multiple similar meetings**
```
Ask for clarification:
"Found multiple recordings:
1. [Meeting A] - 10:00 AM
2. [Meeting B] - 10:15 AM

Which one is [Calendar Event]?"
```

---

## Expected Outputs

### Per Meeting:
- ✅ Calendar event updated with formatted recap
- ✅ Slack DM confirmation
- ✅ tl;dv link in calendar description

### Summary Report:
```
✨ **Today's Meeting Recaps Complete**

✅ Updated: 5 events
⏳ Pending approval: 1 event
⏭️ Skipped: 1 event (no recording)
📝 Manual input needed: 1 event

View all in your calendar
```

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| tl;dv API unreachable | Graceful failure + Slack notification |
| Transcript not processed yet | Fall back to highlights only |
| No matching calendar event | Ask user if they attended |
| API rate limits | Retry with exponential backoff |
| Slack DM fails | Log error, continue with next meeting |
| Calendar update fails | Notify user, ask to update manually |

---

## Configuration

### Environment Variables Required:
```bash
TLDV_TOKEN=7d730ba8-8a19-4fb9-b47a-efdbd28ee054
```

### Optional Tweaks:
- Time proximity threshold: ±5 minutes (adjustable)
- Title similarity threshold: 0.7 (70% match)
- Max topics to include: 10
- Retry count: 3 with exponential backoff

---

## Testing Checklist

Before running on all meetings:
- [ ] tl;dv API token is valid and active
- [ ] Google Calendar MCP is connected
- [ ] Slack MCP can send DMs
- [ ] Test with 1 meeting: fetch → review → update
- [ ] Verify Slack message formatting
- [ ] Test edge case: meeting in calendar but no tl;dv recording
- [ ] Test edge case: tl;dv recording but no calendar event
- [ ] Verify action items/decisions extraction

---

## Usage Examples

### Example 1: Single Meeting Recap
```
"Show me the recap for my 2 PM meeting"
→ Fetches notes from tl;dv
→ Sends Slack DM for review
→ Updates calendar on approval
```

### Example 2: Batch Processing
```
"Recap all my meetings today"
→ Fetches all calendar events + tl;dv recordings
→ Matches them intelligently
→ Sends batch Slack DM with all recaps
→ Updates all on approval
```

### Example 3: Ad-hoc Meeting
```
"I just recorded a meeting on tl;dv, add recap to calendar"
→ Finds unmatched tl;dv recording
→ Extracts notes
→ Asks if you attended + to select which calendar event (if any)
→ Updates calendar
```

---

## Tips & Best Practices

### For Best Results:
1. **Calendar titles** - Keep them consistent with tl;dv recording titles
2. **Recording timing** - tl;dv processes transcripts within 2-5 minutes
3. **Manual edits** - Can edit generated recap before calendar update
4. **Ad-hoc meetings** - Check Slack before end of day for unmatched recordings

### Privacy & Security:
- tl;dv API token is required but never exposed in calendar descriptions
- Slack DMs are between you and Claude (authenticated)
- Calendar descriptions are updated with business-appropriate summaries only

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "TLDV_TOKEN not found" | Ensure environment variable is set |
| "Google Calendar MCP not connected" | Connect in Claude.ai settings |
| "Slack DM not received" | Verify Slack MCP permissions |
| "No topics extracted" | tl;dv still processing; wait 5 minutes and retry |
| "Title matching fails" | Titles don't match; use [Edit] to add custom recap |
| "API rate limited" | Wait a few minutes and retry |


#!/usr/bin/env python3
"""
Cowork Integration - Wraps mention_tracker.py with Slack MCP calls
This script is meant to be called by Cowork's scheduler
"""

import json
import sys
from datetime import datetime, timedelta
import pytz
from mention_tracker import (
    MentionTracker,
    MentionExtractor,
    WorkingHoursManager,
)

IST = pytz.timezone('Asia/Kolkata')


def fetch_mentions_from_slack(since: datetime, user_id: str) -> list:
    """
    Fetch mentions using Slack MCP connector
    
    This would be called via Cowork's MCP bridge:
    - Call slack_search_public with query: "to:me after:{timestamp}"
    - Parse results and extract mention data
    """
    # NOTE: In real Cowork environment, this would be:
    # from anthropic import Anthropic
    # client = Anthropic()
    # response = client.messages.create(
    #     model="claude-opus-4-1",
    #     tools=[slack_search_public],
    #     messages=[{
    #         "role": "user",
    #         "content": f"Search for all mentions to me since {since.isoformat()}"
    #     }]
    # )
    
    print(f"[MCP] Calling slack_search_public for mentions since {since.isoformat()}")
    return []


def send_dm_to_slack(user_id: str, message: str) -> bool:
    """
    Send DM using Slack MCP connector
    
    This would be called via Cowork's MCP bridge:
    - Call slack_send_message with channel_id=user_id
    """
    # NOTE: In real Cowork environment, this would be:
    # from anthropic import Anthropic
    # client = Anthropic()
    # response = client.messages.create(
    #     model="claude-opus-4-1",
    #     tools=[slack_send_message],
    #     messages=[{
    #         "role": "user",
    #         "content": f"Send this DM to {user_id}: {message}"
    #     }]
    # )
    
    print(f"[MCP] Calling slack_send_message to {user_id}")
    return True


def run_tracker_cycle(user_id: str, dry_run: bool = False) -> dict:
    """
    Execute one tracker cycle with MCP integration
    
    Returns:
        Result dict with execution details
    """
    
    # Initialize tracker
    tracker = MentionTracker(user_id)
    
    # Skip if outside working hours
    if not WorkingHoursManager.is_working_hours():
        return {
            "status": "skipped",
            "reason": "Outside working hours (6pm-10am IST)",
            "timestamp": datetime.now(IST).isoformat(),
        }
    
    # Determine alert window
    window_start = WorkingHoursManager.get_alert_window_start()
    
    # Fetch mentions from Slack via MCP
    mentions = fetch_mentions_from_slack(window_start, user_id)
    
    # Extract structured data
    structured_mentions = MentionExtractor.extract_mentions(mentions)
    
    # Filter mentions
    weeded_threads = tracker._get_weeded_threads()
    filtered_mentions = MentionFilter.filter_mentions(
        structured_mentions,
        tracker.state,
        weeded_threads
    )
    
    result = {
        "status": "success",
        "timestamp": datetime.now(IST).isoformat(),
        "alert_window": f"{window_start.isoformat()} to now",
        "mentions_found": len(mentions),
        "mentions_alerted": len(filtered_mentions),
        "dm_sent": False,
    }
    
    # Send DM if there are mentions
    if filtered_mentions and not dry_run:
        from mention_tracker import AlertFormatter
        cycle_time = datetime.now(IST).strftime("%I:%M %p")
        alert_message = AlertFormatter.format_alert(filtered_mentions, cycle_time)
        
        dm_sent = send_dm_to_slack(user_id, alert_message)
        result["dm_sent"] = dm_sent
    
    # Update state
    tracker._update_state(filtered_mentions)
    
    return result


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Slack Mention Tracker - Cowork Integration")
    parser.add_argument("--user-id", required=True, help="Your Slack user ID")
    parser.add_argument("--dry-run", action="store_true", help="Run without sending DM")
    
    args = parser.parse_args()
    
    result = run_tracker_cycle(args.user_id, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    
    return 0 if result["status"] in ["success", "skipped"] else 1


if __name__ == "__main__":
    sys.exit(main())

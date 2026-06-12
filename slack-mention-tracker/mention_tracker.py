#!/usr/bin/env python3
"""
Slack Mention Tracker - Main orchestration script
Runs every 3 hours during working hours (10am, 1pm, 4pm IST)
"""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import pytz

IST = pytz.timezone('Asia/Kolkata')


class MentionTrackerState:
    """Manages state persistence and retrieval"""
    
    STATE_FILE = "/tmp/mention_tracker_state.json"
    
    @staticmethod
    def load() -> Dict:
        """Load state from file"""
        if os.path.exists(MentionTrackerState.STATE_FILE):
            try:
                with open(MentionTrackerState.STATE_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return MentionTrackerState._init_state()
        return MentionTrackerState._init_state()
    
    @staticmethod
    def save(state: Dict) -> None:
        """Save state to file"""
        with open(MentionTrackerState.STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    
    @staticmethod
    def _init_state() -> Dict:
        """Initialize fresh state"""
        now = datetime.now(IST).isoformat()
        return {
            "last_alert_cycle": now,
            "weeded_threads": {},
            "alerted_threads_this_cycle": [],
            "buffer": [],
            "cycle_start": now
        }


class MentionExtractor:
    """Extracts and parses mentions from search results"""
    
    @staticmethod
    def extract_mentions(search_results: List[Dict]) -> List[Dict]:
        """Transform Slack search results into structured mention data"""
        mentions = []
        
        for result in search_results:
            mention = {
                "date": result.get("ts_human", "Unknown"),
                "timestamp": result.get("ts", ""),
                "channel": result.get("channel_name", result.get("channel", "Unknown")),
                "channel_id": result.get("channel_id", ""),
                "context": result.get("text", "")[:500],
                "thread_link": MentionExtractor._build_thread_link(
                    result.get("channel_id", ""),
                    result.get("ts", "")
                ),
                "message_ts": result.get("ts", ""),
                "user": result.get("username", "Unknown"),
                "is_thread_reply": result.get("thread_ts") is not None,
            }
            mentions.append(mention)
        
        return mentions
    
    @staticmethod
    def _build_thread_link(channel_id: str, message_ts: str) -> str:
        """Build Slack thread permalink"""
        if not channel_id or not message_ts:
            return ""
        ts_clean = message_ts.replace(".", "")
        return f"https://slack.com/archives/{channel_id}/p{ts_clean}"


class MentionFilter:
    """Filters mentions based on state and rules"""
    
    @staticmethod
    def filter_mentions(
        mentions: List[Dict],
        state: Dict,
        weeded_threads: Set[str]
    ) -> List[Dict]:
        """Apply filtering rules to mentions"""
        filtered = []
        seen_threads = set(state.get("alerted_threads_this_cycle", []))
        
        for mention in mentions:
            thread_id = mention["message_ts"]
            
            if thread_id in weeded_threads:
                continue
            
            if thread_id in seen_threads:
                continue
            
            filtered.append(mention)
            seen_threads.add(thread_id)
        
        return filtered


class WorkingHoursManager:
    """Manages working hours logic (10am-6pm IST)"""
    
    WORKING_HOURS_START = 10
    WORKING_HOURS_END = 18
    ALERT_TIMES = [10, 13, 16]
    
    @staticmethod
    def is_working_hours(dt: Optional[datetime] = None) -> bool:
        """Check if current time is within working hours"""
        if dt is None:
            dt = datetime.now(IST)
        return WorkingHoursManager.WORKING_HOURS_START <= dt.hour < WorkingHoursManager.WORKING_HOURS_END
    
    @staticmethod
    def get_alert_window_start(dt: Optional[datetime] = None) -> datetime:
        """Get the start of the current/last alert window"""
        if dt is None:
            dt = datetime.now(IST)
        
        hour = dt.hour
        
        if hour < 10:
            yesterday = dt - timedelta(days=1)
            return yesterday.replace(hour=16, minute=0, second=0, microsecond=0)
        elif hour < 13:
            return dt.replace(hour=10, minute=0, second=0, microsecond=0)
        elif hour < 16:
            return dt.replace(hour=13, minute=0, second=0, microsecond=0)
        else:
            return dt.replace(hour=16, minute=0, second=0, microsecond=0)
    
    @staticmethod
    def should_include_buffer(dt: Optional[datetime] = None) -> bool:
        """Should this alert include off-hours buffer (only at 10am)"""
        if dt is None:
            dt = datetime.now(IST)
        return dt.hour == 10


class AlertFormatter:
    """Formats mentions into DM alert"""
    
    @staticmethod
    def format_alert(mentions: List[Dict], cycle_time: str) -> str:
        """Format mentions into Slack DM message"""
        if not mentions:
            return "📌 *Slack Mentions Summary*\n\nNo new mentions in this window."
        
        lines = [
            f"📌 *Slack Mentions Summary* — {cycle_time}",
            "",
        ]
        
        for i, mention in enumerate(mentions, 1):
            lines.extend([
                f"*{i}. {mention['channel']}*",
                f"_Date:_ {mention['date']}",
                f"_From:_ @{mention['user']}",
                f"_Message:_ {mention['context']}",
                f"_Link:_ <{mention['thread_link']}|View Thread>",
                "",
            ])
        
        lines.extend([
            "━━━━━━━━━━━━━━━━━━━━━━",
            "_Add ✅ to your message in any thread above to mark it complete._",
            "_It'll be auto-weeded from future alerts for 3 hours._",
        ])
        
        return "\n".join(lines)


class MentionTracker:
    """Main orchestration class"""
    
    def __init__(self, user_id: str):
        """Initialize tracker"""
        self.user_id = user_id
        self.state = MentionTrackerState.load()
    
    def run(self, dry_run: bool = False) -> Dict:
        """Main execution flow"""
        result = {
            "status": "success",
            "timestamp": datetime.now(IST).isoformat(),
            "mentions_found": 0,
            "mentions_alerted": 0,
            "dm_sent": False,
            "errors": [],
        }
        
        try:
            if not WorkingHoursManager.is_working_hours():
                result["status"] = "skipped"
                result["reason"] = "Outside working hours (6pm-10am IST)"
                return result
            
            window_start = WorkingHoursManager.get_alert_window_start()
            result["alert_window"] = f"{window_start.isoformat()} to now"
            
            mentions = self._fetch_mentions(window_start)
            result["mentions_found"] = len(mentions)
            
            weeded_threads = self._get_weeded_threads()
            filtered_mentions = MentionFilter.filter_mentions(
                mentions,
                self.state,
                weeded_threads
            )
            result["mentions_alerted"] = len(filtered_mentions)
            
            if filtered_mentions:
                cycle_time = datetime.now(IST).strftime("%I:%M %p")
                alert_message = AlertFormatter.format_alert(filtered_mentions, cycle_time)
                
                if not dry_run:
                    self._send_dm(alert_message)
                    result["dm_sent"] = True
                else:
                    result["dry_run"] = True
                    result["alert_preview"] = alert_message
            
            self._update_state(filtered_mentions)
            
            return result
        
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))
            return result
    
    def _fetch_mentions(self, since: datetime) -> List[Dict]:
        """Fetch mentions from Slack using search"""
        print(f"[FETCH] Would search Slack for mentions since {since.isoformat()}")
        return []
    
    def _get_weeded_threads(self) -> Set[str]:
        """Get set of weeded thread IDs"""
        now = datetime.now(IST)
        three_hours_ago = now - timedelta(hours=3)
        
        weeded = set()
        for thread_id, weeded_time_str in self.state.get("weeded_threads", {}).items():
            weeded_time = datetime.fromisoformat(weeded_time_str)
            if three_hours_ago <= weeded_time <= now:
                weeded.add(thread_id)
        
        return weeded
    
    def _send_dm(self, message: str) -> None:
        """Send DM to user"""
        print(f"[DM] Would send message to {self.user_id}:")
        print(message)
    
    def _update_state(self, mentions: List[Dict]) -> None:
        """Update state after sending alert"""
        now = datetime.now(IST)
        
        for mention in mentions:
            self.state["alerted_threads_this_cycle"].append(mention["message_ts"])
        
        self.state["last_alert_cycle"] = now.isoformat()
        
        MentionTrackerState.save(self.state)


def main():
    """Entry point for Cowork"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Slack Mention Tracker")
    parser.add_argument("--user-id", required=True, help="Your Slack user ID")
    parser.add_argument("--dry-run", action="store_true", help="Run without sending DM")
    
    args = parser.parse_args()
    
    tracker = MentionTracker(args.user_id)
    result = tracker.run(dry_run=args.dry_run)
    
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in ["success", "skipped"] else 1


if __name__ == "__main__":
    sys.exit(main())

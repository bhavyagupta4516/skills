#!/usr/bin/env python3
"""
Test suite for Slack Mention Tracker
"""

import json
import sys
from datetime import datetime, timedelta
import pytz
from mention_tracker import (
    MentionTracker,
    MentionExtractor,
    MentionFilter,
    WorkingHoursManager,
    AlertFormatter,
)

IST = pytz.timezone('Asia/Kolkata')


def test_working_hours():
    """Test working hours logic"""
    print("Testing WorkingHoursManager...")
    
    # Test 10am IST (should be working hours)
    dt_10am = datetime.now(IST).replace(hour=10, minute=0, second=0)
    assert WorkingHoursManager.is_working_hours(dt_10am), "10am should be working hours"
    
    # Test 2pm IST (should be working hours)
    dt_2pm = datetime.now(IST).replace(hour=14, minute=0, second=0)
    assert WorkingHoursManager.is_working_hours(dt_2pm), "2pm should be working hours"
    
    # Test 8pm IST (should NOT be working hours)
    dt_8pm = datetime.now(IST).replace(hour=20, minute=0, second=0)
    assert not WorkingHoursManager.is_working_hours(dt_8pm), "8pm should NOT be working hours"
    
    # Test 6am IST (should NOT be working hours)
    dt_6am = datetime.now(IST).replace(hour=6, minute=0, second=0)
    assert not WorkingHoursManager.is_working_hours(dt_6am), "6am should NOT be working hours"
    
    print("✅ WorkingHoursManager tests passed")


def test_alert_window():
    """Test alert window calculation"""
    print("\nTesting AlertWindow logic...")
    
    # At 10:30am, window should start at 10am
    dt_10_30 = datetime.now(IST).replace(hour=10, minute=30, second=0)
    window = WorkingHoursManager.get_alert_window_start(dt_10_30)
    assert window.hour == 10, f"Window at 10:30am should start at 10am, got {window.hour}"
    
    # At 2pm, window should start at 1pm
    dt_2pm = datetime.now(IST).replace(hour=14, minute=0, second=0)
    window = WorkingHoursManager.get_alert_window_start(dt_2pm)
    assert window.hour == 13, f"Window at 2pm should start at 1pm, got {window.hour}"
    
    # At 5pm, window should start at 4pm
    dt_5pm = datetime.now(IST).replace(hour=17, minute=0, second=0)
    window = WorkingHoursManager.get_alert_window_start(dt_5pm)
    assert window.hour == 16, f"Window at 5pm should start at 4pm, got {window.hour}"
    
    print("✅ AlertWindow tests passed")


def test_mention_extractor():
    """Test mention extraction"""
    print("\nTesting MentionExtractor...")
    
    mock_search_results = [
        {
            "ts_human": "May 28, 2026 2:15 PM",
            "ts": "1234567890.123456",
            "channel_name": "#engineering",
            "channel_id": "C123456",
            "text": "@bhavya can you review this PR?",
            "username": "john",
        },
        {
            "ts_human": "May 28, 2026 3:00 PM",
            "ts": "1234567900.654321",
            "channel_name": "#product",
            "channel_id": "C789012",
            "text": "Jumping on thread with @bhavya",
            "username": "jane",
            "thread_ts": "1234567800.000000",
        }
    ]
    
    mentions = MentionExtractor.extract_mentions(mock_search_results)
    
    assert len(mentions) == 2, f"Should extract 2 mentions, got {len(mentions)}"
    assert mentions[0]["channel"] == "#engineering"
    assert mentions[0]["user"] == "john"
    assert mentions[0]["thread_link"] == "https://slack.com/archives/C123456/p1234567890123456"
    assert mentions[1]["is_thread_reply"] == True
    
    print("✅ MentionExtractor tests passed")


def test_mention_filter():
    """Test mention filtering"""
    print("\nTesting MentionFilter...")
    
    mentions = [
        {"message_ts": "ts1", "channel": "#eng"},
        {"message_ts": "ts2", "channel": "#prod"},
        {"message_ts": "ts3", "channel": "#general"},
    ]
    
    state = {
        "alerted_threads_this_cycle": ["ts2"],  # Already alerted about ts2
    }
    
    weeded_threads = {"ts3"}  # Marked with ✅
    
    filtered = MentionFilter.filter_mentions(mentions, state, weeded_threads)
    
    # Should only keep ts1 (ts2 already alerted, ts3 weeded)
    assert len(filtered) == 1, f"Should filter to 1 mention, got {len(filtered)}"
    assert filtered[0]["message_ts"] == "ts1"
    
    print("✅ MentionFilter tests passed")


def test_alert_formatter():
    """Test alert formatting"""
    print("\nTesting AlertFormatter...")
    
    mentions = [
        {
            "channel": "#engineering",
            "date": "May 28, 2026 2:15 PM",
            "user": "john",
            "context": "Can you review this PR?",
            "thread_link": "https://slack.com/archives/C123/p1234",
        }
    ]
    
    alert = AlertFormatter.format_alert(mentions, "2:15 PM")
    
    assert "#engineering" in alert, "Alert should include channel"
    assert "@john" in alert, "Alert should include user"
    assert "View Thread" in alert, "Alert should have thread link"
    assert "✅" in alert, "Alert should mention green tick"
    
    print("✅ AlertFormatter tests passed")


def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("Running Slack Mention Tracker Tests")
    print("=" * 50)
    
    try:
        test_working_hours()
        test_alert_window()
        test_mention_extractor()
        test_mention_filter()
        test_alert_formatter()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("=" * 50)
        return 0
    
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())

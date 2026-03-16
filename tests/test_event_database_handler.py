#!/usr/bin/env python3
"""
Tests for event_database_handler, including is_event_past (no past events rule).

Manual integration test steps (run a real scraper and verify):
  1. Past single-day event skipped: Scrape a venue with past events; past ones should not appear as new.
  2. Today event kept: Event with start_date=today should be created.
  3. Future event kept: Event with start_date in future should be created.
  4. Multi-day event with end_date in future kept: Event spanning past-to-future should be created.
  5. Ongoing exhibition still kept: Exhibition without dates gets start_date=today from handler; should be created.
"""
import os
import sys
from datetime import date, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from scripts.event_database_handler import is_event_past


def test_is_event_past_past_single_day():
    """Past single-day event should be treated as past."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    assert is_event_past({'start_date': yesterday, 'title': 'Past Event'}) is True


def test_is_event_past_today():
    """Today's event should be kept."""
    today = date.today()
    assert is_event_past({'start_date': today, 'title': 'Today Event'}) is False


def test_is_event_past_future():
    """Future event should be kept."""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    assert is_event_past({'start_date': tomorrow, 'title': 'Future Event'}) is False


def test_is_event_past_multi_day_still_running():
    """Multi-day event with end_date in future should be kept."""
    today = date.today()
    start = today - timedelta(days=5)
    end = today + timedelta(days=5)
    assert is_event_past({'start_date': start, 'end_date': end, 'title': 'Festival'}) is False


def test_is_event_past_multi_day_ends_today():
    """Multi-day event ending today should be kept."""
    today = date.today()
    start = today - timedelta(days=3)
    assert is_event_past({'start_date': start, 'end_date': today, 'title': 'Exhibition'}) is False


def test_is_event_past_multi_day_fully_past():
    """Multi-day event fully in past should be treated as past."""
    today = date.today()
    start = today - timedelta(days=10)
    end = today - timedelta(days=1)
    assert is_event_past({'start_date': start, 'end_date': end, 'title': 'Old Festival'}) is True


def test_is_event_past_no_start_date():
    """No start_date should not be treated as past (conservative)."""
    assert is_event_past({'title': 'Ongoing Exhibition'}) is False


def test_is_event_past_string_dates():
    """String dates should be parsed correctly."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    assert is_event_past({'start_date': yesterday.isoformat(), 'title': 'Past'}) is True
    assert is_event_past({'start_date': today.isoformat(), 'end_date': (today + timedelta(days=1)).isoformat(), 'title': 'Current'}) is False


def run_tests():
    """Run all tests and report results."""
    tests = [
        test_is_event_past_past_single_day,
        test_is_event_past_today,
        test_is_event_past_future,
        test_is_event_past_multi_day_still_running,
        test_is_event_past_multi_day_ends_today,
        test_is_event_past_multi_day_fully_past,
        test_is_event_past_no_start_date,
        test_is_event_past_string_dates,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
    return passed == len(tests)


if __name__ == '__main__':
    print("Running is_event_past tests...")
    ok = run_tests()
    sys.exit(0 if ok else 1)

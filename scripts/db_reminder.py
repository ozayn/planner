#!/usr/bin/env python3
"""
Database Change Reminder System
Reminds you to update everything when you make database changes
"""

import os
import sys
from datetime import datetime

class DatabaseChangeReminder:
    def __init__(self):
        self.reminder_file = os.path.expanduser('~/.local/share/planner/db_reminders.txt')
        self.current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def add_reminder(self, change_description: str):
        """Add a reminder about a database change"""
        os.makedirs(os.path.dirname(self.reminder_file), exist_ok=True)
        
        with open(self.reminder_file, 'a') as f:
            f.write(f"[{self.current_time}] {change_description}\n")
        
        print(f"📝 Added reminder: {change_description}")
        self.show_reminders()
    
    def show_reminders(self):
        """Show all pending reminders"""
        if not os.path.exists(self.reminder_file):
            print("✅ No pending reminders")
            return
        
        with open(self.reminder_file, 'r') as f:
            reminders = f.readlines()
        
        if not reminders:
            print("✅ No pending reminders")
            return
        
        print(f"\n📋 Pending Database Changes ({len(reminders)} reminders):")
        for i, reminder in enumerate(reminders, 1):
            print(f"  {i}. {reminder.strip()}")
        
        print(f"\n🔧 To update everything, run:")
        print(f"   python scripts/auto_database_manager.py")
        print(f"   OR")
        print(f"   ./update_database.sh")
    
    def clear_reminders(self):
        """Clear all reminders (after successful update)"""
        if os.path.exists(self.reminder_file):
            os.remove(self.reminder_file)
            print("✅ All reminders cleared")
    
    def check_and_remind(self):
        """Check if there are pending reminders and show them"""
        if os.path.exists(self.reminder_file):
            with open(self.reminder_file, 'r') as f:
                reminders = f.readlines()
            
            if reminders:
                print("⚠️  You have pending database changes!")
                self.show_reminders()
                return True
        
        return False

def main():
    reminder = DatabaseChangeReminder()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'add':
            if len(sys.argv) > 2:
                description = ' '.join(sys.argv[2:])
                reminder.add_reminder(description)
            else:
                print("Usage: python scripts/db_reminder.py add 'description of change'")
        
        elif command == 'show':
            reminder.show_reminders()
        
        elif command == 'clear':
            reminder.clear_reminders()
        
        elif command == 'check':
            reminder.check_and_remind()
        
        else:
            print("Usage: python scripts/db_reminder.py [add|show|clear|check]")
    else:
        # Default: check for reminders
        reminder.check_and_remind()

if __name__ == '__main__':
    main()


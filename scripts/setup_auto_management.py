#!/usr/bin/env python3
"""
Git Hook for Automatic Database Management
Runs automatically when you commit changes to database-related files
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_git_hooks():
    """Setup git hooks for automatic database management"""
    
    project_root = os.getcwd()
    git_hooks_dir = os.path.join(project_root, '.git', 'hooks')
    
    if not os.path.exists(git_hooks_dir):
        print("❌ Not a git repository")
        return False
    
    # Create pre-commit hook
    pre_commit_hook = os.path.join(git_hooks_dir, 'pre-commit')
    
    hook_content = '''#!/bin/bash
# Auto Database Manager - Pre-commit Hook

echo "🤖 Auto Database Manager - Checking for database changes..."

# Check if any database-related files changed
if git diff --cached --name-only | grep -E "(app\.py|scripts/.*\.py|docs/.*\.md)" > /dev/null; then
    echo "📊 Database-related files changed, running auto-update..."
    
    # Run the auto database manager
    python scripts/auto_database_manager.py --silent
    
    if [ $? -eq 0 ]; then
        echo "✅ Auto-update completed successfully"
        # Add updated documentation to commit
        git add docs/*.md
        git add scripts/migrations.json
    else
        echo "❌ Auto-update failed"
        exit 1
    fi
else
    echo "ℹ️ No database-related files changed"
fi
'''
    
    with open(pre_commit_hook, 'w') as f:
        f.write(hook_content)
    
    # Make it executable
    os.chmod(pre_commit_hook, 0o755)
    
    print("✅ Git hooks setup complete!")
    print("📋 The following will happen automatically:")
    print("   - When you commit changes to app.py or scripts/*.py")
    print("   - Auto-detect schema changes")
    print("   - Apply migrations")
    print("   - Update all documentation")
    print("   - Add updated docs to your commit")
    
    return True

def create_manual_trigger():
    """Create a simple script to manually trigger updates"""
    
    trigger_script = '''#!/bin/bash
# Manual trigger for auto database management

echo "🤖 Manual Database Update Trigger"
echo "This will update everything automatically..."

python scripts/auto_database_manager.py

echo "✅ Manual update completed!"
'''
    
    with open('update_database.sh', 'w') as f:
        f.write(trigger_script)
    
    os.chmod('update_database.sh', 0o755)
    
    print("✅ Created manual trigger: ./update_database.sh")

if __name__ == '__main__':
    print("🔧 Setting up automatic database management...")
    
    # Setup git hooks
    if setup_git_hooks():
        print("✅ Git hooks configured")
    
    # Create manual trigger
    create_manual_trigger()
    
    print("\n🎉 Setup complete!")
    print("\n📋 How it works:")
    print("1. **Automatic**: Runs when you commit database changes")
    print("2. **Manual**: Run `./update_database.sh` anytime")
    print("3. **Direct**: Run `python scripts/auto_database_manager.py`")
    
    print("\n💡 Pro tip: Always run this after making model changes!")


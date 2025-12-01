#!/usr/bin/env python3
"""
Fix venue loading and reload production data
"""
import subprocess
import sys
import time
import urllib.request
import urllib.parse
import json
import os

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            cmd,
            cwd='/Users/oz/Dropbox/2025/planner',
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print(f"✅ {description} - SUCCESS")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ {description} - FAILED")
            if result.stderr:
                print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def main():
    print("🔧 Fixing venue loading and reloading production data...")
    print("=" * 60)
    
    # Step 1: Commit and push the fix
    print("\n📦 Step 1: Committing and pushing the fix...")
    if not run_command(['git', 'add', 'app.py'], "Staging app.py"):
        print("⚠️  Could not stage app.py - it may already be staged")
    
    if not run_command(
        ['git', 'commit', '-m', 'Fix venue loading in load-all-data endpoint\n\n- Fix venues.json structure mismatch\n- Use city_name field from venue data\n- Add better error handling'],
        "Committing changes"
    ):
        print("⚠️  Commit may have failed or nothing to commit")
    
    if not run_command(['git', 'push', 'origin', 'master'], "Pushing to GitHub"):
        print("❌ Failed to push to GitHub")
        return 1
    
    # Step 2: Wait for deployment
    print("\n⏳ Step 2: Waiting 30 seconds for Railway to start deploying...")
    time.sleep(30)
    
    # Step 3: Reload data
    print("\n🔄 Step 3: Reloading all data in production...")
    try:
        req = urllib.request.Request(
            'https://planner.ozayn.com/api/admin/load-all-data',
            method='POST',
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=120) as response:
            if response.status == 200:
                print("✅ Data reload initiated successfully!")
                result = json.loads(response.read().decode())
                print(f"Response: {result}")
            else:
                print(f"❌ Failed to reload data: {response.status}")
                print(f"Response: {response.read().decode()}")
                return 1
    except Exception as e:
        print(f"❌ Error calling reload endpoint: {e}")
        return 1
    
    # Step 4: Verify
    print("\n📊 Step 4: Verifying data was loaded...")
    time.sleep(5)
    
    try:
        req = urllib.request.Request('https://planner.ozayn.com/api/admin/stats')
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 200:
                stats = json.loads(response.read().decode())
                print(f"\n📊 Production Database Stats:")
                print(f"   Cities: {stats.get('cities', 'N/A')}")
                print(f"   Venues: {stats.get('venues', 'N/A')}")
                print(f"   Sources: {stats.get('sources', 'N/A')}")
                print(f"   Events: {stats.get('events', 'N/A')}")
            else:
                print("⚠️  Could not verify stats")
    except Exception as e:
        print(f"⚠️  Could not verify: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Done!")
    return 0

if __name__ == '__main__':
    sys.exit(main())


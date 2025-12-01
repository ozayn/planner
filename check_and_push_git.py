#!/usr/bin/env python3
"""
Check git status and push changes to GitHub
"""
import subprocess
import sys
import os

def run_git_command(cmd, cwd=None):
    """Run a git command and return the result"""
    try:
        result = subprocess.run(
            ['git'] + cmd,
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    repo_path = '/Users/oz/Dropbox/2025/planner'
    
    print("🔍 Checking Git Status...")
    print("=" * 60)
    
    # Check current branch
    success, output, error = run_git_command(['branch', '--show-current'], cwd=repo_path)
    if success:
        print(f"📍 Current branch: {output.strip()}")
    else:
        print(f"⚠️  Could not get branch: {error}")
    
    # Check status
    print("\n📊 Files that have been modified:")
    success, output, error = run_git_command(['status', '--short'], cwd=repo_path)
    if success:
        if output.strip():
            print(output)
        else:
            print("  (no changes)")
    else:
        print(f"⚠️  Error: {error}")
    
    # Check staged files
    print("\n📦 Files staged for commit:")
    success, output, error = run_git_command(['diff', '--cached', '--name-only'], cwd=repo_path)
    if success:
        if output.strip():
            print(output)
        else:
            print("  (none staged)")
    else:
        print(f"⚠️  Error: {error}")
    
    # Check recent commits
    print("\n📝 Recent commits (last 5):")
    success, output, error = run_git_command(['log', '--oneline', '-5'], cwd=repo_path)
    if success:
        print(output)
    else:
        print(f"⚠️  Error: {error}")
    
    # Check commits ahead of origin
    print("\n🔄 Commits ahead of origin/master:")
    success, output, error = run_git_command(['log', 'origin/master..HEAD', '--oneline'], cwd=repo_path)
    if success:
        if output.strip():
            print(output)
            commits_ahead = len([l for l in output.strip().split('\n') if l])
        else:
            print("  (none - all pushed)")
            commits_ahead = 0
    else:
        print(f"⚠️  Could not check: {error}")
        commits_ahead = 0
    
    # Check uncommitted changes
    success, output, error = run_git_command(['status', '--porcelain'], cwd=repo_path)
    uncommitted = 0
    if success:
        uncommitted = len([l for l in output.strip().split('\n') if l and not l.startswith('??')])
    
    print("\n" + "=" * 60)
    
    # Determine what needs to be done
    if uncommitted > 0:
        print(f"\n⚠️  You have {uncommitted} uncommitted file(s)")
        print("\nFiles to stage:")
        print("  - data/cities.json")
        print("  - scripts/check_duplicates.py")
        print("  - scripts/data_integrity_validator.py")
        print("  - scripts/pre_commit_data_check.py")
        print("  - docs/MISTAKE_PREVENTION_CHECKLIST.md")
        print("  - docs/QUICK_REFERENCE.md")
        
        response = input("\nDo you want to stage and commit these files? (y/n): ")
        if response.lower() == 'y':
            # Stage files
            files_to_add = [
                'data/cities.json',
                'scripts/check_duplicates.py',
                'scripts/data_integrity_validator.py',
                'scripts/pre_commit_data_check.py',
                'docs/MISTAKE_PREVENTION_CHECKLIST.md',
                'docs/QUICK_REFERENCE.md'
            ]
            
            print("\n📦 Staging files...")
            for file in files_to_add:
                success, output, error = run_git_command(['add', file], cwd=repo_path)
                if success:
                    print(f"  ✅ {file}")
                else:
                    print(f"  ⚠️  {file}: {error}")
            
            # Commit
            print("\n💾 Committing...")
            commit_message = """Add State College PA, remove duplicate city, and implement duplicate checker

- Add State College, Pennsylvania to cities (ID 26)
- Remove duplicate Silver Spring entry (ID 25)
- Create scripts/check_duplicates.py for checking duplicates in cities, venues, and events
- Integrate duplicate checking into data_integrity_validator.py and pre_commit_data_check.py
- Update documentation to require duplicate checks before data changes
- Update cities.json metadata and total count"""
            
            success, output, error = run_git_command(
                ['commit', '-m', commit_message],
                cwd=repo_path
            )
            if success:
                print("✅ Committed successfully!")
                commits_ahead = 1  # We just created a commit
            else:
                print(f"❌ Commit failed: {error}")
                return 1
    
    if commits_ahead > 0:
        print(f"\n📤 You have {commits_ahead} commit(s) ready to push")
        response = input("Do you want to push to GitHub? (y/n): ")
        if response.lower() == 'y':
            print("\n🚀 Pushing to GitHub...")
            success, output, error = run_git_command(['push', 'origin', 'master'], cwd=repo_path)
            if success:
                print("✅ Successfully pushed to GitHub!")
                print(output)
            else:
                print(f"❌ Push failed: {error}")
                if "Authentication" in error or "permission" in error.lower():
                    print("\n💡 Tip: You may need to authenticate with GitHub")
                return 1
    else:
        print("\n✅ Everything is up to date with GitHub!")
    
    print("\n" + "=" * 60)
    print("✅ Done!")
    return 0

if __name__ == '__main__':
    sys.exit(main())



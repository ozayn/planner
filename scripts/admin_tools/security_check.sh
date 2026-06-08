#!/bin/bash

# 🔒 Security Check Script
# Run this before every commit to ensure no secrets are exposed

echo "🔍 Running security checks..."

# Check for common API key patterns
echo "Checking for API key patterns..."

# Google API keys (exclude .env files which are expected to contain keys)
if grep -r "AIza[0-9A-Za-z_-]\{35\}" --exclude-dir=.git --exclude-dir=venv --exclude=".env" .; then
    echo "❌ ERROR: Google API key found in files!"
    exit 1
fi

# OpenAI API keys (exclude .env files)
if grep -r "sk-[0-9A-Za-z]\{48\}" --exclude-dir=.git --exclude-dir=venv --exclude=".env" .; then
    echo "❌ ERROR: OpenAI API key found in files!"
    exit 1
fi

# Google OAuth secrets (exclude .env files)
if grep -r "GOCSPX-[0-9A-Za-z_-]\{40\}" --exclude-dir=.git --exclude-dir=venv --exclude=".env" .; then
    echo "❌ ERROR: Google OAuth secret found in files!"
    exit 1
fi

# AWS access keys (exclude .env files)
if grep -r "AKIA[0-9A-Z]\{16\}" --exclude-dir=.git --exclude-dir=venv --exclude=".env" .; then
    echo "❌ ERROR: AWS access key found in files!"
    exit 1
fi

# Check for hardcoded password patterns (exclude .env files and this script)
if grep -r "password.*=.*['\"][^'\"]\{8,\}['\"]" --exclude-dir=.git --exclude-dir=venv --exclude=".env" --exclude="security_check.sh" .; then
    echo "❌ ERROR: Potential hardcoded password found in files!"
    exit 1
fi

# Check for hardcoded secret patterns (exclude .env files and this script)
if grep -r "secret.*=.*['\"][^'\"]\{10,\}['\"]" --exclude-dir=.git --exclude-dir=venv --exclude=".env" --exclude="security_check.sh" .; then
    echo "❌ ERROR: Potential hardcoded secret found in files!"
    exit 1
fi

# Check for .env files being committed
if git status --porcelain | grep -E "\.env$|\.env\."; then
    echo "❌ ERROR: .env file detected in git staging!"
    echo "Add .env to .gitignore and remove from staging"
    exit 1
fi

# Check for key files being committed
if git status --porcelain | grep -E "\.key$|\.pem$|\.p12$|\.pfx$"; then
    echo "❌ ERROR: Key file detected in git staging!"
    exit 1
fi

echo "✅ Security check passed!"
echo "🔒 No secrets detected in staged files"

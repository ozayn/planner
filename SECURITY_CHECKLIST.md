# 🔒 Security Checklist

## ✅ Pre-Commit Checklist
- [ ] No API keys in code files
- [ ] No credentials in documentation
- [ ] All secrets use environment variables
- [ ] No hardcoded passwords or tokens
- [ ] Placeholders used in examples: `[REDACTED]`, `YOUR_API_KEY_HERE`

## 🚫 Never Commit
- API keys (Google, OpenAI, AWS, etc.)
- Database passwords
- OAuth client secrets
- Private keys
- Real credentials in documentation

## ✅ Safe Patterns
```python
# ✅ CORRECT - Use environment variables
api_key = os.getenv('GOOGLE_MAPS_API_KEY')
```

```markdown
# ✅ CORRECT - Use placeholders in docs
GOOGLE_CLIENT_ID=[REDACTED - stored in Railway environment variables]
```

## 🔍 Pre-Commit Checks
Run these before every commit:
```bash
# Check for potential secrets
git secrets --scan

# Check for API key patterns
grep -r "AIza\|sk-\|GOCSPX" --exclude-dir=.git .

# Verify .env is ignored
git status | grep -v ".env"
```

## 🛡️ Security Tools Installed
- ✅ `git-secrets` - Prevents credential commits
- ✅ Enhanced `.gitignore` - Blocks sensitive files
- ✅ Pre-commit hooks - Automatic scanning

## 🚨 If You Find Exposed Credentials
1. **Immediately revoke** the compromised credentials
2. **Remove from code** and commit the fix
3. **Create new credentials** 
4. **Update environment variables**
5. **Test the fix**

## 📝 Documentation Rules
- Use placeholders: `[REDACTED]`, `YOUR_API_KEY_HERE`
- Never include real credentials
- Reference environment variables instead
- Use examples with fake values

---
**Remember: Once committed to git, credentials exist in history forever!**


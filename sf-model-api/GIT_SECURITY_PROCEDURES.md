# Git Security Procedures - Salesforce Models API Gateway

## Overview

This document outlines the security procedures and best practices for safely committing and pushing code to GitHub while protecting sensitive credentials and configuration data.

## Critical Security Requirements

### 🔐 Files That Must NEVER Be Committed

**Primary Sensitive Files:**
- `config.json` - Contains Salesforce OAuth credentials (consumer_key, consumer_secret, username, instance_url)
- `src/salesforce_models_token.json` - Live authentication tokens
- `*.token.json` - Any token files (current or future)
- `context-manager.json` - Development context with potential sensitive data

**Development Files to Exclude:**
- `__pycache__/` directories - Python bytecode
- `.DS_Store` files - macOS system files  
- `*.pyc` files - Python compiled files
- `.env` files - Environment variables
- `development-environment-setup.md` - May contain local paths/configs

## Pre-Flight Security Checklist

### Phase 1: Status Assessment
```bash
# Check what files are staged/modified
git status

# Review staged changes in detail
git diff --cached
```

### Phase 2: Sensitive Data Scan
For each file being committed, verify:
- ✅ No API keys, secrets, or credentials
- ✅ No authentication tokens
- ✅ No instance URLs or usernames
- ✅ No private configuration data
- ✅ No local development paths

### Phase 3: .gitignore Verification
Ensure `.gitignore` contains:
```gitignore
# Sensitive Configuration Files
config.json
*.token.json
context-manager.json
development-environment-setup.md

# Python
__pycache__/
*.pyc
*.pyo

# OS/IDE Files
.DS_Store
.vscode/
.idea/

# Environment Files
.env
.env.local
```

## Safe Git Push Procedure

### Step 1: Pre-Flight Security Check
```bash
# Use agent-organizer for comprehensive security validation
# Agent will analyze all files for sensitive content
```

### Step 2: Staging and Commit
```bash
# Stage only safe files
git add .

# Commit with descriptive security-focused message
git commit -m "$(cat <<'EOF'
[Brief description of changes]

- Security: Describe any security improvements
- Performance: List performance optimizations
- Features: New functionality added

🤖 Generated with [Claude Code](https://claude.ai/code)
Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### Step 3: Push to Remote
```bash
# Push to main branch
git push origin main
```

## Executed Example (2025-08-05)

### Security Assessment Results
**Protected Files (NOT committed):**
- `config.json` - Salesforce credentials secured
- `src/salesforce_models_token.json` - Auth tokens protected
- `context-manager.json` - Development files excluded
- All `__pycache__/` and `.DS_Store` files

**Files Successfully Committed (12 files, 207 insertions):**
- `.gitignore` (NEW) - Future credential protection
- `DEPLOYMENT_CHECKLIST.md` - Documentation improvements
- `src/salesforce_models_client.py` - SSL and performance fixes
- `src/tool_handler.py` - Memory optimizations
- `start_llm_service.sh` - File permissions fix

### Commit Details
```
Commit: 9728cac
Message: "Add security protections and performance optimizations"
Changes: 12 files changed, 207 insertions(+), 17 deletions(-)
Status: Successfully pushed to https://github.com/larry-deee/ai_projects.git
```

## Emergency Procedures

### If Sensitive Data Was Accidentally Committed

**Immediate Actions:**
1. **DO NOT** push to remote if not already pushed
2. Reset the commit: `git reset HEAD~1`
3. Remove sensitive files: `git rm --cached <filename>`
4. Update `.gitignore` to prevent future commits
5. Re-commit safely

**If Already Pushed:**
1. Contact repository admin immediately
2. Consider repository cleanup tools (BFG Repo-Cleaner)
3. Rotate any exposed credentials
4. Update security protocols

## Agent-Organizer Integration

### Recommended Workflow
1. **Always use agent-organizer** for git operations involving sensitive projects
2. **Request pre-flight security check** before any push
3. **Verify protection measures** are in place
4. **Document the process** for audit trail

### Agent Command Example
```
Use agent-organizer to delegate tasks. We want to perform a pre-flight check and then perform a git push. Note be mindful of sensitive files, they should not be pushed/updated to github of course. Do not delete special files like config.json they should be protected. Show me what you're about to do before doing it.
```

## Security Best Practices

### Development Environment
- **Never hardcode credentials** in source files
- **Use environment variables** or config files for sensitive data
- **Maintain separate configs** for development/staging/production
- **Regular credential rotation** per security policy

### Version Control
- **Review every commit** for sensitive content
- **Use descriptive commit messages** that explain security changes
- **Maintain comprehensive .gitignore** file
- **Regular security audits** of repository history

### Team Collaboration
- **Document security procedures** for all team members
- **Use pre-commit hooks** for automated sensitive data detection
- **Regular security training** on git best practices
- **Incident response plan** for credential exposure

## Maintenance

### Regular Reviews
- **Monthly .gitignore updates** as project evolves
- **Quarterly security audit** of git history
- **Annual procedure review** and updates
- **Continuous monitoring** for new sensitive file types

### File Monitoring
Keep watch for new file types that may contain sensitive data:
- Configuration files (*.conf, *.ini, *.yaml)
- Database files (*.db, *.sqlite)
- Certificate files (*.pem, *.crt, *.key)
- API response caches that may contain tokens

---

**Last Updated:** 2025-08-05  
**Review Schedule:** Quarterly  
**Next Review Due:** 2025-11-05  
**Procedure Version:** 1.0
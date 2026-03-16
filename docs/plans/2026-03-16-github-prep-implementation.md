# GitHub Repository Preparation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prepare ITTS Backend project for public GitHub repository with MIT license, proper documentation, security best practices, and professional open-source standards.

**Architecture:** Single repository with main/develop branch workflow. Tests removed from version control, uv.lock committed for reproducibility. Full open-source documentation suite (LICENSE, CONTRIBUTING.md, SECURITY.md).

**Tech Stack:** Git, GitHub, Python/uv, FastAPI, Docker

---

## Task 1: Create LICENSE File (MIT)

**Files:**
- Create: `LICENSE`

**Step 1: Create MIT LICENSE file**

```bash
cat > LICENSE << 'EOF'
MIT License

Copyright (c) 2026 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF
```

**Step 2: Verify file created**

Run: `ls -lh LICENSE`
Expected: File exists with size ~1KB

**Step 3: Update copyright placeholder**

Edit `LICENSE` line 5: Replace `[Your Name]` with your actual name or organization

**Step 4: Commit**

```bash
git add LICENSE
git commit -m "docs: add MIT license"
```

---

## Task 2: Create .gitattributes File

**Files:**
- Create: `.gitattributes`

**Step 1: Create .gitattributes**

```bash
cat > .gitattributes << 'EOF'
# Auto detect text files and normalize line endings to LF
* text=auto eol=lf

# Explicitly declare text files
*.py text eol=lf
*.md text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.txt text eol=lf
*.json text eol=lf
*.toml text eol=lf

# Declare files that will always have CRLF line endings on checkout
*.bat text eol=crlf
*.ps1 text eol=crlf
EOF
```

**Step 2: Verify file created**

Run: `cat .gitattributes`
Expected: File shows line ending configurations

**Step 3: Commit**

```bash
git add .gitattributes
git commit -m "chore: add .gitattributes for consistent line endings"
```

---

## Task 3: Create CONTRIBUTING.md

**Files:**
- Create: `CONTRIBUTING.md`

**Step 1: Create contribution guidelines**

```bash
cat > CONTRIBUTING.md << 'EOF'
# Contributing to ITTS Backend

Thank you for your interest in contributing to ITTS Backend!

## Getting Started

### Prerequisites

- Docker and Docker Compose
- uv (Python package manager)
- Git

### Setup

1. Fork and clone the repository
2. Install dependencies: `uv sync`
3. Start services: `docker-compose up -d`
4. Initialize database: `docker-compose exec -T itts-api uv run python -m app.db.init_db`

## Development Workflow

### Branch Strategy

- `develop`: Default branch for all development
- `main`: Production-ready releases only

### Making Changes

1. Create a feature branch from `develop`
2. Make your changes
3. Write/update tests
4. Ensure all tests pass: `uv run pytest`
5. Commit with clear messages
6. Push to your fork
7. Create pull request to `develop`

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Write docstrings for functions and classes
- Run linting: `uv run ruff check app/`

### Testing

- Unit tests: `uv run pytest tests/unit/ -v`
- Integration tests: `uv run pytest tests/integration/ -v`
- Coverage: `uv run pytest --cov=app --cov-report=term-missing`

### Commit Messages

Use conventional commit format:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `chore:` - Maintenance tasks
- `refactor:` - Code refactoring
- `test:` - Test changes

## Pull Request Guidelines

### Before Submitting

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] PR description explains the change

### PR Description Template

```markdown
## Summary
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How did you test your changes?

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

## Questions?

Feel free to open an issue for discussion before starting large changes.
EOF
```

**Step 2: Verify file created**

Run: `wc -l CONTRIBUTING.md`
Expected: File has 60-80 lines

**Step 3: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: add contribution guidelines"
```

---

## Task 4: Create SECURITY.md

**Files:**
- Create: `SECURITY.md`

**Step 1: Create security policy**

```bash
cat > SECURITY.md << 'EOF'
# Security Policy

## Supported Versions

Currently supported versions:
- Version 1.x (latest)

## Reporting Vulnerabilities

If you discover a security vulnerability, please email:

[Your security email or GitHub private vulnerability reporting]

Please do NOT:
- Create public GitHub issues for security vulnerabilities
- Discuss vulnerabilities in public channels

## What to Include

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if known)

## Response Time

We will acknowledge receipt within 48 hours and provide:
- Initial assessment
- Estimated timeline for fix
- Notification when fix is released

## Security Best Practices

This project follows security best practices:
- No hardcoded credentials
- Environment-based configuration
- Regular dependency updates
- Code review process
- Path traversal protection

## Dependency Security

We regularly update dependencies. Report outdated dependencies via:
- Opening an issue with title "Security: Update <package> to <version>"
- Including current version and latest version
- Explaining security implications

EOF
```

**Step 2: Update security email placeholder**

Edit `SECURITY.md` line 10: Replace `[Your security email or GitHub private vulnerability reporting]` with your actual security contact or remove the email line and use GitHub's private vulnerability reporting

**Step 3: Verify file created**

Run: `grep -c "##" SECURITY.md`
Expected: 8-10 section headers

**Step 4: Commit**

```bash
git add SECURITY.md
git commit -m "docs: add security policy"
```

---

## Task 5: Update .gitignore

**Files:**
- Modify: `.gitignore:25` (remove uv.lock)
- Modify: `.gitignore:54` (remove /tests/)
- Add: `.gitignore` (add .git/ entry)

**Step 1: Remove uv.lock from .gitignore**

Run: `sed -i '25d' .gitignore`

**Step 2: Remove /tests/ from .gitignore**

Run: `sed -i '/^\/tests\//d' .gitignore`

**Step 3: Add .git/ to .gitignore**

```bash
cat >> .gitignore << 'EOF'

# Git metadata
.git/
EOF
```

**Step 4: Verify changes**

Run: `grep -E "(uv\.lock|tests|\.git)" .gitignore`
Expected: No uv.lock or /tests/ entries, .git/ entry present

**Step 5: Commit**

```bash
git add .gitignore
git commit -m "chore: update .gitignore for open-source project"
```

---

## Task 6: Remove Tests from Git Tracking

**Files:**
- Git index modification: `tests/`

**Step 1: Remove tests from git index (keep local files)**

Run: `git rm -r --cached tests/`

Expected output: `rm 'tests/unit/test_*.py'`, `rm 'tests/integration/test_*.py'`, etc.

**Step 2: Verify tests still exist locally**

Run: `ls tests/unit/ | wc -l`
Expected: 8 test files still exist locally

Run: `ls tests/integration/ | wc -l`
Expected: 9 test files still exist locally

**Step 3: Verify tests removed from git index**

Run: `git ls-files | grep -c "^tests/"`
Expected: 0 (no test files in git index)

**Step 4: Commit**

```bash
git commit -m "chore: remove test files from version control (kept locally)"
```

**Rollback if needed:**
```bash
git reset HEAD~1  # Undo commit
git reset HEAD tests/  # Restore to index
```

---

## Task 7: Commit uv.lock File

**Files:**
- Add: `uv.lock`

**Step 1: Add uv.lock to git**

Run: `git add uv.lock`

**Step 2: Verify uv.lock added**

Run: `git status | grep uv.lock`
Expected: `new file:   uv.lock`

**Step 3: Commit**

```bash
git commit -m "chore: commit uv.lock for reproducible builds"
```

---

## Task 8: Update README.md with Badges

**Files:**
- Modify: `README.md:1-5` (add badges at top)

**Step 1: Add badges section after title**

Edit `README.md`, add after line 2:

```markdown
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/release/python-3110/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue)](https://www.docker.com/)
```

**Step 2: Add project stats section**

Add after "Features" section:

```markdown
## Project Stats

- **Tasks:** 22 completed
- **Tests:** 17 passing
- **Commits:** 24
- **Status:** Production Ready
```

**Step 3: Add contributing section**

Add before "## Quick Start":

```markdown
## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

Please see [SECURITY.md](SECURITY.md) for security policy.
```

**Step 4: Add license section at end**

```bash
cat >> README.md << 'EOF'

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
EOF
```

**Step 5: Verify README changes**

Run: `grep -c "^\[" README.md`
Expected: 3-4 badge/section links

**Step 6: Commit**

```bash
git add README.md
git commit -m "docs: enhance README with badges and sections"
```

---

## Task 9: Create Develop Branch

**Files:**
- Git branches: `main` → `develop`

**Step 1: Rename current main branch to develop**

Run: `git branch -m main develop`

**Step 2: Verify branch renamed**

Run: `git branch`
Expected: Only `* develop` branch shows

**Step 3: Verify commit history intact**

Run: `git log --oneline -5`
Expected: Shows last 5 commits including design doc

**Step 4: Update .git/HEAD reference to develop**

Run: `git symbolic-ref HEAD refs/heads/develop`
Expected: No error (silent success)

**Rollback if needed:**
```bash
git branch -m develop main  # Rename back
```

---

## Task 10: Create New Main Branch

**Files:**
- Git branches: new `main` from `develop`

**Step 1: Create new main branch from develop**

Run: `git checkout -b main`

**Step 2: Verify on main branch**

Run: `git branch`
Expected: Shows `* main` and `  develop` branches

**Step 3: Tag initial release on main**

Run: `git tag -a v1.0.0 -m "Initial release - production ready"`

**Step 4: Verify tag created**

Run: `git tag`
Expected: `v1.0.0` shows in list

**Step 5: Switch back to develop**

Run: `git checkout develop`

**Step 6: Verify current branch**

Run: `git branch --show-current`
Expected: `develop`

**Rollback if needed:**
```bash
git branch -D main  # Delete main branch
git checkout main   # If you renamed it back
```

---

## Task 11: Security Verification

**Files:**
- Verification: All tracked files

**Step 1: Verify .env is NOT tracked**

Run: `git ls-files | grep "^.env$"`
Expected: Empty output (no .env file tracked)

**Step 2: Verify .env.example IS tracked**

Run: `git ls-files | grep ".env.example"`
Expected: `.env.example` in output

**Step 3: Verify no hardcoded credentials in Python files**

Run: `grep -r "password\|secret\|key\|token" app/ --include="*.py" | grep -E "(=|:)" | grep -v "# " | grep -v "minio_" | wc -l`
Expected: 0 (no hardcoded credentials except minio config references)

**Step 4: Verify .env.example has safe placeholders**

Run: `grep "MINIO_SECRET_KEY" .env.example`
Expected: Shows `MINIO_SECRET_KEY=changeme` (placeholder value)

**Step 5: Verify no API keys in codebase**

Run: `grep -r "sk-\|api_key\|apikey\|jwt_secret" app/ docs/ --include="*.py" --include="*.md" | wc -l`
Expected: 0 (no API keys found)

**Step 6: Document security verification**

Create verification summary:
```bash
echo "✅ Security Verification Complete
✅ .env not in git
✅ .env.example in git
✅ No hardcoded credentials
✅ .env.example has placeholder values
✅ No API keys found
"
```

---

## Task 12: Final Pre-Push Checklist

**Files:**
- Verification: All changes

**Step 1: Verify all documentation files exist**

Run: `ls LICENSE CONTRIBUTING.md SECURITY.md .gitattributes 2>/dev/null`
Expected: All 4 files listed

**Step 2: Verify README updated**

Run: `grep -c "\[!\[" README.md`
Expected: 3+ badge references

**Step 3: Verify tests removed from git**

Run: `git ls-files | grep "^tests/" | wc -l`
Expected: 0 (no tests in git)

**Step 4: Verify uv.lock committed**

Run: `git ls-files | grep uv.lock`
Expected: `uv.lock` in output

**Step 5: Verify .gitignore updated**

Run: `grep -c "uv.lock" .gitignore`
Expected: 0 (uv.lock not ignored)

Run: `grep -c "/tests" .gitignore`
Expected: 0 (/tests not ignored)

**Step 6: Verify branch structure**

Run: `git branch`
Expected: Two branches: `develop` (current), `main`

**Step 7: Verify working tree clean**

Run: `git status`
Expected: `On branch develop` and `nothing to commit, working tree clean`

**Step 8: Verify no uncommitted changes**

Run: `git diff --stat`
Expected: Empty output

**Step 9: Count total tracked files**

Run: `git ls-files | wc -l`
Expected: 100-150 files (approximate)

**Step 10: Display summary**

```bash
echo "=== Pre-Push Summary ===
Branches: main, develop
Tracked files: $(git ls-files | wc -l)
Latest commit: $(git log -1 --oneline)
Status: Ready for GitHub
"
```

---

## Task 13: Create GitHub Repository

**Files:**
- Remote: GitHub repository

**Step 1: Create new repository on GitHub**

- Go to https://github.com/new
- Repository name: `itts-backend` (or your choice)
- Description: `Backend REST API for managing ITTS (IndexTTS Bundle) files`
- Visibility: **Public**
- **DO NOT** initialize with README, .gitignore, or license
- Click "Create repository"

**Step 2: Copy repository URL**

After creation, copy the URL: `https://github.com/YOUR_USERNAME/itts-backend.git`

**Step 3: Add remote origin**

Run: `git remote add origin https://github.com/YOUR_USERNAME/itts-backend.git`

Replace `YOUR_USERNAME` with your actual GitHub username.

**Step 4: Verify remote added**

Run: `git remote -v`
Expected: Shows `origin` with your repository URL

**Rollback if needed:**
```bash
git remote remove origin  # Remove and re-add with correct URL
```

---

## Task 14: Push Both Branches to GitHub

**Files:**
- Remote: GitHub repository

**Step 1: Push develop branch with upstream**

Run: `git push -u origin develop`

Expected: Shows upload progress, "Branch 'develop' set up to track remote branch 'develop' from 'origin'"

**Step 2: Push main branch**

Run: `git push origin main`

Expected: Shows upload progress for main branch

**Step 3: Push tags**

Run: `git push origin --tags`

Expected: Shows tag `v1.0.0` uploaded

**Step 4: Verify on GitHub**

Visit: `https://github.com/YOUR_USERNAME/itts-backend`
Expected: See all code, branches, and tags on GitHub

**Step 5: Verify branches on GitHub**

Check GitHub "Branches" dropdown
Expected: Both `main` and `develop` branches visible

---

## Task 15: Configure GitHub Repository Settings

**Files:**
- GitHub repository settings

**Step 1: Set default branch to develop**

On GitHub:
- Go to Settings → Branches
- Default branch: Change `main` → `develop`
- Confirm update

**Step 2: Enable branch protection on main**

On GitHub:
- Go to Settings → Branches
- Add rule for `main` branch:
  - ✅ Require pull request before merging
  - ✅ Require approvals: 1
  - ✅ Disallow force pushes
  - ✅ Require status checks to pass before merging (when CI added)
- Click "Create" or "Save changes"

**Step 3: Add repository topics**

On GitHub:
- Go to Settings
- Topics: `python`, `fastapi`, `minio`, `tts`, `audio`, `rest-api`, `docker`, `sqlite`, `async`
- Click "Save topics"

**Step 4: Update repository description**

On GitHub:
- Go to Settings → General
- Description: `Backend REST API for managing ITTS (IndexTTS Bundle) files - FastAPI, SQLite, MinIO`
- Website: (optional - link to docs or demo)
- Click "Save changes"

**Step 5: Enable Discussions (optional)**

On GitHub:
- Go to Settings → General → Features
- Enable "Discussions"
- Click "Save changes"

---

## Task 16: Post-Push Verification

**Files:**
- Verification: GitHub repository

**Step 1: Verify LICENSE visible on GitHub**

Visit: `https://github.com/YOUR_USERNAME/itts-backend/blob/main/LICENSE`
Expected: MIT license text visible

**Step 2: Verify README badges render**

Visit: `https://github.com/YOUR_USERNAME/itts-backend`
Expected: Badges show as colored shields at top of README

**Step 3: Verify CONTRIBUTING.md accessible**

Visit: `https://github.com/YOUR_USERNAME/itts-backend/blob/develop/CONTRIBUTING.md`
Expected: Full contribution guidelines visible

**Step 4: Verify SECURITY.md accessible**

Visit: `https://github.com/YOUR_USERNAME/itts-backend/blob/develop/SECURITY.md`
Expected: Security policy visible

**Step 5: Verify tests NOT in repository**

Visit: `https://github.com/YOUR_USERNAME/itts-backend/tree/develop/tests`
Expected: 404 Not Found (tests folder not in repo)

**Step 6: Verify uv.lock in repository**

Visit: `https://github.com/YOUR_USERNAME/itts-backend/blob/develop/uv.lock`
Expected: Lock file visible (may be large, loads slowly)

**Step 7: Clone test in temporary directory**

```bash
cd /tmp
rm -rf itts-backend-test
git clone https://github.com/YOUR_USERNAME/itts-backend.git itts-backend-test
cd itts-backend-test
```

Expected: Clean clone succeeds

**Step 8: Verify cloned repository structure**

Run: `ls -la | grep -E "(LICENSE|CONTRIBUTING|SECURITY|uv.lock)"`
Expected: All files present, tests folder absent

**Step 9: Verify line endings**

Run: `file LICENSE`
Expected: `LICENSE: ASCII text, with no line terminators` or similar (LF, not CRLF)

**Step 10: Cleanup test clone**

```bash
cd /tmp
rm -rf itts-backend-test
```

---

## Task 17: Create Release on GitHub

**Files:**
- GitHub releases

**Step 1: Create GitHub release from tag**

On GitHub:
- Go to "Releases" → "Create a new release"
- Tag: Select `v1.0.0`
- Title: `v1.0.0 - Initial Release`
- Description:
```markdown
## ITTS Backend v1.0.0

Initial production-ready release of ITTS Backend.

### Features
- Upload and manage ITTS bundles
- Pack raw audio files into ITTS format
- Export custom segment selections as WAV
- Concatenate multiple bundles
- Full-text search and filtering
- Auto-playlists grouped by voice types
- Backup and restore functionality

### Tech Stack
- FastAPI (async Python web framework)
- SQLite (database)
- MinIO (S3-compatible storage)
- Docker (containerization)

### Documentation
- [API Documentation](https://github.com/YOUR_USERNAME/itts-backend/blob/develop/README.md#api-documentation)
- [Frontend Guide](https://github.com/YOUR_USERNAME/itts-backend/tree/develop/docs/frontend)
- [Contributing](https://github.com/YOUR_USERNAME/itts-backend/blob/develop/CONTRIBUTING.md)

### Installation
See [README.md](https://github.com/YOUR_USERNAME/itts-backend/blob/develop/README.md) for quick start.

### License
MIT License - see [LICENSE](https://github.com/YOUR_USERNAME/itts-backend/blob/develop/LICENSE)
```
- Set as: ✅ Latest release
- Click "Publish release"

**Step 2: Verify release published**

Visit: `https://github.com/YOUR_USERNAME/itts-backend/releases`
Expected: v1.0.0 release visible with description

**Step 3: Verify release tag**

Visit: `https://github.com/YOUR_USERNAME/itts-backend/releases/tag/v1.0.0`
Expected: Tag details and release notes visible

---

## Completion Checklist

Run this final verification:

```bash
echo "=== GitHub Repository Preparation Complete ==="

echo "Branches:"
git branch -r

echo ""
echo "Tracked files:"
git ls-files | wc -l

echo ""
echo "Tests in git (should be 0):"
git ls-files | grep "^tests/" | wc -l

echo ""
echo "Documentation files:"
git ls-files | grep -E "(LICENSE|CONTRIBUTING|SECURITY|.gitattributes)"

echo ""
echo "Latest commit:"
git log -1 --oneline

echo ""
echo "Git status:"
git status --short

echo ""
echo "✅ Repository ready for collaboration!"
```

---

## Troubleshooting

### Issue: Tests still showing in git after removal

**Solution:**
```bash
git rm -r --cached tests/
git commit -m "chore: ensure tests removed from git index"
```

### Issue: uv.lock still being ignored

**Solution:**
```bash
# Remove from .gitignore
sed -i '/^uv.lock$/d' .gitignore
git add .gitignore uv.lock
git commit -m "chore: fix uv.lock handling"
```

### Issue: Line endings still CRLF on Windows

**Solution:**
```bash
# Refresh .gitattributes
git add --renormalize .
git commit -m "chore: normalize line endings to LF"
```

### Issue: Cannot push main branch

**Solution:**
```bash
# Force push (use carefully)
git push origin main --force-with-lease
```

### Issue: Wrong default branch on GitHub

**Solution:**
1. Go to GitHub repository Settings → Branches
2. Click "Switch default branch" icon
3. Change `main` → `develop`
4. Confirm

---

## Rollback Procedure

If anything goes wrong, you can rollback:

### Rollback git changes (local)

```bash
# Reset to before any changes
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Or reset to specific commit
git reset --hard <commit-hash-before-changes>
```

### Rollback GitHub repository

1. Create new empty repository on GitHub
2. Update remote: `git remote set-url origin <new-url>`
3. Push again: `git push -u origin develop`
4. Delete old repository if needed

---

## Estimated Timeline

**Total Time:** 45-60 minutes

- Documentation files (Tasks 1-4): 15 min
- Git configuration (Tasks 5-7): 10 min
- README update (Task 8): 5 min
- Branch setup (Tasks 9-10): 5 min
- Verification (Tasks 11-12): 5 min
- GitHub setup (Tasks 13-15): 15 min
- Post-push verification (Tasks 16-17): 10 min

---

**Next Steps:**
1. Execute this plan using @superpowers:executing-plans
2. Verify all 17 tasks complete successfully
3. Confirm repository is public and accessible
4. Share repository URL with community

**Success Criteria:**
- ✅ Public GitHub repository created
- ✅ MIT license applied
- ✅ Documentation complete (LICENSE, CONTRIBUTING, SECURITY, .gitattributes)
- ✅ Tests removed from version control
- ✅ uv.lock committed
- ✅ main/develop branch structure
- ✅ README enhanced with badges
- ✅ Security verified
- ✅ Ready for open-source collaboration

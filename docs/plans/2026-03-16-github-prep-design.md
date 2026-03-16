# GitHub Repository Preparation Design

**Date:** 2026-03-16
**Project:** ITTS Backend
**Purpose:** Prepare project for public GitHub repository
**License:** MIT
**Type:** Infrastructure/Documentation

---

## Overview

Prepare the ITTS Backend project for public GitHub release as an open-source project with MIT licensing, proper documentation, security best practices, and professional open-source standards.

---

## Requirements

### Functional Requirements
1. Project must be safe for public repository (no credentials, sensitive data)
2. Must include standard open-source documentation (LICENSE, CONTRIBUTING, SECURITY)
3. Must use proper Git workflow (main for releases, develop for development)
4. Must include MIT license
5. README should include badges and comprehensive information
6. Dependency lock file should be committed for reproducible builds

### Non-Functional Requirements
1. All security concerns addressed before public release
2. Professional presentation for open-source community
3. Clear contribution guidelines
4. Proper line ending handling (LF for Python)
5. Tests kept private (development only, not in public repo)

---

## Design Decisions

### 1. License
**Choice:** MIT License

**Rationale:**
- Permissive, simple, widely used
- Allows commercial use
- Short and easy to understand
- Compatible with most projects

### 2. Branch Strategy
**Choice:** GitFlow simplified (main + develop)

```
main (production)
  ↑
  │ merge when releasing
  │
develop (development)
```

**Rationale:**
- Simple two-branch workflow
- `main`: Stable releases only
- `develop`: All development work
- Easy to understand for contributors

### 3. Test Files
**Choice:** Remove from git tracking, keep local copies

**Rationale:**
- Tests are for development validation
- Reduces repository size
- Keeps private test fixtures (`.itts` files) out of public repo
- Users can run tests locally if they choose

### 4. Dependency Management
**Choice:** Commit `uv.lock` file

**Rationale:**
- Ensures reproducible builds
- Everyone gets exact same dependency versions
- Standard practice for Python projects using uv
- Helps with debugging environment-specific issues

### 5. Documentation Set
**Choice:** Full standard documentation

**Files:**
- `LICENSE` - MIT license
- `CONTRIBUTING.md` - Contribution guidelines
- `SECURITY.md` - Security policy and vulnerability reporting
- `.gitattributes` - Line ending handling
- `README.md` - Enhanced with badges and sections

**Rationale:**
- Professional open-source standards
- Clear expectations for contributors
- Security transparency
- Better cross-platform compatibility

---

## Architecture

### File Structure Changes

```
itts_server/
├── .env                    # ✅ NOT in git (contains credentials)
├── .env.example            # ✅ IS in git (template)
├── .gitignore              # ✅ Updated (remove uv.lock, /tests/)
├── .gitattributes          # ✅ NEW (line endings)
├── LICENSE                 # ✅ NEW (MIT license)
├── CONTRIBUTING.md         # ✅ NEW (guidelines)
├── SECURITY.md             # ✅ NEW (security policy)
├── README.md               # ✅ Updated (badges, sections)
├── uv.lock                 # ✅ IS in git (reproducible builds)
├── tests/                  # ✅ NOT in git (kept locally)
├── app/                    # ✅ IS in git (source code)
├── bundle_tools/           # ✅ IS in git (utilities)
├── docs/                   # ✅ IS in git (documentation)
└── scripts/                # ✅ IS in git (utility scripts)
```

### Git Workflow

```
┌─────────────────────────────────────┐
│     Developer Workflow               │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  Clone repo     │
│  (default:      │
│   develop)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Create feature │
│  branch         │
│  (optional)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Make changes   │
│  Commit work    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Push to        │
│  develop        │
└─────────────────┘
         │
         ▼ (when ready to release)
┌─────────────────┐
│  Create PR      │
│  develop → main │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Merge to main  │
│  (after review) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Tag release    │
│  (v1.0.0)       │
└─────────────────┘
```

---

## Components

### 1. LICENSE File
**Content:** Full MIT license text with copyright year and owner

### 2. CONTRIBUTING.md
**Sections:**
- Getting Started
- Development Setup
- Code Style
- Testing Guidelines
- Pull Request Process
- Issue Reporting

### 3. SECURITY.md
**Sections:**
- Supported Versions
- Reporting Vulnerabilities
- Security Policy
- Dependency Updates

### 4. .gitattributes
**Content:**
```
* text=auto eol=lf
*.py text eol=lf
*.md text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
```

### 5. README.md Enhancements
**Additions:**
- Badges section (top)
- Project stats
- Contributing section
- Security section
- License section
- Star request

---

## Data Flow

### Pre-Push Verification Flow

```
Start
  │
  ├─→ Check .env NOT in git
  ├─→ Check .env.example IS in git
  ├─→ Check tests removed from git
  ├─→ Check uv.lock IS in git
  ├─→ Check .gitignore updated
  ├─→ Check documentation files created
  ├─→ Check README updated
  ├─→ Check branches created
  ├─→ Check for sensitive data
  └─→ Verify working tree clean
  │
  ▼
All checks pass?
  │
  ├─→ YES: Push to GitHub
  └─→ NO: Fix issues and retry
```

---

## Error Handling

### Edge Cases

**1. Tests already tracked:**
- Solution: `git rm -r --cached tests/`
- Keeps local files, removes from git index

**2. Wrong branch name:**
- Solution: Rename `main` → `develop` first
- Then create new `main` from `develop`

**3. Sensitive data in git history:**
- Solution: Use `git filter-repo` or BFG Repo-Cleaner
- (Not needed here - verified clean)

**4. uv.lock already ignored:**
- Solution: Remove from .gitignore, then add and commit

---

## Testing Strategy

### Verification Checklist

Before pushing to GitHub:
- [ ] `.env` not in `git ls-files`
- [ ] `.env.example` in `git ls-files`
- [ ] `tests/` not in `git ls-files`
- [ ] `uv.lock` in `git ls-files`
- [ ] `LICENSE` exists
- [ ] `CONTRIBUTING.md` exists
- [ ] `SECURITY.md` exists
- [ ] `.gitattributes` exists
- [ ] README has badges
- [ ] Branch `main` exists
- [ ] Branch `develop` exists
- [ ] `git status` shows clean working tree
- [ ] No hardcoded credentials in code

---

## Security Considerations

### Already Verified ✅
- `.env` file not tracked
- No hardcoded credentials in code
- `.env.example` has safe placeholder values
- No API keys or secrets in codebase

### Best Practices Implemented
- Environment variable configuration
- Credentials in `.env` only
- `.env.example` as template
- Security policy documented
- Vulnerability reporting process defined

---

## Performance Considerations

### Repository Size
- Removing tests reduces repo size
- `uv.lock` adds size but ensures reproducibility
- Git LFS not needed (no large binary files in repo)

### Clone Time
- Standard clone time for Python project
- No external dependencies in git history
- Efficient .gitignore patterns

---

## Future Enhancements

### Potential Additions
- GitHub Actions CI/CD workflow
- Issue templates (bug_report.md, feature_request.md)
- PR template (pull_request_template.md)
- Dependabot for dependency updates
- Code coverage badge
- Release automation

### Not in Scope
- CI/CD pipeline (user chose D)
- Issue/PR templates (user chose D)
- Advanced GitHub features

---

## Success Criteria

**Repository is ready for GitHub when:**
1. ✅ All sensitive data excluded
2. ✅ MIT license present
3. ✅ Standard documentation files created
4. ✅ Tests removed from version control
5. ✅ Dependency lock file committed
6. ✅ Proper Git branch structure
7. ✅ README enhanced with badges
8. ✅ Security documentation present
9. ✅ Line endings configured
10. ✅ Ready for public collaboration

---

## Timeline Estimate

**Total Time:** ~30-45 minutes

- Create documentation: 10 min
- Update .gitignore: 2 min
- Remove tests from git: 2 min
- Commit uv.lock: 2 min
- Update README: 5 min
- Create/rename branches: 3 min
- Verification: 5 min
- Push to GitHub: 5 min
- Configure repo settings: 5 min

---

## Alternatives Considered

### 1. Keep Tests in Repo
**Rejected:** User wants tests private

### 2. Single Branch (main only)
**Rejected:** User wants main/develop workflow

### 3. Apache 2.0 License
**Rejected:** User chose MIT

### 4. No Badges
**Rejected:** User wants standard badges

### 5. Include CI/CD
**Rejected:** User chose to skip for now

---

## References

- MIT License: https://opensource.org/licenses/MIT
- GitHub Open Source Guide: https://opensource.guide/
- Python Packaging: https://packaging.python.org/
- uv Documentation: https://github.com/astral-sh/uv

---

**Status:** ✅ Approved
**Next Step:** Create implementation plan using writing-plans skill

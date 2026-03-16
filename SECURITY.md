# Security Policy

## Supported Versions

The latest 1.x release line is supported for security fixes.

## Reporting a Vulnerability

Please use GitHub private vulnerability reporting if it is enabled for the repository. If that is not available, contact the maintainers privately before disclosing details publicly.

Do not open public GitHub issues for unpatched vulnerabilities.

## What to Include

Please include:

- A description of the issue
- Reproduction steps
- Expected impact
- Any suggested mitigation or fix

## Response Expectations

Maintainers should acknowledge reports within 48 hours and provide an initial assessment as soon as practical.

## Security Practices

This project follows these baseline practices:

- Environment-based configuration
- No committed runtime secrets
- Schema validation for bundle manifests
- Path traversal protection for archive and object paths
- Dependency pinning through `uv.lock`

# Security Policy

## Supported Versions

We actively support the following versions with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

Once version 1.0 is released, only the latest stable version will receive security updates.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Security vulnerabilities should be reported privately to allow us to fix them before public disclosure.

### How to Report

**Email**: [Create a GitHub Security Advisory](https://github.com/TechR10n/ai-asst-mgr/security/advisories/new)

Or email directly to: `security@[your-domain-here]` (update this with your actual email)

### What to Include

Please include as much of the following information as possible:

- **Type of vulnerability** (e.g., SQL injection, XSS, authentication bypass)
- **Affected component(s)** (e.g., specific file, function, or module)
- **Step-by-step reproduction** (how to trigger the vulnerability)
- **Proof of concept** (code or commands that demonstrate the issue)
- **Impact** (what an attacker could achieve)
- **Suggested fix** (if you have one)
- **Your contact information** (for follow-up questions)

### What to Expect

1. **Acknowledgment**: You will receive a response within **48 hours** acknowledging receipt
2. **Assessment**: We will assess the vulnerability and determine its severity
3. **Fix**: We will develop and test a fix
4. **Disclosure**: We will coordinate disclosure with you
5. **Credit**: We will credit you in the security advisory (unless you prefer to remain anonymous)

### Timeline

- **Initial response**: Within 48 hours
- **Status update**: Within 7 days
- **Fix development**: Varies by severity (typically 1-4 weeks)
- **Public disclosure**: After fix is released and users have time to upgrade

## Security Best Practices

When using ai-asst-mgr:

### API Keys and Tokens
- **Never commit API keys** to git repositories
- Store API keys in environment variables or secure credential stores
- Rotate API keys regularly
- Use read-only tokens when possible

### Configuration Files
- Review permissions on config directories (`~/.claude/`, `~/.gemini/`, etc.)
- Ensure config files are not world-readable
- Be cautious about syncing configs to public repositories

### Vendor Adapters
- Only use vendor adapters from trusted sources
- Review adapter code before using custom adapters
- Keep adapters updated to latest versions

### Backup Files
- Encrypt backup files if they contain sensitive data
- Store backups in secure locations
- Set appropriate file permissions on backups

### Web Dashboard
- Only run the web dashboard on localhost (127.0.0.1)
- Use authentication if exposing dashboard to network
- Keep the web server updated

## Known Security Considerations

### Local Data Storage
ai-asst-mgr stores data locally in:
- `~/Data/ai-asst-mgr/sessions.db` - Session tracking database
- `~/.ai-asst-mgr/` - Configuration directory
- Vendor-specific directories (`~/.claude/`, etc.)

**Implications**:
- Data is not encrypted at rest by default
- Data is accessible to other users on multi-user systems
- Backups may contain sensitive information

**Recommendations**:
- Use full-disk encryption on your system
- Restrict user access on multi-user systems
- Encrypt backups if syncing to cloud storage

### GitHub Integration
When using GitHub integration:
- GitHub CLI stores authentication tokens
- Tokens grant access to your GitHub account
- Review GitHub token scopes regularly

**Recommendations**:
- Use fine-grained personal access tokens
- Grant minimum necessary permissions
- Revoke tokens when no longer needed
- Enable 2FA on your GitHub account

### Vendor SDKs
ai-asst-mgr integrates with vendor SDKs:
- Claude Code, Gemini CLI, OpenAI Codex
- Each has its own security model
- Vulnerabilities in vendor SDKs affect ai-asst-mgr

**Recommendations**:
- Keep vendor tools updated
- Review vendor security advisories
- Follow vendor security best practices

## Disclosure Policy

We follow **coordinated disclosure**:

1. **Private reporting** - You report the vulnerability privately
2. **Private acknowledgment** - We acknowledge and begin work
3. **Private collaboration** - We work with you to understand and fix
4. **Coordinated release** - We release the fix and advisory together
5. **Public disclosure** - We publicly disclose after users can upgrade

We aim to disclose vulnerabilities within **90 days** of initial report, but this may vary based on severity and complexity.

## Security Updates

Security updates are distributed via:

1. **GitHub Security Advisories** - https://github.com/TechR10n/ai-asst-mgr/security/advisories
2. **GitHub Releases** - Version releases include security fixes
3. **README Updates** - Critical issues noted in README
4. **Dependabot** - Automatically creates PRs for dependency updates

## Hall of Fame

We appreciate security researchers who help keep ai-asst-mgr secure. Contributors will be credited here (with permission):

- *No reported vulnerabilities yet*

## Questions?

If you have questions about this security policy, open a [GitHub Discussion](https://github.com/TechR10n/ai-asst-mgr/discussions) or contact the maintainer.

Thank you for helping keep ai-asst-mgr and its users safe! 🔒

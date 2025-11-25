# Command Reference

Complete documentation for all AI Assistant Manager CLI commands.

## Global Options

All commands support these global options:

| Option | Description |
|--------|-------------|
| `--help` | Show help message and exit |
| `--version` | Show version and exit |

---

## status

Display vendor status and installation information.

```bash
ai-asst-mgr status [OPTIONS]
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--vendor` | `-v` | Show status for specific vendor only |

### Examples

```bash
# Show all vendors
ai-asst-mgr status

# Show specific vendor
ai-asst-mgr status --vendor claude
```

### Output

```
╭─────────────────────────────────────────────────────────────╮
│                    AI Assistant Status                       │
╰─────────────────────────────────────────────────────────────╯

┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Vendor         ┃ Status       ┃ Notes                       ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Claude Code    │ ✓ Configured │ 5 agents, 12 skills         │
│ Gemini CLI     │ ✓ Installed  │ Run 'ai-asst-mgr init'      │
│ OpenAI Codex   │ ✗ Not Found  │ Install from openai.com     │
└────────────────┴──────────────┴─────────────────────────────┘
```

---

## init

Initialize vendor configurations with sensible defaults.

```bash
ai-asst-mgr init [OPTIONS]
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--vendor` | `-v` | Initialize specific vendor only |

### Examples

```bash
# Initialize all vendors
ai-asst-mgr init

# Initialize Claude only
ai-asst-mgr init --vendor claude
```

---

## health

Run comprehensive health checks on vendor configurations.

```bash
ai-asst-mgr health [OPTIONS]
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--vendor` | `-v` | Check specific vendor only |

### Examples

```bash
# Check all vendors
ai-asst-mgr health

# Check Claude only
ai-asst-mgr health --vendor claude
```

### Health Check Items

- Configuration file existence and validity
- Required directories (agents, skills, etc.)
- Permission checks
- API key validation (where applicable)

---

## doctor

Diagnose and automatically fix common configuration issues.

```bash
ai-asst-mgr doctor [OPTIONS]
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--vendor` | `-v` | Diagnose specific vendor only |
| `--fix` | `-f` | Automatically fix issues |

### Examples

```bash
# Diagnose all vendors
ai-asst-mgr doctor

# Auto-fix issues
ai-asst-mgr doctor --fix

# Diagnose specific vendor
ai-asst-mgr doctor --vendor claude --fix
```

---

## config

Get or set configuration values.

```bash
ai-asst-mgr config KEY [VALUE] [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `KEY` | Configuration key to get/set |
| `VALUE` | Value to set (optional, omit to get) |

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--vendor` | `-v` | Target specific vendor |

### Examples

```bash
# Get config value
ai-asst-mgr config model

# Set config value
ai-asst-mgr config model claude-sonnet-4

# Set for specific vendor
ai-asst-mgr config --vendor claude model claude-sonnet-4
```

---

## backup

Create compressed backups of vendor configurations.

```bash
ai-asst-mgr backup [OPTIONS]
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--vendor` | `-v` | Backup specific vendor only |
| `--backup-dir` | `-d` | Directory to store backups |
| `--list` | `-l` | List existing backups |
| `--verify` | | Verify backup integrity |

### Examples

```bash
# Backup all vendors
ai-asst-mgr backup

# Backup specific vendor
ai-asst-mgr backup --vendor claude

# List existing backups
ai-asst-mgr backup --list

# Verify backup integrity
ai-asst-mgr backup --verify backup.tar.gz
```

### Backup Format

- Compressed tar.gz archives
- SHA256 checksums for integrity verification
- Retention policies for automatic cleanup

---

## restore

Restore configurations from backup archives.

```bash
ai-asst-mgr restore [BACKUP_PATH] [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `BACKUP_PATH` | Path to backup file (optional) |

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--vendor` | `-v` | Restore specific vendor (uses latest backup) |
| `--backup-dir` | `-d` | Directory containing backups |
| `--preview` | `-p` | Preview without making changes |
| `--selective` | `-s` | Restore specific directories (comma-separated) |
| `--no-backup` | | Skip pre-restore backup |

### Examples

```bash
# Restore from specific file
ai-asst-mgr restore backup.tar.gz

# Restore latest backup for vendor
ai-asst-mgr restore --vendor claude

# Preview restore
ai-asst-mgr restore backup.tar.gz --preview

# Selective restore
ai-asst-mgr restore backup.tar.gz --selective agents,skills
```

---

## sync

Synchronize configurations from a Git repository.

```bash
ai-asst-mgr sync REPO_URL [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `REPO_URL` | Git repository URL |

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--branch` | `-b` | Git branch to sync (default: main) |
| `--strategy` | `-s` | Merge strategy (see below) |
| `--preview` | `-p` | Preview without making changes |
| `--no-backup` | | Skip pre-sync backup |
| `--backup-dir` | `-d` | Directory for pre-sync backups |

### Merge Strategies

| Strategy | Description |
|----------|-------------|
| `replace` | Replace all local files with remote |
| `merge` | Keep both (creates .remote files for conflicts) |
| `keep_local` | Keep local files if they exist |
| `keep_remote` | Use remote files (default) |

### Examples

```bash
# Basic sync
ai-asst-mgr sync https://github.com/user/configs.git

# Sync with preview
ai-asst-mgr sync https://github.com/user/configs.git --preview

# Sync specific branch
ai-asst-mgr sync https://github.com/user/configs.git --branch develop

# Sync with merge strategy
ai-asst-mgr sync https://github.com/user/configs.git --strategy merge
```

---

## coach

Get AI-powered usage insights and optimization recommendations.

```bash
ai-asst-mgr coach [OPTIONS]
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--vendor` | `-v` | Coach specific vendor only |
| `--compare` | `-c` | Compare all vendors |
| `--report` | `-r` | Report period (daily, weekly, monthly) |

### Examples

```bash
# Get insights for all vendors
ai-asst-mgr coach

# Coach specific vendor
ai-asst-mgr coach --vendor claude

# Compare vendors
ai-asst-mgr coach --compare

# Generate weekly report
ai-asst-mgr coach --report weekly
```

### Coaching Features

- Usage statistics and trends
- Unused resource identification
- Optimization recommendations
- Cross-vendor comparison
- Periodic reports (daily, weekly, monthly)

---

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `AI_ASST_MGR_CONFIG_DIR` | Override default config directory |
| `AI_ASST_MGR_BACKUP_DIR` | Default backup directory |
| `NO_COLOR` | Disable colored output |

---

## See Also

- [Installation Guide](installation.md)
- [Architecture](architecture.md)
- [Contributing](contributing.md)

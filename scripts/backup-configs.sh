#!/bin/bash
# AI Assistant Manager - Daily Backup Script
# This script backs up all AI assistant configurations

set -e

PROJECT_DIR="/Users/ryan.hammang/Developer/ai-asst-mgr"
LOG_FILE="$HOME/Library/Logs/ai-asst-mgr-backup.log"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting backup..." >> "$LOG_FILE"

cd "$PROJECT_DIR"
/opt/homebrew/bin/uv run ai-asst-mgr backup --all >> "$LOG_FILE" 2>&1

echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup completed." >> "$LOG_FILE"

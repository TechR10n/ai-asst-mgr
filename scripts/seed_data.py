#!/usr/bin/env python3
"""Seed the database with dummy data for Gemini, Claude, and Codex.

This script initializes the database and populates it with sample sessions,
events, and metrics for multiple vendors to demonstrate the system's
multi-vendor capabilities.
"""

import sys
import random
from datetime import datetime, timedelta, UTC
from pathlib import Path

# Add src to path to allow imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from ai_asst_mgr.database.manager import DatabaseManager

# Configuration
DB_PATH = Path.home() / "Data" / "claude-sessions" / "sessions.db"
VENDORS = ["gemini", "claude", "openai"]
PROJECTS = [
    "/home/ryan/Developer/ai-asst-mgr",
    "/home/ryan/Developer/website-project",
    "/home/ryan/Developer/api-service",
    "/home/ryan/Developer/mobile-app",
]

def generate_session_id() -> str:
    """Generate a random session ID."""
    chars = "abcdef0123456789"
    return "".join(random.choice(chars) for _ in range(8))

def seed_data() -> None:
    """Seed the database."""
    print(f"Initializing database at {DB_PATH}...")
    
    # Ensure directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    db = DatabaseManager(DB_PATH)
    db.initialize()
    
    print("Generating dummy data...")
    
    # Generate sessions for the last 14 days
    end_date = datetime.now(tz=UTC)
    start_date = end_date - timedelta(days=14)
    
    total_sessions = 0
    
    for vendor in VENDORS:
        # Generate random number of sessions for each vendor
        # Skew towards Gemini as it's the focus
        count = 25 if vendor == "gemini" else 10
        
        print(f"  Creating {count} sessions for {vendor.capitalize()}...")
        
        for _ in range(count):
            session_id = generate_session_id()
            project = random.choice(PROJECTS)
            
            # Random start time within the window
            time_offset = random.random() * (end_date - start_date).total_seconds()
            session_start = start_date + timedelta(seconds=time_offset)
            session_start_iso = session_start.isoformat()
            
            # Record session
            db.record_session(
                session_id=session_id,
                vendor_id=vendor,
                project_path=project,
                start_time=session_start_iso
            )
            
            # Generate events (messages and tools)
            num_messages = random.randint(5, 20)
            num_tools = random.randint(2, 8)
            num_errors = 1 if random.random() < 0.2 else 0
            
            # Simulate events
            current_time = session_start
            
            for i in range(num_messages):
                # User message
                db.record_event(
                    session_id=session_id,
                    vendor_id=vendor,
                    event_type="message",
                    event_name="user",
                    event_data={
                        "length": random.randint(20, 200),
                        "timestamp": current_time.isoformat()
                    }
                )
                current_time += timedelta(seconds=random.randint(5, 30))
                
                # Assistant message/tool
                if i < num_tools:
                    tool_name = random.choice([
                        "read_file", "write_file", "search", "run_command", "list_files"
                    ])
                    db.record_event(
                        session_id=session_id,
                        vendor_id=vendor,
                        event_type="tool_call",
                        event_name=tool_name,
                        event_data={
                            "args": "...",
                            "timestamp": current_time.isoformat()
                        }
                    )
                    current_time += timedelta(seconds=random.randint(10, 60))
            
            # End session
            db.end_session(
                session_id=session_id,
                tool_calls_count=num_tools,
                messages_count=num_messages,
                errors_count=num_errors
            )
            
            total_sessions += 1

    print(f"\nSuccessfully created {total_sessions} sessions across {len(VENDORS)} vendors.")
    print("You can now run 'ai-asst-mgr serve' to view the dashboard.")

if __name__ == "__main__":
    seed_data()

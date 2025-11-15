#!/usr/bin/env python3
"""
A simple linter for 'shifty' raw notes files.

It checks for common formatting errors that can confuse the LLM, based on
the expected format:
1. Participant Heading (e.g., '### Jake')
2. Timestamp (HH:MM)
3. Level Code (l8, lx, etc.)
4. Detail lines

Usage:
    python shifty_linter.py --notes-file your_notes.txt
"""

import sys
import re
import argparse
from pathlib import Path

# --- Configuration ---

# Valid level codes, based on pass1.txt
VALID_LEVELS = {
    'l8', 'l7', 'l6', 'l5', 'l4', 'l3', 'l1', 'l0', 'lx', 'l_'
}

# Regex for a valid 24-hour timestamp (HH:MM) followed by optional activity text
TIMESTAMP_ACTIVITY_RE = re.compile(r'^\d{2}:\d{2}(?:\s+.*)?$')

# Regex for an AMBIGUOUS 12-hour timestamp (H:MM) - this is a warning
AMBIGUOUS_TIMESTAMP_RE = re.compile(r'^\d{1}:\d{2}(?:\s+.*)?$')

# Regex for the participant heading
PARTICIPANT_RE = re.compile(r'^\s*#{1,3}\s+([A-Za-z]+)\s*$')

# --- ANSI Color Codes for Output ---
class Colors:
    """Class to hold ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def lint_notes(file_path: Path) -> bool:
    """
    Lints the given notes file against the expected format.
    Returns True if linting passes (even with warnings), False if it fails.
    """
    print(f"{Colors.HEADER}--- Linting {file_path} ---{Colors.ENDC}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"{Colors.FAIL}Error: File not found at: {file_path}{Colors.ENDC}")
        return False
    except Exception as e:
        print(f"{Colors.FAIL}Error: Could not read file: {e}{Colors.ENDC}")
        return False

    if not lines:
        print(f"{Colors.FAIL}Error: File is empty.{Colors.ENDC}")
        return False

    errors = []
    warnings = []
    
    # State machine variables
    # State can be 'START', 'EXPECT_TIMESTAMP_AND_ACTIVITY', 'EXPECT_LEVEL', 'EXPECT_DETAILS'
    state = 'START'
    last_timestamp = "00:00"

    for i, line in enumerate(lines):
        line_number = i + 1
        original_line = line # Keep original line for error reporting
        line = line.strip()

        if not line:
            # Blank lines are allowed, but reset state if we were expecting details
            if state == 'EXPECT_DETAILS':
                state = 'EXPECT_TIMESTAMP_AND_ACTIVITY'
            continue

        # --- State: START ---
        # We must find a participant heading first.
        if state == 'START':
            match = PARTICIPANT_RE.match(line)
            if match:
                print(f"INFO: Found participant: {Colors.BOLD}{match.group(1)}{Colors.ENDC}")
                state = 'EXPECT_TIMESTAMP_AND_ACTIVITY'
                continue
            else:
                errors.append(f"L{line_number}: {Colors.FAIL}Critical: File must start with a participant heading (e.g., '### Jake'). Found: '{original_line.strip()}'{Colors.ENDC}")
                state = 'EXPECT_TIMESTAMP_AND_ACTIVITY' # Try to recover
        
        # --- Check for Timestamps and Activity ---
        is_timestamp_activity = TIMESTAMP_ACTIVITY_RE.match(line)
        is_ambiguous_timestamp = AMBIGUOUS_TIMESTAMP_RE.match(line)

        if is_timestamp_activity:
            if state == 'EXPECT_LEVEL':
                errors.append(f"L{line_number}: {Colors.FAIL}Critical: Found timestamp/activity but expected a level code for the previous entry.{Colors.ENDC}")
            
            if is_ambiguous_timestamp:
                warnings.append(f"L{line_number}: {Colors.WARNING}Warning: Ambiguous 12-hour timestamp: '{line.split(' ', 1)[0]}'. Use 24-hour format (e.g., 19:15) to avoid time-guessing errors.{Colors.ENDC}")
            
            # Check chronology
            current_timestamp = line.split(' ', 1)[0].zfill(5) # '7:15' -> '07:15'
            if last_timestamp and current_timestamp < last_timestamp:
                warnings.append(f"L{line_number}: {Colors.WARNING}Warning: Non-chronological timestamp. '{current_timestamp}' is earlier than previous '{last_timestamp}'.{Colors.ENDC}")
            
            last_timestamp = current_timestamp
            state = 'EXPECT_LEVEL'
            continue
            
        # --- State: EXPECT_LEVEL ---
        # The line right after a timestamp *must* be a level code
        if state == 'EXPECT_LEVEL':
            if line in VALID_LEVELS:
                state = 'EXPECT_DETAILS'
                continue
            else:
                errors.append(f"L{line_number}: {Colors.FAIL}Critical: Expected a valid level code (e.g., l8, lx) but found: '{original_line.strip()}'{Colors.ENDC}")
                state = 'EXPECT_DETAILS' # Try to recover
                continue
        
        # --- State: EXPECT_TIMESTAMP_AND_ACTIVITY ---
        # If we are in this state, we haven't found the first timestamp yet or we are between entries.
        if state == 'EXPECT_TIMESTAMP_AND_ACTIVITY':
            errors.append(f"L{line_number}: {Colors.FAIL}Critical: Expected a timestamp and activity (HH:MM Activity) but found: '{original_line.strip()}'{Colors.ENDC}")
            state = 'EXPECT_DETAILS' # Try to recover
            continue
            
        # --- State: EXPECT_DETAILS ---
        # Any other line is a detail line. This is a valid state.
        if state == 'EXPECT_DETAILS':
            # This is a detail line, no checks needed.
            pass

    # --- Final checks after loop ---
    if state == 'EXPECT_LEVEL':
        errors.append(f"L{len(lines)}: {Colors.FAIL}Critical: File ends on a timestamp/activity. A level code is missing.{Colors.ENDC}")
    elif state == 'EXPECT_TIMESTAMP_AND_ACTIVITY':
        # This means the file ended after the heading but before any entries
        if not errors: # Only add if no other critical errors already reported for start
            errors.append(f"L{len(lines)}: {Colors.FAIL}Critical: File ends unexpectedly after participant heading. No entries found.{Colors.ENDC}")


    print("---")
    
    # --- Report Warnings ---
    if warnings:
        print(f"{Colors.WARNING}Found {len(warnings)} Warning(s):{Colors.ENDC}")
        for warning in warnings:
            print(f"- {warning}")
    
    # --- Report Errors ---
    if errors:
        print(f"\n{Colors.FAIL}{Colors.BOLD}Found {len(errors)} Critical Error(s):{Colors.ENDC}")
        for error in errors:
            print(f"- {error}")
        
        print(f"\n{Colors.FAIL}{Colors.BOLD}Linting FAILED. Please fix errors before processing.{Colors.ENDC}")
        return False
    
    # --- Success ---
    if warnings:
        print(f"\n{Colors.OKGREEN}Linting PASSED (with warnings).{Colors.ENDC}")
    else:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}Linting PASSED. File looks good!{Colors.ENDC}")
    
    return True

def main():
    """
    Main function to parse arguments and run the linter.
    """
    parser = argparse.ArgumentParser(
        description='Linter for "shifty" raw notes files.'
    )
    parser.add_argument(
        '--notes-file',
        help='Path to the raw notes file to lint.',
        required=True
    )
    args = parser.parse_args()
    
    notes_file_path = Path(args.notes_file)

    if not lint_notes(notes_file_path):
        sys.exit(1)

if __name__ == "__main__":
    main()

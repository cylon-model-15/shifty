#!/usr/bin/env python3
"""
A simple linter for 'shifty' raw notes files.
...
"""

import sys
import re
import argparse
from pathlib import Path
from enum import Enum, auto
import logging

# --- Configuration ---

VALID_LEVELS = {'l8', 'l7', 'l6', 'l5', 'l4', 'l3', 'l1', 'l0', 'lx', 'l_'}
TIMESTAMP_ACTIVITY_RE = re.compile(r'^\d{2}:\d{2}(?:\s+.*)?$')
AMBIGUOUS_TIMESTAMP_RE = re.compile(r'^\d{1}:\d{2}(?:\s+.*)?$')
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

class LinterState(Enum):
    """Defines the possible states for the linter's state machine."""
    START = auto()
    EXPECT_TIMESTAMP = auto()
    EXPECT_LEVEL = auto()
    EXPECT_DETAILS = auto()

class Linter:
    """Encapsulates the logic for linting a notes file."""
    def __init__(self, file_path: Path, logger: logging.Logger):
        self.file_path = file_path
        self.logger = logger
        self.errors = []
        self.warnings = []
        self.state = LinterState.START
        self.last_timestamp = "00:00"
        self.line_number = 0
        self.lines_processed = 0

    def lint(self) -> bool:
        """
        Lints the notes file, reading it line-by-line.
        Returns True if linting passes (even with warnings), False if it fails.
        """
        self.logger.info(f"{Colors.HEADER}--- Linting {self.file_path} ---{Colors.ENDC}")
        try:
            with self.file_path.open('r', encoding='utf-8') as f:
                for line in f:
                    self.line_number += 1
                    self.lines_processed += 1
                    self._process_line(line)
            
            if self.lines_processed == 0:
                self.errors.append(f"L{self.line_number}: {Colors.FAIL}Critical: File is empty.{Colors.ENDC}")

            self._final_state_check()

        except FileNotFoundError:
            self.logger.error(f"File not found at: {self.file_path}")
            return False
        except Exception as e:
            self.logger.error(f"Could not read file: {e}")
            return False
        
        return self._report_results()

    def _process_line(self, original_line: str):
        """Processes a single line based on the current linter state."""
        line = original_line.strip()

        if not line:
            if self.state == LinterState.EXPECT_DETAILS:
                self.state = LinterState.EXPECT_TIMESTAMP
            return

        if self.state == LinterState.START:
            self._handle_start_state(line, original_line)
        elif self.state == LinterState.EXPECT_TIMESTAMP:
            self._handle_expect_timestamp(line, original_line)
        elif self.state == LinterState.EXPECT_LEVEL:
            self._handle_expect_level(line, original_line)
        elif self.state == LinterState.EXPECT_DETAILS:
            self._handle_expect_details(line, original_line)

    def _handle_start_state(self, line: str, original_line: str):
        """Handler for the START state."""
        match = PARTICIPANT_RE.match(line)
        if match:
            self.logger.info(f"Found participant: {Colors.BOLD}{match.group(1)}{Colors.ENDC}")
            self.state = LinterState.EXPECT_TIMESTAMP
        else:
            self.errors.append(f"L{self.line_number}: {Colors.FAIL}Critical: File must start with a participant heading (e.g., '### Jake'). Found: '{original_line.strip()}'{Colors.ENDC}")
            self.state = LinterState.EXPECT_TIMESTAMP # Try to recover

    def _handle_expect_timestamp(self, line: str, original_line: str):
        """Handler for the EXPECT_TIMESTAMP state."""
        if self._check_for_timestamp(line):
            return
        
        # If it's not a timestamp, it's an error.
        self.errors.append(f"L{self.line_number}: {Colors.FAIL}Critical: Expected a timestamp and activity (HH:MM Activity) but found: '{original_line.strip()}'{Colors.ENDC}")
        self.state = LinterState.EXPECT_DETAILS # Try to recover

    def _handle_expect_level(self, line: str, original_line: str):
        """Handler for the EXPECT_LEVEL state."""
        if self._check_for_timestamp(line):
            self.errors.append(f"L{self.line_number}: {Colors.FAIL}Critical: Found timestamp/activity but expected a level code for the previous entry.{Colors.ENDC}")
            return

        if line in VALID_LEVELS:
            self.state = LinterState.EXPECT_DETAILS
        else:
            self.errors.append(f"L{self.line_number}: {Colors.FAIL}Critical: Expected a valid level code (e.g., l8, lx) but found: '{original_line.strip()}'{Colors.ENDC}")
            self.state = LinterState.EXPECT_DETAILS # Try to recover

    def _handle_expect_details(self, line: str, original_line: str):
        """Handler for the EXPECT_DETAILS state."""
        if self._check_for_timestamp(line):
            return
        # Any other line is a detail line, no checks needed.
        pass

    def _check_for_timestamp(self, line: str) -> bool:
        """Checks if a line is a timestamp and updates state if it is. Returns True if it was a timestamp."""
        is_timestamp_activity = TIMESTAMP_ACTIVITY_RE.match(line)
        if not is_timestamp_activity:
            return False

        if AMBIGUOUS_TIMESTAMP_RE.match(line):
            self.warnings.append(f"L{self.line_number}: {Colors.WARNING}Warning: Ambiguous 12-hour timestamp: '{line.split(' ', 1)[0]}'. Use 24-hour format (e.g., 19:15).{Colors.ENDC}")
        
        current_timestamp = line.split(' ', 1)[0].zfill(5)
        if self.last_timestamp and current_timestamp < self.last_timestamp:
            self.warnings.append(f"L{self.line_number}: {Colors.WARNING}Warning: Non-chronological timestamp. '{current_timestamp}' is earlier than previous '{self.last_timestamp}'.{Colors.ENDC}")
        
        self.last_timestamp = current_timestamp
        self.state = LinterState.EXPECT_LEVEL
        return True

    def _final_state_check(self):
        """Performs checks after all lines have been processed."""
        if self.state == LinterState.EXPECT_LEVEL:
            self.errors.append(f"L{self.line_number}: {Colors.FAIL}Critical: File ends on a timestamp/activity. A level code is missing.{Colors.ENDC}")
        elif self.state == LinterState.EXPECT_TIMESTAMP and self.lines_processed > 0 and not self.errors:
            self.errors.append(f"L{self.line_number}: {Colors.FAIL}Critical: File ends unexpectedly after participant heading. No entries found.{Colors.ENDC}")

    def _report_results(self) -> bool:
        """Prints all warnings and errors and returns the linting status."""
        self.logger.info("---")
        if self.warnings:
            self.logger.warning(f"Found {len(self.warnings)} Warning(s):")
            for warning in self.warnings:
                self.logger.warning(f"- {warning}")
        
        if self.errors:
            self.logger.error(f"{Colors.BOLD}Found {len(self.errors)} Critical Error(s):{Colors.ENDC}")
            for error in self.errors:
                self.logger.error(f"- {error}")
            
            self.logger.error(f"{Colors.BOLD}Linting FAILED. Please fix errors before processing.{Colors.ENDC}")
            return False
        
        if self.warnings:
            self.logger.info(f"\n{Colors.OKGREEN}Linting PASSED (with warnings).{Colors.ENDC}")
        else:
            self.logger.info(f"\n{Colors.OKGREEN}{Colors.BOLD}Linting PASSED. File looks good!{Colors.ENDC}")
        
        return True

def lint_notes(file_path: Path, logger: logging.Logger) -> bool:
    """
    Public function to lint the given notes file.
    Returns True if linting passes (even with warnings), False if it fails.
    """
    linter = Linter(file_path, logger)
    return linter.lint()

def main():
    """
    Main function to parse arguments and run the linter as a standalone script.
    """
    parser = argparse.ArgumentParser(
        description='Linter for "shifty" raw notes files.'
    )
    parser.add_argument(
        '--notes-file',
        help='Path to the raw notes file to lint.',
        required=True
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_const',
        dest='loglevel',
        const=logging.DEBUG,
        default=logging.INFO,
        help='Enable verbose, debug-level logging.'
    )
    args = parser.parse_args()
    
    # --- Configure Logging for standalone execution ---
    logging.basicConfig(level=args.loglevel, format='%(message)s')
    logger = logging.getLogger()

    notes_file_path = Path(args.notes_file)

    if not lint_notes(notes_file_path, logger):
        sys.exit(1)

if __name__ == "__main__":
    main()

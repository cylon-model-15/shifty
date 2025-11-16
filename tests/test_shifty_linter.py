
import pytest
from pathlib import Path
import logging
from shifty_linter import lint_notes, Linter, LinterState

# --- Test Fixtures ---

@pytest.fixture
def logger():
    """Fixture to provide a logger for tests."""
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    return logging.getLogger('test-linter')

# --- Test Cases ---

def test_linter_valid_file(tmp_path: Path, logger: logging.Logger):
    """Tests that a correctly formatted file passes linting with no errors or warnings."""
    notes_content = """### Jake

09:00 Woke up
l8

10:00 Had breakfast
l7
Ate cereal.
"""
    notes_file = tmp_path / "valid_notes.md"
    notes_file.write_text(notes_content)

    linter = Linter(notes_file, logger)
    assert linter.lint() is True
    assert not linter.errors
    assert not linter.warnings

def test_linter_missing_header(tmp_path: Path, logger: logging.Logger):
    """Tests that a file missing the initial participant header fails."""
    notes_content = """
09:00 Woke up
l8
"""
    notes_file = tmp_path / "missing_header.md"
    notes_file.write_text(notes_content)

    linter = Linter(notes_file, logger)
    assert linter.lint() is False
    assert len(linter.errors) == 2
    assert "must start with a participant heading" in linter.errors[0]

def test_linter_missing_level_code(tmp_path: Path, logger: logging.Logger):
    """Tests that a file with a timestamp followed by another timestamp fails."""
    notes_content = """### Jake

09:00 Woke up
10:00 Had breakfast
l7
"""
    notes_file = tmp_path / "missing_level.md"
    notes_file.write_text(notes_content)

    linter = Linter(notes_file, logger)
    assert linter.lint() is False
    assert len(linter.errors) == 1
    assert "expected a level code" in linter.errors[0]

def test_linter_non_chronological_timestamp(tmp_path: Path, logger: logging.Logger):
    """Tests that a non-chronological timestamp generates a warning but passes."""
    notes_content = """### Jake

10:00 Had breakfast
l7

09:00 Woke up
l8
"""
    notes_file = tmp_path / "non_chrono.md"
    notes_file.write_text(notes_content)

    linter = Linter(notes_file, logger)
    assert linter.lint() is True # Should still pass
    assert not linter.errors
    assert len(linter.warnings) == 1
    assert "Non-chronological timestamp" in linter.warnings[0]

def test_linter_empty_file(tmp_path: Path, logger: logging.Logger):
    """Tests that an empty file fails linting."""
    notes_file = tmp_path / "empty.md"
    notes_file.write_text("")

    linter = Linter(notes_file, logger)
    assert linter.lint() is False
    assert len(linter.errors) == 1
    assert "File is empty" in linter.errors[0]

def test_linter_ends_on_timestamp(tmp_path: Path, logger: logging.Logger):
    """Tests that a file ending on a timestamp (missing a level) fails."""
    notes_content = """### Jake

09:00 Woke up
"""
    notes_file = tmp_path / "ends_on_ts.md"
    notes_file.write_text(notes_content)

    linter = Linter(notes_file, logger)
    assert linter.lint() is False
    assert len(linter.errors) == 1
    assert "A level code is missing" in linter.errors[0]

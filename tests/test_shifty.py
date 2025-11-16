import pytest
from pathlib import Path
import logging
import os
import json
from unittest.mock import MagicMock, call
import shifty

# --- Test Fixtures ---

@pytest.fixture
def logger():
    """Fixture to provide a logger for tests."""
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    return logging.getLogger('test-shifty')

@pytest.fixture
def mock_files(tmp_path: Path):
    """Fixture to create a set of mock files in a temporary directory."""
    notes_content = "### Test\n09:00 Test Event\nl8"
    pass1_prompt = "Extract facts from: {{RAW_NOTES}}"
    pass2_prompt = "Definitions: {{SHORTHAND_DEFINITIONS}}\nWrite a story about: {{OBSERVED_FACTS}}. Style: {{OPTIONAL_STYLE_GUIDE}}"
    style_guide_content = "Be dramatic."
    shorthand_content = {"l8": "Completely Independent", "j1": "Afternoon nap"}

    (tmp_path / "notes.md").write_text(notes_content)
    (tmp_path / "pass1.txt").write_text(pass1_prompt)
    (tmp_path / "pass2.txt").write_text(pass2_prompt)
    (tmp_path / "style.txt").write_text(style_guide_content)
    (tmp_path / "shorthand.json").write_text(json.dumps(shorthand_content))
    
    return tmp_path

# --- Test Cases ---

def test_main_logic_flow(monkeypatch, mock_files: Path, logger: logging.Logger):
    """
    Tests the main logic of shifty.py from end-to-end, mocking the Ollama call.
    """
    # Mock call_ollama to return different results based on the prompt
    def mock_ollama(prompt, model, host, logger):
        if "Extract facts" in prompt:
            return "Extracted Facts"
        elif "Write a story" in prompt:
            return "Final Narrative"
        return "Unknown call"

    monkeypatch.setattr(shifty, 'call_ollama', mock_ollama)
    
    # Mock lint_notes to always pass
    monkeypatch.setattr(shifty, 'lint_notes', lambda path, logger: True)

    # Run the main function with arguments
    output_file = mock_files / "output.shifty"
    args = [
        'shifty.py',
        '--notes-file', str(mock_files / "notes.md"),
        '--output-file', str(output_file),
        '--prompt-file-pass1', str(mock_files / "pass1.txt"),
        '--prompt-file-pass2', str(mock_files / "pass2.txt"),
        '--shorthand-file', str(mock_files / "shorthand.json"),
    ]
    monkeypatch.setattr('sys.argv', args)
    monkeypatch.setattr(shifty.sys, 'exit', lambda x: None)

    shifty.main()

    # Assert the final file was written with the correct content
    assert output_file.exists()
    assert output_file.read_text() == "Final Narrative"

def test_config_precedence(monkeypatch, mock_files: Path, logger: logging.Logger):
    """
    Tests that command-line arguments override environment variables.
    """
    # Set environment variables
    monkeypatch.setenv("SHIFTY_MODEL", "env_model")
    monkeypatch.setenv("SHIFTY_STYLE_GUIDE", "env_style.txt")
    monkeypatch.setenv("OLLAMA_HOST", "env_host")
    monkeypatch.setenv("SHIFTY_SHORTHAND", "env_shorthand.json")

    # Mock the functions that will be called
    mocked_ollama = MagicMock(return_value="mocked_response")
    monkeypatch.setattr(shifty, 'call_ollama', mocked_ollama)
    monkeypatch.setattr(shifty, 'lint_notes', lambda path, logger: True)

    # Run main with command-line args that override the env vars
    args = [
        'shifty.py',
        '--notes-file', str(mock_files / "notes.md"),
        '--model', 'cli_model',
        '--style-guide-file', str(mock_files / "style.txt"),
        '--shorthand-file', str(mock_files / "shorthand.json"),
        '--ollama-host', 'cli_host',
        '--prompt-file-pass1', str(mock_files / "pass1.txt"),
        '--prompt-file-pass2', str(mock_files / "pass2.txt"),
    ]
    monkeypatch.setattr('sys.argv', args)
    monkeypatch.setattr(shifty.sys, 'exit', lambda x: None)
    monkeypatch.setattr(shifty.logging, 'getLogger', lambda name=None: logger)

    shifty.main()

    # Construct expected prompt strings based on mock_files content and mocked response
    expected_raw_notes = (mock_files / "notes.md").read_text()
    expected_pass1_template = (mock_files / "pass1.txt").read_text()
    expected_pass2_template = (mock_files / "pass2.txt").read_text()
    expected_style_guide = (mock_files / "style.txt").read_text()
    
    with (mock_files / "shorthand.json").open('r') as f:
        shorthand_data = json.load(f)
    expected_shorthand_text = "\n".join(f"- {key}: {value}" for key, value in shorthand_data.items())

    expected_pass1_final_prompt = expected_pass1_template.replace("{{RAW_NOTES}}", expected_raw_notes)
    
    expected_pass2_final_prompt = expected_pass2_template.replace("{{OBSERVED_FACTS}}", "mocked_response")
    expected_pass2_final_prompt = expected_pass2_final_prompt.replace("{{OPTIONAL_STYLE_GUIDE}}", expected_style_guide)
    expected_pass2_final_prompt = expected_pass2_final_prompt.replace("{{SHORTHAND_DEFINITIONS}}", expected_shorthand_text)


    # Check that call_ollama was called with the values from the CLI, not the environment
    expected_calls = [
        call(expected_pass1_final_prompt, 'cli_model', 'cli_host', logger),
        call(expected_pass2_final_prompt, 'cli_model', 'cli_host', logger)
    ]
    mocked_ollama.assert_has_calls(expected_calls, any_order=False)

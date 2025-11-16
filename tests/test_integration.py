
import pytest
from pathlib import Path
import subprocess
import os

def test_shifty_sh_integration(tmp_path: Path, monkeypatch):
    """
    Tests that shifty.sh runs, finds .md files, and calls the python script
    with the correct file arguments.
    """
    # 1. Set up the test environment in tmp_path
    
    # Create a fake shifty.py that we can assert was called correctly.
    # This script will just touch the output file to prove it was run.
    fake_python_script = tmp_path / "shifty.py"
    fake_python_script.write_text(
        "import sys; from pathlib import Path; Path(sys.argv[4]).touch()"
    )
    
    # Create dummy notes and prompt files
    (tmp_path / "jake.md").write_text("### Jake\n09:00 Notes\nl8")
    (tmp_path / "sarah.md").write_text("### Sarah\n10:00 Notes\nl7")
    (tmp_path / "README.md").write_text("This should be ignored.")

    # The shifty.sh script is in the parent directory
    script_path = Path(__file__).parent.parent / "shifty.sh"

    # 2. Run the script from within the temporary directory
    monkeypatch.chdir(tmp_path)
    result = subprocess.run(
        [str(script_path)],
        capture_output=True,
        text=True
    )

    # 3. Assert the results
    assert result.returncode == 0, f"Script failed to run: {result.stderr}"
    assert "Processing: jake.md" in result.stdout
    assert "Processing: sarah.md" in result.stdout
    assert "README.md" not in result.stdout

    # Check that the fake python script was called and created the output files
    assert (tmp_path / "jake.shifty").exists()
    assert (tmp_path / "sarah.shifty").exists()
    assert not (tmp_path / "README.shifty").exists()

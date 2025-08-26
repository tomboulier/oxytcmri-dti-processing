import subprocess
import sys
from pathlib import Path
import pytest


class TestCommandLineInterface:
    """Test cases for the command line interface."""
    
    def test_help_output(self):
        """Test that running 'python main.py --help' shows the expected help message.
        
        This test verifies that the help output contains the standard options
        and commands sections.
        """
        # Get the path to the source directory
        project_base_directory = Path(__file__).parents[3]
        
        # Run the command
        result = subprocess.run(
            [sys.executable, "main.py", "--help"],
            cwd=project_base_directory,
            capture_output=True,
            text=True
        )
        
        # Check command executed successfully
        assert result.returncode == 0, f"Command failed with error: {result.stderr}"
        
        # Check the output contains the expected elements (updated for Rich/Typer format)
        # The CLI uses Rich formatting, so we check for key elements instead of exact format
        assert "--help" in result.stdout, f"Help output missing --help option.\nActual output: {result.stdout}"
        assert "Show this message and exit" in result.stdout, f"Help output missing help text.\nActual output: {result.stdout}"
        assert "Commands" in result.stdout, f"Help output missing Commands section.\nActual output: {result.stdout}"
        assert "compute-dti-normative-values" in result.stdout, f"Help output missing main command.\nActual output: {result.stdout}"

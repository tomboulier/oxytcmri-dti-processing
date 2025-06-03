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
        
        # Check the output contains the expected substring
        expected_substring = """Options:\n  --help  Show this message and exit.\n\nCommands:"""
        
        assert expected_substring in result.stdout, \
            f"Help output does not contain the expected substring.\nActual output: {result.stdout}"

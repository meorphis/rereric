import unittest
import os
import tempfile
import json
from pathlib import Path
from git_fuzzy_rerere.fuzzy_rerere import FuzzyRerere

class TestFuzzyRerere(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.test_dir = tempfile.mkdtemp()
        os.chdir(self.test_dir)
        
        # Initialize git repo
        os.system("git init")
        
        # Create .git directory structure
        self.git_dir = Path(self.test_dir) / ".git"
        self.fuzzy_rerere = FuzzyRerere(similarity_threshold=0.8, context_lines=3)

    def tearDown(self):
        """Clean up test environment after each test."""
        import shutil
        os.chdir("/")  # Move out of directory before removing
        shutil.rmtree(self.test_dir)

    def create_conflict_file(self, content):
        """Helper method to create a file with conflict markers."""
        file_path = Path(self.test_dir) / "conflict.txt"
        with open(file_path, "w") as f:
            f.write(content)
        return file_path

    def test_extract_conflict_markers_single_conflict(self):
        """Test extracting a single conflict with context lines."""
        content = """Some context before
More context before
[conflict start]
my local changes
span multiple
lines here


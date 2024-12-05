import unittest
from pathlib import Path
import tempfile
import shutil
import os
import json
from git_fuzzy_rerere.fuzzy_rerere import FuzzyRerere

class TestFuzzyRerere(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        
        # Initialize a test git repository
        os.chdir(self.test_dir)
        os.system("git init")
        
        self.fuzzy_rerere = FuzzyRerere(
            similarity_threshold=0.8,
            context_lines=3
        )

    def create_conflict_file(self, content, filename="test.txt"):
        """Helper to create a file with conflict markers"""
        file_path = Path(self.test_dir) / filename
        with open(file_path, "w") as f:
            f.write(content)
        return file_path

import unittest
from pathlib import Path
import tempfile
import shutil
import os
import json
from git_fuzzy_rerere.fuzzy_rerere import FuzzyRerere

class TestFuzzyRerere(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)
        
        # Initialize a test git repository
        os.chdir(self.test_dir)
        os.system("git init")
        
        self.fuzzy_rerere = FuzzyRerere(
            similarity_threshold=0.8,
            context_lines=3
        )

    def create_conflict_file(self, content, filename="test.txt"):
        """Helper to create a file with conflict markers"""
        file_path = Path(self.test_dir) / filename
        with open(file_path, "w") as f:
            f.write(content)
        return file_path

    def test_extract_conflict_markers(self):
        content = """Some context before
More context
<<<<<<< HEAD
my local changes
that span
multiple lines


import unittest
from pathlib import Path
import tempfile
import shutil
import os
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


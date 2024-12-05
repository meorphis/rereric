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
<<<<<<<
my local changes
span multiple
lines here
=======
their remote changes
also span
multiple lines
>>>>>>>
Some context after
More context after"""
        
        file_path = self.create_conflict_file(content)
        conflicts = self.fuzzy_rerere._extract_conflict_markers(file_path)
        
        self.assertEqual(len(conflicts), 1)
        expected_conflict = """More context before
<<<<<<<
my local changes
span multiple
lines here
=======
their remote changes
also span
multiple lines
>>>>>>>
Some context after"""
        self.assertEqual(conflicts[0], expected_conflict)

    def test_extract_conflict_markers_multiple_conflicts(self):
        """Test extracting multiple conflicts from a single file."""
        content = """First section
<<<<<<<
local change 1
=======
remote change 1
>>>>>>>
Middle section
<<<<<<<
local change 2
=======
remote change 2
>>>>>>>
Last section"""
        
        file_path = self.create_conflict_file(content)
        conflicts = self.fuzzy_rerere._extract_conflict_markers(file_path)
        
        self.assertEqual(len(conflicts), 2)
        self.assertIn("local change 1", conflicts[0])
        self.assertIn("local change 2", conflicts[1])

    def test_record_resolution(self):
        """Test recording a conflict resolution."""
        content = """
<<<<<<<
my changes
=======
their changes
>>>>>>>"""
        
        file_path = self.create_conflict_file(content)
        self.fuzzy_rerere.record_resolution(file_path)
        
        # Check that a record file was created
        records = list(self.fuzzy_rerere.rerere_dir.glob("*.json"))
        self.assertEqual(len(records), 1)
        
        # Verify record contents
        with open(records[0]) as f:
            record = json.load(f)
            self.assertEqual(record["file_path"], str(file_path))
            self.assertIn("my changes", record["conflict"])
            self.assertIn("their changes", record["conflict"])

    def test_find_similar_resolution_exact_match(self):
        """Test finding an exact match for conflict resolution."""
        content = """
<<<<<<<
feature code
=======
base code
>>>>>>>"""
        
        file_path = self.create_conflict_file(content)
        self.fuzzy_rerere.record_resolution(file_path)
        
        # Try to resolve the same conflict
        resolution, confidence = self.fuzzy_rerere._find_similar_resolution(content, file_path)
        self.assertIsNotNone(resolution)
        self.assertGreaterEqual(confidence, 0.8)

    def test_find_similar_resolution_different_file(self):
        """Test finding similar resolution from a different file."""
        content1 = """
<<<<<<<
def hello():
    print("Hello")
=======
def hello():
    print("Hi")
>>>>>>>"""

        content2 = """
<<<<<<<
def hello():
    print("Hello")
=======
def hello():
    print("Hey")
>>>>>>>"""
        
        file1 = self.create_conflict_file(content1)
        self.fuzzy_rerere.record_resolution(file1)
        
        # Create a second file with similar conflict
        file2 = Path(self.test_dir) / "conflict2.txt"
        with open(file2, "w") as f:
            f.write(content2)
            
        resolution, confidence = self.fuzzy_rerere._find_similar_resolution(content2, file2)
        self.assertIsNotNone(resolution)
        self.assertGreaterEqual(confidence, 0.8)

content here
>>>>>>>"""
        
        content2 = """
<<<<<<<
completely unrelated
=======
content here
>>>>>>>"""
        
        content2 = """
<<<<<<<
completely unrelated
=======
different stuff
>>>>>>>"""
        
        file1 = self.create_conflict_file(content1)
        self.fuzzy_rerere.record_resolution(file1)
        
        file2 = Path(self.test_dir) / "conflict2.txt"
        with open(file2, "w") as f:
            f.write(content2)
            
        resolution, confidence = self.fuzzy_rerere._find_similar_resolution(content2, file2)
        self.assertLess(confidence, 0.8)


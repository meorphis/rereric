"""Tests for the FuzzyRerere class."""

import shutil
import tempfile
from pathlib import Path

import pytest

from rerereric.core import Rerereric

@pytest.fixture(autouse=True)
def clean_fuzzy_rerere_dir(temp_git_dir):
    """Clean up fuzzy-rerere directory before and after each test."""
    # Clean before test
    git_dir = Path(temp_git_dir)
    fuzzy_rerere_dir = git_dir / '.git' / 'fuzzy-rerere'
    if fuzzy_rerere_dir.exists():
        shutil.rmtree(fuzzy_rerere_dir)

    yield

    # Clean after test
    if fuzzy_rerere_dir.exists():
        shutil.rmtree(fuzzy_rerere_dir)

@pytest.fixture
def temp_git_dir():
    """Create a temporary directory with a .git subdirectory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        git_dir = Path(tmpdir) / ".git"
        git_dir.mkdir()
        yield tmpdir

@pytest.fixture
def rerereric(temp_git_dir):
    """Create a FuzzyRerere instance with a temporary directory."""
    return Rerereric(similarity_threshold=0.8, context_lines=2, git_dir=temp_git_dir)

@pytest.fixture
def fixture_path():
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"

def read_fixture(fixture_path: Path, name: str) -> str:
    """Read a fixture file and return its contents."""
    with open(fixture_path / name) as f:
        return f.read()

def test_extract_conflict_markers(rerereric, fixture_path, tmp_path):
    # Copy fixture to temporary file
    test_file = tmp_path / "test.txt"
    shutil.copy(fixture_path / "simple_conflict.txt", test_file)
    
    conflicts = rerereric._extract_conflict_markers(test_file)
    
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict['before_context'].strip() == "This is some content before the conflict"
    assert conflict['after_context'].strip() == "This is some content after the conflict"
    assert "<<<<<<<" in conflict['conflict']
    assert "=======" in conflict['conflict']
    assert ">>>>>>>" in conflict['conflict']

def test_hash_conflict(rerereric):
    conflict = "<<<<<<<\nversion A\n=======\nversion B\n>>>>>>>"
    hash1 = rerereric._hash_conflict(conflict)
    hash2 = rerereric._hash_conflict(conflict)
    
    assert isinstance(hash1, str)
    assert len(hash1) == 16  # Check hash length
    assert hash1 == hash2    # Check hash consistency

def test_calculate_context_similarity(rerereric):
    context1_before = "def test():\n    x = 1\n"
    context1_after = "    return x\n"
    context2_before = "def test():\n    x = 1\n"
    context2_after = "    return x\n"
    
    similarity = rerereric._calculate_context_similarity(
        context1_before, context1_after,
        context2_before, context2_after
    )
    
    assert similarity == 1.0  # Identical contexts

def test_mark_and_save_resolutions(rerereric, fixture_path, tmp_path):
    # Setup test files
    conflict_file = tmp_path / "test.txt"
    shutil.copy(fixture_path / "simple_conflict.txt", conflict_file)
    
    # Mark conflicts
    rerereric.mark_conflicts([conflict_file])
    
    # Verify pre-file exists
    pre_path = rerereric.get_pre_path_from_file_path(conflict_file)
    assert pre_path.exists()
    
    # Simulate resolution
    shutil.copy(fixture_path / "simple_conflict_resolved.txt", conflict_file)
    
    # Save resolutions
    rerereric.save_resolutions()
    
    # Verify resolution file was created
    resolution_files = list(rerereric.rerere_dir.glob("*.json"))
    assert len(resolution_files) == 1

def test_reapply_resolutions_simple(rerereric, fixture_path, tmp_path):
    # First save a resolution
    conflict_file = tmp_path / "test.txt"
    shutil.copy(fixture_path / "simple_conflict.txt", conflict_file)
    
    rerereric.mark_conflicts([conflict_file])
    shutil.copy(fixture_path / "simple_conflict_resolved.txt", conflict_file)
    rerereric.save_resolutions()
    
    # Now test reapplying to a new conflict
    new_conflict_file = tmp_path / "test2.txt"
    shutil.copy(fixture_path / "simple_conflict.txt", new_conflict_file)
    
    # Try to resolve
    resolved = rerereric.reapply_resolutions([new_conflict_file])
    assert resolved
    
    # Verify content matches resolution
    with open(new_conflict_file) as f:
        content = f.read()
    expected = read_fixture(fixture_path, "simple_conflict_resolved.txt")
    assert content.strip() == expected.strip()

def test_reapply_resolutions_complex(rerereric, fixture_path, tmp_path):
    # First save a resolution
    conflict_file = tmp_path / "test.txt"
    shutil.copy(fixture_path / "complex_conflict.txt", conflict_file)
    
    rerereric.mark_conflicts([conflict_file])
    shutil.copy(fixture_path / "complex_conflict_resolved.txt", conflict_file)
    rerereric.save_resolutions()
    
    # Now test reapplying to a new conflict
    new_conflict_file = tmp_path / "test2.txt"
    shutil.copy(fixture_path / "complex_conflict_reappearance.txt", new_conflict_file)
    
    # Try to resolve
    resolved = rerereric.reapply_resolutions([new_conflict_file])
    assert resolved
    
    # Verify content matches resolution
    with open(new_conflict_file) as f:
        content = f.read()
    expected = read_fixture(fixture_path, "complex_conflict_reappearance_resolved.txt")
    assert content.strip() == expected.strip()

def test_hash_record(rerereric):
    record1 = {
        "conflict": "<<<<<<<\nA\n=======\nB\n>>>>>>>",
        "before_context": "before",
        "after_context": "after",
        "start_line": 1,
        "end_line": 5
    }
    record2 = record1.copy()
    
    hash1 = rerereric._hash_record(record1)
    hash2 = rerereric._hash_record(record2)
    
    assert isinstance(hash1, str)
    assert len(hash1) == 16
    assert hash1 == hash2

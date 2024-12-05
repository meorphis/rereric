import pytest
import shutil
from pathlib import Path

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

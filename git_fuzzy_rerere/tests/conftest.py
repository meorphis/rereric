import pytest
import shutil
from pathlib import Path

def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )

def pytest_sessionfinish(session, exitstatus):
    """Clean up any cached files after tests complete."""
    # Find the git directory from any test that created it
    for item in session.items:
        try:
            if hasattr(item, 'funcargs') and item.funcargs is not None:
                if 'temp_git_dir' in item.funcargs:
                    git_dir = Path(item.funcargs['temp_git_dir'])
                    fuzzy_rerere_dir = git_dir / '.git' / 'fuzzy-rerere'
                    if fuzzy_rerere_dir.exists():
                        shutil.rmtree(fuzzy_rerere_dir)
        except AttributeError:
            continue

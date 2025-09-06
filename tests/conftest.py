"""
Pytest configuration file to set up the Python path for tests.
"""
import sys
from pathlib import Path

# Add the project root to Python path so tests can import modules
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
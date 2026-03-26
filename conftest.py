"""Root conftest — add project subdirectories to sys.path without adding root."""
import sys
from pathlib import Path

root = Path(__file__).parent
for subdir in ["bot_templates", "shared", "tests"]:
    path = str(root / subdir)
    if path not in sys.path:
        sys.path.insert(0, path)

# Add root but after stdlib paths (append, not insert)
root_str = str(root)
if root_str not in sys.path:
    sys.path.append(root_str)

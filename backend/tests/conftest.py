"""
conftest.py — adds the backend root to sys.path so that bare imports like
`from services.dynamic_roadmap_service import ...` resolve without needing
an installed package.
"""
import sys
import os

# Insert the backend/ directory (parent of this tests/ folder) at the front
# of sys.path so pytest can find the service modules.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

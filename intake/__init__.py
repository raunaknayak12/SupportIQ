import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from web.intake import intake_bp

__all__ = ["intake_bp"]

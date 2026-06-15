import os
import shutil

def test_go_binary_available():
    assert shutil.which("go") is not None, "Go binary not found in PATH."

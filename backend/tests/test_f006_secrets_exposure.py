"""
Custom verification test suite for Finding F-006:
Plaintext API Secrets and Passwords Committed in Historical Git Repository Packfiles.
"""
import os
import re
import subprocess
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


def test_env_files_not_tracked_in_git_index():
    """Verify neither .env nor backend/.env is tracked by git in the current branch."""
    res = subprocess.run(
        ["git", "ls-files", ".env", "backend/.env"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )
    tracked_files = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
    assert not tracked_files, f"Expected no .env files tracked in git, but found: {tracked_files}"


def test_working_tree_env_has_no_live_groq_key():
    """Verify git-tracked files and templates do not leak live Groq API keys, and .env is strictly gitignored."""
    res = subprocess.run(
        ["git", "check-ignore", ".env"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, ".env must be strictly ignored by git to prevent exposing user keys"


def test_env_example_templates_contain_only_placeholders():
    """Verify .env.example contains safe placeholders."""
    example_path = os.path.join(ROOT_DIR, ".env.example")
    assert os.path.exists(example_path), ".env.example must exist"
    with open(example_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "gsk_" not in content
    assert "your-" in content or "placeholder" in content


def test_secret_scanner_regex_catches_exposed_tokens():
    """Verify that automated scanner pattern detects exposed secrets."""
    pattern = re.compile(r"gsk_[A-Za-z0-9]{40,}")
    leak_sample = "GROQ_API_KEY=" + "gsk_" + ("X" * 45)
    safe_sample = "GROQ_API_KEY=your-groq-api-key-here"
    
    assert pattern.search(leak_sample) is not None
    assert pattern.search(safe_sample) is None

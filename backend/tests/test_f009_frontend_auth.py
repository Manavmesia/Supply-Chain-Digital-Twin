"""
Custom verification test suite for Finding F-009:
Complete Absence of Client-Side Authentication Flow and Login Interface in Web Frontend.
"""
import os
import subprocess
import pytest

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))


def test_auth_frontend_components_exist():
    """Verify all required authentication components and pages are implemented."""
    required_files = [
        "src/context/AuthContext.tsx",
        "src/components/common/AuthGuard.tsx",
        "src/pages/LoginPage.tsx",
    ]
    for rel_path in required_files:
        full_path = os.path.join(FRONTEND_DIR, rel_path)
        assert os.path.exists(full_path), f"Missing required auth component: {rel_path}"


def test_app_router_wires_auth_guard_and_login():
    """Verify App.tsx wires AuthProvider, LoginPage, and AuthGuard."""
    app_tsx_path = os.path.join(FRONTEND_DIR, "src/App.tsx")
    with open(app_tsx_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "AuthProvider" in content
    assert "LoginPage" in content
    assert "AuthGuard" in content
    assert 'path="/login"' in content


def test_topbar_includes_auth_state_and_logout():
    """Verify TopBar.tsx imports and uses useAuth with logout button."""
    topbar_path = os.path.join(FRONTEND_DIR, "src/components/layout/TopBar.tsx")
    with open(topbar_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "useAuth" in content
    assert "logout" in content
    assert "Sign In" in content


def test_frontend_production_build_succeeds():
    """Verify 'npm run build' passes with zero TypeScript or packaging errors."""
    res = subprocess.run(
        ["npm", "run", "build"],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Frontend build failed:\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}"

"""
Custom verification test suite for Finding F-005:
Alembic Database Migration Failure via Unparameterized Host-Dependent Subprocess Invocation.
"""
import ast
import inspect
from unittest.mock import MagicMock, patch
import pytest
import importlib.util
import os

MIGRATION_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../alembic/versions/922ae13073d0_initial_schema.py")
)

spec = importlib.util.spec_from_file_location("initial_schema", MIGRATION_PATH)
migration_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration_mod)


def test_no_subprocess_import_in_migration_ast():
    """Verify that the migration file does not contain 'import subprocess' in its AST."""
    with open(MIGRATION_PATH, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=MIGRATION_PATH)

    subprocess_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if "subprocess" in alias.name:
                    subprocess_calls.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and "subprocess" in node.module:
                subprocess_calls.append(node.module)

    assert not subprocess_calls, f"Found prohibited subprocess imports in migration: {subprocess_calls}"


def test_upgrade_executes_via_bound_connection_not_psql():
    """Verify upgrade() uses op.get_bind() to execute DDL and never invokes subprocess."""
    mock_connection = MagicMock()
    mock_raw_conn = MagicMock()
    mock_dbapi = MagicMock()
    mock_connection.connection = mock_raw_conn
    mock_raw_conn.dbapi_connection = mock_dbapi
    
    # Configure mock_dbapi to support run_async or executescript
    executed_sql = []
    def fake_run_async(fn):
        fake_conn = MagicMock()
        def fake_exec(sql):
            executed_sql.append(sql)
        fake_conn.execute = fake_exec
        return fn(fake_conn)
    
    mock_dbapi.run_async = fake_run_async

    with patch("alembic.op.get_bind", return_value=mock_connection), \
         patch("subprocess.run") as mock_subprocess:
        
        migration_mod.upgrade()

        # Assert subprocess was never called
        assert not mock_subprocess.called, "subprocess.run should NOT be invoked"
        # Assert DDL was executed via bound connection
        assert len(executed_sql) == 1
        assert "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"" in executed_sql[0]


def test_upgrade_handles_executescript_fallback():
    """Verify upgrade() falls back to executescript for drivers providing it (e.g., sqlite test runner)."""
    mock_connection = MagicMock()
    mock_raw_conn = MagicMock()
    mock_dbapi = MagicMock(spec=["executescript"])
    mock_connection.connection = mock_raw_conn
    mock_raw_conn.dbapi_connection = mock_dbapi
    
    executed_scripts = []
    mock_dbapi.executescript.side_effect = lambda sql: executed_scripts.append(sql)

    with patch("alembic.op.get_bind", return_value=mock_connection), \
         patch("subprocess.run") as mock_subprocess:
        
        migration_mod.upgrade()

        assert not mock_subprocess.called
        assert len(executed_scripts) == 1
        assert "order_status" in executed_scripts[0]

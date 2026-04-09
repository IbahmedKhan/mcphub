"""Tests for Database Query MCP Server."""
import sys
import os
import sqlite3
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from servers.database.engine import DatabaseEngine


@pytest.fixture
def db():
    engine = DatabaseEngine()
    # Create test database
    conn = sqlite3.connect("test_mcphub.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, role TEXT)")
    conn.execute("DELETE FROM users")
    conn.executemany("INSERT INTO users VALUES (?,?,?)", [
        (1, "Alice", "admin"), (2, "Bob", "user"), (3, "Charlie", "user"),
    ])
    conn.commit()
    conn.close()
    return engine


@pytest.fixture(autouse=True)
def cleanup():
    yield
    if os.path.exists("test_mcphub.db"):
        os.remove("test_mcphub.db")


class TestConnection:
    @pytest.mark.asyncio
    async def test_connect_success(self, db):
        result = await db.connect_database("sqlite:///test_mcphub.db", "test")
        assert result["status"] == "connected"
        assert "users" in result["tables"]

    @pytest.mark.asyncio
    async def test_connect_nonexistent(self, db):
        result = await db.connect_database("sqlite:///nonexistent_xyz.db", "bad")
        assert result["status"] == "connected"  # SQLite creates file


class TestQuery:
    @pytest.mark.asyncio
    async def test_select_query(self, db):
        await db.connect_database("sqlite:///test_mcphub.db", "test")
        result = await db.query("SELECT * FROM users", "test")
        assert result["row_count"] == 3
        assert result["columns"] == ["id", "name", "role"]

    @pytest.mark.asyncio
    async def test_blocks_drop(self, db):
        await db.connect_database("sqlite:///test_mcphub.db", "test")
        result = await db.query("DROP TABLE users", "test")
        assert "error" in result
        assert "Blocked" in result["error"]

    @pytest.mark.asyncio
    async def test_blocks_delete(self, db):
        await db.connect_database("sqlite:///test_mcphub.db", "test")
        result = await db.query("DELETE FROM users WHERE id=1", "test")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_blocks_insert(self, db):
        await db.connect_database("sqlite:///test_mcphub.db", "test")
        result = await db.query("INSERT INTO users VALUES (4,'Dan','user')", "test")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_allows_updated_in_column_name(self, db):
        """Ensure word-boundary matching doesn't block 'UPDATED_RECORDS' style names."""
        await db.connect_database("sqlite:///test_mcphub.db", "test")
        # This should NOT be blocked — 'updated' appears as part of a column reference
        result = await db.query("SELECT name FROM users WHERE name = 'UPDATED_VALUE'", "test")
        # Should execute (0 rows), not be blocked
        assert "error" not in result or "Blocked" not in result.get("error", "")

    @pytest.mark.asyncio
    async def test_no_alias_error(self, db):
        result = await db.query("SELECT 1", "nonexistent")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_auto_limit(self, db):
        await db.connect_database("sqlite:///test_mcphub.db", "test")
        result = await db.query("SELECT * FROM users", "test", limit=2)
        assert result["row_count"] == 2


class TestDescribe:
    @pytest.mark.asyncio
    async def test_describe_table(self, db):
        await db.connect_database("sqlite:///test_mcphub.db", "test")
        result = await db.describe_table("users", "test")
        assert result["column_count"] == 3
        assert result["row_count"] == 3

    @pytest.mark.asyncio
    async def test_invalid_table_name(self, db):
        await db.connect_database("sqlite:///test_mcphub.db", "test")
        result = await db.describe_table("../../etc/passwd", "test")
        assert "error" in result


class TestExport:
    @pytest.mark.asyncio
    async def test_csv_export(self, db):
        await db.connect_database("sqlite:///test_mcphub.db", "test")
        result = await db.export_results("SELECT * FROM users", "csv", "test")
        assert result["format"] == "csv"
        assert "Alice" in result["content"]
        assert result["row_count"] == 3

    @pytest.mark.asyncio
    async def test_csv_injection_prevention(self, db):
        """Values starting with = + - @ should be prefixed."""
        engine = DatabaseEngine()
        assert engine._sanitize_csv_value("=cmd()") == "'=cmd()"
        assert engine._sanitize_csv_value("+1234") == "'+1234"
        assert engine._sanitize_csv_value("normal") == "normal"

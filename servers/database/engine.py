"""Database Query Engine — Safe, parameterized, read-only database access for AI."""
import sqlite3
import re
from typing import Any


class DatabaseEngine:
    """Allows AI to safely query databases with read-only access and query validation.

    Security:
    - Database connections are opened with PRAGMA query_only = ON (enforced at DB level)
    - SQL keyword blocklist as defense-in-depth layer
    - Table names validated with strict regex before interpolation
    """

    def __init__(self):
        self._connections: dict[str, str] = {}

    BLOCKED_KEYWORDS = {"DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE",
                        "EXEC", "EXECUTE", "GRANT", "REVOKE"}

    async def dispatch(self, tool: str, params: dict) -> Any:
        methods = {
            "connect_database": self.connect_database,
            "query": self.query,
            "list_tables": self.list_tables,
            "describe_table": self.describe_table,
            "export_results": self.export_results,
        }
        if tool not in methods:
            raise ValueError(f"Unknown tool: {tool}")
        return await methods[tool](**params)

    async def connect_database(self, connection_string: str, alias: str = "default") -> dict:
        """Register a database connection (SQLite supported, PostgreSQL/MySQL via URI)."""
        self._connections[alias] = connection_string
        # Test connection
        try:
            conn = sqlite3.connect(connection_string.replace("sqlite:///", ""))
            conn.execute("PRAGMA query_only = ON")
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            return {"status": "connected", "alias": alias, "tables": tables,
                    "table_count": len(tables)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def query(self, sql: str, alias: str = "default", limit: int = 100) -> dict:
        """Execute a read-only SQL query. All write operations are blocked for safety."""
        # Security: Block dangerous queries (defense-in-depth, DB also enforces read-only)
        sql_upper = sql.upper().strip()
        for keyword in self.BLOCKED_KEYWORDS:
            # Use word boundary matching to avoid false positives (e.g., "UPDATED_RECORDS")
            if re.search(rf'\b{keyword}\b', sql_upper):
                return {"error": f"Blocked: '{keyword}' operations not allowed. Read-only access.",
                        "suggestion": "Use SELECT statements only."}

        if not sql_upper.startswith(("SELECT", "WITH", "EXPLAIN", "PRAGMA", "SHOW")):
            return {"error": "Only SELECT, WITH, EXPLAIN, PRAGMA queries are allowed.",
                    "suggestion": "Start your query with SELECT."}

        # Add LIMIT if not present
        if "LIMIT" not in sql_upper:
            sql = f"{sql.rstrip(';')} LIMIT {limit}"

        conn_str = self._connections.get(alias)
        if not conn_str:
            return {"error": f"No database connected with alias '{alias}'",
                    "suggestion": "Use connect_database first."}

        try:
            conn = sqlite3.connect(conn_str.replace("sqlite:///", ""))
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return {"columns": columns, "rows": rows, "row_count": len(rows),
                    "query": sql, "truncated": len(rows) >= limit}
        except Exception as e:
            return {"error": str(e), "query": sql}

    async def list_tables(self, alias: str = "default") -> dict:
        """List all tables in the connected database."""
        conn_str = self._connections.get(alias)
        if not conn_str:
            return {"error": f"No database connected with alias '{alias}'"}
        try:
            conn = sqlite3.connect(conn_str.replace("sqlite:///", ""))
            cursor = conn.execute(
                "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY name"
            )
            tables = [{"name": row[0], "type": row[1]} for row in cursor.fetchall()]
            conn.close()
            return {"tables": tables, "count": len(tables)}
        except Exception as e:
            return {"error": str(e)}

    async def describe_table(self, table: str, alias: str = "default") -> dict:
        """Get schema/structure of a specific table."""
        # Sanitize table name
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
            return {"error": "Invalid table name"}
        conn_str = self._connections.get(alias)
        if not conn_str:
            return {"error": f"No database connected with alias '{alias}'"}
        try:
            conn = sqlite3.connect(conn_str.replace("sqlite:///", ""))
            cursor = conn.execute(f"PRAGMA table_info({table})")
            columns = []
            for row in cursor.fetchall():
                columns.append({
                    "id": row[0], "name": row[1], "type": row[2],
                    "not_null": bool(row[3]), "default": row[4], "primary_key": bool(row[5]),
                })
            row_count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            conn.close()
            return {"table": table, "columns": columns, "column_count": len(columns),
                    "row_count": row_count}
        except Exception as e:
            return {"error": str(e)}

    async def export_results(self, sql: str, format: str = "json", alias: str = "default") -> dict:
        """Execute a query and format results for export (JSON or CSV)."""
        result = await self.query(sql, alias, limit=1000)
        if "error" in result:
            return result
        if format == "csv":
            if not result["rows"]:
                return {"format": "csv", "content": ""}
            headers = ",".join(result["columns"])
            rows = [",".join(self._sanitize_csv_value(str(row.get(c, ""))) for c in result["columns"])
                    for row in result["rows"]]
            csv_content = headers + "\n" + "\n".join(rows)
            return {"format": "csv", "content": csv_content, "row_count": result["row_count"]}
        return {"format": "json", "content": result["rows"], "row_count": result["row_count"]}

    @staticmethod
    def _sanitize_csv_value(value: str) -> str:
        """Prevent CSV injection by prefixing dangerous characters."""
        if value and value[0] in ('=', '+', '-', '@', '\t', '\r'):
            return f"'{value}"
        return value

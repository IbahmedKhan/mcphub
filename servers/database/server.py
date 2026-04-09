"""Database Query MCP Server — Safe AI-powered database access via MCP."""
from fastmcp import FastMCP

from .engine import DatabaseEngine

mcp = FastMCP(
    "mcphub-database-query",
    description="Safe, read-only database query engine for AI. Supports SQLite with "
                "query validation, SQL injection prevention, and automatic result limiting.",
)

engine = DatabaseEngine()


@mcp.tool()
async def connect_database(connection_string: str, alias: str = "default") -> dict:
    """Connect to a database. Currently supports SQLite databases.

    Args:
        connection_string: Database connection string (e.g., 'sqlite:///mydata.db')
        alias: Friendly name for this connection (default: 'default')
    """
    return await engine.connect_database(connection_string, alias)


@mcp.tool()
async def query(sql: str, alias: str = "default", limit: int = 100) -> dict:
    """Execute a read-only SQL query. Write operations (INSERT, UPDATE, DELETE, DROP)
    are blocked for safety. Results are automatically limited.

    Args:
        sql: The SQL SELECT query to execute
        alias: Database connection alias (default: 'default')
        limit: Maximum rows to return (default: 100)
    """
    return await engine.query(sql, alias, limit)


@mcp.tool()
async def list_tables(alias: str = "default") -> dict:
    """List all tables and views in the connected database.

    Args:
        alias: Database connection alias (default: 'default')
    """
    return await engine.list_tables(alias)


@mcp.tool()
async def describe_table(table: str, alias: str = "default") -> dict:
    """Get the schema/structure of a table including column names, types, and constraints.

    Args:
        table: Name of the table to describe
        alias: Database connection alias (default: 'default')
    """
    return await engine.describe_table(table, alias)


@mcp.tool()
async def export_results(sql: str, format: str = "json", alias: str = "default") -> dict:
    """Execute a query and export results in JSON or CSV format.

    Args:
        sql: The SQL SELECT query to execute
        format: Output format — 'json' or 'csv' (default: 'json')
        alias: Database connection alias (default: 'default')
    """
    return await engine.export_results(sql, format, alias)


if __name__ == "__main__":
    mcp.run()

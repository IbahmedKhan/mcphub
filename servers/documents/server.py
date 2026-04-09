"""Document Analyzer MCP Server — AI-powered document analysis via MCP."""
from fastmcp import FastMCP

from .analyzer import DocumentAnalyzer

mcp = FastMCP(
    "mcphub-document-analyzer",
    description="AI-powered document analysis and extraction. Supports PDF text extraction, "
                "CSV parsing with statistics, plain text analysis, and table detection.",
)

analyzer = DocumentAnalyzer()


@mcp.tool()
async def analyze_pdf(file_path: str) -> dict:
    """Extract and analyze content from a PDF file. Returns page count, text content,
    metadata, and character counts per page.

    Args:
        file_path: Absolute path to the PDF file
    """
    return await analyzer.analyze_pdf(file_path)


@mcp.tool()
async def analyze_csv(file_path: str, max_rows: int = 100) -> dict:
    """Parse and analyze a CSV file. Returns column names, data types, statistics
    (min/max/avg for numeric columns), sample values, and row counts.

    Args:
        file_path: Absolute path to the CSV file
        max_rows: Maximum rows to analyze (default: 100)
    """
    return await analyzer.analyze_csv(file_path, max_rows)


@mcp.tool()
async def extract_text(file_path: str, max_chars: int = 10000) -> dict:
    """Extract plain text content from any text-based file (.txt, .md, .log, .json, etc).

    Args:
        file_path: Absolute path to the file
        max_chars: Maximum characters to extract (default: 10000)
    """
    return await analyzer.extract_text(file_path, max_chars)


@mcp.tool()
async def summarize_document(file_path: str) -> dict:
    """Generate an intelligent summary of any document. Auto-detects file type
    and provides relevant information (structure, content preview, statistics).

    Args:
        file_path: Absolute path to the document
    """
    return await analyzer.summarize_document(file_path)


@mcp.tool()
async def extract_tables(file_path: str) -> dict:
    """Extract tabular data from CSV or text files. Detects tables in text files
    by identifying tab-separated or pipe-separated data.

    Args:
        file_path: Absolute path to the file
    """
    return await analyzer.extract_tables(file_path)


if __name__ == "__main__":
    mcp.run()

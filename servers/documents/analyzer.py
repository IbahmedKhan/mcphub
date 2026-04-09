"""Document Analyzer — AI-powered document analysis, text extraction, and summarization."""
import csv
import io
import json
import os
import sys
from typing import Any
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from orchestrator.security import validate_file_path


class DocumentAnalyzer:
    """Analyzes documents — PDF text extraction, CSV parsing, data summarization."""

    async def dispatch(self, tool: str, params: dict) -> Any:
        methods = {
            "analyze_pdf": self.analyze_pdf,
            "analyze_csv": self.analyze_csv,
            "extract_text": self.extract_text,
            "summarize_document": self.summarize_document,
            "extract_tables": self.extract_tables,
        }
        if tool not in methods:
            raise ValueError(f"Unknown tool: {tool}")
        return await methods[tool](**params)

    async def analyze_pdf(self, file_path: str) -> dict:
        """Extract and analyze content from a PDF file."""
        path = validate_file_path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}
        if not path.suffix.lower() == ".pdf":
            return {"error": "Not a PDF file"}

        try:
            # Try PyPDF2 first, fallback to basic extraction
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(str(path))
                pages = []
                full_text = ""
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    pages.append({"page": i + 1, "text": text[:2000],
                                  "char_count": len(text)})
                    full_text += text + "\n"
                return {
                    "file": path.name,
                    "size_bytes": path.stat().st_size,
                    "page_count": len(reader.pages),
                    "total_characters": len(full_text),
                    "pages": pages[:20],
                    "metadata": dict(reader.metadata) if reader.metadata else {},
                }
            except ImportError:
                return {
                    "file": path.name,
                    "size_bytes": path.stat().st_size,
                    "note": "PyPDF2 not installed. Install with: pip install PyPDF2",
                    "basic_info": {
                        "exists": True,
                        "size_mb": round(path.stat().st_size / 1024 / 1024, 2),
                        "modified": os.path.getmtime(str(path)),
                    },
                }
        except Exception as e:
            return {"error": str(e), "file": file_path}

    async def analyze_csv(self, file_path: str, max_rows: int = 100) -> dict:
        """Parse and analyze a CSV file — columns, data types, statistics."""
        path = validate_file_path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                # Detect delimiter
                sample = f.read(4096)
                f.seek(0)
                dialect = csv.Sniffer().sniff(sample)
                reader = csv.DictReader(f, dialect=dialect)
                columns = reader.fieldnames or []
                rows = []
                for i, row in enumerate(reader):
                    if i >= max_rows:
                        break
                    rows.append(dict(row))

            # Column statistics
            col_stats = {}
            for col in columns:
                values = [r.get(col, "") for r in rows if r.get(col)]
                numeric_values = []
                for v in values:
                    try:
                        numeric_values.append(float(v))
                    except (ValueError, TypeError):
                        pass
                stat = {"non_empty": len(values), "unique": len(set(values))}
                if numeric_values:
                    stat["type"] = "numeric"
                    stat["min"] = min(numeric_values)
                    stat["max"] = max(numeric_values)
                    stat["avg"] = round(sum(numeric_values) / len(numeric_values), 2)
                else:
                    stat["type"] = "text"
                    stat["sample_values"] = list(set(values))[:5]
                col_stats[col] = stat

            return {
                "file": path.name,
                "size_bytes": path.stat().st_size,
                "columns": columns,
                "column_count": len(columns),
                "row_count": len(rows),
                "column_stats": col_stats,
                "sample_rows": rows[:5],
                "truncated": len(rows) >= max_rows,
            }
        except Exception as e:
            return {"error": str(e), "file": file_path}

    async def extract_text(self, file_path: str, max_chars: int = 10000) -> dict:
        """Extract plain text from any text-based file."""
        path = validate_file_path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_chars)

            lines = content.split("\n")
            words = content.split()

            return {
                "file": path.name,
                "size_bytes": path.stat().st_size,
                "content": content,
                "line_count": len(lines),
                "word_count": len(words),
                "char_count": len(content),
                "truncated": len(content) >= max_chars,
            }
        except Exception as e:
            return {"error": str(e), "file": file_path}

    async def summarize_document(self, file_path: str) -> dict:
        """Generate a summary of a document — detects type and provides key information."""
        path = validate_file_path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        ext = path.suffix.lower()
        info = {
            "file": path.name,
            "type": ext,
            "size_bytes": path.stat().st_size,
            "size_readable": self._format_size(path.stat().st_size),
        }

        if ext == ".csv":
            csv_data = await self.analyze_csv(file_path, max_rows=50)
            info["summary"] = (f"CSV file with {csv_data.get('column_count', 0)} columns "
                              f"and {csv_data.get('row_count', 0)}+ rows. "
                              f"Columns: {', '.join(csv_data.get('columns', []))}")
            info["details"] = csv_data
        elif ext == ".pdf":
            pdf_data = await self.analyze_pdf(file_path)
            info["summary"] = (f"PDF with {pdf_data.get('page_count', '?')} pages, "
                              f"{pdf_data.get('total_characters', '?')} characters.")
            info["details"] = pdf_data
        elif ext in (".txt", ".md", ".log", ".json", ".xml", ".yaml", ".yml"):
            text_data = await self.extract_text(file_path, max_chars=5000)
            info["summary"] = (f"Text file with {text_data.get('line_count', 0)} lines, "
                              f"{text_data.get('word_count', 0)} words.")
            info["details"] = text_data
        else:
            info["summary"] = f"File type '{ext}' — basic info only."

        return info

    async def extract_tables(self, file_path: str) -> dict:
        """Extract tabular data from CSV or text files."""
        path = validate_file_path(file_path)
        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        if path.suffix.lower() == ".csv":
            return await self.analyze_csv(file_path, max_rows=500)

        # Try to detect tables in text files
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(50000)

            # Look for tab-separated or pipe-separated data
            lines = content.split("\n")
            tables = []
            current_table = []

            for line in lines:
                if "\t" in line or "|" in line:
                    sep = "\t" if "\t" in line else "|"
                    cells = [c.strip() for c in line.split(sep) if c.strip()]
                    if len(cells) >= 2:
                        current_table.append(cells)
                else:
                    if len(current_table) >= 2:
                        tables.append(current_table)
                    current_table = []

            if len(current_table) >= 2:
                tables.append(current_table)

            return {
                "file": path.name,
                "tables_found": len(tables),
                "tables": [{"rows": len(t), "columns": len(t[0]) if t else 0,
                            "data": t[:20]} for t in tables[:5]],
            }
        except Exception as e:
            return {"error": str(e)}

    def _format_size(self, size_bytes: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"

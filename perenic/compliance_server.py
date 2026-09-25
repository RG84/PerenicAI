"""A small local MCP server that lets Claude read a folder of compliance documents.

PAT Compliance starts this automatically when you pass --compliance-docs, so
you normally never run it yourself. To try it by hand:

    python -m perenic.compliance_server compliance_docs/healthcare

Supported files: .md, .txt and .pdf. Markdown files are split into sections
at their headings (#, ##, ...), PDFs into pages, and text files into parts.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

SUPPORTED = {".md", ".txt", ".pdf"}
LINES_PER_TEXT_PART = 40
WORD = re.compile(r"[a-z0-9§.]+")


@dataclass
class Section:
    document: str  # file name, e.g. "hipaa_security_rule.md"
    title: str  # heading, page or part, e.g. "§164.312(b) Audit controls"
    text: str


class DocumentLibrary:
    """Loads every document in a folder and lets you search and read sections."""

    def __init__(self, folder: str | Path):
        self.folder = Path(folder)
        if not self.folder.is_dir():
            raise FileNotFoundError(f"Compliance folder not found: {self.folder}")
        self.sections: list[Section] = []
        for path in sorted(self.folder.rglob("*")):
            if path.suffix.lower() in SUPPORTED and path.is_file():
                self.sections.extend(self.split_into_sections(path))

    def split_into_sections(self, path: Path) -> list[Section]:
        name = str(path.relative_to(self.folder))
        if path.suffix.lower() == ".pdf":
            from pypdf import PdfReader

            pages = PdfReader(path).pages
            return [Section(name, f"Page {n}", page.extract_text() or "") for n, page in enumerate(pages, 1)]

        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if path.suffix.lower() == ".md":
            return self.split_markdown(name, lines)
        return [
            Section(name, f"Part {n}", "\n".join(lines[start : start + LINES_PER_TEXT_PART]))
            for n, start in enumerate(range(0, len(lines), LINES_PER_TEXT_PART), 1)
        ]

    def split_markdown(self, name: str, lines: list[str]) -> list[Section]:
        sections = []
        title, body = "Introduction", []
        for line in lines:
            if line.startswith("#"):
                if "".join(body).strip():
                    sections.append(Section(name, title, "\n".join(body).strip()))
                title, body = line.lstrip("#").strip(), []
            else:
                body.append(line)
        if "".join(body).strip():
            sections.append(Section(name, title, "\n".join(body).strip()))
        return sections

    def list_documents(self) -> list[str]:
        """Each document with the titles of its sections."""
        documents: dict[str, list[str]] = {}
        for section in self.sections:
            documents.setdefault(section.document, []).append(section.title)
        return [f"{document}: {'; '.join(titles)}" for document, titles in documents.items()]

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        """Sections that share the most words with the query, best first."""
        query_words = {word for word in WORD.findall(query.lower()) if len(word) > 2}
        scored = []
        for section in self.sections:
            section_words = set(WORD.findall(f"{section.title} {section.text}".lower()))
            score = len(query_words & section_words)
            if score:
                scored.append((score, section))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            {"document": s.document, "section": s.title, "text": s.text[:1500]}
            for _, s in scored[:max_results]
        ]

    def read_section(self, document: str, section: str) -> str:
        """The full text of one section. Only documents in the folder can be read."""
        for s in self.sections:
            if s.document == document and s.title == section:
                return s.text
        return f"No section '{section}' in '{document}'. Use list_documents to see what exists."


def build_server(folder: str | Path):
    """Create the MCP server with three tools Claude can call."""
    from mcp.server.mcpserver import MCPServer

    library = DocumentLibrary(folder)
    server = MCPServer(
        "perenic-compliance-docs",
        instructions="Read-only access to an organisation's compliance and regulation documents.",
    )

    @server.tool()
    def list_documents() -> list[str]:
        """List every compliance document and the titles of its sections."""
        return library.list_documents()

    @server.tool()
    def search_documents(query: str, max_results: int = 5) -> list[dict]:
        """Search the compliance documents. Returns the best-matching sections with their document name and title."""
        return library.search(query, max_results)

    @server.tool()
    def read_section(document: str, section: str) -> str:
        """Read the full text of one section, using the document and section names from the other tools."""
        return library.read_section(document, section)

    return server


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m perenic.compliance_server <folder>")
    build_server(sys.argv[1]).run("stdio")

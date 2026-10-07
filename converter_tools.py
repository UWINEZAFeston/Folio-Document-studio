"""Tools the agent is allowed to call (read_document, write_document)."""
import io, html, re
from statistics import median
from html.parser import HTMLParser
from pypdf import PdfReader
import pdfplumber
from docx import Document
from docx.shared import Pt
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import markdown as md_lib


class _TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], False
    def handle_starttag(self, tag, attrs):
        self.skip = tag in ("script", "style")
        if tag in ("p", "br", "div", "h1", "h2", "h3", "li"):
            self.parts.append("\n")
    def handle_endtag(self, tag):
        self.skip = False
        if tag in ("p", "div", "h1", "h2", "h3", "li"):
            self.parts.append("\n")
    def handle_data(self, d):
        if not self.skip:
            self.parts.append(d)


class _RichDocumentText(str):
    def __new__(cls, text, docx_blocks):
        instance = super().__new__(cls, text)
        instance.docx_blocks = docx_blocks
        return instance


def _pdf_char_is_underlined(character, lines):
    return any(
        abs(line["top"] - character["bottom"]) <= 2
        and line["x0"] < character["x1"]
        and line["x1"] > character["x0"]
        and abs(line["bottom"] - line["top"]) <= 1
        for line in lines
    )


def _pdf_line_runs(characters, lines):
    runs = []
    previous_character = None
    for character in characters:
        value = character.get("text", "")
        if not value:
            continue
        if (previous_character and not value.isspace()
                and character["x0"] - previous_character["x1"] > character.get("size", 12) * 0.2):
            value = " " + value
        font_name = character.get("fontname", "").lower()
        style = {
            "bold": any(marker in font_name for marker in ("bold", "black", "heavy", "demi")),
            "italic": "italic" in font_name or "oblique" in font_name,
            "underline": _pdf_char_is_underlined(character, lines),
            "size": character.get("size"),
        }
        if runs and all(runs[-1][key] == style[key] for key in style):
            runs[-1]["text"] += value
        else:
            runs.append({"text": value, **style})
        previous_character = character
    return runs


def _pdf_heading_level(font_size, body_font_size):
    if not body_font_size or not font_size:
        return None
    ratio = font_size / body_font_size
    if ratio >= 1.5:
        return 1
    if ratio >= 1.3:
        return 2
    if ratio >= 1.15:
        return 3
    return None


def read_document(data: bytes, ext: str) -> str:
    """TOOL 1: extract text and table structure from supported document bytes."""
    if ext in ("txt", "md"):
        return data.decode("utf-8", errors="ignore")
    if ext == "html":
        p = _TextOnly(); p.feed(data.decode("utf-8", errors="ignore"))
        return "".join(p.parts)
    if ext == "pdf":
        pages, docx_blocks = [], []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                tables = page.find_tables()
                if not tables:
                    tables = page.find_tables(table_settings={
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                    })
                    tables = [table for table in tables if len(table.extract()[0]) > 1]
                boxes = [table.bbox for table in tables]
                body_page = page.filter(
                    lambda item: item.get("object_type") != "char"
                    or not any(
                        left <= (item["x0"] + item["x1"]) / 2 <= right
                        and top <= (item["top"] + item["bottom"]) / 2 <= bottom
                        for left, top, right, bottom in boxes
                    )
                ) if boxes else page
                body_sizes = [
                    character["size"] for character in page.chars
                    if character.get("text", "").strip()
                ]
                body_font_size = median(body_sizes) if body_sizes else None
                page_items = []
                for line in body_page.extract_text_lines(return_chars=True):
                    characters = line["chars"]
                    sizes = [character["size"] for character in characters if character.get("text", "").strip()]
                    font_size = median(sizes) if sizes else body_font_size
                    heading = _pdf_heading_level(font_size, body_font_size)
                    page_items.append({
                        "top": line["top"],
                        "bottom": line["bottom"],
                        "type": "paragraph",
                        "text": line["text"],
                        "heading": heading,
                        "runs": _pdf_line_runs(characters, page.lines),
                    })
                for table in tables:
                    rows = [
                        row for row in table.extract()
                        if any(cell and cell.strip() for cell in row)
                    ]
                    table_text = _format_markdown_table(rows)
                    if table_text:
                        page_items.append({"top": table.bbox[1], "type": "table", "rows": rows, "text": table_text})

                page_items.sort(key=lambda item: item["top"])
                page_text = []
                for item in page_items:
                    if item["type"] == "paragraph":
                        previous = docx_blocks[-1] if docx_blocks else None
                        line_gap = item["top"] - previous["bottom"] if previous and previous["type"] == "paragraph" else None
                        if (line_gap is not None and line_gap <= 0.45 * max(1, previous["bottom"] - previous["top"])
                                and not item["heading"] and not previous["heading"]):
                            _append_pdf_runs(previous["runs"], item["runs"], separator=" ")
                            previous["text"] += " " + item["text"]
                            previous["bottom"] = item["bottom"]
                            page_text[-1] += "\n" + item["text"]
                            continue
                    docx_blocks.append(item)
                    page_text.append(item["text"])
                if page_text:
                    pages.append("\n".join(page_text))
        return _RichDocumentText("\n\n".join(pages), docx_blocks)
    if ext == "docx":
        doc = Document(io.BytesIO(data))
        return "\n\n".join(p.text for p in doc.paragraphs)
    raise ValueError(f"Unsupported input format: {ext}")


def _clean_paragraphs(text: str):
    return [p.strip() for p in text.replace("\r", "").split("\n\n") if p.strip()]


def _append_pdf_runs(destination, incoming, separator=""):
    if destination and incoming and separator:
        first_style = {key: value for key, value in incoming[0].items() if key != "text"}
        destination.append({"text": separator, **first_style})
    for run in incoming:
        if destination and all(destination[-1][key] == run[key] for key in run if key != "text"):
            destination[-1]["text"] += run["text"]
        else:
            destination.append(run.copy())


def _format_markdown_table(rows) -> str:
    if not rows:
        return ""
    column_count = max(len(row) for row in rows)
    if not column_count:
        return ""

    normalized = [
        [str(cell or "").replace("\n", " ").replace("|", "\\|").strip() for cell in row]
        + [""] * (column_count - len(row))
        for row in rows
    ]
    lines = ["| " + " | ".join(normalized[0]) + " |"]
    lines.append("| " + " | ".join("---" for _ in range(column_count)) + " |")
    lines.extend("| " + " | ".join(row) + " |" for row in normalized[1:])
    return "\n".join(lines)


def _parse_markdown_table(block: str):
    lines = block.splitlines()
    if len(lines) < 2:
        return None

    def cells(line):
        line = line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            return None
        return [cell.strip().replace("\\|", "|") for cell in line[1:-1].split("|")]

    header, separator = cells(lines[0]), cells(lines[1])
    if not header or not separator or len(header) != len(separator):
        return None
    if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator):
        return None

    rows = [header]
    for line in lines[2:]:
        row = cells(line)
        if row is None or len(row) != len(header):
            return None
        rows.append(row)
    return rows


def write_document(text: str, fmt: str) -> bytes:
    """TOOL 2: render text into txt/md/html/pdf/docx bytes."""
    paras = _clean_paragraphs(text)
    if fmt in ("txt", "md"):
        return "\n\n".join(paras).encode("utf-8")
    if fmt == "html":
        body = "\n".join(f"<p>{html.escape(p)}</p>" for p in paras)
        return f"<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>{body}</body></html>".encode()
    if fmt == "docx":
        d = Document()
        if isinstance(text, _RichDocumentText):
            for block in text.docx_blocks:
                if block["type"] == "table":
                    table = d.add_table(rows=len(block["rows"]), cols=max(len(row) for row in block["rows"]))
                    table.style = "Table Grid"
                    for row_index, row in enumerate(block["rows"]):
                        for column_index, value in enumerate(row):
                            cell = table.cell(row_index, column_index)
                            cell.text = value or ""
                            if row_index == 0:
                                for run in cell.paragraphs[0].runs:
                                    run.bold = True
                    continue

                style = f"Heading {block['heading']}" if block["heading"] else "Normal"
                paragraph = d.add_paragraph(style=style)
                for item in block["runs"]:
                    run = paragraph.add_run(item["text"])
                    run.bold = item["bold"]
                    run.italic = item["italic"]
                    run.underline = item["underline"]
                    if item["size"]:
                        run.font.size = Pt(item["size"])
            buf = io.BytesIO(); d.save(buf); return buf.getvalue()

        for p in paras:
            rows = _parse_markdown_table(p)
            if rows is None:
                d.add_paragraph(p)
                continue
            table = d.add_table(rows=len(rows), cols=len(rows[0]))
            table.style = "Table Grid"
            for row_index, row in enumerate(rows):
                for column_index, value in enumerate(row):
                    cell = table.cell(row_index, column_index)
                    cell.text = value
                    if row_index == 0:
                        for run in cell.paragraphs[0].runs:
                            run.bold = True
        buf = io.BytesIO(); d.save(buf); return buf.getvalue()
    if fmt == "pdf":
        buf, styles = io.BytesIO(), getSampleStyleSheet()
        story = []
        for p in paras:
            story += [Paragraph(html.escape(p).replace("\n", "<br/>"), styles["Normal"]), Spacer(1, 8)]
        SimpleDocTemplate(buf, pagesize=A4).build(story)
        return buf.getvalue()
    raise ValueError(f"Unsupported output format: {fmt}")

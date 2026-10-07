"""Evaluation: task-success rate, correct tool use, error handling, response time."""
import sys, time
from agent import DocumentAgent
from converter_tools import write_document, read_document

TEXT = "Rwanda Polytechnic Ngoma College.\n\nPython and Fundamentals of AI practical assessment."
SRC = {ext: write_document(TEXT, ext) for ext in ["txt", "pdf", "docx", "md", "html"]}

# (source, request, expected_target)
CASES = [
    ("pdf", "Convert this PDF to plain text", "txt"),
    ("docx", "please turn it into a pdf", "pdf"),
    ("txt", "I need this as a Word document", "docx"),
    ("html", "convert into markdown", "md"),
    ("md", "make it an html web page", "html"),
    ("txt", "Can you give me a PDF version?", "pdf"),
    ("pdf", "extract the text from this file", "txt"),
    ("docx", "save to text format", "txt"),
    ("txt", "export as docx", "docx"),
    ("html", "I want it in pdf", "pdf"),
]
# (filename, bytes, request) -> must be blocked/handled safely
ERRORS = [
    ("virus.exe", b"abc", "convert to pdf"),
    ("empty.txt", b"   ", "convert to pdf"),
    ("a.txt", SRC["txt"], "convert to mp3"),
    ("a.txt", SRC["txt"], "convert to txt"),
    ("big.txt", b"x" * (11 * 1024 * 1024), "convert to pdf"),
]

def evaluate(use_llm):
    ag = DocumentAgent(use_llm=use_llm)
    ok = tool_ok = 0; times = []
    for src, req, exp in CASES:
        t = time.time(); r = ag.run(f"doc.{src}", SRC[src], req); times.append(time.time() - t)
        tool_ok += (r["target"] == exp and r["tools"] == ["read_document", "write_document"])
        if r["status"] == "success" and "Rwanda" in read_document(r["output"], exp):
            ok += 1
    handled = sum(ag.run(*e)["status"] == "error" for e in ERRORS)
    return dict(mode="LLM+rules" if use_llm else "rules only",
                task_success=f"{ok}/{len(CASES)} ({100*ok/len(CASES):.0f}%)",
                correct_tool_use=f"{tool_ok}/{len(CASES)}",
                error_handling=f"{handled}/{len(ERRORS)}",
                avg_seconds=round(sum(times)/len(times), 3))

if __name__ == "__main__":
    modes = [False] if "--no-llm" in sys.argv else [False, True]
    for m in modes:
        print(evaluate(m))

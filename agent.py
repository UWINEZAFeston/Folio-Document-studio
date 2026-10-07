"""Agentic AI: LLM (intent) -> guardrails -> whitelisted tools -> activity log."""
import json, re, time, os, datetime
from converter_tools import read_document, write_document

CONFIG = json.load(open(os.path.join(os.path.dirname(__file__), "config.json")))

SYNONYMS = {"text": "txt", "txt": "txt", "pdf": "pdf", "word": "docx", "docx": "docx",
            "markdown": "md", "md": "md", "html": "html"}
_WORDS = "|".join(SYNONYMS)
_TO = re.compile(rf"\b(?:to|into|as|in)\s+(?:a\s+|an\s+)?(?:plain\s+)?({_WORDS})\b", re.I)
_ANY = re.compile(rf"\b({_WORDS})\b", re.I)


class GuardrailError(Exception):
    pass


class DocumentAgent:
    def __init__(self, use_llm=None):
        self.use_llm = CONFIG["use_llm"] if use_llm is None else use_llm
        self.pipe = None
        if self.use_llm:
            try:
                from transformers import pipeline
                self.pipe = pipeline("text2text-generation", model=CONFIG["model_name"])
            except Exception as e:           # error handling: fall back safely
                print("LLM unavailable, using rules:", e)
                self.use_llm = False

    # ---- reasoning step -------------------------------------------------
    def _rules(self, request):
        m = _TO.findall(request) or _ANY.findall(request)
        return SYNONYMS[m[-1].lower()] if m else None

    def parse_intent(self, request):
        """Returns (target_format, method). LLM output is validated (guardrail)."""
        if self.use_llm and self.pipe:
            prompt = CONFIG["prompt_template"].format(request=request)
            out = self.pipe(prompt, max_new_tokens=CONFIG["max_new_tokens"],
                            do_sample=CONFIG["do_sample"])[0]["generated_text"].strip().lower()
            if out in CONFIG["supported_output"]:
                return out, "llm"
        return self._rules(request), "rules"

    # ---- action step ----------------------------------------------------
    def run(self, filename, data, request):
        t0 = time.time()
        rec = {"time": datetime.datetime.now().isoformat(timespec="seconds"),
               "file": os.path.basename(filename), "request": request, "tools": []}
        result = {"status": "error", "message": "", "output": None, "target": None}
        try:
            src = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if src not in CONFIG["supported_input"]:
                raise GuardrailError(f"Input type '.{src}' is not allowed.")
            if len(data) > CONFIG["max_file_mb"] * 1024 * 1024:
                raise GuardrailError("File is too large.")
            target, method = self.parse_intent(request)
            rec["intent"], rec["method"] = target, method
            if target not in CONFIG["supported_output"]:
                raise GuardrailError("Requested output format is not supported "
                                     f"(allowed: {', '.join(CONFIG['supported_output'])}).")
            if target == src:
                raise GuardrailError("Source and target formats are the same.")
            text = read_document(data, src); rec["tools"].append("read_document")
            if not text.strip():
                raise GuardrailError("No readable text found (scanned PDF or empty file).")
            out = write_document(text, target); rec["tools"].append("write_document")
            result.update(status="success", output=out, target=target,
                          message=f"Converted {src.upper()} -> {target.upper()}")
        except GuardrailError as e:
            result["message"] = f"Blocked: {e}"
        except Exception as e:
            result["message"] = f"Error: {e}"
        rec.update(status=result["status"], message=result["message"],
                   seconds=round(time.time() - t0, 3))
        self._log(rec)
        result["seconds"], result["tools"] = rec["seconds"], rec["tools"]
        return result

    def _log(self, rec):
        path = os.path.join(os.path.dirname(__file__), CONFIG["log_file"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

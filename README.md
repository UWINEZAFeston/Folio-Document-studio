# AI Document Converter (Agentic AI)
Module ITLPA701 – Python and Fundamentals of AI | CAT 2 Practical

## 1. Problem domain
Task automation / document processing. People struggle to move content between formats (PDF → text, Word → PDF ...). The user uploads a file and **asks in plain English**; the AI works out what is wanted and does it.

## 2. AI approach and justification
**Agentic AI** = pretrained LLM + tools + controlled actions.
- A pretrained `google/flan-t5-small` (Hugging Face) reads the request and chooses the target format (no training from scratch).
- The LLM never touches files directly; it can only trigger two whitelisted tools (`read_document`, `write_document`).
- Why not RAG or deep learning? Nothing needs retrieval or a trained classifier; the problem is "understand request -> perform action", which is exactly what an agent does.

## 3. Resources
Test documents (txt, pdf, docx, md, html) are generated in `evaluate.py`; users supply their own files. Prompt set = 10 request phrasings + 5 error cases.

## 4. Architecture
```
User file + request ──► Guardrails (type, size) ──► LLM intent parser (flan-t5-small)
                                                       │ validate output ∈ {txt,pdf,docx,md,html}
                                                       │ (fallback: keyword rules)
                                                       ▼
          Tool 1 read_document ──► clean text ──► Tool 2 write_document ──► Converted file
                                                       │
                                            Activity log (logs/activity_log.jsonl)
```
Environment: Python 3.10+, PyCharm/Jupyter/Spyder, `pip install -r requirements.txt`.
Functionalities: read 5 formats, write 5 formats, intent detection, guardrails, logging, web UI.

## 5. Implementation (files)
| File | Role |
|---|---|
| `converter_tools.py` | The two tools (pypdf, python-docx, reportlab, html parser) |
| `agent.py` | LLM intent parsing, guardrails, tool orchestration, logging |
| `config.json` | Saved model name, prompt, parameters, limits (reproducibility) |
| `evaluate.py` | Evaluation harness |
| `app.py` | Streamlit interface |

Run: `streamlit run app.py` and `python evaluate.py`.

## 6. Parameters chosen
| Parameter | Value | Why |
|---|---|---|
| model | flan-t5-small | Instruction-following, tiny, runs on lab CPUs |
| do_sample | False | Deterministic, repeatable answers |
| max_new_tokens | 6 | Answer is a single word (e.g. "docx") |
| prompt | closed list of options | Forces the LLM to pick from allowed formats |
| max_file_mb | 10 | Prevents memory abuse |
| allowed formats | whitelist | Agent control / guardrail |

## 7. Evaluation (agentic metrics)
`python evaluate.py` measures:
- **Task-success rate** – output re-read and must contain original content.
- **Correct tool use** – right target format and tools called in order (read then write).
- **Error handling** – 5 bad cases (.exe file, empty file, unsupported "mp3", same format, 11 MB file) must be blocked politely.
- **Response time** – average seconds per request.

Rule-based mode result: 10/10 success, 10/10 correct tool use, 5/5 errors handled, ~0.03 s.
Run the LLM mode in the lab and record your numbers. **Tuning:** if the LLM misreads a phrase, adjust `prompt_template` in `config.json`; the validator already falls back to keyword rules whenever the LLM's answer is not a valid format. Compare both modes in your report and keep the better one.

## 8. Demonstration
Streamlit page: upload → type request → Convert → Download, with an expandable activity log.

## 9. Responsible use
| Risk / limitation | Mitigation |
|---|---|
| Private documents uploaded | Processed in memory only; no files stored, only metadata logged |
| LLM misreads request (hallucination) | Output validated against a whitelist; fallback rules |
| Malicious/oversized files | Extension whitelist, 10 MB limit, no code execution |
| Scanned PDFs have no text, layout/images lost | Clear error message; state that only text is converted |

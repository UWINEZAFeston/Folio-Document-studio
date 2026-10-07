import json
import os

import streamlit as st

from agent import CONFIG, DocumentAgent


st.set_page_config(
    page_title="Folio | Document studio",
    page_icon=":material/article:",
    layout="wide",
)

dark_mode = st.session_state.get("folio_dark_mode", False)
theme = {
    "background": "#142019" if dark_mode else "#F2F4EC",
    "surface": "#223229" if dark_mode else "#E5ECE4",
    "text": "#EDF2E9" if dark_mode else "#1D3028",
    "muted": "#A8B7AA" if dark_mode else "#586B60",
    "border": "#3D5044" if dark_mode else "#C8D4C8",
    "link": "#E99A79" if dark_mode else "#A6422C",
}

st.html("""
<style>
:root {
    --folio-ink: #1d3028;
    --folio-paper: #f2f4ec;
    --folio-sage: #dce7dc;
    --folio-vermilion: #c45134;
    --folio-blue: #496f82;
}

[data-testid="stMainBlockContainer"] {
    max-width: 1240px;
    padding-top: 2.4rem;
    padding-bottom: 3.5rem;
}

[data-testid="stHeader"] {
    background: transparent;
}

.st-key-folio_dark_mode {
    margin-top: 90px;
}

.folio-masthead {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    color: var(--folio-text);
    font-family: 'DM Sans', sans-serif;
    font-size: 0.86rem;
    font-weight: 700;
}

.folio-mark {
    display: grid;
    width: 2rem;
    height: 2rem;
    place-items: center;
    background: var(--folio-ink);
    color: var(--folio-paper);
    font-family: 'Fraunces', serif;
    font-size: 1.15rem;
}

.folio-masthead small {
    display: block;
    margin-top: 0.08rem;
    color: var(--folio-muted);
    font-size: 0.68rem;
    font-weight: 500;
}

.folio-intro {
    padding: 2.1rem 0 1rem;
    animation: folio-arrive 650ms ease-out both;
}

.folio-eyebrow,
.folio-art-label,
.folio-art-meta,
.folio-format-line {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
}

.folio-eyebrow {
    color: var(--folio-vermilion);
    text-transform: uppercase;
}

.folio-title {
    margin: 0.15rem 0 0;
    color: var(--folio-text);
    font-family: 'Fraunces', Georgia, serif;
    font-size: 5.5rem;
    font-weight: 500;
    line-height: 0.98;
}

.folio-subtitle {
    margin-top: 0.8rem;
    color: var(--folio-muted);
    font-size: 1.05rem;
}

.folio-art {
    position: relative;
    min-height: 470px;
    overflow: hidden;
    background-color: var(--folio-ink);
    background-image: repeating-linear-gradient(
        0deg,
        transparent 0,
        transparent 35px,
        rgba(232, 239, 224, 0.055) 36px
    );
    color: var(--folio-paper);
    animation: folio-arrive 780ms 100ms ease-out both;
}

.folio-art-label {
    position: absolute;
    top: 1.25rem;
    left: 1.4rem;
    color: #c4d2c7;
}

.folio-art-number {
    position: absolute;
    right: 1.4rem;
    bottom: 1.25rem;
    color: #c4d2c7;
}

.folio-sheet {
    position: absolute;
    top: 5.4rem;
    width: 47%;
    height: 19rem;
    padding: 1.35rem;
    color: var(--folio-ink);
    box-shadow: 0 18px 40px rgba(5, 20, 14, 0.28);
}

.folio-sheet-source {
    left: 5%;
    z-index: 1;
    transform: rotate(-7deg);
    background: #f5f0df;
    animation: folio-source-in 800ms 160ms ease-out both;
}

.folio-sheet-output {
    right: 5%;
    z-index: 2;
    transform: rotate(5deg);
    background: #eef3e8;
    animation: folio-output-in 850ms 240ms ease-out both;
}

.folio-filetype {
    display: inline-block;
    padding: 0.25rem 0.45rem;
    background: var(--folio-vermilion);
    color: white;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.67rem;
}

.folio-sheet-output .folio-filetype {
    background: var(--folio-blue);
}

.folio-sheet-heading {
    margin: 1.55rem 0 1.1rem;
    font-family: 'Fraunces', Georgia, serif;
    font-size: 1.48rem;
    line-height: 1.08;
}

.folio-rule {
    height: 1px;
    margin: 0.7rem 0;
    background: rgba(29, 48, 40, 0.19);
}

.folio-rule.short {
    width: 68%;
}

.folio-highlight {
    width: 71%;
    height: 0.58rem;
    margin: 1.1rem 0 0.75rem;
    background: #e6b29b;
}

.folio-sheet-output .folio-highlight {
    width: 82%;
    height: 0.95rem;
    background: #c8d9cb;
}

.folio-transform {
    position: absolute;
    top: 48%;
    left: 50%;
    z-index: 3;
    display: grid;
    width: 2.35rem;
    height: 2.35rem;
    place-items: center;
    border: 1px solid rgba(242, 244, 236, 0.48);
    background: var(--folio-ink);
    color: #f2a079;
    font-size: 1.25rem;
    transform: translate(-50%, -50%);
}

.folio-format-line {
    margin-top: 0.9rem;
    color: var(--folio-muted);
}

@keyframes folio-arrive {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes folio-source-in {
    from { opacity: 0; transform: translate(-8px, 8px) rotate(-7deg); }
    to { opacity: 1; transform: translate(0, 0) rotate(-7deg); }
}

@keyframes folio-output-in {
    from { opacity: 0; transform: translate(8px, 8px) rotate(5deg); }
    to { opacity: 1; transform: translate(0, 0) rotate(5deg); }
}

@media (max-width: 760px) {
    [data-testid="stMainBlockContainer"] {
        padding-top: 1.2rem;
    }

    .folio-intro {
        padding-top: 1.6rem;
    }

    .folio-title {
        font-size: 4.1rem;
    }

    .folio-art {
        min-height: 390px;
        margin-top: 1.6rem;
    }

    .folio-sheet {
        top: 5rem;
        width: 44%;
        height: 16rem;
        padding: 1rem;
    }

    .folio-sheet-heading {
        margin-top: 1.1rem;
        font-size: 1.2rem;
    }
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        scroll-behavior: auto !important;
    }
}
</style>
""")

st.html(f"""
<style>
:root {{
    --background-color: {theme["background"]};
    --secondary-background-color: {theme["surface"]};
    --text-color: {theme["text"]};
    --border-color: {theme["border"]};
    --link-color: {theme["link"]};
    --folio-text: {theme["text"]};
    --folio-muted: {theme["muted"]};
}}
[data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
    background-color: {theme["background"]};
}}
[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stExpander"] {{
    border-color: {theme["border"]};
}}
[data-testid="stFileUploaderDropzone"] {{
    background-color: {theme["surface"]};
    border-color: {theme["border"]};
}}
[data-testid="stTextInput"] [data-baseweb="input"] > div {{
    background-color: {theme["surface"]};
    border-color: {theme["border"]};
}}
[data-testid="stTextInput"] input {{
    background-color: {theme["surface"]} !important;
    color: {theme["text"]} !important;
}}
[data-testid="stWidgetLabel"], [data-testid="stCaptionContainer"] {{
    color: {theme["text"]};
}}
[data-testid="stToolbar"] button {{
    color: {theme["text"]} !important;
}}
[data-testid="stToolbar"] button svg {{
    fill: {theme["text"]} !important;
}}
</style>
""")

brand_column, mode_column = st.columns([6, 1], vertical_alignment="center")
with brand_column:
    st.html("""
    <div class="folio-masthead">
        <div class="folio-mark">F</div>
        <div>FOLIO<small>DOCUMENT STUDIO</small></div>
    </div>
    """)
with mode_column:
    st.toggle("Dark mode", key="folio_dark_mode")


@st.cache_resource
def get_agent():
    return DocumentAgent()


agent = get_agent()

intro_column, art_column = st.columns([1.02, 0.98], gap="large", vertical_alignment="center")

with intro_column:
    st.html("""
    <section class="folio-intro">
        <div class="folio-eyebrow">A considered workspace</div>
        <h1 class="folio-title">Folio</h1>
        <div class="folio-subtitle">Document studio <span aria-hidden="true">/</span> 01</div>
    </section>
    """)

    with st.form("folio_conversion_form", border=True):
        uploaded_file = st.file_uploader(
            "Choose a document",
            type=CONFIG["supported_input"],
            max_upload_size=CONFIG["max_file_mb"],
        )
        request = st.text_input(
            "Conversion request",
            value="Convert this document to PDF",
            placeholder="Convert this PDF to Word",
        )
        submitted = st.form_submit_button(
            "Convert",
            type="primary",
            icon=":material/arrow_forward:",
            width="stretch",
        )

    formats = "  /  ".join(fmt.upper() for fmt in CONFIG["supported_input"])
    st.html(f'<div class="folio-format-line">{formats} <span aria-hidden="true">&nbsp;&nbsp;·&nbsp;&nbsp;</span> {CONFIG["max_file_mb"]} MB max</div>')

with art_column:
    st.html("""
    <div class="folio-art" role="img" aria-label="Two document pages in PDF and Word formats">
        <div class="folio-art-label">FIELD NOTES&nbsp;&nbsp;/&nbsp;&nbsp;001</div>
        <div class="folio-sheet folio-sheet-source">
            <span class="folio-filetype">PDF</span>
            <div class="folio-sheet-heading">A study in<br>clearer pages</div>
            <div class="folio-rule"></div>
            <div class="folio-rule short"></div>
            <div class="folio-highlight"></div>
            <div class="folio-rule"></div>
            <div class="folio-rule short"></div>
        </div>
        <div class="folio-sheet folio-sheet-output">
            <span class="folio-filetype">DOCX</span>
            <div class="folio-sheet-heading">A study in<br>clearer pages</div>
            <div class="folio-rule"></div>
            <div class="folio-rule short"></div>
            <div class="folio-highlight"></div>
            <div class="folio-rule"></div>
            <div class="folio-rule short"></div>
        </div>
        <div class="folio-transform" aria-hidden="true">&rarr;</div>
        <div class="folio-art-number">F&nbsp;&nbsp;/&nbsp;&nbsp;01</div>
    </div>
    """)

if submitted:
    if uploaded_file is None:
        st.session_state["folio_conversion"] = {
            "status": "error",
            "message": "Choose a document to convert.",
        }
    else:
        with st.spinner("Preparing your document..."):
            result = agent.run(uploaded_file.name, uploaded_file.getvalue(), request)
        if result["status"] == "success":
            output_name = uploaded_file.name.rsplit(".", 1)[0] + "." + result["target"]
            st.session_state["folio_conversion"] = {
                **result,
                "filename": output_name,
            }
        else:
            st.session_state["folio_conversion"] = result

conversion = st.session_state.get("folio_conversion")
if conversion:
    with st.container(border=True):
        if conversion["status"] == "success":
            st.success(f'{conversion["message"]} · {conversion["seconds"]:.2f}s')
            st.download_button(
                "Download converted document",
                data=conversion["output"],
                file_name=conversion["filename"],
                icon=":material/download:",
                type="primary",
                width="stretch",
            )
        else:
            st.error(conversion["message"])

with st.expander("Recent activity", icon=":material/history:"):
    log_path = os.path.join(os.path.dirname(__file__), CONFIG["log_file"])
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as log_file:
            records = [json.loads(line) for line in log_file if line.strip()]
        if records:
            st.json(records[-10:])
        else:
            st.caption("No recent conversions.")
    else:
        st.caption("No recent conversions.")
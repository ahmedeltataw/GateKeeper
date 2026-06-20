"""Docs — the GateKeeper documentation hub, embedded in the dashboard.

Renders the markdown under ``dashboard/docs_content`` with section navigation,
full-text search, interactive in-page links, and a card layout — all the
features of the former standalone portal, now a dashboard page.

Conflict avoidance (this page coexists with ``st.navigation`` and the other
pages):
* CSS is scoped under ``.gk-doc`` so it never restyles the rest of the dashboard.
* Session/query state is namespaced: search uses ``docs_search`` and the current
  document is tracked with the ``?doc=`` query param (distinct from anything the
  dashboard navigation uses).
"""

from __future__ import annotations

import html
import posixpath
import re
from pathlib import Path

import streamlit as st

from session import require_auth  # keep docs behind the dashboard gate

CONTENT_DIR = Path(__file__).resolve().parent.parent / "docs_content"

# Sidebar-style index sections: display label -> content subfolder.
SECTIONS: dict[str, str] = {
    "📘 Users": "users",
    "🛠️ Developer Portal": "developers",
    "🧩 Model Cards": "models",
}

ORDER: dict[str, list[str]] = {
    "users": ["getting_started.md", "authentication.md", "making_requests.md", "faq.md"],
    "developers": ["adding_new_model.md", "running_tests.md"],
    "models": ["overview.md", "glm-4.7-flash.md", "glm-4.5-flash.md", "glm-4.6v-flash.md"],
}

DEFAULT_PAGE = "users/getting_started.md"
_QUERY_KEY = "doc"          # URL param holding the current document
_SEARCH_KEY = "docs_search"  # session/widget key for the search box


# --------------------------------------------------------------------------- #
# Scoped styling (everything lives under .gk-doc so it cannot leak)
# --------------------------------------------------------------------------- #
CSS = """
<style>
.gk-doc {
    background: #ffffff;
    border: 1px solid #e6e6ef;
    border-radius: 16px;
    padding: 2rem 2.5rem;
    box-shadow: 0 8px 30px rgba(20, 20, 60, 0.10);
    color: #2c2c3a;
}
.gk-doc h1 {
    font-size: 1.9rem; font-weight: 800; color: #1a1a2e;
    border-bottom: 2px solid #e6e6ef; padding-bottom: 0.5rem; margin: 0 0 1.2rem 0;
}
.gk-doc h2 { color: #1a1a2e; margin-top: 1.8rem; font-weight: 700; }
.gk-doc h3 { color: #1a1a2e; margin-top: 1.4rem; font-weight: 600; }
.gk-doc p, .gk-doc li { color: #2c2c3a; line-height: 1.7; }
.gk-doc a { color: #5b5bd6; text-decoration: none; font-weight: 600; }
.gk-doc a:hover { text-decoration: underline; }
.gk-doc code {
    background: #f0f0f7; color: #c7254e; padding: 0.12rem 0.4rem;
    border-radius: 6px; font-size: 0.88em;
}
.gk-doc pre {
    background: #0f1020; color: #e8e8f5; padding: 1rem 1.1rem;
    border: 1px solid #e6e6ef; border-radius: 12px; overflow-x: auto;
}
.gk-doc pre code { background: transparent; color: #e8e8f5; padding: 0; }
.gk-doc table {
    border-collapse: collapse; width: 100%; margin: 1rem 0;
    border-radius: 10px; overflow: hidden; box-shadow: 0 1px 4px rgba(20,20,60,0.05);
}
.gk-doc th { background: #5b5bd6; color: #fff; text-align: left; padding: 0.6rem 0.9rem; }
.gk-doc td { border-top: 1px solid #e6e6ef; padding: 0.55rem 0.9rem; }
.gk-doc blockquote {
    border-left: 4px solid #5b5bd6; background: #f3f3fc;
    padding: 0.75rem 1.1rem; border-radius: 8px; color: #33334d; margin: 1.25rem 0;
}
.gk-result {
    border: 1px solid #e6e6ef; border-radius: 12px; padding: 1rem 1.25rem;
    margin-bottom: 0.9rem; background: #ffffff; box-shadow: 0 2px 10px rgba(20,20,60,0.05);
    color: #2c2c3a;
}
.gk-result .gk-path { color: #6b7280; font-size: 0.78rem; }
.gk-snippet { color: #44445a; font-size: 0.9rem; }
.gk-snippet mark { background: #fff1a8; padding: 0 2px; border-radius: 3px; }
.gk-section-label {
    color: #6b7280; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; margin: 1rem 0 0.2rem 0;
}
</style>
"""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def docs_in(folder: str) -> list[Path]:
    base = CONTENT_DIR / folder
    if not base.is_dir():
        return []
    files = sorted(base.glob("*.md"), key=lambda p: p.name)
    preferred = ORDER.get(folder, [])
    rank = {name: i for i, name in enumerate(preferred)}
    return sorted(files, key=lambda p: (rank.get(p.name, len(preferred)), p.name))


def all_docs() -> list[Path]:
    return sorted(CONTENT_DIR.rglob("*.md"))


def rel(path: Path) -> str:
    return path.relative_to(CONTENT_DIR).as_posix()


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def title_of(path: Path) -> str:
    for line in read(path).splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("_", " ").replace("-", " ").title()


def nav_to(page: str) -> None:
    """Callback: select a document and clear any active search."""
    st.query_params[_QUERY_KEY] = page
    st.session_state[_SEARCH_KEY] = ""


_MD_LINK = re.compile(r"\]\((?!https?://)([^)#]+\.md)(#[^)]*)?\)")


def rewrite_links(markdown: str, current_page: str) -> str:
    """Turn relative .md links into in-app navigation (?doc=...) links."""
    base = posixpath.dirname(current_page)

    def repl(match: re.Match[str]) -> str:
        target = posixpath.normpath(posixpath.join(base, match.group(1)))
        if (CONTENT_DIR / target).is_file():
            return f"](?{_QUERY_KEY}={target})"
        return match.group(0)

    return _MD_LINK.sub(repl, markdown)


def make_snippet(text: str, query: str, width: int = 160) -> str:
    low = text.lower()
    idx = low.find(query.lower())
    if idx == -1:
        return ""
    start = max(0, idx - width // 2)
    end = min(len(text), idx + width // 2)
    fragment = text[start:end].replace("\n", " ").strip()
    safe = html.escape(fragment)
    pattern = re.compile(re.escape(html.escape(query)), re.IGNORECASE)
    safe = pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", safe, count=1)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{safe}{suffix}"


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #
def _render_index() -> None:
    """Left-hand section navigation (buttons drive ?doc=...)."""
    for label, folder in SECTIONS.items():
        files = docs_in(folder)
        if not files:
            continue
        st.markdown(f'<div class="gk-section-label">{label}</div>', unsafe_allow_html=True)
        for path in files:
            st.button(
                title_of(path),
                key=f"docs-nav-{rel(path)}",
                width="stretch",
                on_click=nav_to,
                args=(rel(path),),
            )


def _render_document() -> None:
    """Render the document selected via the ?doc= query param."""
    page = st.query_params.get(_QUERY_KEY, DEFAULT_PAGE)
    current = CONTENT_DIR / page
    if not current.is_file():
        page, current = DEFAULT_PAGE, CONTENT_DIR / DEFAULT_PAGE
    body = rewrite_links(read(current), page)
    st.markdown(f'<div class="gk-doc">\n\n{body}\n\n</div>', unsafe_allow_html=True)


def _render_search(query: str) -> None:
    """Full-width search results across every doc file."""
    st.markdown(f"#### Search results for “{query}”")
    hits = 0
    for path in all_docs():
        text = read(path)
        if query.lower() not in text.lower():
            continue
        hits += 1
        st.markdown(
            f'<div class="gk-result"><div class="gk-path">{rel(path)}</div>'
            f'<b>{title_of(path)}</b>'
            f'<div class="gk-snippet">{make_snippet(text, query)}</div></div>',
            unsafe_allow_html=True,
        )
        st.button(
            f"Open: {title_of(path)}",
            key=f"docs-open-{rel(path)}",
            on_click=nav_to,
            args=(rel(path),),
        )
    if hits == 0:
        st.info("No matches found. Try a different term.")


def main() -> None:
    require_auth()
    st.markdown(CSS, unsafe_allow_html=True)
    st.title("📖 Documentation")

    query = st.text_input(
        "Search the docs",
        key=_SEARCH_KEY,
        placeholder="🔍 Search all docs…",
        label_visibility="collapsed",
    ).strip()

    if query:
        _render_search(query)
        return

    index_col, doc_col = st.columns([1, 3], gap="large")
    with index_col:
        _render_index()
    with doc_col:
        _render_document()


main()

import html
import streamlit as st
from agent import ask

st.set_page_config(page_title="Doubt Agent", layout="wide", initial_sidebar_state="collapsed")

# Design tokens. Spacing is on a 4px grid (4, 8, 12, 16, 24, 32, 48).
# Colour: sage-grey background, near-black ink, one bright accent used once
# (the rule beside the answer).
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,600&display=swap');

:root {
  --ink: #14181C;
  --muted: #4A544E;
  --line: #B9C1B5;
  --paper: #E2E6DF;
  --field: #F4F6F2;
  --hover: #D3D9CF;
  --bright: #1F4FFF;
}

.stApp, p, li, a, label, input, button, h1, h2, h3 {
  font-family: 'Public Sans', system-ui, sans-serif;
}
* { transition: none !important; animation: none !important; }

header[data-testid="stHeader"], footer, #MainMenu,
[data-testid="stHeaderActionElements"], [data-testid="stSidebar"],
[data-testid="collapsedControl"] { display: none; }

.block-container {
  max-width: 1040px;
  margin: 0 auto 0 0;
  padding: 48px 32px 48px 32px;
}

h1.title {
  font-family: 'Source Serif 4', Georgia, serif;
  font-size: 32px; line-height: 40px; font-weight: 600;
  margin: 0 0 8px 0; padding: 0; color: var(--ink);
}
p.lead {
  font-size: 16px; line-height: 24px; color: var(--muted);
  max-width: 560px; margin: 0 0 32px 0;
}
h2.sec {
  font-size: 20px; line-height: 28px; font-weight: 600;
  margin: 0 0 12px 0; padding: 0; color: var(--ink);
}

.stTextInput label p { font-size: 14px; line-height: 20px; font-weight: 500; }
.stTextInput input {
  font-size: 16px; line-height: 24px; padding: 12px 16px;
  background: var(--field); border: 1px solid var(--ink); border-radius: 4px;
}

.stButton button {
  min-height: 32px; padding: 4px 12px; font-size: 14px; line-height: 20px;
  background: transparent; color: var(--ink);
  border: 1px solid var(--line); border-radius: 4px;
}
.stButton button:hover { background: var(--hover); border-color: var(--ink); color: var(--ink); }

.st-key-answer { border-left: 4px solid var(--bright); padding-left: 16px; }
.st-key-answer p, .st-key-answer li { font-size: 16px; line-height: 24px; }

.kv { border-top: 1px solid var(--line); margin: 0 0 32px 0; }
.kv div {
  display: flex; justify-content: space-between; gap: 16px;
  padding: 12px 0; border-bottom: 1px solid var(--line);
  font-size: 14px; line-height: 20px;
}
.kv .k { color: var(--muted); }
.kv .v { text-align: right; font-weight: 500; }

ul.links { list-style: none; margin: 0 0 32px 0; padding: 0; }
ul.links li { padding: 8px 0; border-bottom: 1px solid var(--line); font-size: 14px; line-height: 20px; }
ul.links a { color: var(--ink); text-decoration: underline; text-underline-offset: 4px; }

.src-name { font-weight: 600; font-size: 14px; line-height: 20px; margin: 0 0 4px 0; }
.src-text { font-size: 14px; line-height: 20px; color: var(--muted); margin: 0 0 16px 0; }
p.warn { font-size: 14px; line-height: 20px; color: var(--muted); margin: 16px 0 0 0; }

p.note {
  font-size: 14px; line-height: 20px; color: var(--muted);
  margin: 48px 0 0 0; padding-top: 16px; border-top: 1px solid var(--line);
  max-width: 560px;
}
</style>
""",
    unsafe_allow_html=True,
)

EXAMPLES = [
    "explain normalization in dbms",
    "how does binary search work",
    "what is an adjective in english",
    "when is the internal exam",
]


def use_example(text):
    st.session_state["doubt"] = text


def link_list(items):
    """Render [(label, url)] as a plain list. Only https links are allowed."""
    rows = ""
    for label, url in items:
        if url.startswith("https://"):
            rows += (f'<li><a href="{html.escape(url, quote=True)}" target="_blank" '
                     f'rel="noopener noreferrer">{html.escape(label)}</a></li>')
    return f'<ul class="links">{rows}</ul>'


st.markdown('<h1 class="title">Doubt Agent</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="lead">Type any doubt. The agent finds the subject, explains it with '
    "Gemini, and lists places to read more.</p>",
    unsafe_allow_html=True,
)

question = st.text_input("Your doubt", key="doubt", placeholder="For example: explain normalization in dbms")

cols = st.columns(len(EXAMPLES))
for col, ex in zip(cols, EXAMPLES):
    col.button(ex, on_click=use_example, args=(ex,), key=f"ex_{ex}")

if question.strip():
    # Remember answers for this visit, so clicking around never re-asks Gemini.
    cache = st.session_state.setdefault("answers", {})
    cache_key = question.strip().lower()
    if cache_key in cache:
        result = cache[cache_key]
    else:
        with st.spinner("Writing the answer"):
            result = ask(question)
        if result.get("answer_source") != "None":     # never remember failures
            cache[cache_key] = result
    confidence = f"{result['confidence']:.0%}"
    if result.get("topic"):
        confidence += " (keyword match)"
    route = result["route"].split(" (")[0]

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
    left, right = st.columns([5, 3], gap="large")

    with left:
        st.markdown('<h2 class="sec">Answer</h2>', unsafe_allow_html=True)
        with st.container(key="answer"):
            st.markdown(result["answer"])
        if result.get("llm_error") and result.get("answer_source") != "Not applicable":
            st.markdown(
                f'<p class="warn">Live answer failed: {html.escape(result["llm_error"])}'
                f'{" Rate limit reached: wait a minute and ask again." if "429" in result["llm_error"] else ""}</p>',
                unsafe_allow_html=True,
            )

    with right:
        st.markdown('<h2 class="sec">How it was handled</h2>', unsafe_allow_html=True)
        extra_rows = ""
        if result.get("model"):
            extra_rows += ('<div><span class="k">Model</span>'
                           f'<span class="v">{html.escape(result["model"])}</span></div>')
        if result.get("seconds"):
            extra_rows += ('<div><span class="k">Time</span>'
                           f'<span class="v">{result["seconds"]:.1f} s</span></div>')
        st.markdown(
            '<div class="kv">'
            f'<div><span class="k">Subject</span><span class="v">{html.escape(result["subject"])}</span></div>'
            f'<div><span class="k">Confidence</span><span class="v">{html.escape(confidence)}</span></div>'
            f'<div><span class="k">Route</span><span class="v">{html.escape(route)}</span></div>'
            f'<div><span class="k">Answer from</span><span class="v">{html.escape(result.get("answer_source", ""))}</span></div>'
            f"{extra_rows}"
            "</div>",
            unsafe_allow_html=True,
        )
        if result.get("links"):
            st.markdown('<h2 class="sec">Read more</h2>', unsafe_allow_html=True)
            st.markdown(link_list(result["links"]), unsafe_allow_html=True)
        if result.get("sources"):
            st.markdown('<h2 class="sec">Pages the answer used</h2>', unsafe_allow_html=True)
            st.markdown(link_list(result["sources"]), unsafe_allow_html=True)
        if result.get("context"):
            st.markdown('<h2 class="sec">Notes used</h2>', unsafe_allow_html=True)
            for text, src in result["context"]:
                st.markdown(
                    f'<p class="src-name">{html.escape(src)}</p>'
                    f'<p class="src-text">{html.escape(text)}</p>',
                    unsafe_allow_html=True,
                )

st.markdown(
    '<p class="note">This is an AI system and can be wrong. Check important answers '
    "against the linked sources. Exam and admin questions go to faculty.</p>",
    unsafe_allow_html=True,
)

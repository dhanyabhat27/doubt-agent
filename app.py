import html
import streamlit as st
import streamlit.components.v1 as components
from agent import ask

st.set_page_config(page_title="Doubt Agent", layout="centered", initial_sidebar_state="collapsed")

# ---------------------------------------------------------------
# Design tokens. Two palettes, picked by the device setting.
# Spacing is on a 4px grid. Corners: 12px bubbles, 16px composer, round send button.
# Every colour below is used for BOTH text and background, so text can never
# match its background: text uses --text/--muted, surfaces use --bg/--bubble/--composer.
# ---------------------------------------------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500&display=swap');

:root {
  color-scheme: light dark;
  --bg: #EDECE8;
  --composer: #F8F7F4;
  --bubble: #DFDED9;
  --text: #1A1A19;
  --muted: #6B6A66;
  --line: #D3D2CC;
  --faint: #A8A7A1;
  --send-bg: #1A1A19;
  --send-fg: #F8F7F4;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #191918;
    --composer: #262625;
    --bubble: #2C2C2B;
    --text: #ECEBE7;
    --muted: #9A9993;
    --line: #343433;
    --faint: #5C5B57;
    --send-bg: #ECEBE7;
    --send-fg: #191918;
  }
}

/* Backgrounds: every layer Streamlit paints */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stBottom"], [data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] { background: var(--bg) !important; }

/* Text: one colour for everything, muted where we ask for it */
.stApp, .stApp p, .stApp li, .stApp span, .stApp label, .stApp div,
.stApp h1, .stApp h2, .stApp h3, .stApp strong, .stApp em, .stApp summary {
  color: var(--text);
  font-family: 'Public Sans', system-ui, sans-serif;
}
.stApp a { color: var(--text); }
* { transition: none !important; animation: none !important; }

header[data-testid="stHeader"], footer, #MainMenu,
[data-testid="stHeaderActionElements"], [data-testid="stSidebar"],
[data-testid="collapsedControl"], [data-testid="stToolbar"] { display: none !important; }

.block-container { max-width: 720px; padding: 32px 16px 160px 16px; }

/* Empty state */
.hello { text-align: center; padding: 120px 0 32px 0; }
.hello h1 {
  font-family: 'Source Serif 4', Georgia, serif !important;
  font-size: 32px; line-height: 40px; font-weight: 400;
  margin: 16px 0 8px 0; padding: 0; color: var(--text);
}
.stApp .hello p { font-size: 16px; line-height: 24px; color: var(--muted) !important; margin: 0; }

/* Example buttons: one quiet, wrapping row */
.st-key-examples, .st-key-examples [data-testid="stVerticalBlock"] {
  flex-direction: row !important; flex-wrap: wrap; justify-content: center; gap: 8px;
}
.st-key-examples [data-testid="stElementContainer"], .st-key-examples .stElementContainer,
.st-key-examples .stButton { width: auto !important; flex: 0 0 auto; }
.stButton button {
  width: auto; min-height: 32px; padding: 4px 12px;
  font-size: 13px; line-height: 20px;
  background: transparent !important; color: var(--muted) !important;
  border: 1px solid var(--line) !important; border-radius: 10px;
}
.stButton button p { color: inherit !important; font-size: 13px; line-height: 20px; }
.stButton button:hover { color: var(--text) !important; border-color: var(--muted) !important; }

/* Conversation */
.u-row { display: flex; justify-content: flex-end; margin: 24px 0 16px 0; }
.u-bubble {
  background: var(--bubble); border-radius: 12px; padding: 12px 16px;
  max-width: 80%; font-size: 16px; line-height: 24px; overflow-wrap: anywhere;
}
.st-key-answer p, .st-key-answer li { font-size: 16px; line-height: 26px; color: var(--text); }
.stApp p.warn { font-size: 14px; line-height: 20px; color: var(--muted) !important; margin: 8px 0 0 0; }

/* Read more links */
.links-title { font-size: 14px; line-height: 20px; font-weight: 600; margin: 16px 0 8px 0; }
.stApp ul.links { list-style: none; margin: 0 0 8px 0 !important; padding: 0 !important; }
ul.links li { padding: 8px 0; border-bottom: 1px solid var(--line); font-size: 14px; line-height: 20px; }
ul.links a { text-decoration: underline; text-underline-offset: 4px; }

/* How it was handled (collapsed by default) */
details.more { margin: 8px 0 0 0; }
details.more summary {
  cursor: pointer; font-size: 14px; line-height: 20px; color: var(--muted) !important;
  padding: 8px 0; list-style: none;
}
details.more summary::-webkit-details-marker { display: none; }
details.more summary::before { content: "+  "; }
details.more[open] summary::before { content: "–  "; }
details.more summary:focus:not(:focus-visible) { outline: none; }
.kv { border-top: 1px solid var(--line); margin: 0 0 16px 0; }
.kv .row {
  display: flex; justify-content: space-between; gap: 16px;
  padding: 12px 0; border-bottom: 1px solid var(--line); font-size: 14px; line-height: 20px;
}
.kv .k { color: var(--muted) !important; }
.kv .v { text-align: right; font-weight: 500; }
.stApp p.src-name { font-weight: 600; font-size: 14px; line-height: 20px; margin: 8px 0 4px 0; }
.stApp p.src-text { font-size: 14px; line-height: 20px; color: var(--muted) !important; margin: 0 0 16px 0; }

.stApp p.note { font-size: 11px !important; line-height: 16px !important; color: var(--faint) !important; text-align: center; margin: 48px 0 0 0; }

/* Composer: the chat box pinned at the bottom */
[data-testid="stChatInput"] {
  background: var(--composer) !important; border: 1px solid var(--line) !important;
  border-radius: 16px !important; box-shadow: none !important;
}
[data-testid="stChatInput"] > div, [data-testid="stChatInput"] div[data-baseweb] {
  background: transparent !important; border: none !important; border-radius: 16px !important;
}
[data-testid="stChatInput"] textarea {
  background: transparent !important; color: var(--text) !important;
  -webkit-text-fill-color: var(--text) !important;
  font-size: 16px; line-height: 24px; font-family: 'Public Sans', system-ui, sans-serif;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--muted) !important; -webkit-text-fill-color: var(--muted) !important; opacity: 1; }
[data-testid="stChatInputSubmitButton"] {
  background: var(--send-bg) !important; color: var(--send-fg) !important;
  border-radius: 50% !important;
}
[data-testid="stChatInputSubmitButton"] svg { fill: var(--send-fg) !important; color: var(--send-fg) !important; }
[data-testid="stSpinner"], [data-testid="stSpinner"] * { color: var(--muted) !important; }
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

def keep_focus(n):
    """Put the cursor in the chat box on page load and after every answer.
    n changes each turn so the script runs again."""
    components.html(
        """<script>
        (function () {
          var tries = 0;
          var t = setInterval(function () {
            var d = window.parent.document;
            var el = d.querySelector('textarea[data-testid="stChatInputTextArea"]')
                  || d.querySelector('[data-testid="stChatInput"] textarea');
            if (el) { el.focus(); if (d.activeElement === el) { clearInterval(t); } }
            if (++tries > 40) { clearInterval(t); }
          }, 150);
        })();
        </script><!-- turn """ + str(n) + " -->",
        height=0,
    )


def use_example(text):
    st.session_state["pending"] = text


def link_list(items):
    """Render [(label, url)] as a plain list. Only https links are allowed."""
    rows = ""
    for label, url in items:
        if url.startswith("https://"):
            rows += (f'<li><a href="{html.escape(url, quote=True)}" target="_blank" '
                     f'rel="noopener noreferrer">{html.escape(label)}</a></li>')
    return f'<ul class="links">{rows}</ul>'


def details_html(result):
    """The 'How it was handled' block, collapsed until the student opens it."""
    confidence = f"{result['confidence']:.0%}"
    if result.get("topic"):
        confidence += " (keyword match)"
    route = result["route"].split(" (")[0]

    def row(k, v):
        return f'<div class="row"><span class="k">{k}</span><span class="v">{html.escape(str(v))}</span></div>'

    rows = row("Subject", result["subject"]) + row("Confidence", confidence) + row("Route", route)
    rows += row("Answer from", result.get("answer_source", ""))
    if result.get("model"):
        rows += row("Model", result["model"])
    if result.get("seconds"):
        rows += row("Time", f'{result["seconds"]:.1f} s')
    out = f'<details class="more"><summary>How it was handled</summary><div class="kv">{rows}</div>'
    if result.get("sources"):
        out += '<div class="links-title">Pages the answer used</div>' + link_list(result["sources"])
    if result.get("context"):
        out += '<div class="links-title">Notes used</div>'
        for text, src in result["context"]:
            out += (f'<p class="src-name">{html.escape(src)}</p>'
                    f'<p class="src-text">{html.escape(text)}</p>')
    return out + "</details>"


def show_user(question):
    st.markdown(f'<div class="u-row"><div class="u-bubble">{html.escape(question)}</div></div>',
                unsafe_allow_html=True)


def show_answer(result, index):
    with st.container(key=f"answer_{index}"):
        st.markdown(result["answer"])
    if result.get("llm_error") and result.get("answer_source") != "Not applicable":
        extra = " Rate limit reached: wait a minute and ask again." if "429" in result["llm_error"] else ""
        st.markdown(f'<p class="warn">Live answer failed: {html.escape(result["llm_error"])}{extra}</p>',
                    unsafe_allow_html=True)
    if result.get("links"):
        st.markdown('<div class="links-title">Read more</div>' + link_list(result["links"]),
                    unsafe_allow_html=True)
    st.markdown(details_html(result), unsafe_allow_html=True)


# ---------------------------------------------------------------
# Page
# ---------------------------------------------------------------
history = st.session_state.setdefault("history", [])    # [(question, result)]
cache = st.session_state.setdefault("answers", {})      # remembers answers for this visit

typed = st.chat_input("Type your doubt")
question = st.session_state.pop("pending", None) or typed

if not history and not question:
    st.markdown(
        f'<div class="hello"><h1>What is your doubt today?</h1>'
        "<p>Ask about any subject. I find the subject, explain it, and list places to read more.</p></div>",
        unsafe_allow_html=True,
    )
    with st.container(key="examples"):
        for ex in EXAMPLES:
            st.button(ex, on_click=use_example, args=(ex,), key=f"ex_{ex}")

for i, (q, res) in enumerate(history):
    show_user(q)
    show_answer(res, i)

if question and question.strip():
    show_user(question)
    key = question.strip().lower()
    if key in cache:
        result = cache[key]
    else:
        with st.spinner("Writing the answer"):
            result = ask(question)
        if result.get("answer_source") != "None":     # never remember failures
            cache[key] = result
    history.append((question, result))
    st.rerun()

st.markdown(
    '<p class="note">This is an AI system and can be wrong. Check important answers '
    "against the linked sources. Exam and admin questions go to faculty.</p>",
    unsafe_allow_html=True,
)

keep_focus(len(history))

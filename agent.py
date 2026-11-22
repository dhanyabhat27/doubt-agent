"""
Student Doubt Classification Agent  (Version 4.2)
Pipeline: classify (scikit-learn) -> route (LangGraph) -> answer (Gemini + Google Search)
Every answer also comes with recommended learning links. Notes are an offline fallback.
"""
import os
import re
import glob
import time
from typing import TypedDict
from urllib.parse import quote_plus

import pandas as pd
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import make_pipeline
from langgraph.graph import StateGraph, END

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIDENCE_THRESHOLD = 0.30   # below this the subject is treated as "general"

# ---------------------------------------------------------------
# 1. TEXT CLASSIFIER  (technique: text classification)
# ---------------------------------------------------------------
_df = pd.read_csv(os.path.join(BASE, "train_data.csv"))
classifier = make_pipeline(
    TfidfVectorizer(ngram_range=(1, 2), lowercase=True),
    LogisticRegression(max_iter=1000, C=10),
)
classifier.fit(_df["text"], _df["subject"])

# ---------------------------------------------------------------
# 2. CLASS NOTES  (offline fallback only; technique: retrieval)
# ---------------------------------------------------------------
_chunks, _sources = [], []
for path in sorted(glob.glob(os.path.join(BASE, "notes", "*.txt"))):
    with open(path, encoding="utf-8") as f:
        for para in f.read().split("\n\n"):
            if para.strip():
                _chunks.append(para.strip())
                _sources.append(os.path.basename(path))

if _chunks:
    _vectorizer = TfidfVectorizer(stop_words="english").fit(_chunks)
    _matrix = _vectorizer.transform(_chunks)


def retrieve(question, subject=None, k=2):
    """Return the k most relevant note paragraphs as (text, source_file)."""
    if not _chunks:
        return []
    sims = cosine_similarity(_vectorizer.transform([question]), _matrix)[0]
    results = []
    for i in sims.argsort()[::-1]:
        if subject and _sources[i] != f"{subject}.txt":
            continue
        if sims[i] <= 0:
            continue
        results.append((_chunks[i], _sources[i]))
        if len(results) == k:
            break
    return results


# ---------------------------------------------------------------
# 3. LLM CALL: Gemini with Google Search grounding
# ---------------------------------------------------------------
# Model names change often. Set GEMINI_MODEL to force one; the others are tried if it fails.
DEFAULT_MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash"]
_good_model = None   # the model that worked last is tried first


def _setting(name, default=None):
    """Read an option from environment variables first, then from Streamlit secrets
    (.streamlit/secrets.toml on your laptop, or the Secrets box on Streamlit Cloud)."""
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets.get(name, default)
    except Exception:
        return default


def _get_key():
    return _setting("GEMINI_API_KEY")


def _call(model, key, prompt, grounded):
    """One Gemini request. grounded=True turns on Google Search. Returns (text, sources)."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    if grounded:
        body["tools"] = [{"google_search": {}}]
    r = requests.post(url, headers={"x-goog-api-key": key}, json=body, timeout=30)
    r.raise_for_status()
    cand = r.json()["candidates"][0]
    text = "".join(p.get("text", "") for p in cand["content"]["parts"]).strip()
    sources, seen = [], set()
    for chunk in cand.get("groundingMetadata", {}).get("groundingChunks", []):
        web = chunk.get("web") or {}
        uri = web.get("uri")
        if uri and uri not in seen:
            seen.add(uri)
            sources.append((web.get("title") or uri, uri))
    return text, sources


_search_paused_until = 0.0   # after a rate-limit on search, skip search for 2 minutes (faster)


def ask_gemini(prompt):
    """Return (text, sources, error, model).
    The model that worked last time is tried first, so later answers skip the failed names.
    For each model: try with Google Search, then without it (search can have its own limit).
    If search hits a rate limit (429), it is skipped for 2 minutes so answers stay fast.
    A 404 means the model name does not exist, so that model is skipped straight away.
    The error lists every attempt, e.g. 'gemini-3.5-flash (search/plain): 429/429'."""
    global _search_paused_until, _good_model
    key = _get_key()
    if not key:
        return None, [], "No GEMINI_API_KEY is set", ""
    use_search = str(_setting("USE_SEARCH", "1")) != "0"      # USE_SEARCH=0 skips Google Search
    models = [m for m in ([_setting("GEMINI_MODEL")] + DEFAULT_MODELS) if m]
    order = ([_good_model] if _good_model else []) + [m for m in models if m != _good_model]
    errors = []
    for model in order:
        search_ok = use_search and time.time() >= _search_paused_until
        modes = (True, False) if search_ok else (False,)
        status = []
        for grounded in modes:
            try:
                text, sources = _call(model, key, prompt, grounded)
                if text:
                    _good_model = model
                    return text, sources, None, model
                status.append("empty")
            except requests.HTTPError as e:
                code = e.response.status_code
                status.append(str(code))
                if grounded and code == 429:
                    _search_paused_until = time.time() + 120
                if code == 404:
                    break
            except Exception as e:
                status.append(type(e).__name__)
        label = "search/plain" if len(modes) == 2 else "plain"
        errors.append(f"{model} ({label}): {'/'.join(status)}")
    return None, [], "; ".join(errors), ""


# ---------------------------------------------------------------
# 3b. RECOMMENDED LINKS (for every question)
# ---------------------------------------------------------------
EXTERNAL_TOPICS = {
    "english": {
        "keywords": ["english", "grammar", "adjective", "noun", "verb", "adverb", "tense",
                     "vocabulary", "essay", "preposition", "synonym", "antonym", "pronoun"],
        "sites": [("British Council LearnEnglish", "learnenglish.britishcouncil.org"),
                  ("Khan Academy", "khanacademy.org")],
    },
    "maths": {
        "keywords": ["maths", "math", "calculus", "algebra", "matrix", "integration", "derivative",
                     "probability", "statistics", "trigonometry", "geometry", "equation"],
        "sites": [("Khan Academy", "khanacademy.org"), ("NPTEL", "nptel.ac.in")],
    },
    "science": {
        "keywords": ["physics", "chemistry", "biology", "force", "atom", "molecule", "energy",
                     "newton", "organic", "reaction"],
        "sites": [("Khan Academy", "khanacademy.org"), ("NPTEL", "nptel.ac.in")],
    },
    "other programming": {
        "keywords": ["java", "javascript", "html", "css", "react", "c++", "kotlin", "php",
                     "machine", "learning", "ai", "android", "git", "linux"],
        "sites": [("GeeksforGeeks", "geeksforgeeks.org"), ("W3Schools", "w3schools.com")],
    },
}
SITES_BY_SUBJECT = {
    "dbms": [("GeeksforGeeks", "geeksforgeeks.org"), ("W3Schools", "w3schools.com")],
    "os": [("GeeksforGeeks", "geeksforgeeks.org"), ("NPTEL", "nptel.ac.in")],
    "networks": [("GeeksforGeeks", "geeksforgeeks.org"), ("NPTEL", "nptel.ac.in")],
    "dsa": [("GeeksforGeeks", "geeksforgeeks.org"), ("VisuAlgo", "visualgo.net")],
    "python": [("Python documentation", "docs.python.org"), ("W3Schools", "w3schools.com")],
}
GENERAL_SITES = [("Khan Academy", "khanacademy.org"), ("NPTEL", "nptel.ac.in")]
FILLER_WORDS = {"what", "is", "are", "an", "a", "the", "explain", "how", "does", "do", "to",
                "me", "about", "tell", "define", "please", "can", "you", "i", "of", "in", "my"}


def detect_external(question):
    """Return a non-core topic name (english, maths, ...) if the question mentions one."""
    words = set(re.findall(r"[a-z+#]+", question.lower()))
    for topic, info in EXTERNAL_TOPICS.items():
        if words & set(info["keywords"]):
            return topic
    return None


def search_terms(question):
    """'what is an adjective in english' -> 'adjective english'."""
    words = [w for w in re.findall(r"[a-z0-9+#]+", question.lower()) if w not in FILLER_WORDS]
    return " ".join(words) or question


def build_links(question, topic, subject):
    """Links that open results for THIS question on sites that suit the subject."""
    terms = search_terms(question)
    links = [(f"YouTube videos: {terms}",
              f"https://www.youtube.com/results?search_query={quote_plus(terms + ' explained')}")]
    if topic:
        sites = EXTERNAL_TOPICS[topic]["sites"]
    else:
        sites = SITES_BY_SUBJECT.get(subject, GENERAL_SITES)
    for label, domain in sites:
        links.append((f"{label}: pages about '{terms}'",
                      f"https://www.google.com/search?q={quote_plus(terms + ' site:' + domain)}"))
    links.append((f"Wikipedia: {terms}",
                  f"https://en.wikipedia.org/w/index.php?search={quote_plus(terms)}"))
    return links


# ---------------------------------------------------------------
# 4. LANGGRAPH WORKFLOW  (technique: tool routing)
# ---------------------------------------------------------------
class State(TypedDict, total=False):
    question: str
    subject: str
    confidence: float
    topic: str
    route: str
    answer: str
    answer_source: str
    llm_error: str
    sources: list      # [(title, url)] used by Google Search
    context: list      # [(text, file)] class notes, fallback only
    links: list        # [(label, url)] recommended for every question
    model: str         # which Gemini model answered
    seconds: float     # how long the answer took


def classify_node(state):
    topic = detect_external(state["question"])
    if topic:
        return {"subject": topic, "confidence": 1.0, "topic": topic}
    probs = classifier.predict_proba([state["question"]])[0]
    best = probs.argmax()
    confidence = float(probs[best])
    subject = str(classifier.classes_[best])
    if confidence < CONFIDENCE_THRESHOLD:
        subject = "general"
    return {"subject": subject, "confidence": confidence}


def decide(state):
    if state["subject"] == "admin":
        return "human"
    if state["subject"] in ("python", "dsa"):
        return "tutor"
    return "explain"


def _answer(state, prompt, offline_fallback):
    """Ask Gemini; if that fails use class notes; if no notes, say so honestly."""
    started = time.time()
    links = build_links(state["question"], state.get("topic"), state["subject"])
    text, sources, err, model = ask_gemini(prompt)
    seconds = round(time.time() - started, 1)
    if text:
        label = "Gemini with Google Search" if sources else "Gemini (no search used)"
        return {"answer": text, "answer_source": label, "sources": sources,
                "context": [], "links": links, "llm_error": "",
                "model": model, "seconds": seconds}
    ctx = retrieve(state["question"], state["subject"])
    if ctx:
        notes = "\n\n".join(c for c, _ in ctx)
        return {"answer": offline_fallback.format(notes=notes),
                "answer_source": "Class notes (offline fallback)", "sources": [],
                "context": ctx, "links": links, "llm_error": err or "",
                "model": "", "seconds": seconds}
    return {"answer": ("A live explanation is not available right now. "
                       "Use the recommended links to read about this topic."),
            "answer_source": "None", "sources": [], "context": [],
            "links": links, "llm_error": err or "", "model": "", "seconds": seconds}


def explain_node(state):
    prompt = (
        "You are a helpful college tutor. Use Google Search to check reliable sources, "
        "then explain the student's doubt in simple language, in about 120 to 180 words. "
        "Start with a one-line definition, then the key points, and add a tiny example "
        "if it helps. Do not put URLs or a source list in the text. If the question is "
        "unclear, say what you would need to know.\n\n"
        f"DOUBT: {state['question']}"
    )
    out = _answer(state, prompt, "{notes}")
    out["route"] = "Explanation from the web (Gemini + search)"
    return out


def tutor_node(state):
    prompt = (
        "You are a patient programming tutor. Use Google Search to check reliable sources. "
        "Do NOT give the full solution. Give a short explanation of the concept, then two "
        "hints, then one small example. Keep it under 200 words. Do not put URLs or a "
        "source list in the text.\n\n"
        f"DOUBT: {state['question']}"
    )
    fallback = (
        "**Hint 1:** Break the problem into small steps and trace it by hand.\n\n"
        "**Hint 2:** Read the error message from the bottom up. It names the line and the cause.\n\n"
        "**From your notes:**\n\n{notes}"
    )
    out = _answer(state, prompt, fallback)
    out["route"] = "Tutor workflow (hints)"
    return out


def human_node(state):
    return {
        "route": "Escalated to faculty (human in the loop)",
        "answer": ("This looks like an exam or admin question. The web cannot answer it. "
                   "Please ask your faculty or class coordinator."),
        "answer_source": "Not applicable",
        "sources": [], "context": [], "links": [], "llm_error": "",
        "model": "", "seconds": 0.0,
    }


_graph = StateGraph(State)
_graph.add_node("classify", classify_node)
_graph.add_node("explain", explain_node)
_graph.add_node("tutor", tutor_node)
_graph.add_node("human", human_node)
_graph.set_entry_point("classify")
_graph.add_conditional_edges(
    "classify", decide, {"explain": "explain", "tutor": "tutor", "human": "human"}
)
for _n in ("explain", "tutor", "human"):
    _graph.add_edge(_n, END)
agent = _graph.compile()


def ask(question):
    """Convenience wrapper used by the app and the tests."""
    return agent.invoke({"question": question})

"""Run with:  python test_agent.py
Prints a table you can paste into the Testing section of your report.
Routing is tested offline. Set GEMINI_API_KEY first to also see the live answer source."""
from agent import ask

# (type, question, expected subject, expected route keyword)
CASES = [
    ("Normal", "explain normalization in dbms", "dbms", "Explanation"),
    ("Normal", "what is a deadlock in operating system", "os", "Explanation"),
    ("Normal", "difference between tcp and udp", "networks", "Explanation"),
    ("Normal", "how does binary search work", "dsa", "Tutor"),
    ("Normal", "why am i getting a typeerror in my code", "python", "Tutor"),
    ("Normal", "when is the internal exam", "admin", "Escalated"),
    ("Edge", "what is a join", "dbms", "Explanation"),
    ("Edge", "explain round robin", "os", "Explanation"),
    ("Any topic", "what is an adjective in english", "english", "Explanation"),
    ("Any topic", "how to solve a quadratic equation in maths", "maths", "Explanation"),
    ("Failure", "asdfgh qwerty zxcv", "general", "Explanation"),
    ("Any topic", "what is the weather today", "general", "Explanation"),
]

passed = 0
print(f"{'Type':10} {'Question':42} {'Subject':9} {'Conf':>5}  {'Route':22} {'Links':>5} {'Answer from':30} Result")
print("-" * 140)
for kind, q, exp_subject, exp_route in CASES:
    r = ask(q)
    route_ok = exp_route in r["route"]
    subject_ok = r["subject"] == exp_subject
    # every question except faculty escalations must come with recommended links
    links_ok = bool(r["links"]) or "Escalated" in r["route"]
    ok = route_ok and subject_ok and links_ok
    passed += ok
    print(f"{kind:10} {q[:42]:42} {r['subject']:9} {r['confidence']:5.0%}  "
          f"{r['route'][:22]:22} {len(r['links']):5} {r['answer_source'][:30]:30} {'PASS' if ok else 'FAIL'}")
print(f"\n{passed}/{len(CASES)} passed")

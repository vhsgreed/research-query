#!/usr/bin/env python3
"""research-query.py — query the research corpus.

Usage:
  research-query.py "query" [--top N]            # FTS5 matches + snippets
  research-query.py "query" --ask                # + LLM answer over top chunks
  research-query.py --reindex                    # refresh index first
Frugal: --ask costs ~$0.001 (flash-latest). Deny-trivial policy: only useful
for mission-relevant lookups, not googling.
"""
import argparse, json, os, re, sqlite3, sys, urllib.request

DB = os.environ.get("RESEARCH_DB", os.path.expanduser("~/research/research.db"))
KEY_FILE = os.path.expanduser("~/.config/openrouter/key")
ASK_MODEL = "~deepseek/deepseek-v4-flash-latest"


def ask_llm(question, chunks):
    key = open(KEY_FILE).read().strip()
    ctx = "\n\n".join(f"[{c['kind']} {c['date']}] {c['title']}\n{c['snippet']}" for c in chunks)
    sys_p = ("You answer questions using ONLY the provided research-corpus excerpts. "
             "Cite the source kind+date for each claim. If the corpus doesn't answer, "
             "say so plainly. No fabrication.")
    body = json.dumps({"model": ASK_MODEL, "messages": [
        {"role": "system", "content": sys_p},
        {"role": "user", "content": f"QUESTION: {question}\n\nCORPUS EXCERPTS:\n{ctx[:24000]}"}],
        "max_tokens": 600, "temperature": 0.2}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read())
    return d["choices"][0]["message"].get("content") or "(empty)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", help="search query (FTS5 syntax)")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--ask", action="store_true", help="also produce an LLM answer")
    ap.add_argument("--reindex", action="store_true")
    args = ap.parse_args()
    if args.reindex:
        import subprocess
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "research-index.py")])
    if not args.query:
        con = sqlite3.connect(DB)
        n = con.execute("SELECT count(*) FROM research").fetchone()[0]
        print(f"corpus: {n} docs | try: research-query.py 'ox-alpha' --ask")
        return
    con = sqlite3.connect(DB)
    # FTS5: hyphen/minus is an operator — quote tokens with special chars
    toks = [t for t in re.split(r"\s+", args.query.strip()) if t]
    STOP = {"what", "with", "the", "a", "an", "and", "or", "for", "did", "do", "how",
            "when", "where", "why", "is", "are", "was", "were", "happened", "happen",
            "to", "of", "in", "on", "about", "from", "by", "at"}
    if args.ask:
        toks = [t for t in toks if t.lower() not in STOP]
        fts = " OR ".join(f'"{t}"' if re.search(r"[^A-Za-z0-9_]", t) else t for t in toks)
    else:
        fts = " ".join(f'"{t}"' if re.search(r"[^A-Za-z0-9_]", t) else t for t in toks)
    rows = con.execute(
        "SELECT kind, date, title, snippet(research, 4, '<b>', '</b>', '…', 12), path "
        "FROM research WHERE research MATCH ? ORDER BY rank LIMIT ?",
        (fts, args.top)).fetchall()
    if not rows:
        print(f"no matches for {args.query!r}")
        return
    chunks = []
    for i, (kind, date, title, snip, path) in enumerate(rows, 1):
        print(f"{i}. [{kind} {date}] {title}  ({path})")
        print(f"   {snip}\n")
        chunks.append({"kind": kind, "date": date, "title": title, "snippet": snip})
    if args.ask:
        print("--- answer ---")
        print(ask_llm(args.query, chunks))


if __name__ == "__main__":
    main()

# research-query

Query a sqlite FTS5 research corpus — plain search or LLM-answered.

```
python3 research-query.py "scaling laws"              # FTS5 matches + snippets
python3 research-query.py "scaling laws" --top 5      # top N chunks
python3 research-query.py "scaling laws" --ask        # + LLM answer over top chunks
```

## Why

The companion to [research-index](https://github.com/karlsune/research-index):
once your notes are in a sqlite FTS5 corpus, this gives you fast local
search plus an optional LLM synthesis pass over the best-matching chunks.

## Config (env vars)

- `RESEARCH_DB` — path to the corpus database (default `~/research/research.db`)
- `OR_KEY_FILE` — OpenRouter API key file for `--ask` mode
  (default `~/.config/openrouter/key`)

## Requirements

- Python 3.8+ (stdlib only for search mode)
- `--ask` mode needs an OpenRouter API key

## Output

- Search mode: ranked matches with snippets
- `--ask` mode: the LLM's answer, grounded in your own notes

# Engineering notes: bugs found and fixed

This project was reviewed and refactored from its first version. What was wrong and what changed:

| # | Problem in v0 | Impact | Fix |
|---|---|---|---|
| 1 | Setup script shared the results sheet with `anyone` as `writer` | Passport data publicly editable | Sheet is private; sharing code removed |
| 2 | Flask API bound to `0.0.0.0` with no authentication | Anyone on the network could submit files | Binds to `127.0.0.1` by default; `X-API-Key` check with constant-time compare |
| 3 | Passport text and the Gemini key were passed as **command-line arguments** to subprocesses | Visible in the process list (`ps`) | Modules called directly; key read from the environment only |
| 4 | Temp passport file deleted only on the happy path | Scans left on disk after any crash | `TemporaryDirectory` context manager |
| 5 | Regex `Passport(?: No\|Number)?:?\s*([A-Z0-9]+)` | `Passport Number: AB123` returned `Number`; `Passport of ...` returned `of` | Requires a label and 6-9 alphanumerics; regression tests added |
| 6 | `is_valid` accepted up to 2 missing required fields and trusted the LLM's own value | Incomplete records marked valid | Computed in code: all fields present and not expired |
| 7 | Free-text OCR only | LLM/regex can silently misread a digit | MRZ parser with ICAO check digits + OCR repair step |
| 8 | Gemini failure aborted the whole request | Document lost on a transient API error | Falls back to regex and records a warning |
| 9 | `gemini-1.5-flash` hard-coded with the deprecated `google-generativeai` SDK | Model/SDK retirement breaks extraction | Model configurable via `GEMINI_MODEL`; `google-genai` SDK |
| 10 | Paths hard-coded to `~/visa-processor`; README told users to run `api_server.py` from the wrong folder | Did not run for anyone else | Package layout, config from environment |
| 11 | README was a PDF (`README.md.pdf`) and referenced a missing `sheet_config.example.json` | GitHub shows no README | Real `README.md` + example file |
| 12 | `create_sheet_from_n8n.py` decrypted n8n's credential database; `fix_n8n_workflow.py` edited n8n's SQLite DB directly | Fragile, risky, and the decryption format very likely does not match n8n's | Removed; replaced by importable `n8n/workflow.json` and a standard OAuth script |
| 13 | `token.pickle` (pickled credentials) | Unsafe to load from untrusted files | JSON token via `Credentials.to_json()` |
| 14 | No tests, no dependency list, no CI, no upload limits | Impossible to trust or reproduce | pytest suite, `requirements.txt`, Dockerfile, GitHub Actions, size/type limits |

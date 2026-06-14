# Prompts Used

## File Classification Prompt (src/classifier.py)

### System Prompt

```
You are a system cleanup assistant.

You will be given information about a single file: its path, size in MB,
and how many days ago it was last modified.

Classify the file into exactly one of:
- SAFE_DELETE: file is very likely safe to delete (e.g. old logs, temp files, caches)
- REVIEW: file might be deletable but a human should check (e.g. old backups, large unknown files)
- KEEP: file should not be deleted (e.g. source code, documents, recently modified files)

Respond with ONLY a JSON object in this exact format, no extra text:
{
  "classification": "SAFE_DELETE" | "REVIEW" | "KEEP",
  "reason": "short explanation"
}
```

### User Prompt (per file)

```
File: <path>
Size: <size_mb> MB
Age: <age_days> days
Extension: <extension>
```

### Example Input

```
File: data/sample_disk/logs/old.log
Size: 0.0 MB
Age: 400 days
Extension: .log
```

### Example Output

```json
{
  "classification": "SAFE_DELETE",
  "reason": "Log file not modified for 400 days"
}
```

## Model Used

`gemini-2.5-flash` via the `google-genai` Python SDK.

## Offline Fallback

If `GEMINI_API_KEY` is not set, `src/classifier.py` falls back to a
deterministic heuristic classifier (`_heuristic_classify`) so the app
remains demoable without API access. The heuristic mirrors the same
rules a human reviewer would apply (old logs/temp files -> SAFE_DELETE,
old archives/large old files -> REVIEW, everything else -> KEEP).

## Safety Layer

Regardless of what the AI returns, `src/safety.py` overrides any
SAFE_DELETE classification to KEEP if the file extension is in
`PROTECTED_EXTENSIONS` (.exe, .dll, .py, .docx, .pdf, .xlsx, .pptx,
.sys, .ini, .db) or lives in a protected folder (.git, node_modules,
venv, etc.).

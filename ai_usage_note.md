# AI Usage Note


- Scaffold the overall project architecture and folder structure
- Generate the disk scanner, AI classifier, safety layer, deletion tool,
  report generator, Streamlit UI, and optional Discord bot modules
- Write the sample dataset and basic unit tests
- Write this documentation (prompts.md, README.md, ai_usage_note.md)

## AI Capability in the Project Itself

The application's core AI capability is the **file classifier**
(`src/classifier.py`), which sends file metadata (path, size, age,
extension) to Google's Gemini API (`gemini-2.5-flash`) and receives a
structured JSON classification (`SAFE_DELETE`, `REVIEW`, or `KEEP`)
with a short natural-language reason.

This satisfies the "AI-based decision making" requirement of the
challenge: the LLM reasons over file metadata and produces a
recommendation, which is then subject to:

1. A rule-based safety layer that can override unsafe recommendations
2. A human approval gate (Streamlit buttons, or optionally a Discord
   bot) before any file is moved

## Model & Provider

- Provider: Google Gemini (free tier)
- Model: `gemini-2.5-flash`
- SDK: `google-genai` Python package

## Fallback Behavior

If no `GEMINI_API_KEY` is configured, the app uses a deterministic,
rule-based heuristic classifier so it remains fully functional and
demoable offline.

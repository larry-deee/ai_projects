# Claude-Code Master Task — End-to-end doc consolidation, safe cleanup, verify, and PR

## Context
- Repo: sf-model-api (existing local prototype).
- Environment: local laptop, single user. No production hardening required.
- Clients: n8n v1.105.4 (OpenAI node, non-stream UI), Claude Code (full tool-calling & streaming).
- Models via Salesforce Models API; respect 429 backoff semantics.
- You (Claude-Code, claude-4-sonnet) have MCP tools (filesystem, terminal, git, editor) and sub-agents from lst97/claude-code-sub-agents.

## Objectives
1) Consolidate docs to a minimal, clear set for the local prototype; archive everything non-critical (no deletions).
2) Keep all critical code and dependencies intact (no broken imports, no broken doc links).
3) Verify runtime still works (uvicorn), run curl smoke tests; confirm headers/stream behaviour.
4) Commit, push a branch, and open a clean PR with verification steps.

## Hard Safety Rules (must follow)
- Never delete first; move to `archive/` (or `archive/prod-hardening/`) unless explicitly confirmed by me.
- Build and use two maps before moving anything:
  a) **Import graph** for Python (`**/*.py`) to find critical files and entrypoints.
  b) **Doc link graph** for Markdown links to local files.
- Produce a **Proposed Actions Table** (file → action → reason → inbound references count).
- Abort any move/remove when you detect references that you cannot auto-update safely.
- After changes, re-run both graphs; fail if new broken imports/links appear.
- Keep a rollback tag (already created by the shell: `pre-consolidation-<timestamp>`).

## Scope of change
**Keep & highlight**
- `README.md` (single source of truth)
- Key code: `async_endpoint_server.py`, `streaming_architecture.py`, `salesforce_models_client.py`,
  `unified_response_formatter.py`, `tool_handler.py`, `tool_schemas.py`, `connection_pool.py`, `requirements.txt`, start scripts.
- Tests/scripts that prove local behaviour.

**Create / consolidate**
- `docs/ARCHITECTURE.md` (trimmed overview)
- `docs/COMPATIBILITY.md` (n8n behaviour; Claude Code tool-calling & SSE notes)
- `docs/TESTING.md` (curl commands + expected headers)
- `docs/reports/` for keepworthy QA/validation summaries

**Archive (not delete)**
- Production/security hardening docs (e.g., PRODUCTION_SECURITY_CHECKLIST.md, SECURITY_AUDIT_REPORT.md, SECURITY_REMEDIATION_GUIDE.md) to `archive/prod-hardening/`
- Debug scratchpads/duplicates to `archive/` (only if no code/docs depend on them)

## Runtime & behaviour (must remain true)
- Local start:
  ```bash
  uvicorn async_endpoint_server:app --host 127.0.0.1 --port 8000 --loop uvloop --http h11
When tools are present: default non-stream; set header x-stream-downgraded: true.

Non-stream JSON responses include header x-proxy-latency-ms.

Streaming uses SSE heartbeats (:ka) ~every 15s (OpenAI-style and Anthropic-style streams).

Respect Salesforce Models API 429 behaviour: short exponential backoff, then clean OpenAI-style error envelope.

Acceptance Criteria
No broken Python imports after consolidation.

No broken README/docs links.

Curl tests pass:

Non-stream + tools → single tool_calls, headers include x-stream-downgraded: true and x-proxy-latency-ms.

Stream smoke → text/event-stream and periodic :ka if held open.

PR contains summary, why safe (graphs re-verified), how to run, and how to verify.

Plan (sub-agents)
Spec-Agent: Inventory files; outline exact moves and edits.

Dep-Map-Agent: Build import graph (Python) + link graph (Markdown). Output CRITICAL FILES LIST and DOCS LINK TABLE.

Implementer-Agent: Create docs/, docs/reports/, archive/, archive/prod-hardening/. Perform git mv according to the plan. Update README and any links. Do not delete files.

QA-Agent:

Run: uvicorn async_endpoint_server:app --host 127.0.0.1 --port 8000 --loop uvloop --http h11

Curl tests:

Non-stream + tools:
curl -i -sS -X POST http://127.0.0.1:8000/v1/chat/completions
-H "Content-Type: application/json"
-d '{"model":"claude-4-sonnet","messages":[{"role":"user","content":"What time is it in Melbourne?"}],
"tools":[{"type":"function","function":{"name":"get_time","parameters":{"type":"object","properties":{}}}}]}'

Expect: single tool_calls; headers x-stream-downgraded:true, x-proxy-latency-ms present
Stream smoke:
curl -N -sS -X POST http://127.0.0.1:8000/v1/chat/completions
-H "Content-Type: application/json"
-d '{"model":"claude-4-sonnet","messages":[{"role":"user","content":"Explain SSE heartbeats briefly."}],"stream":true}'

Expect: text/event-stream with periodic ':ka' if kept open
Docs-Agent: Finalise docs/ARCHITECTURE.md, docs/COMPATIBILITY.md, docs/TESTING.md. Ensure README links are correct and minimal.

Verifier-Agent: Re-run graphs; ensure zero broken imports/links. Prepare a summary.

GitOps-Agent:

Small commits:

docs: consolidate local prototype docs; add architecture/compat/testing

docs: update README (local quick start, behaviour, tests)

chore: archive prod-hardening docs (no functional changes)

Push branch and open PR titled: Local Prototype Consolidation (docs + behaviour notes)

PR body must include: summary; why safe (no deletions; graphs re-verified); how to run; how to verify; rollback note (use tag pre-consolidation-... or revert the merge).

Abort / rollback
If any code import is unresolved after moves → abort and restore from pre-consolidation-<timestamp> tag.

If any doc link is broken after auto-update → abort and request my guidance.

Do not permanently delete without my explicit approval.

Begin
Execute this plan now. Ask me only if you detect a risky move you cannot auto-fix safely.

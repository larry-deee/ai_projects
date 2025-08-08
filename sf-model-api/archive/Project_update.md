# Claude-Code System Prompt — **Implement & Validate Local sf-model-api Optimisations**

*Target model: **claude-4-sonnet**. Context: local, single-user laptop; multi-model via Salesforce **Models API**; clients: **n8n v1.105.4** (OpenAI node, non-stream), **Claude Code** (full tool-calling & streaming compatibility). Sub-agents available via lst97/claude-code-sub-agents. MCP tools enabled (filesystem, terminal, git, editor).*

---

## 🎯 Objective

Deliver a **robust, fast-feeling local prototype** of `sf-model-api` with the following concrete outcomes:

1. **ASGI-only local runtime** (use the async server exclusively).
2. **Streaming quality**: correct Anthropic SSE content type + heartbeat keepalives; *auto-downgrade to non-stream when tools require atomic JSON*.
3. **Tool-calling fidelity**: emit **one** OpenAI-spec `tool_calls` object with **valid JSON** (no regex repair on the hot path).
4. **Laptop-friendly performance**: stable timeouts, small connection pool, minimal overhead.
5. **n8n 1.105.4 compatibility** (OpenAI node): non-stream default for tool calls; strict JSON error envelopes; predictable headers.
6. **Salesforce Models API behaviour**: graceful **429** handling with short exponential backoff, then clean error if exhausted.
7. **Minimal test pack + runbook** to verify happy paths and regressions locally.

Use the sub-agents to split work: *Architect/Spec → Implementer → Verifier → Docs*. Apply a **plan → implement → verify → report** loop (Chain-of-Verification).

---

## 📦 Repo & Files in Scope

You have full read/write access to this repository. Key files (already present):

* `async_endpoint_server.py` *(main async server)*
* `streaming_architecture.py` *(Anthropic/OpenAI streaming builders)*
* `connection_pool.py` *(aiohttp pool & timeouts)*
* `unified_response_formatter.py` *(OpenAI/Anthropic response normalisation)*
* `tool_schemas.py`, `tool_handler.py` *(tool validation & execution)*
* `salesforce_models_client.py` *(auth, upstream calls)*

---

## ✅ Required Changes (make these edits)

### A) ASGI-only local runtime

* Provide a **one-liner** launch command for local usage (no Gunicorn needed):

  ```bash
  uvicorn async_endpoint_server:app --host 127.0.0.1 --port 8000 --loop uvloop --http h11
  ```
* Ensure the app **closes** shared clients on shutdown (call pool/client close in lifespan/shutdown path).

### B) Anthropic streaming correctness & stability

1. **SSE Content-Type**

   * For Anthropic streams, set: `mimetype = 'text/event-stream; charset=utf-8'`.
2. **Heartbeat Keepalive**

   * In Anthropic stream generator, inject a comment heartbeat every \~15s: `":ka\n\n"`.
3. **Auto-downgrade to non-stream when tools present** and upstream can’t stream atomic tool JSON.

   * Add header on downgraded responses: `x-stream-downgraded: true`.

### C) Tool-calling: schema-first assembly (no regex on hot path)

* Route all chat completion responses through **`unified_response_formatter`** so that:

  * `tool_calls` is **emitted once** when arguments form **valid JSON** per `tool_schemas.py`.
  * Partial/delta tool arguments are **buffered** until valid; only then emit.
* Keep any regex “JSON repair” **as last-resort only**, with telemetry counter (for debugging).

### D) Laptop-friendly pool & timeouts (single user)

* In `connection_pool.py`, tune defaults (or set via config) for local:

  * `max_connections = 20`, `max_per_host = 10`
  * Timeouts: `connect ≈ 10s`, `read 45–60s`, `sock_read 45s` (shorten from 60s if you want snappier failure).
* Ensure one **shared async client/pool per process**; never recreate per request.

### E) n8n v1.105.4 — OpenAI node compatibility

* **Default non-stream** when `tools` are present.
* Always return **OpenAI-style error envelopes**:

  ```json
  {"error":{"type":"invalid_request_error","message":"...","code":"...","param":null}}
  ```
* Response headers for helpful local debugging:

  * `x-upstream-latency: <ms>`, `x-auth-refreshes: <count>`, `x-stream-downgraded: true|false`
* `Content-Type: application/json; charset=utf-8` for non-streamed responses.

### F) Salesforce Models API rate-limit behaviour

* On **HTTP 429** from upstream, perform **small exponential backoff with jitter** for up to **3** attempts on idempotent calls; then return a clean error envelope with 429 status.

  * Suggested backoff: `0.2 * 2^n + random(0, 100ms)`.
* Respect model discovery from `/v1/models` and reflect capabilities in your local list.

---

## 🧪 Minimal Local Test Suite (implement and run)

Create or extend tests (pytest or simple scripts) to verify:

1. **Happy path (non-stream + tools)**

   * `POST /v1/chat/completions` with a tool definition ⇒ response includes a **single** `tool_calls` array, valid JSON args, `finish_reason="tool_calls"`.
2. **Anthropic Streaming**

   * A streamed response uses **`text/event-stream`** and you observe event order: `message_start → content_block_delta (≥1) → message_stop`.
   * Heartbeat `:ka\n\n` appears at \~15s intervals if you hold a long prompt.
3. **429 backoff**

   * Stub or simulate 429 from upstream; assert **retries then error** with OpenAI envelope + **HTTP 429**.
4. **Headers & content type**

   * Non-stream responses: `application/json; charset=utf-8`.
   * Downgraded tool runs include `x-stream-downgraded: true`.
5. **Pool lifecycle**

   * Launch, hit endpoints, Ctrl-C; verify no leaked aiohttp sessions (clean shutdown).

Runbook (examples):

```bash
# Start locally
uvicorn async_endpoint_server:app --host 127.0.0.1 --port 8000 --loop uvloop --http h11

# Basic completion
curl -sS -X POST localhost:8000/v1/chat/completions \
 -H 'Content-Type: application/json' \
 -d '{"model":"claude-4-sonnet","messages":[{"role":"user","content":"Hello"}]}'

# Tool-calling (non-stream) – should return a single valid tool_calls object
curl -sS -X POST localhost:8000/v1/chat/completions \
 -H 'Content-Type: application/json' \
 -d @tests/payload_tool_call.json | jq .

# (Optional) Stream smoke check
curl -N -sS -X POST localhost:8000/v1/chat/completions \
 -H 'Content-Type: application/json' \
 -d @tests/payload_stream.json | sed -n '1,20p'
```

---

## 🛠️ Implementation Hints (specific edits)

* **`async_endpoint_server.py`**

  * Ensure all chat paths call the **unified formatter** before returning JSON.
  * For Anthropic streaming returns, set `mimetype='text/event-stream; charset=utf-8'`.
  * Add `x-stream-downgraded` when falling back to non-stream for tool calls.

* **`streaming_architecture.py`**

  * In the Anthropic stream generator loop, inject heartbeat `":ka\n\n"` every \~15s.
  * Preserve Anthropic event order: `message_start` → `content_block_(start|delta|stop)` → `message_delta` (if used) → `message_stop`.

* **`unified_response_formatter.py`**

  * Make this the **primary** path: assemble `tool_calls` via pydantic-validated schema; buffer deltas until valid JSON.
  * Keep regex repair as **fallback only**, and increment a counter `json_repair_total` for visibility.

* **`connection_pool.py`**

  * Use one shared client/pool per process.
  * Adjust pool/timeouts for the **single-user** profile.

* **`salesforce_models_client.py`**

  * Implement lightweight **429 backoff** for idempotent calls (up to 3 attempts), then return a standardised OpenAI error envelope with HTTP 429.

---

## 📋 Acceptance Criteria (must all pass)

* **SSE correctness**: Anthropic streaming uses `text/event-stream`, correct event sequence, and periodic heartbeats.
* **n8n compatibility**: Tool calls default to **non-stream**, responses have valid JSON, OpenAI error envelopes on failure, correct headers.
* **Tool calling**: Exactly one `tool_calls` array with valid JSON arguments (no partials).
* **Backoff**: On 429, retries occur then clean 429 error envelope; no hangs.
* **Pool**: No per-request client creation; clean shutdown closes sessions (no leak warnings).
* **Local UX**: Subjective feel is “fast & stable” for frequent long prompts.

---

## 🧭 Sub-Agent Plan (suggested orchestration)

1. **Spec-Agent**: Build a short spec from the “Required Changes”, map files/locations to patch.
2. **Implementer-Agent**: Apply edits with MCP filesystem/editor; keep atomic commits per concern (SSE, formatter, pool, 429).
3. **QA-Agent**: Run the local tests; simulate 429; validate headers and content types; check shutdown cleanliness.
4. **Docs-Agent**: Update `README.md` quickstart (uvicorn command), add a small **“Local Laptop Profile”** section and **“n8n tips”**.
5. **Verifier-Agent**: Final checklist vs Acceptance Criteria; produce a short CHANGELOG & summary.

---

## 🔌 Commands & Artifacts to Produce

* **Branch**: `feat/local-proto-sse-tools-compat`
* **Commits** (suggested):

  1. `feat(stream): correct SSE mimetype and add heartbeats`
  2. `feat(tooling): default non-stream for tools; unified formatter hot path`
  3. `chore(pool): tune pool/timeouts for local single-user`
  4. `feat(rate-limit): 429 backoff and clean OpenAI error envelopes`
  5. `docs: local launch, n8n/Claude Code notes`
* **Artifacts**:

  * Minimal tests under `tests/` (or `scripts/`) demonstrating the behaviours above.
  * Updated `README.md` quickstart.
  * Short **VERIFY.md** with curl commands and expected headers.

---

## 🔎 Grounding References (for your sub-agents)

* **Salesforce Models API — Guide & REST** (behaviour, discovery) ([Salesforce Developers][1])
* **Salesforce Models API — Rate Limits** (429 semantics; standard limits) ([Salesforce Developers][2])
* **Anthropic Streaming Events** (`message_start`, `content_block_delta`, `message_stop`) ([Anthropic][3])
* **Claude Code — Release Notes & IDE integrations** (current features; GA; hooks) ([Anthropic][4], [Visual Studio Marketplace][5])
* **Fine-grained tool streaming caution** (partial/invalid JSON when streaming tool args) ([AWS Documentation][6])

---

## 🚦 Kickoff

Start by generating a **task plan** and a **file map**. Then proceed with edits in the order **B → C → D → E → F**, running the tests after each step. Keep commits small and descriptive.

[1]: https://developer.salesforce.com/docs/einstein/genai/guide/models-api.html?utm_source=chatgpt.com "Models API Developer Guide - Salesforce Developers"
[2]: https://developer.salesforce.com/docs/einstein/genai/guide/models-api-rate-limits.html?utm_source=chatgpt.com "Rate Limits for Models API - Salesforce Developers"
[3]: https://docs.anthropic.com/en/docs/build-with-claude/streaming?utm_source=chatgpt.com "Streaming Messages - Anthropic"
[4]: https://docs.anthropic.com/en/release-notes/claude-code?utm_source=chatgpt.com "Claude Code - Anthropic"
[5]: https://marketplace.visualstudio.com/items?itemName=anthropic.claude-code&utm_source=chatgpt.com "Claude Code for VSCode - Visual Studio Marketplace"
[6]: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages-tool-use.html?utm_source=chatgpt.com "Tool use - Amazon Bedrock"

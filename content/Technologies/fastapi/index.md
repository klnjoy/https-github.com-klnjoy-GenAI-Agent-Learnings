---
icon: material/lightning-bolt
---

# FastAPI

FastAPI is a modern, high-performance Python web framework for building APIs. It
uses **type hints** for automatic validation and docs, is **async-first** (built
on Starlette + Pydantic), and is a common choice for **serving GenAI/LLM
endpoints**.

## Why FastAPI

- **Fast** — on par with Node/Go for I/O-bound work, thanks to ASGI/async.
- **Type-driven** — Pydantic models validate requests/responses automatically.
- **Auto docs** — interactive Swagger UI at `/docs` and ReDoc at `/redoc`, free.
- **Editor support** — type hints give autocomplete and catch errors early.

## A minimal API

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Demo")

class AskRequest(BaseModel):
    question: str
    area: str = "all"

class AskResponse(BaseModel):
    answer: str
    citations: list[str] = []

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    # ... call your logic ...
    return AskResponse(answer=f"You asked about {req.area}: {req.question}")
```

Run it: `uvicorn main:app --reload` → open `http://127.0.0.1:8000/docs`.

## Request lifecycle

```mermaid
flowchart LR
    C[Client] --> U[Uvicorn ASGI server]
    U --> MW[Middleware]
    MW --> DEP[Dependencies - injected]
    DEP --> V[Pydantic validation]
    V --> H[Path operation function]
    H --> R[Response model serialize]
    R --> C
```

## Core concepts

| Concept | What it does |
|---------|--------------|
| **Path operations** | `@app.get/post/...` decorators map routes to functions |
| **Pydantic models** | Typed request/response schemas + validation |
| **Path & query params** | Declared as function args with type hints |
| **Dependencies (`Depends`)** | Reusable injected logic: auth, DB sessions, config |
| **`async def`** | Non-blocking handlers for I/O (DB, HTTP, LLM calls) |
| **Background tasks** | Fire-and-forget work after responding |
| **Routers** | Split endpoints across modules (`APIRouter`) |

## async vs sync

Use `async def` when the handler does **I/O** (calling an LLM, DB, or HTTP
service) with an async client — it frees the event loop to serve other requests.
Use plain `def` for CPU-bound or blocking-library code (FastAPI runs it in a
threadpool so it won't block the loop).

## Serving an LLM / RAG endpoint

FastAPI is a natural front door for a GenAI service — the same role Lambda +
Chainlit play in the course's SQL Assistant project:

```python
@app.post("/chat")
async def chat(req: AskRequest):
    # 1. retrieve context from a vector store (RAG)
    # 2. build the prompt
    # 3. await the LLM call (async client)
    # 4. return the grounded answer + citations
    ...
```

Good practices: stream responses (`StreamingResponse`) for token-by-token UX,
set timeouts on model calls, validate/limit input size, and add rate limiting.

## Validation, errors, docs

- **Validation** — invalid bodies auto-return `422` with details; no manual checks.
- **Errors** — raise `HTTPException(status_code=..., detail=...)`.
- **Docs** — `/docs` (Swagger) and `/redoc` are generated from your models.
- **Settings** — use `pydantic-settings` / env vars for config and secrets.

## Deployment

- **Uvicorn** (ASGI server), often behind **Gunicorn** with uvicorn workers.
- Containerize; put **Nginx**/ALB in front for TLS and load balancing.
- On AWS: run on ECS/Fargate, or wrap with **Mangum** to run on Lambda + API
  Gateway.

## Interview questions

??? question "Why FastAPI over Flask?"
    Async-first (ASGI) for high I/O concurrency, automatic request/response
    validation via Pydantic type hints, and auto-generated interactive docs.
    Flask is sync-first (WSGI) and needs extensions for much of that.

??? question "When do you use async def vs def in a path operation?"
    `async def` for non-blocking I/O with async clients (DB, HTTP, LLM). Plain
    `def` for blocking/CPU-bound code — FastAPI runs it in a threadpool so it
    doesn't block the event loop.

??? question "What are dependencies (Depends) used for?"
    Reusable injected logic — auth, DB sessions, shared config, pagination —
    declared once and injected into any endpoint, improving testability and reuse.

??? question "How does FastAPI validate input?"
    You declare Pydantic models / typed params; FastAPI validates automatically
    and returns a structured 422 on failure — no manual parsing.

??? question "How would you serve an LLM/RAG app with FastAPI?"
    A `/chat` endpoint that retrieves context from a vector store, builds a
    grounded prompt, awaits an async LLM call, and returns the answer with
    citations — optionally streaming tokens via StreamingResponse.

## Related course modules

- **[MODULE3-PYTHON](../../Course-Modules/module3-python.md)** — Python and the
  Lambda + API project (FastAPI plays the same API role).
- **[MODULE4-PROMPT-ENGINEERING](../../Course-Modules/module4-prompt-engineering.md)**
  — the SQL Assistant serving pattern.

---

## Interview deep dive

### 60-second talking points

- **"Type hints do the work."** Pydantic validates requests/responses and
  generates OpenAPI docs automatically — less boilerplate, fewer bugs.
- **"Async-first for I/O concurrency."** Built on ASGI, so one process serves
  many concurrent I/O-bound requests (DB, HTTP, LLM calls).
- **"Dependencies = clean, testable wiring."** Auth, DB sessions, config injected
  via `Depends`.

### Scenario & system-design questions

??? question "Design a streaming chat endpoint for an LLM app."
    `POST /chat` → retrieve context (RAG) → build prompt → `await` the model with
    an **async client** → return a **`StreamingResponse`** yielding tokens.
    Add input-size limits, per-user rate limiting, timeouts, and a fallback if the
    model call fails.

??? question "Your API blocks under load even though it's async. Why?"
    A **blocking call inside an `async def`** (e.g. a sync DB driver or `requests`)
    stalls the event loop. Fix: use async clients, or move blocking work to a
    threadpool (`def` handler / `run_in_executor`). CPU-bound work belongs in a
    worker, not the loop.

??? question "How do you deploy FastAPI to production?"
    **Uvicorn** workers under **Gunicorn**, behind Nginx/ALB for TLS + load
    balancing; containerized on ECS/Fargate/K8s, or **Mangum** to run on Lambda +
    API Gateway. Health checks, structured logging, and config via env/secrets.

??? question "How do you keep request/response contracts safe as the API evolves?"
    Pydantic **response_model** enforces the output shape; version the API
    (`/v1`); validate inputs strictly; and rely on the auto OpenAPI schema as the
    contract for clients.

### Pitfalls interviewers probe

- Blocking I/O inside `async def` (kills concurrency).
- No `response_model` → leaking internal fields.
- Doing heavy CPU work in the event loop.
- Skipping input validation/limits on public endpoints.
- Global mutable state instead of dependency injection.

### Rapid-fire

| Q | A |
|---|---|
| FastAPI vs Flask? | ASGI/async + Pydantic validation + auto docs vs sync WSGI |
| `async def` vs `def`? | Async for non-blocking I/O; def (threadpool) for blocking/CPU |
| What is `Depends` for? | Injecting reusable logic: auth, DB, config |
| Auto docs URLs? | `/docs` (Swagger), `/redoc` |
| Stream tokens with? | `StreamingResponse` |

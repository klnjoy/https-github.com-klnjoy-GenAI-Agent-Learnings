# AI Engineer Interview Q&A — Advanced & Scenario-Based

Senior GenAI / AI-engineering questions: RAG design, agents, evaluation,
guardrails, cost/latency, and productionizing LLM systems. Concise talking
points with snippets where they help.

---

## 60-second talking points

- **"Ground the model, don't trust its memory."** Retrieval + context beats
  fine-tuning for factual, changing knowledge.
- **"Evaluate before you tune."** A labeled eval set turns prompt/model changes
  from vibes into measured decisions.
- **"Determinism and structure where correctness matters."** Low temperature,
  JSON-only output, and validation for anything auditable.

---

## RAG

=== "Retrieve → ground → answer"

    ```text
    query → embed → vector/hybrid search (top-k)
          → rerank → assemble context (within token budget)
          → prompt with citations → answer + sources
    ```

??? question "RAG vs fine-tuning — when do you pick which?"
    **RAG** for factual, frequently-changing, or large knowledge you must cite and
    keep current — you update the index, not the model. **Fine-tuning** for
    teaching *behavior/format/style* or a narrow domain skill the model lacks, not
    for injecting facts. Often combined: fine-tune tone/format, RAG for facts. RAG
    is cheaper to keep fresh and gives provenance.

??? question "Retrieval returns irrelevant chunks. How do you fix quality?"
    Work the pipeline end to end: fix **chunking** (size/overlap aligned to
    semantics, not arbitrary splits); use a better **embedding model**; switch to
    **hybrid** (vector + keyword) so exact terms aren't lost; add a **reranker** to
    reorder top-k; and add **metadata filters** to scope the search. Measure with a
    retrieval eval set (hit rate / MRR / recall@k) so you know which change helped.

??? question "How do you choose chunk size and overlap?"
    Chunk to **semantic units** (paragraphs/sections) rather than fixed tokens
    where possible; typical ranges are a few hundred tokens with modest overlap so
    context isn't cut mid-thought. Too large → diluted relevance and wasted context
    budget; too small → lost context and more chunks to manage. Tune empirically
    against your eval set.

??? question "The answer is grounded but the model still hallucinates a detail. Why?"
    The model is filling gaps from parametric memory. Mitigate: instruct it to
    answer **only** from provided context and say "not found" otherwise; lower
    temperature; require **citations** tied to retrieved chunks and validate them;
    and tighten retrieval so the needed fact is actually present. If the context
    lacks it, the fix is retrieval, not prompting.

---

## Agents

??? question "When do you actually need an agent vs a fixed pipeline?"
    Use a **fixed pipeline** when the steps are known and stable (cheaper, more
    reliable, easier to test). Use an **agent** when the task is open-ended and the
    path depends on intermediate results — the model must plan, choose tools, and
    iterate. Agents add latency, cost, and failure modes, so don't reach for them
    when a deterministic chain works.

??? question "Design a reliable tool-using agent."
    Narrow, well-described tools (typed schemas, least privilege, read vs write
    separated); a **plan → act → observe** loop with a step cap to prevent runaway
    loops; **grounding** (tools return real data); **guardrails** on inputs and
    outputs; **human-in-the-loop** for destructive actions; and full **tracing** of
    every step for debugging and eval. Treat tool output as untrusted (injection).

??? question "Single agent vs multi-agent (supervisor)?"
    Start single-agent — it's simpler and often enough. Move to **supervisor +
    specialists** when domains are genuinely distinct (each needs different tools/
    context) and a router improves reliability. Multi-agent adds coordination cost
    and more failure surface, so justify it with real separation of concerns.

---

## Evaluation & guardrails

=== "Structured, deterministic output"

    ```text
    System: Answer ONLY from the provided context. If missing, return NA.
    Return JSON only: {"answer": "...", "citations": ["chunk_id", ...]}
    temperature = 0.0
    ```

??? question "How do you evaluate an LLM feature before shipping a change?"
    Build a **labeled eval set** of representative inputs with expected outputs or
    rubrics. Measure per-dimension: retrieval quality (recall@k/MRR), answer
    correctness/faithfulness (exact match, or **LLM-as-judge** with a rubric),
    format validity, latency, and cost. Run it on every prompt/model change so you
    ship on evidence, not vibes. Pin model versions and re-run before upgrading.

??? question "LLM-as-judge — how do you keep it trustworthy?"
    Use a clear rubric and structured scores, calibrate the judge against a
    human-labeled subset, watch for known biases (position, verbosity,
    self-preference), and use a strong judge model at low temperature. Treat it as
    a scalable approximation of human eval, spot-checked by humans, not gospel.

??? question "What guardrails go around a production LLM?"
    **Input** guardrails (block injection/unsafe requests, PII handling),
    **output** guardrails (validate schema, filter unsafe/off-policy content,
    verify citations), **grounding** (answer only from context), and **operational**
    controls (rate limits, cost caps, timeouts, fallback responses). Human review
    for high-stakes actions. Log everything for audit.

---

## Cost, latency, production

??? question "Your LLM feature is too slow and too expensive. Levers?"
    **Model routing**: small/cheap model for easy cases, escalate hard ones.
    **Caching**: exact + semantic caching of frequent queries. **Prompt
    trimming**: retrieve less, compress context, drop redundant history.
    **Batching** where possible. **Streaming** to cut *perceived* latency. Right-
    size context (tokens = cost + latency). Measure per-request cost/latency and
    optimize the top offenders.

??? question "How do you handle prompt injection in a RAG/agent system?"
    Treat all retrieved/tool content as **data, not instructions**; the system
    prompt should say to ignore embedded directives. Separate trusted instructions
    from untrusted context, validate/scope tool actions, gate writes with approval,
    and sanitize/pattern-check where feasible. Never let untrusted text trigger a
    privileged action directly.

??? question "How do you deploy and monitor an LLM app responsibly?"
    Version prompts and models; roll out changes behind flags/canary with the eval
    set as a gate; monitor **quality drift** (sampled evals in prod), latency,
    cost, and error rates; capture user feedback (thumbs up/down); and keep a fast
    rollback. Re-run the eval set before any model upgrade to catch silent
    regressions.

---

## Rapid-fire

| Q | A |
|---|---|
| RAG vs fine-tune? | RAG = facts/fresh/cited; fine-tune = behavior/format/style |
| Hybrid search? | vector + keyword combined for better recall |
| Reranker role? | reorders top-k for relevance before context assembly |
| Temperature for auditing? | 0.0 (deterministic, repeatable) |
| LLM-as-judge? | model scores outputs against a rubric, human-calibrated |
| Semantic cache? | reuse answers for similar (not just identical) queries |
| Agent step cap? | prevents runaway plan→act loops |
| Biggest agent risk? | prompt injection via tool/retrieved content |

---

## Pitfalls interviewers probe

- Fine-tuning to inject facts (use RAG).
- Shipping prompt/model changes with no eval set.
- Trusting retrieved/tool content as instructions (injection).
- Reaching for multi-agent when a fixed chain works.
- Ignoring token budget → cost/latency blowups.
- No versioning/rollback → silent quality drift on model upgrades.

---
icon: material/help-circle
---

# FAQ

Quick answers to common questions. Each links to a deeper page.

## Concepts

??? question "RAG or fine-tuning — which do I use?"
    **Knowledge** (fresh/private/changing facts, need citations) → **RAG**.
    **Behavior/style/format** → **fine-tuning** (or LoRA). Most apps start with
    RAG. See [LLM Fundamentals](../../GenAI-Topics/llm-fundamentals/index.md).

??? question "What's the difference between prompt engineering and context engineering?"
    Prompt engineering is the *wording*; context engineering is *what goes into
    the context window and how it's budgeted* across a conversation/agent run.
    See [Context Engineering](../../GenAI-Topics/context-engineering/index.md).

??? question "Top-K vs reranking?"
    Top-K = how many candidates retrieval returns. Reranking = a second, more
    accurate model that reorders those candidates by true relevance. Use both:
    retrieve a wider K, then rerank down. See [RAG](../../GenAI-Topics/rag/index.md).

??? question "Vector DB or graph DB for retrieval?"
    Vector DB for semantic similarity over text; graph DB for multi-hop,
    relationship questions (GraphRAG). Often complementary. See
    [Vector DB](../../GenAI-Topics/vector-db/index.md) /
    [Graph DB](../../GenAI-Topics/graph-db/index.md).

## Building

??? question "Chain or agent?"
    Chain when the steps are known and fixed; agent when the model must decide
    which tools to call. Agents cost more and need guardrails. See
    [Agent Engineering](../../GenAI-Topics/agent-engineering/index.md).

??? question "How do I stop my agent from doing something dangerous?"
    Least-privilege tools, human-in-the-loop for writes, iteration/cost caps, and
    full tracing. See [Agent Workflow](../agent-workflow/index.md).

??? question "How do I evaluate a GenAI app?"
    Separate retrieval metrics (precision/recall) from generation (faithfulness,
    answer relevance); use a labeled set + LLM-as-judge calibrated to humans; run
    it in CI. See [Observability & Eval](../../GenAI-Topics/observability/index.md).

## Operations

??? question "How do I cut LLM cost?"
    Model routing (cheap for easy, strong for hard), prompt caching, token
    budgets, and caching repeated queries. See [LLMOps](../../GenAI-Topics/llmops/index.md).

??? question "Managed API or self-hosted model?"
    Managed (Bedrock/OpenAI/Azure) to ship fast; self-host (vLLM/TGI) for control,
    fixed cost, or data-in-house requirements. See
    [Model Selection](../model-selection/index.md).

??? question "How do I use the retrieval agent in this site?"
    ```bash
    cd agent
    python ask.py "your question"
    python ask.py --area snowflake "MERGE upsert pattern"
    ```
    It answers from this knowledge base with citations. See the `agent/README.md`.

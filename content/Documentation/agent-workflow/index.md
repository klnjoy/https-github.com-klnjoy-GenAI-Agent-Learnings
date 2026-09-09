---
icon: material/robot
---

# Agent Workflow

How an LLM agent turns a goal into actions. For patterns and interview prep, see
[Agent Engineering](../../GenAI-Topics/agent-engineering/index.md).

## The control loop

```mermaid
flowchart TB
    G([Goal]) --> P[Reason / plan next step]
    P --> DEC{Need a tool?}
    DEC -- yes --> SEL[Select tool + args]
    SEL --> GRD[Guardrail check]
    GRD --> EXE[Execute tool]
    EXE --> OBS[Observe result]
    OBS --> P
    DEC -- no --> FIN[Compose final answer]
    FIN --> OUT([Answer])
    P -. iteration cap .- STOP{Over budget?}
    STOP -- yes --> FALL[Deterministic fallback]
```

## Anatomy

| Component | Role |
|-----------|------|
| **Planner/reasoner** | The LLM deciding the next step |
| **Tools** | Actions: search, DB query, API call (often via MCP) |
| **Memory** | Short-term (conversation) + long-term (facts) |
| **Guardrails** | Gate risky/irreversible actions |
| **Controller** | Iteration cap, cost budget, timeouts |
| **Tracer** | Logs every step for debugging/eval |

## Control & safety

- **Bound the loop** — max iterations + cost budget stop runaways.
- **Least-privilege tools** — separate read vs write; gate writes behind checks.
- **Human-in-the-loop** — approval before high-impact actions.
- **Deterministic fallback** — if the agent stalls, degrade to a fixed flow.
- **Trace everything** — you can't debug an agent you can't see.

## Single vs multi-agent

```mermaid
flowchart LR
    subgraph Multi-agent
      SUP[Supervisor / planner]
      SUP --> A1[Researcher]
      SUP --> A2[Writer]
      SUP --> A3[Reviewer]
    end
```

Start single-agent. Use a supervisor + specialists only when one agent's scope
and tools become unreliable — coordination adds latency and failure modes.

## Related

- [Agent Engineering](../../GenAI-Topics/agent-engineering/index.md)
  · [LangGraph](../../GenAI-Topics/langgraph/index.md)
  · [MCP](../../GenAI-Topics/mcp/index.md)
  · [AgentCore](../../GenAI-Topics/agentcore/index.md)

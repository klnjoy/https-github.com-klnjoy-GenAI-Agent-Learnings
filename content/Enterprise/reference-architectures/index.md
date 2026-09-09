---
icon: material/cloud-braces
---

# Reference Architectures

Blueprint RAG/agent architectures on the major platforms. Same pattern
everywhere — API → retrieval → model → guardrails → observability — with
platform-native services.

=== "AWS"

    ```mermaid
    flowchart LR
        U([User]) --> APIGW[API Gateway]
        APIGW --> L[Lambda / ECS]
        L --> KB[Bedrock Knowledge Base]
        KB --> OSS[(OpenSearch / vector)]
        L --> BR[Bedrock model]
        BR --> GR[Bedrock Guardrails]
        GR --> U
        L --> CW[CloudWatch]
        IAM[IAM] -.-> L
    ```

    Bedrock (models + Knowledge Bases + Guardrails), OpenSearch/pgvector for
    vectors, Lambda/ECS compute, IAM + KMS + Secrets Manager, CloudWatch. Data
    stays in your account.

=== "Azure"

    ```mermaid
    flowchart LR
        U([User]) --> APP[App Service / Functions]
        APP --> AIS[Azure AI Search - vector]
        APP --> AOAI[Azure OpenAI]
        AOAI --> CS[Content Safety]
        CS --> U
        APP --> MON[Azure Monitor]
        AAD[Entra ID / RBAC] -.-> APP
    ```

    Azure OpenAI for models, Azure AI Search for retrieval, Content Safety for
    guardrails, Entra ID (RBAC), Key Vault, Azure Monitor.

=== "GCP"

    ```mermaid
    flowchart LR
        U([User]) --> RUN[Cloud Run]
        RUN --> VEC[Vertex AI Vector Search]
        RUN --> GEM[Vertex AI - Gemini]
        GEM --> SAF[Safety filters]
        SAF --> U
        RUN --> OPS[Cloud Logging / Monitoring]
        IAM[Cloud IAM] -.-> RUN
    ```

    Vertex AI (Gemini + Vector Search), Cloud Run compute, IAM, Secret Manager,
    Cloud Logging/Monitoring.

=== "Snowflake"

    ```mermaid
    flowchart LR
        U([User]) --> ST[Streamlit in Snowflake]
        ST --> CS[Cortex Search - retrieval]
        CS --> DATA[(Governed tables)]
        ST --> CA[Cortex Analyst / LLM functions]
        CA --> U
        RBAC[RBAC + masking + tags] -.-> DATA
    ```

    Everything inside Snowflake: Cortex Search (RAG), Cortex Analyst / LLM
    functions, Streamlit apps, governed by existing RBAC, masking, and tags — no
    data egress.

## Choosing

| If you... | Lean |
|-----------|------|
| Already on AWS, want managed GenAI | **AWS + Bedrock** |
| Microsoft shop, want OpenAI models | **Azure OpenAI** |
| On Google Cloud / want Gemini | **GCP Vertex AI** |
| Data lives in Snowflake, want zero egress | **Snowflake Cortex** |

## Related

- [Architecture Overview](../../Documentation/architecture-overview/index.md)
  · [Bedrock](../../GenAI-Topics/bedrock/index.md)
  · [Snowflake](../../Technologies/snowflake/index.md)
  · [Security Architecture](../security-architecture/index.md)

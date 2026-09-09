---
icon: material/database
---

# Databricks

Databricks is a unified **Lakehouse** platform built on Apache Spark and Delta
Lake — combining the low-cost, open storage of a data lake with the reliability
and performance of a warehouse, plus native ML/GenAI (Mosaic AI).

## Lakehouse architecture

```mermaid
flowchart TB
    subgraph SRC[Sources]
      S1[Files / DBs / Streams]
    end
    subgraph LH[Lakehouse on Delta Lake]
      B[Bronze - raw]
      SI[Silver - cleaned/conformed]
      G[Gold - business aggregates]
    end
    subgraph GOV[Unity Catalog]
      GV[Governance, lineage, access]
    end
    SRC --> B --> SI --> G
    GOV -.governs.-> LH
    G --> BI[BI / SQL]
    G --> ML[Mosaic AI / ML]
```

The **medallion architecture** (Bronze → Silver → Gold) is the standard pattern:
raw ingestion, then cleaning/conforming, then business-level aggregates.

## Delta Lake

The storage layer that makes the lakehouse work:

- **ACID transactions** on object storage (no more partial writes).
- **Time Travel** — query/restore previous versions (`VERSION AS OF`).
- **Schema enforcement & evolution**.
- **`MERGE`** for upserts/CDC; **`OPTIMIZE`** + **Z-ordering** for file compaction
  and data skipping; **`VACUUM`** to clean old files.

```sql
-- Upsert with Delta MERGE
MERGE INTO gold.customers t
USING staging.customers s ON t.id = s.id
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *;

-- Optimize + data skipping
OPTIMIZE gold.customers ZORDER BY (region, signup_date);
```

## Spark essentials

- **Lazy evaluation**: transformations build a DAG; actions trigger execution.
- **Narrow vs wide transformations**: wide ops (joins, groupBy) cause shuffles —
  the main perf cost.
- **Partitioning & caching**: repartition to balance work; cache reused DataFrames.
- **PySpark / SQL / Scala** interchangeable on the same engine.

```python
from pyspark.sql import functions as F
gold = (silver
        .filter(F.col("status") == "active")
        .groupBy("region")
        .agg(F.sum("amount").alias("total")))
gold.write.mode("overwrite").saveAsTable("gold.region_totals")
```

## Unity Catalog (governance)

Centralized governance across workspaces: a three-level namespace
`catalog.schema.table`, fine-grained access control, **column/row masking**,
**data lineage**, and a discovery search. One place to secure all data & AI assets.

## Mosaic AI & Genie (GenAI)

| Capability | What it does |
|------------|--------------|
| **Mosaic AI Model Serving** | Deploy/serve ML & LLM endpoints |
| **Vector Search** | Managed vector index for RAG |
| **AI Functions (`ai_query`)** | Call LLMs from SQL, like Snowflake Cortex |
| **Genie** | Natural-language analytics over your data (text-to-insight) |
| **MLflow** | Experiment tracking, model registry, deployment |

```sql
-- Call an LLM from Databricks SQL
SELECT ai_query('databricks-meta-llama-3-70b-instruct',
                'Summarize: ' || review) AS summary
FROM feedback;
```

## Snowflake vs Databricks (quick take)

| Dimension | Snowflake | Databricks |
|-----------|-----------|------------|
| Origin | Cloud data warehouse | Spark/lakehouse |
| Sweet spot | SQL analytics, sharing, ease of use | Data engineering, ML/AI, big data |
| Storage | Managed micro-partitions | Open Delta Lake on your storage |
| GenAI | Cortex | Mosaic AI / Genie |
| Governance | RBAC, tags, masking | Unity Catalog |

They overlap more each year; choice often comes down to existing skills, workload
mix (heavy ML → Databricks; SQL-first + sharing → Snowflake), and openness needs.

## Interview questions

??? question "What is the Lakehouse and how is it different from a warehouse or lake?"
    A lakehouse combines the open, cheap storage of a data lake with the ACID
    transactions, schema, and performance of a warehouse — on one copy of data via
    Delta Lake. Avoids the two-system (lake + warehouse) copy/sync problem.

??? question "Explain the medallion architecture."
    Bronze (raw ingested), Silver (cleaned/conformed/deduped), Gold
    (business-level aggregates for BI/ML). Progressive refinement with clear
    quality contracts at each layer.

??? question "Narrow vs wide transformations in Spark?"
    Narrow (map, filter) need no data movement; wide (join, groupBy, distinct)
    trigger shuffles across the network — the main performance cost. Minimize/
    optimize shuffles.

??? question "What does Delta Lake add on top of Parquet?"
    ACID transactions, a transaction log, Time Travel, schema enforcement/
    evolution, MERGE/upserts, and OPTIMIZE/Z-order for performance.

## Related course modules

- **[MODULE2-AWS-CLOUD](../../Course-Modules/module2-aws-cloud.md)** — cloud data
  fundamentals that transfer to Databricks.
- **[MODULE3-PYTHON](../../Course-Modules/module3-python.md)** — PySpark and
  Python data engineering.

---

## Interview deep dive

### 60-second talking points

- **"Lakehouse = one copy, both worlds."** Delta Lake adds ACID, schema, and
  performance to cheap open object storage, so you avoid the lake-plus-warehouse
  copy/sync problem.
- **"The cost is the shuffle."** Spark's speed comes from parallelism; wide
  transformations (join, groupBy) shuffle data across the network — that's what
  you tune.
- **"Unity Catalog governs data *and* AI."** One place for access, lineage, and
  masking across workspaces.

### Spark internals worth knowing

- **Lazy DAG**: transformations build a plan; an **action** (`count`, `write`)
  triggers execution. The Catalyst optimizer + Tungsten engine plan it.
- **Jobs → stages → tasks**: a shuffle boundary splits stages; tasks run per
  partition.
- **Skew & spill**: uneven partitions overload one executor; salting or AQE
  (Adaptive Query Execution) helps. Spill = not enough memory → disk.
- **Broadcast join**: small table sent to every executor to avoid a shuffle.

### Scenario & system-design questions

??? question "A Spark job is slow and one task takes 10x longer than the rest. Diagnose it."
    Classic **data skew** — one partition/key has far more rows. Fixes: enable
    **AQE** (skew join handling), **salt** the hot key, repartition on a better
    key, or broadcast the small side if it's a join. Check the Spark UI stage view
    for the long task and its input size.

??? question "Design an ingestion pipeline for streaming + batch into the lakehouse."
    **Medallion**: Auto Loader / Structured Streaming into **Bronze** (raw, append)
    → cleanse/dedupe/conform into **Silver** (`MERGE` for CDC) → aggregate into
    **Gold**. Delta gives ACID + Time Travel; `OPTIMIZE`/Z-order Gold for reads;
    Unity Catalog governs it.

??? question "How do you handle GDPR 'delete my data' on an append-only lake?"
    Delta **`DELETE`** rewrites affected files transactionally; run **`VACUUM`** to
    purge old file versions past the retention window (so time-travel copies are
    also removed). Track with Unity Catalog lineage.

??? question "When would you pick Databricks over Snowflake and vice versa?"
    Databricks for heavy **data engineering / ML / unstructured / big-data** work
    and open Delta storage; Snowflake for **SQL-first analytics, ease of use, and
    data sharing**. They overlap increasingly; decide on workload mix, team
    skills, and openness/lock-in preferences.

### Pitfalls interviewers probe

- Confusing **narrow vs wide** transformations (only wide ones shuffle).
- Calling `collect()` on big data (pulls everything to the driver → OOM).
- Not running `OPTIMIZE`/`VACUUM` → tiny-file problem, slow reads.
- Assuming Delta = Parquet (Delta adds the transaction log, ACID, Time Travel).
- Ignoring partitioning strategy → skew and shuffle blowups.

### Rapid-fire

| Q | A |
|---|---|
| Transformation vs action? | Transformation is lazy; action triggers the DAG |
| What triggers a shuffle? | Wide transformations: join, groupBy, distinct, repartition |
| Delta over Parquet adds? | ACID, transaction log, Time Travel, schema evolution, MERGE |
| Medallion layers? | Bronze (raw) → Silver (clean) → Gold (aggregates) |
| Broadcast join is for? | Joining a small table without shuffling the large one |

# Snowflake Interview Q&A — Advanced & Scenario-Based

Senior-level, real-world Snowflake questions: performance forensics, cost
control, architecture trade-offs, and the failures that actually happen in
production. Answers are concise talking points you can expand on.

---

## 60-second talking points

Crisp framings to sound fluent, not memorized:

- **"Storage and compute are decoupled."** One copy of data, many independent
  virtual warehouses — scale up for a heavy query, out for concurrency, pay
  per-second, clone with zero copy.
- **"Micro-partitions + pruning are the performance story."** ~16 MB compressed
  columnar micro-partitions with min/max metadata; the optimizer skips partitions
  that can't match. No manual indexes.
- **"Cortex is governed GenAI with no data egress."** LLM functions, Cortex
  Search, and Cortex Analyst run inside the RBAC/masking/tag boundary.

---

## Performance & tuning

=== "Diagnose a slow query"

    ```sql
    -- Start from history, then read the Query Profile in Snowsight
    SELECT query_id, total_elapsed_time, bytes_scanned,
           partitions_scanned, partitions_total,
           bytes_spilled_to_local_storage, bytes_spilled_to_remote_storage
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE query_text ILIKE '%my_table%'
    ORDER BY start_time DESC
    LIMIT 20;
    ```

    Look for: low `partitions_scanned / partitions_total` (good pruning) vs high
    (poor filter/cluster key); any **spill** (undersized warehouse); an
    **exploding join** (output rows >> input, wrong grain).

=== "Check clustering health"

    ```sql
    SELECT SYSTEM$CLUSTERING_INFORMATION('sales', '(event_date)');
    ```

    `average_overlaps` / `average_depth` high → partitions overlap on the key →
    pruning is weak. Consider a cluster key aligned to your filter columns, or
    reload in natural order. Don't cluster small or low-cardinality tables.

=== "Right-size warehouses"

    ```sql
    ALTER WAREHOUSE etl_wh SET
      WAREHOUSE_SIZE = 'LARGE'          -- up: bigger single query
      MAX_CLUSTER_COUNT = 4             -- out: concurrency
      MIN_CLUSTER_COUNT = 1
      SCALING_POLICY = 'STANDARD'
      AUTO_SUSPEND = 60 AUTO_RESUME = TRUE;
    ```

??? question "A dashboard was fast, then data grew 10x and it crawled. Walk me through it."
    Open the **Query Profile**. Four usual suspects: (1) **full scans** → add a
    cluster key aligned to filters or fix load order; (2) **spilling to
    local/remote disk** → size the warehouse up; (3) **exploding joins** → verify
    grain/keys, deduplicate before joining; (4) **weak pruning** → check
    `SYSTEM$CLUSTERING_INFORMATION`. Confirm the **result cache** isn't defeated by
    `CURRENT_TIMESTAMP()` or other non-deterministic functions in the query.

??? question "Query spills to remote storage. What does that mean and how do you fix it?"
    The operator (sort/join/aggregate) exceeded warehouse memory and spilled to
    local SSD, then to remote storage (much slower). Fixes: size the warehouse up
    (more memory per node), reduce the working set (filter earlier, project fewer
    columns), fix a bad join grain that inflates rows, or break the query into
    stages. Remote spill in the profile is a red flag to act on.

??? question "When does a cluster key hurt more than it helps?"
    Small tables, low-cardinality keys, or write-heavy tables where reclustering
    cost (a background, credit-consuming service) outweighs read savings. Clustering
    pays off on large tables (hundreds of GB+) queried with selective predicates on
    the cluster key. Measure with clustering info before and after.

---

## Cost control

??? question "The account bill doubled this month. How do you find and stop the bleed?"
    Query `ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY` and `QUERY_HISTORY` to rank
    credit burn by warehouse and by query. Common causes: a warehouse with
    `AUTO_SUSPEND` too high (idle burn), a runaway multi-cluster scaling out, an
    unpartitioned full-scan report running frequently, or `SELECT *` into BI tools.
    Put **resource monitors** with quotas + alerts on each warehouse, tighten
    `AUTO_SUSPEND` to 60s, and separate workloads so ETL doesn't wake the BI cluster.

    ```sql
    SELECT warehouse_name, SUM(credits_used) AS credits
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE start_time > DATEADD('day', -30, CURRENT_TIMESTAMP())
    GROUP BY 1 ORDER BY 2 DESC;
    ```

??? question "How do you cap spend without blocking critical workloads?"
    **Resource monitors** at the account and per-warehouse level with graduated
    triggers: notify at 75%, suspend-at-quota for non-critical warehouses, but
    leave critical ones on notify-only so you don't kill prod. Combine with tight
    auto-suspend and workload isolation.

??? question "Storage costs are climbing even though tables aren't growing. Why?"
    Time Travel + Fail-safe retain historical micro-partitions, and heavy
    update/delete churn multiplies retained versions. Zero-copy clones also hold
    references. Check `TABLE_STORAGE_METRICS` for `time_travel_bytes` and
    `failsafe_bytes`; reduce `DATA_RETENTION_TIME_IN_DAYS` on high-churn transient
    tables, and use **transient/temporary** tables for staging (no Fail-safe).

---

## Architecture & data engineering

=== "Snapshot + Current-State (CDC/Merge)"

    ```sql
    CREATE OR REPLACE STREAM s_orders ON TABLE staging.orders;

    CREATE OR REPLACE TASK t_merge_orders
      WAREHOUSE = etl_wh
      SCHEDULE = '5 MINUTE'
      WHEN SYSTEM$STREAM_HAS_DATA('s_orders')
    AS
      MERGE INTO current.orders tgt
      USING s_orders src ON tgt.id = src.id
      WHEN MATCHED AND src.metadata$action = 'DELETE' THEN DELETE
      WHEN MATCHED THEN UPDATE SET tgt.val = src.val, tgt.updated = src.ts
      WHEN NOT MATCHED THEN INSERT (id, val, updated)
        VALUES (src.id, src.val, src.ts);
    ```

=== "Dynamic Tables (declarative)"

    ```sql
    CREATE OR REPLACE DYNAMIC TABLE current_orders
      TARGET_LAG = '5 minutes'
      WAREHOUSE = etl_wh
    AS
      SELECT id, val, updated FROM staging.orders QUALIFY
        ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated DESC) = 1;
    ```

??? question "Streams + Tasks vs Dynamic Tables — when do you pick which?"
    **Streams + Tasks** give imperative control: custom MERGE logic, multi-step
    DAGs, side effects. **Dynamic Tables** are declarative — you define the target
    query and a `TARGET_LAG`, Snowflake figures out the incremental refresh. Reach
    for Dynamic Tables when the transform is expressible as a query and you want
    less orchestration code; use Streams+Tasks when you need branching logic,
    procedural steps, or fine-grained control over the merge.

??? question "Design a near-real-time Oracle → Snowflake pipeline with CDC."
    Land CDC files (DMS or a CDC tool) into S3 → **Snowpipe** auto-ingests into a
    staging table → a **Stream** captures row changes → a scheduled **Task** runs
    `MERGE` into the current-state table and archives prior versions into a
    timestamped snapshot table. Query current for operations, snapshot for audit,
    and a view/`UNION` for the full picture. Tag the history table for
    confidentiality/compliance.

??? question "How do you do blue/green or safe schema changes on a huge prod table?"
    **Zero-copy clone** the table (instant, no storage cost), apply and validate
    changes on the clone, then swap with `ALTER TABLE ... SWAP WITH`. Time Travel
    gives you an instant rollback (`AT`/`BEFORE` or `UNDROP`). This avoids long
    locks and gives a tested cutover.

---

## Governance & security

??? question "Implement column-level PII protection across hundreds of tables without editing each."
    **Tag** PII columns once (e.g. `governance.pii = 'email'`), then attach a
    **tag-based masking policy** so masking follows the classification
    automatically as new tables adopt the tag. Combine with **row access policies**
    for tenant isolation and a role hierarchy so only privileged roles see
    cleartext.

    ```sql
    CREATE MASKING POLICY mask_email AS (val STRING) RETURNS STRING ->
      CASE WHEN CURRENT_ROLE() IN ('PII_READER') THEN val
           ELSE REGEXP_REPLACE(val, '.+@', '****@') END;
    ALTER TAG governance.pii SET MASKING POLICY mask_email;
    ```

??? question "Share live data with an external partner with no copies. How?"
    **Secure Data Sharing**: create a share, grant on the objects, add the consumer
    account — or a **reader account** if they're not on Snowflake. They query your
    micro-partitions live; you pay storage, they pay their own compute. No ETL, no
    stale copies. Use **secure views** to expose only the rows/columns intended.

---

## Cortex / AI

??? question "How would you add GenAI to a Snowflake platform without moving data out?"
    Use **Cortex**: LLM functions (`AI_COMPLETE`, `SUMMARIZE`, `SENTIMENT`) run in
    SQL; **Cortex Search** for hybrid retrieval/RAG; **Cortex Analyst** for
    natural-language → governed SQL over a semantic model. All processing stays
    inside Snowflake under existing RBAC, masking, and tags — no egress.

??? question "Cortex Analyst vs Cortex Search — what's the difference?"
    **Analyst** answers questions over **structured** data by generating SQL from a
    semantic model (YAML describing tables, joins, metrics). **Search** does
    retrieval over **unstructured** text (chunks + embeddings, hybrid vector +
    keyword). A conversational assistant often uses both, orchestrated by an agent.

---

## Rapid-fire

| Q | A |
|---|---|
| Default Time Travel window? | 1 day (up to 90 on Enterprise) |
| What is Fail-safe? | 7-day, non-configurable, Snowflake-managed disaster recovery |
| Scale **up** vs **out**? | Up = bigger warehouse (heavy query); out = more clusters (concurrency) |
| Result cache duration? | 24h if underlying data unchanged and query deterministic |
| Micro-partition size? | ~50–500 MB uncompressed (~16 MB compressed), columnar |
| Transient vs permanent table? | Transient has no Fail-safe → cheaper for staging |
| `COPY` vs Snowpipe? | `COPY` = bulk batch; Snowpipe = continuous, auto-triggered micro-batches |
| Materialized view vs Dynamic Table? | MV = single-table precompute; DT = multi-table declarative pipeline with lag |

---

## Pitfalls interviewers probe

- Thinking warehouses store data (storage is separate and shared).
- Over-clustering small/low-cardinality/write-heavy tables (cost > benefit).
- One giant warehouse for everything (contention) — or hundreds of tiny ones.
- Leaving `AUTO_SUSPEND` high so warehouses burn idle credits.
- Treating Time Travel as backup (Fail-safe is disaster-only, not self-serve).
- Assuming Cortex sends data to an external API (it runs in-account).

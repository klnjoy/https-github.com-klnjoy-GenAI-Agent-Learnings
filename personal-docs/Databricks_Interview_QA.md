# Databricks Interview Q&A — Advanced & Scenario-Based

Senior lakehouse questions: Spark performance, Delta Lake internals, data skew,
Unity Catalog governance, and streaming. Concise talking points with code where
it helps.

---

## 60-second talking points

- **"Lakehouse = data lake storage + warehouse semantics."** Delta Lake adds ACID
  transactions, schema enforcement, and time travel on cheap object storage.
- **"Spark is lazy; actions trigger execution."** Transformations build a DAG;
  the shuffle is where performance is won or lost.
- **"Unity Catalog is the single governance plane."** One place for access,
  lineage, and discovery across workspaces.

---

## Spark performance

=== "Diagnose from the Spark UI"

    ```text
    Stages tab → find the long stage
    → check for skew (one task's shuffle read/duration >> others)
    → check spill (memory/disk spill columns > 0)
    → check task count (too few = under-parallelized; too many = overhead)
    ```

=== "Fix skew: salting"

    ```python
    from pyspark.sql import functions as F
    # Add a salt to explode a hot key across partitions before the join
    df = df.withColumn("salt", (F.rand() * 16).cast("int"))
    dim = dim.crossJoin(spark.range(16).withColumnRenamed("id", "salt"))
    joined = df.join(dim, ["key", "salt"])
    ```

=== "Broadcast a small dimension"

    ```python
    from pyspark.sql.functions import broadcast
    fact.join(broadcast(small_dim), "key")
    ```

??? question "A Spark job runs fine on sample data but hangs at scale. Diagnose."
    Almost always **data skew** in a shuffle (join or groupBy on a hot key). Open
    the Spark UI: one task reads/processes far more than the others while the rest
    finish. Fixes: **salt** the skewed key to spread it, **broadcast** the smaller
    side to avoid the shuffle entirely, enable **Adaptive Query Execution** (AQE)
    which does skew-join handling and coalesces partitions, or filter/pre-aggregate
    the hot key separately.

??? question "What is a shuffle and why is it expensive?"
    A shuffle redistributes data across partitions/executors (needed for wide
    transformations like join, groupBy, distinct). It writes to disk and moves data
    over the network — the most expensive operation in Spark. Minimize shuffles:
    broadcast small tables, pre-partition/bucket data, reduce the number of wide
    ops, and push filters/projections down before the shuffle.

??? question "How do you tune partition count?"
    Too few partitions → under-parallelized, spills, OOM. Too many → scheduling
    overhead and tiny files. Target partitions sized ~100–200 MB. Use
    `repartition`/`coalesce` deliberately (coalesce avoids a full shuffle when
    reducing), and let **AQE** coalesce post-shuffle partitions automatically. For
    writes, control output file count to avoid the small-file problem.

??? question "`cache`/`persist` — when does it actually help (or hurt)?"
    Cache pays off when a DataFrame is **reused multiple times** (iterative ML, or
    branching pipelines). It hurts when used once (wasted memory) or when it evicts
    other useful data. Always `unpersist` when done. For a single linear pipeline,
    caching usually adds no value.

---

## Delta Lake

??? question "How does Delta give ACID on object storage?"
    A **transaction log** (`_delta_log`) records ordered JSON commits describing
    which Parquet files are added/removed. Readers reconstruct table state from the
    log (with periodic checkpoints), giving snapshot isolation and atomic commits
    even though the underlying files are immutable objects. This enables time
    travel, `MERGE`, and concurrent writes with optimistic concurrency.

??? question "You have millions of tiny files and reads are slow. Fix it."
    The **small-file problem**. Run `OPTIMIZE` to compact files (and `ZORDER BY`
    high-cardinality filter columns for data skipping). Prevent recurrence: control
    write parallelism, use Auto Optimize / optimized writes, and partition
    sensibly (not over-partitioned). `VACUUM` old files after retention to reclaim
    storage.

    ```sql
    OPTIMIZE sales ZORDER BY (customer_id);
    VACUUM sales RETAIN 168 HOURS;
    ```

??? question "Partitioning vs Z-ordering vs liquid clustering — what's the difference?"
    **Partitioning** physically splits by a low-cardinality column (date) — good
    for pruning but over-partitioning creates small files. **Z-ordering**
    co-locates related data across multiple columns for data skipping within files.
    **Liquid clustering** is the newer, adaptive approach that avoids the rigidity
    of fixed partitions and the maintenance of Z-order. Prefer liquid clustering
    where available for evolving query patterns.

??? question "How does time travel work and when do you use it?"
    Delta keeps versioned commits, so you can query `VERSION AS OF` / `TIMESTAMP AS
    OF` to read past state, audit changes, or roll back a bad write with `RESTORE`.
    Retention is bounded by `VACUUM` — once vacuumed, old versions are gone.

---

## Streaming & pipelines

??? question "Structured Streaming: how do you get exactly-once and handle late data?"
    **Checkpointing** + idempotent sinks (Delta) give exactly-once. Use
    **watermarks** to bound state and drop data later than the threshold for
    windowed aggregations. Choose the right output mode (append/update/complete)
    and trigger interval for the latency/cost trade-off.

??? question "What are Delta Live Tables / declarative pipelines for?"
    Declarative pipeline framework: you define tables (bronze/silver/gold) with
    quality **expectations**, and the framework manages orchestration, incremental
    processing, retries, and lineage. Less orchestration code than hand-rolled
    jobs, with built-in data-quality enforcement.

---

## Governance

??? question "What does Unity Catalog give you over workspace-local access control?"
    A **centralized** governance layer across workspaces: three-level namespace
    (`catalog.schema.table`), fine-grained grants, automated **column/row-level**
    security, **data lineage**, audit, and discovery. Access is consistent
    everywhere instead of per-workspace ACLs. It also governs ML models, volumes,
    and functions.

??? question "Databricks vs Snowflake — how do you frame the choice?"
    Databricks leads for **Spark/ML, unstructured data, and code-heavy data
    engineering** on open Delta format. Snowflake leads for **SQL analytics, ease
    of operations, and near-zero tuning**. Both now overlap (Snowpark, Databricks
    SQL). Choose on workload center of gravity, existing skills, and openness vs
    managed-simplicity preference — not on a feature checklist.

---

## Rapid-fire

| Q | A |
|---|---|
| Transformation vs action? | transformation lazy (builds DAG); action triggers execution |
| `repartition` vs `coalesce`? | repartition = full shuffle (up/down); coalesce = merge partitions, no full shuffle |
| Broadcast join when? | one side small enough to fit in memory → avoids shuffle |
| `OPTIMIZE`? | compacts small Delta files (+ ZORDER for skipping) |
| `VACUUM`? | deletes old unreferenced files past retention |
| Watermark? | bounds streaming state; drops late data past threshold |
| AQE? | Adaptive Query Execution — runtime skew/partition/join optimization |
| Bronze/silver/gold? | raw → cleaned/conformed → business-level aggregates |

---

## Pitfalls interviewers probe

- Ignoring data skew until the job hangs at scale.
- Over-partitioning creating the small-file problem.
- Caching data used only once (wasted memory).
- Forgetting `VACUUM`/`OPTIMIZE` maintenance on Delta tables.
- Treating time travel as infinite (VACUUM removes old versions).
- Broadcasting a table that's actually too big → driver OOM.

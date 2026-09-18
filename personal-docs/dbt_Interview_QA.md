# dbt Interview Q&A — Advanced & Scenario-Based

Senior analytics-engineering questions on dbt: incremental models, testing,
project structure, performance, and how dbt fits a governed warehouse. Concise
talking points with code where it helps.

---

## 60-second talking points

- **"dbt is the T in ELT."** SQL transformations, version-controlled, tested, and
  documented — it turns raw tables into trusted models with lineage.
- **"Models are just SELECTs; dbt handles the DDL."** You write the query, dbt
  materializes it as a view/table/incremental and wires up dependencies via `ref`.
- **"Tests + contracts make the warehouse trustworthy."** Schema tests, data
  tests, and model contracts catch breakage before it hits BI.

---

## Materializations

=== "Incremental model"

    ```sql
    {{ config(materialized='incremental', unique_key='order_id',
              incremental_strategy='merge') }}

    SELECT order_id, customer_id, amount, updated_at
    FROM {{ ref('stg_orders') }}
    {% if is_incremental() %}
      WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
    {% endif %}
    ```

=== "Snapshot (SCD2)"

    ```sql
    {% snapshot orders_snapshot %}
    {{ config(target_schema='snapshots', unique_key='order_id',
              strategy='timestamp', updated_at='updated_at') }}
    SELECT * FROM {{ source('erp', 'orders') }}
    {% endsnapshot %}
    ```

??? question "When do you use incremental vs table vs view?"
    **View**: cheap, always fresh, no storage — good for light transforms and
    staging. **Table**: full rebuild each run — simple, good when the model is small
    or logic changes often. **Incremental**: only process new/changed rows — for
    large fact tables where full rebuilds are too slow/expensive. Trade-off:
    incremental adds complexity (late-arriving data, backfills, schema drift), so
    only reach for it when full refresh actually hurts.

??? question "An incremental model is silently missing rows. What's wrong?"
    Usual causes: the `is_incremental()` filter uses a watermark that misses
    **late-arriving** data (an event with an older `updated_at` than the current
    max); a non-unique `unique_key` causing merge collisions; or source
    late-updates not captured by the timestamp. Fixes: use a lookback window
    (`> max - interval`), pick a truly unique key, or periodically `--full-refresh`.
    For correctness-critical data, consider `merge` strategy with a robust key.

??? question "How do you handle a schema change on an incremental model?"
    Incremental models don't auto-add columns by default. Use
    `on_schema_change='append_new_columns'` (or `sync_all_columns`) in config, or
    run `--full-refresh` to rebuild with the new shape. Plan backfills carefully so
    you don't reprocess everything unnecessarily.

---

## Testing & reliability

=== "Schema tests"

    ```yaml
    models:
      - name: fct_orders
        columns:
          - name: order_id
            tests: [unique, not_null]
          - name: customer_id
            tests:
              - relationships:
                  to: ref('dim_customers')
                  field: customer_id
    ```

=== "Model contract"

    ```yaml
    models:
      - name: fct_orders
        config:
          contract: {enforced: true}
        columns:
          - name: order_id
            data_type: number
          - name: amount
            data_type: number
    ```

??? question "How do you stop a bad upstream change from breaking BI?"
    Layered defense: **schema tests** (`unique`, `not_null`, `relationships`,
    `accepted_values`) on key columns; **model contracts** to enforce column
    names/types so a breaking change fails at build; **freshness** checks on
    sources; and run tests in CI on every PR (dbt Cloud CI or a CI job) so
    breakage is caught before merge, not in the dashboard.

??? question "Singular vs generic tests, and when to write custom ones?"
    **Generic tests** are reusable, parameterized (the built-ins + packages like
    dbt-utils). **Singular tests** are one-off SQL queries that should return zero
    rows (e.g. "no order with negative amount"). Write a **custom generic test**
    when you find yourself repeating the same singular logic across models.

---

## Project structure & performance

??? question "How do you structure a dbt project that scales to hundreds of models?"
    Layered folders: **staging** (1:1 with sources, light cleanup, views),
    **intermediate** (business logic building blocks), **marts** (facts/dims for
    consumption). Enforce naming (`stg_`, `int_`, `fct_`, `dim_`), one source of
    truth per concept, and use `ref()`/`source()` everywhere for lineage. Group
    marts by business domain. Keep models single-responsibility.

??? question "dbt runs are getting slow. How do you speed them up?"
    Convert expensive full-refresh models to **incremental**; use `--select` state
    selectors (`state:modified+`) in CI to build only changed models and their
    children; parallelize with higher `threads`; push heavy logic to appropriately
    sized warehouses; and avoid rebuilding staging views unnecessarily. Materialize
    hot intermediate models as tables instead of nesting deep view-on-view chains.

??? question "What does `ref()` actually buy you over hardcoding table names?"
    `ref()` builds the **DAG**: dbt knows dependencies, runs models in the right
    order, enables `--select`/`state:` selection, and swaps schemas per environment
    (dev/prod) automatically. Hardcoding breaks lineage, ordering, and
    environment isolation.

---

## Governance & collaboration

??? question "How do dbt and Snowflake governance fit together?"
    dbt generates the SQL/DDL but runs **as a role** in Snowflake — so RBAC,
    masking policies, and row access policies still apply. Keep dbt's role scoped
    (least privilege), separate dev/prod databases, and use dbt to *document*
    (descriptions, `persist_docs`) while Snowflake enforces access. dbt exposures
    document downstream BI dependencies for impact analysis.

??? question "How do you manage dev vs prod safely?"
    **Targets/environments**: dev builds into a personal/dev schema, prod into the
    prod schema, controlled by `profiles.yml` targets and CI. Use `generate_schema_name`
    conventions, run CI on PRs against a clone or dev, and only prod-deploy from the
    main branch after tests pass.

---

## Rapid-fire

| Q | A |
|---|---|
| `ref` vs `source`? | ref = another dbt model; source = raw external table |
| Seed? | small CSV loaded as a table (lookups/mappings) |
| Snapshot? | SCD2 history tracking of a mutable source |
| `{{ this }}`? | the current model's relation (used in incremental filters) |
| `--full-refresh`? | rebuild incremental models from scratch |
| Exposure? | documents a downstream consumer (dashboard/app) for lineage |
| dbt-utils? | community macro package (surrogate keys, tests, helpers) |
| Contract? | enforces column names/types at build time |

---

## Pitfalls interviewers probe

- Incremental watermark missing late-arriving data (no lookback window).
- Non-unique `unique_key` causing merge duplicates.
- Deep view-on-view chains killing query performance.
- No tests/contracts → silent breakage reaches BI.
- Hardcoding table names instead of `ref()`, breaking lineage.
- Forgetting `on_schema_change` handling on incremental models.

# Python Interview Q&A — Advanced & Scenario-Based

Senior Python questions for data/AI engineering: concurrency, memory,
performance, and the runtime behaviors that trip people up. Answers are concise
talking points with code where it clarifies.

---

## 60-second talking points

- **"The GIL means threads don't parallelize CPU work."** Use threads for
  I/O-bound concurrency, processes (or native extensions) for CPU-bound.
- **"Generators stream; lists materialize."** For large data, generators keep
  memory flat and enable lazy pipelines.
- **"Prefer immutability and pure functions at boundaries."** Easier to test,
  reason about, and parallelize.

---

## Concurrency & the GIL

=== "I/O-bound: asyncio"

    ```python
    import asyncio, aiohttp

    async def fetch(session, url):
        async with session.get(url) as r:
            return await r.text()

    async def main(urls):
        async with aiohttp.ClientSession() as s:
            return await asyncio.gather(*(fetch(s, u) for u in urls))
    ```

=== "CPU-bound: processes"

    ```python
    from concurrent.futures import ProcessPoolExecutor

    def heavy(n): return sum(i*i for i in range(n))

    with ProcessPoolExecutor() as ex:
        results = list(ex.map(heavy, [10_000_000]*8))
    ```

=== "I/O-bound: threads"

    ```python
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=40) as ex:
        results = list(ex.map(call_api, payloads))
    ```

??? question "Explain the GIL and when it actually matters."
    The Global Interpreter Lock lets only one thread execute Python bytecode at a
    time in CPython. It matters for **CPU-bound** work — threads won't speed it up;
    use `multiprocessing`, or push work into C/NumPy which releases the GIL. For
    **I/O-bound** work (network, disk) threads and `asyncio` are great because the
    GIL is released while waiting. (Note: free-threaded CPython is emerging, but
    assume the GIL in most environments.)

??? question "asyncio vs threads vs processes — how do you choose?"
    **asyncio**: many concurrent I/O waits, one thread, cooperative — best for
    thousands of network calls with async libraries. **Threads**: I/O-bound with
    blocking libraries, simpler mental model, GIL-limited for CPU. **Processes**:
    CPU-bound parallelism, separate memory, higher overhead and IPC cost. Rule of
    thumb: I/O → async/threads; CPU → processes or native code.

??? question "You have 10k API calls to make. Design it."
    I/O-bound, so concurrency not parallelism. Use `asyncio` with `aiohttp` and a
    **semaphore** to bound concurrency (e.g. 50) so you don't exhaust sockets or
    get rate-limited. Add retries with backoff, timeouts per request, and gather
    results in chunks. If the client lib is blocking, a `ThreadPoolExecutor` with a
    capped worker count is the pragmatic alternative.

---

## Memory & performance

??? question "A script loads a 20 GB file and OOMs. Fix it."
    Don't materialize it. **Stream** line-by-line or in chunks: iterate the file
    object, or `pandas.read_csv(..., chunksize=...)`, or use a generator pipeline.
    For columnar data use PyArrow/Parquet and process row groups. Keep the working
    set bounded; aggregate incrementally instead of holding everything.

??? question "How do you find what's slow or memory-heavy?"
    Time: `cProfile` + `snakeviz`, or `line_profiler` for hot lines. Memory:
    `tracemalloc` or `memory_profiler`. Don't guess — profile, find the top
    offender, optimize it, remeasure. Often the win is algorithmic (O(n²)→O(n)) or
    avoiding repeated work, not micro-optimizations.

??? question "List vs generator vs NumPy array for a big numeric pipeline?"
    **List**: flexible but memory-heavy and slow for math. **Generator**: lazy,
    flat memory, single-pass, no random access. **NumPy array**: contiguous,
    vectorized C loops, releases the GIL — fastest for numeric work. For big
    numeric transforms, vectorize with NumPy; for streaming ETL, generators.

=== "Vectorize instead of looping"

    ```python
    import numpy as np
    a = np.arange(1_000_000)
    # slow: [x*2 for x in a]  -> fast:
    b = a * 2
    ```

---

## Language internals & gotchas

??? question "Why is a mutable default argument dangerous?"
    Default values are evaluated **once** at function definition, so a mutable
    default (e.g. `def f(x, acc=[])`) is shared across calls and accumulates state.
    Use `None` as the sentinel and create the object inside the function.

    ```python
    def f(x, acc=None):
        acc = [] if acc is None else acc
        acc.append(x); return acc
    ```

??? question "`is` vs `==`, and the small-int/interning trap."
    `==` compares value; `is` compares identity (same object). CPython caches small
    ints (-5..256) and interns some strings, so `is` may accidentally "work" for
    them and then fail for larger values. Always use `==` for value comparison;
    reserve `is` for `None`/singletons.

??? question "Deep vs shallow copy — when does it bite?"
    A shallow copy duplicates the container but shares nested objects, so mutating a
    nested list mutates both. Use `copy.deepcopy` when you need full independence
    (e.g. copying config with nested dicts). Watch the performance cost of deep
    copies on large structures.

??? question "What do decorators and context managers actually give you?"
    **Decorators** wrap a callable to add cross-cutting behavior (timing, retry,
    caching via `functools.lru_cache`, auth) without touching the body.
    **Context managers** (`with`) guarantee setup/teardown even on exceptions —
    files, locks, DB connections, transactions. Both are about clean resource and
    behavior management.

---

## Data engineering flavored

??? question "How would you make an ETL step idempotent and retry-safe?"
    Design so re-running produces the same result: use **upserts/MERGE** keyed on a
    natural or hash key rather than blind inserts; make writes atomic (write to a
    temp location, then swap); checkpoint progress; and use idempotency keys for
    external side effects. Then retries with backoff are safe.

??? question "Pydantic — why use it at boundaries?"
    It validates and coerces external input (API payloads, config, LLM JSON output)
    into typed models, failing fast with clear errors. At system boundaries you
    can't trust input; Pydantic turns "hope it's the right shape" into enforced,
    documented contracts.

---

## Rapid-fire

| Q | A |
|---|---|
| `append` vs `extend`? | append adds one element; extend adds each item of an iterable |
| `sort` vs `sorted`? | sort in-place returns None (lists only); sorted returns a new list (any iterable) |
| Tuple vs list? | tuple immutable/hashable/lighter; list mutable |
| `__str__` vs `__repr__`? | str = human-readable; repr = unambiguous/debug |
| Shallow vs deep copy? | shallow shares nested refs; deep fully duplicates |
| `@staticmethod` vs `@classmethod`? | static = no implicit arg; class = receives `cls` |
| Generator expression vs list comp? | `()` lazy/streaming; `[]` eager/materialized |
| `lru_cache` does what? | memoizes function results by args |

---

## Pitfalls interviewers probe

- Expecting threads to speed up CPU-bound work (GIL).
- Mutable default arguments accumulating state.
- Using `is` for value comparison.
- Loading huge files fully into memory instead of streaming.
- Catching bare `except:` and swallowing errors.
- Micro-optimizing before profiling.

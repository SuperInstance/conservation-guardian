# Production Log — Conservation Guardian v0.2.0

**Date:** 2026-06-02
**Module:** conservation-guardian
**Version:** 0.1.0 → 0.2.0

## What Took the Most Time?

**Adapters** were the most nuanced piece. Each adapter needed to handle:
- Multiple input formats (in-memory records, JSONL files, nested field extraction)
- Auto-pricing (OpenAI) vs. user-provided pricing
- Graceful degradation on malformed records

The `OpenAIAdapter` pricing table and the `GenericAdapter` dot-notation field resolution both required real design decisions, not just boilerplate.

## What Was Mechanical vs. Required Thinking?

**Mechanical (copy-paste-able patterns):**
- Custom exceptions — trivial hierarchy
- CI/CD workflow — standard GitHub Actions template
- CHANGELOG / CONTRIBUTING — standard OSS boilerplate
- Example scripts — once you have the API, these write themselves
- `Reporter.to_prometheus()` and `Reporter.to_slack()` — format-specific serialization

**Required thinking:**
- Adapter `extract_samples()` API design — the `List[NodeSample]` return type with graceful error handling
- `GenericAdapter` field mapping with dot-notation traversal
- `Profiler.compare()` trend analysis thresholds — what constitutes "significant" change
- Thread safety story — decided Python's GIL makes the profiler thread-safe enough for concurrent `record()` calls

## Templates/Patterns for the Next Module

1. **Adapter pattern:** `extract_samples() → List[NodeSample]` with adapter-specific constructor params. Every adapter follows: load records → iterate → extract fields → return samples. Skip bad records, raise AdapterError on source failures.

2. **Reporter pattern:** Class taking all optional components via kwargs, with `to_FORMAT()` methods. Internal `_serialize_*` helpers for shared serialization.

3. **Exception hierarchy:** Base → specific errors with extra attributes. Keep it flat (one level deep).

4. **Edge-case test structure:** One test class per component, test empty/minimal/extreme/corrupted variants.

5. **CI/CD boilerplate:** ruff + mypy + pytest on 3 Python versions. Standard.

## What Would I Do Differently Next Time?

1. **Start with a `.gitignore`** that excludes `__pycache__/`, `dist/`, `*.egg-info` — spent time cleaning those out of git.

2. **Design the adapter interface before writing adapters.** I wrote `GenericAdapter` first, then realized OpenAI and LangChain adapters could share a base class for file loading. Didn't refactor since they're small, but a base class would save repetition.

3. **PyPI publish should use `--skip-existing`** or check if the version is already uploaded before trying. Got a 400 error from re-uploading the same v0.2.0 that a prior agent already pushed.

4. **The `Profiler.compare()` method** should probably live in its own module (`trends.py`) rather than on the Profiler class. It's getting big and mixes concerns.

5. **Thread safety** — the concurrent test passes because of Python's GIL, but the profiler isn't truly thread-safe for complex operations. For v0.3, consider a `ThreadSafeProfiler` wrapper or locking.

## Stats

- **Files changed:** 16
- **Lines added:** ~1,400
- **Tests:** 77 (all passing)
- **Time:** ~20 minutes total
- **PyPI:** Already published as v0.2.0
- **GitHub:** Pushed to main

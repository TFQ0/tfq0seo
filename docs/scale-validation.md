# Offline scale validation

`python -m tfq0seo.benchmark` runs the original 500-page basic fixture without HTTP requests. It measures fixture generation, HTML parsing, the configured static analyzers, site report generation, and verification that every expected URL remains in the report. It does not measure crawling, remote latency, browser rendering, or HTML/CSV/XLSX export.

```sh
# Original default workload
python -m tfq0seo.benchmark --output benchmark.json

# Varied workloads at two sizes, with three measurements of each case
python -m tfq0seo.benchmark --suite --pages 500 2000 --repetitions 3 --timeout-seconds 600 --output scale.json

# One larger workload
python -m tfq0seo.benchmark --scenario link-dense --pages 5000 --timeout-seconds 600 --output links-5000.json
```

`--scenario` selects one workload; `--suite` selects all four. They are mutually exclusive. Repetitions execute sequentially in the same process, ordered by page count, scenario, and repetition. Each measurement creates a fresh analyzer with the standard configuration, disables page caching, and sets `crawler.max_pages` to the fixture size. Full effective configuration is recorded. Library caches and Python allocator state can remain warm, so the raw run order and starting RSS matter when comparing repetitions. There is no discarded warm-up run.

## Workloads

Fixture version 1 generates deterministic `https://benchmark.test/page/{index}` documents. The `.test` references are parsed but never fetched. Each run records a SHA-256 over every generated URL and its UTF-8 HTML, byte and DOM totals, href references, image counts, analyzed word counts, and the number of documents of each variant.

| Scenario | Documents |
| --- | --- |
| `basic` | Original compact English fixture: one heading, one paragraph, and a link to the next page in a ring. Its original markup is unchanged. |
| `content-heavy` | English articles with 12 sections, 24 paragraphs (about 1,200 words), eight images, a 20-row table, stylesheet/script references, and a self canonical. |
| `link-dense` | The basic page plus 32 internal hrefs, four external references, mail and fragment links, and a self canonical. Small fixtures can repeat internal targets; graph edges are deduplicated by the report implementation. |
| `mixed` | Repeats basic, content-heavy, and link-dense documents in that order. |

All supplied page fetch records have HTTP status 200 and complete local HTML. SEO findings are expected; an unfavorable rule result does not mean the analyzer failed. Browser measurements remain unavailable. Offline workload tests prohibit DNS and crawler fetches, including downloads attempted by indirect dependencies. Readability uses only installed resources; its status counts and missing resources are recorded because availability changes the work performed on longer English documents.

## Recorded evidence

The JSON output contains every raw run and per-case median/minimum/maximum summaries. Summary metrics include only complete runs; excluded partial and failed run counts remain explicit. Each run reports successful, partial, failed, skipped, and missing page results. Report verification checks both row count and the exact set of expected URLs, detecting duplicate rows that could conceal missing pages. Site graph node/edge counts, coverage, report summary, and rule coverage are retained.

The environment record includes OS, CPU model and logical/physical counts, RAM, Python, package version, installed direct and optional dependency versions, readability dependency versions, schema/rules/scoring/facts versions, and a hash of package Python source paths and bytes. An absent installed distribution is recorded as `null`. The suite fails if package source changes during the run. Timestamps use UTC.

Elapsed time uses `time.perf_counter()`. Separate analysis and report durations help locate work, while total duration also includes retained-URL verification and benchmark bookkeeping. Process RSS is sampled every 50 ms and at both ends. `memory_sampled_peak_mb` is the largest observed RSS, not a true allocation peak; short-lived allocations can be missed. Start, end, and delta RSS are included. Legacy `memory_used_mb` means RSS delta. Measurements describe the whole Python process, including loaded dependencies and retained library caches.

`--timeout-seconds` is a cooperative per-run deadline. It cancels awaitable work and checks between pages and after reporting, but cannot interrupt synchronous analysis/report work or forcibly terminate worker threads. Use a process supervisor with a hard timeout for unattended runs. A timeout keeps already observed page counts and returns a failed run. Exit codes are 0 for an entirely complete suite, 1 for incomplete/failed runs (including changed source), 2 for invalid CLI arguments, and 130 for interruption.

## Measurements

Final measurements are recorded here after the integrated site-report implementation and offline dependency checks pass. Results are observations for the recorded machine and configuration, not throughput or capacity guarantees for arbitrary websites. Real sites can have larger DOMs, denser graphs, slow remote responses, or different analyzer workloads.

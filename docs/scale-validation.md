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

Measured on 21 September 2026 using Python 3.12.14 on Windows 11 (10.0.26200), an AMD Ryzen 7 7735HS (8 physical / 16 logical CPUs), and 63.21 GiB RAM. Package 3.0.0 used ruleset `2026.09.21`, facts `1.1`, and site analysis `1.0`. Package Python source fingerprint: `077a203b8b1c65de3022f4001a48cc6a1897e89624e9e7e8f967d20f525f4893`.

Each case has two repetitions. The 500-page cases share one process; larger case groups start fresh processes. Full tests and wheel checks finished before measurement. A supervisor set a 1,200-second hard timeout per command, alongside the 360-second cooperative deadline per run. DNS and non-loopback TCP connections were blocked and counted; loopback remained available for asyncio internals.

The measured CLI workloads were:

```sh
python -m tfq0seo.benchmark --suite --pages 500 --repetitions 2 --timeout-seconds 360 --output docs/benchmarks/2026-09-21-python312-500-suite.benchmark
python -m tfq0seo.benchmark --scenario basic --pages 2000 --repetitions 2 --timeout-seconds 360 --output docs/benchmarks/2026-09-21-python312-2000-basic.benchmark
python -m tfq0seo.benchmark --scenario mixed --pages 2000 --repetitions 2 --timeout-seconds 360 --output docs/benchmarks/2026-09-21-python312-2000-mixed.benchmark
```

| Pages | Scenario | Median total seconds (range) | Median report seconds | Median complete pages/second | Highest sampled RSS (MiB) |
| ---: | --- | ---: | ---: | ---: | ---: |
| 500 | basic | 41.45 (40.43–42.48) | 15.99 | 12.07 | 431.44 |
| 500 | content-heavy | 56.84 (56.71–56.97) | 18.20 | 8.80 | 503.59 |
| 500 | link-dense | 53.72 (52.97–54.46) | 19.42 | 9.31 | 514.04 |
| 500 | mixed | 50.78 (50.15–51.42) | 18.07 | 9.85 | 484.86 |
| 2,000 | basic | 165.34 (164.50–166.18) | 63.93 | 12.10 | 1,496.58 |
| 2,000 | mixed | 193.89 (184.03–203.75) | 65.60 | 10.34 | 1,704.72 |

All 12 runs (12,000 page analyses across repetitions) completed with every expected URL retained exactly once, zero partial/failed/skipped/missing results, no timeouts, and zero blocked DNS or external connection attempts. The 500-page link-dense reports retained 16,500 observed graph edges; mixed reports retained 5,812 edges at 500 pages and 23,312 at 2,000 pages. All three artifacts matched the current package source fingerprint, and it remained unchanged during measurement. Fixture hashes and readability statuses also matched between repetitions of each case.

The local NLTK `corpora/cmudict` resource was absent. Longer English documents recorded unavailable readability estimates with explicit missing-resource metadata; basic documents were below the readability word threshold. The measured workload therefore includes content analysis but excludes calculation of those unavailable readability formulas. It also excludes browser metrics, HTTP crawling, and export serialization. These results do not establish network-crawl capacity or maximum supported site size.

Raw evidence uses the `.benchmark` extension with standard JSON content:

- [500 pages, all four scenarios, two repetitions](benchmarks/2026-09-21-python312-500-suite.benchmark)
- [2,000 basic pages, two repetitions](benchmarks/2026-09-21-python312-2000-basic.benchmark)
- [2,000 mixed pages, two repetitions](benchmarks/2026-09-21-python312-2000-mixed.benchmark)

At 2,000 pages, median time was 3.99 times the 500-page basic median and 3.82 times the 500-page mixed median, for four times as many pages. These fixture-specific ratios do not establish general time complexity. The larger mixed timings varied by 19.72 seconds across two repeats; keep repetition and process context when comparing future results.

The 2,000-page reports reached about 1.46 GiB sampled RSS for basic and 1.66 GiB for mixed content. The recorded `max_memory_mb=1024` setting checks process memory during page-processing progress; it is not a hard memory bound on synchronous report assembly. Large reports can exceed it. This is a practical capacity limit to consider before increasing site size. Next, profile report generation and investigate reducing retained objects and copies. Validation stops at 2,000 pages; 5,000 pages were not measured.

The 40 benchmark regression tests passed on Python 3.12 and 3.14, including deterministic real-analyzer fixtures, blocked DNS/fetch attempts, deadline behavior, outcome counting, retained-URL checks, CLI validation, and metadata. Final artifacts were parsed as strict JSON and checked against the current source and their recorded outcomes.

Results are observations for the recorded machine and configuration, not throughput or capacity guarantees for arbitrary websites. Real sites can have larger DOMs, denser graphs, slow remote responses, or different analyzer workloads.

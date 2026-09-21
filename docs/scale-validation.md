# Offline scale validation

## Complete crawl and export pipeline

Use `--pipeline` to measure real HTTP requests against a temporary loopback
server, followed by static analysis, report generation, and atomic JSON, HTML,
CSV, and (when installed) XLSX exports:

```sh
python -m tfq0seo.benchmark --pipeline --scenario mixed --pages 500 2000 --repetitions 2 --timeout-seconds 600 --output pipeline.json
```

The server serves the existing deterministic fixtures. Their canonical origin
is replaced by the loopback origin, and the seed links to every fixture page
so crawl depth does not limit coverage. Asset paths and off-site destinations
are excluded. Robots rules and normal HTTP collection remain enabled; there
is no remote website or browser workload. A hash identifies the transformed
fixtures using a stable origin before the random loopback port is substituted.

Each fresh analyzer disables page caching and retains the standard 1,024 MiB
progress guard. The handoff is bounded to effective fetch concurrency plus
analysis threads. Metrics record that capacity and observed peak, request
counts, page outcomes, exact retained-URL completeness, readability resource
availability, report time, each export's time/size/SHA-256, and total sampled
process RSS. Exports use temporary directories that are removed afterward.
File hashing is included in total time, but file reparsing and browser loading
are not. Regression tests check exported content; the findings controls are
also verified in a browser.
Missing XLSX support is explicitly listed in `unavailable_exports`.

Pipeline and offline timings are different workloads and must not be compared
as equivalent throughput. Both modes now fingerprint package Python and HTML
templates, including the findings JavaScript. Older evidence below fingerprints
Python only. The cooperative deadline covers the crawl and checks between
report/export stages; synchronous work can overrun it. Use a supervisor for a
hard deadline. Incomplete runs and export failures remain failures in the output.

### Pipeline measurements, 21 September 2026

Measured on the same Windows 11 machine described below, using Python 3.12.14
and its full optional dependencies. Each case ran once in a fresh Python
process, with no parallel tests or benchmarks. A supervisor imposed a
900-second hard timeout; each run also used a 600-second cooperative deadline.
Non-loopback DNS and TCP were blocked and counted.

The baseline is an archive of commit
`2d512e4d9c264cf628e9b9a5c94e770d4ef83198`, using the current benchmark harness
to measure the original implementation. Absent buffer counters are recorded
as `null`. The updated runs use this working tree's implementation. The
500-page cases have identical effective configuration, fixture hashes, and
readability availability. Source fingerprints remained stable within each run;
the two updated runs share fingerprint
`adc313afdf65ae80493ad5a9a83de0894e883ea505ba04d14266f8538b77d63c`.

| Implementation | Mixed pages | Crawl + analysis (s) | Report (s) | Exports (s) | Total (s) | Peak sampled RSS (MiB) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original | 500 | 46.36 | 19.60 | 50.85 | 117.26 | 1,398.81 |
| Updated | 500 | 30.00 | 13.58 | 33.53 | 77.66 | 386.50 |
| Updated | 2,000 | 120.98 | 54.90 | 129.61 | 307.31 | 1,297.77 |

At 500 pages, observed peak RSS fell 72.37% and total duration fell 33.77%.
These are single-run observations, not confidence intervals or capacity
guarantees. The updated 2,000-page result measures more work than the older
analysis-only benchmark below, so their elapsed times are not comparable.

All three cases retained every expected URL exactly once, completed every page,
and wrote JSON, HTML, CSV, and XLSX successfully. They made respectively 501,
501, and 2,001 HTTP requests, including one robots request per case, with zero
external network attempts, missing pages, partial/failed/skipped pages, or
timeouts. Both updated runs reached, and stayed within, the 24-slot handoff
capacity (10 fetch slots plus 14 analysis threads on this machine).

The 2,000-page pipeline still peaked at approximately 1.27 GiB, above the
1,024 MiB progress guard. Complete results and the independent report snapshot
remain proportional to site size; bounded HTML buffering is not a hard process
memory limit. Its complete JSON file was 706.82 MiB and HTML file 5.68 MiB.
Streaming avoids retaining those entire serialized files in Python memory.
The local NLTK `cmudict` resource remained absent, with unavailable readability
estimates recorded explicitly, so those formulas were not measured.

Raw evidence (JSON content):

- [Original, 500 mixed pages](benchmarks/2026-09-21-python312-pipeline-before-500-mixed.benchmark)
- [Updated, 500 mixed pages](benchmarks/2026-09-21-python312-pipeline-after-500-mixed.benchmark)
- [Updated, 2,000 mixed pages](benchmarks/2026-09-21-python312-pipeline-after-2000-mixed.benchmark)

Verification included a complete 914-test pass on Python 3.14, the Python 3.12
suite plus the corrected crawler-stub regression, focused export-failure tests,
wheel/sdist validation, and an isolated installed-wheel smoke test. Browser
checks covered all three finding pages, the last page's disabled Next button,
rule/URL search, severity filtering, clearing search, empty results, and inert
untrusted evidence. Raw benchmark artifacts were validated for complete
outcomes, stable source hashes, matching 500-page inputs, and all four exports.

## Historical analysis-only workload

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

# TFQ0SEO

TFQ0SEO is a Python library and CLI for crawling HTML and producing static SEO
reports. It checks metadata, content, technical markup, resource hints, and
links. Reports distinguish failed analyses from unavailable measurements.

## Installation

Python 3.8 or newer is supported. Install from this checkout to use these changes:

```bash
python -m pip install .
# Optional lxml parser, Excel export, and pandas compatibility dependency:
python -m pip install ".[full]"
```

`python -m pip install tfq0seo` installs the published release, which may differ
from this checkout. JSON, HTML, and CSV work with the base installation. XLSX
requires `openpyxl`, included in the `full` extra.

## CLI

```bash
# Single page; JSON goes to stdout when --output is omitted.
tfq0seo analyze https://example.com --format json

# Site crawl with explicit scope limits.
tfq0seo crawl https://example.com --depth 5 --max-pages 500 --concurrent 10 --format html --output report.html

# UTF-8 file: one URL per line; blank lines and # comments are ignored.
tfq0seo batch urls.txt --format json --output batch.json

# XML sitemap or sitemap index.
tfq0seo sitemap https://example.com/sitemap.xml --max-pages 500 --format json --output sitemap.json

# Convert an existing page or site report.
tfq0seo export --input batch.json --format xlsx --output batch.xlsx
```

All commands accept `--config config.yaml` (JSON is also supported). Use
`tfq0seo COMMAND --help` for command options. Incomplete analyses and request
failures return a nonzero exit code; an explicitly requested report is written
first so that failures remain inspectable.

Crawling follows eligible HTTP(S) links in the starting site's hostname/port
scope, including standard HTTP-to-HTTPS transitions. Redirect destinations are
checked against that scope. Explicit `allowed_domains` can expand it.
Robots rules and TLS verification are enabled by default. Queries are retained,
fragments do not create separate crawl targets, and excluded patterns still
apply. Page, depth, response-size, request, and site crawl-time limits bound work.
Reaching a limit is reported; it is not proof that the entire site was analyzed.

## Configuration

CLI precedence is: built-in/profile defaults, configuration file, `TFQ0SEO_`
environment variables, then explicitly supplied command options. An omitted
CLI option does not overwrite a configuration-file value.

```yaml
profile: standard
max_memory_mb: 1024
crawler:
  max_concurrent: 10
  max_connections_per_host: 5
  max_pages: 500
  max_depth: 5
  timeout: 30
  connect_timeout: 10
  read_timeout: 30
  max_crawl_time: 3600
  max_page_size: 10485760
  respect_robots_txt: true
  verify_ssl: true
  delay_between_requests: 0.2
  max_retries: 3
  use_sitemap: true
analysis:
  analysis_mode: standard
  enabled_analyzers: [seo, content, technical, performance, links]
  max_analysis_threads: 4
  check_broken_links: true
  check_internal_links: true
  check_external_links: false
  check_content_uniqueness: true
  target_keywords: []
export:
  primary_format: html
  output_directory: ./reports
  html_template: enhanced
  filename_pattern: "{domain}_{timestamp}_{format}"
```

For example, `TFQ0SEO_CRAWLER_MAX_PAGES=100` overrides the page budget.
`TFQ0SEO_ANALYSIS_ENABLED_ANALYZERS=seo,technical` selects those analyzers.
Lists also accept JSON arrays; mappings use JSON objects. Booleans accept
`true`/`false`, `yes`/`no`, and `1`/`0`. String settings remain strings.

Profiles are `quick`, `standard`, `deep`, `enterprise`, `dev`, and `custom`.
`quick` selects SEO and technical analysis with a smaller crawl budget. `deep`
increases crawl limits and bypasses the analysis cache. `enterprise` changes
concurrency and crawl budgets; it does not enable a separate service or browser.
Explicit values override profile defaults.

In Python, `apply_profile()` replaces values controlled by the selected preset.
Use `merge({'profile': ...})` to change preset defaults while retaining explicit
overrides. Applying `custom` only changes the label.

Other implemented settings include crawler headers/user agent, redirects,
rate limits, retry statuses/backoff, domain/scheme/exclusion filters, sitemap
discovery, proxy, connection pooling, DNS/robots cache TTLs, and bounded analysis
cache size/TTL. Analysis supports weighted category scores and bounded optional
external link checks. `Config.SUPPORTED_FIELDS` lists the active component
settings in [config.py](tfq0seo/core/config.py).

Unknown keys, invalid types, conflicting aliases, and retired configuration
fields fail validation. Active dataclasses and saved configurations expose
supported settings only. JavaScript execution, HTTP/2 selection, background
monitoring, webhooks, email delivery, PDF export, and `dry_run` remain
unimplemented. Use the explicit `Config.migrate_dict()` migration for older
configuration files; it removes only retired values matching their historical
defaults and rejects unsupported requested behavior. See the
[configuration migration guide](docs/configuration-migration.md) before upgrading.

## Python API

```python
import asyncio

from tfq0seo import SEOAnalyzer
from tfq0seo.core.config import Config
from tfq0seo.exporters.base import ExportManager


async def main():
    config = Config.from_dict({"crawler": {"max_pages": 100}})
    analyzer = SEOAnalyzer(config)
    pages = [page async for page in analyzer.crawl_site("https://example.com")]
    report = analyzer.generate_site_report(pages)
    ExportManager(config.export).export(report, "json", "report.json")


asyncio.run(main())
```

`analyze_url(url)` returns one page result. `analyze_urls(urls)` is an async
iterator for a batch. `analyze_sitemap(url)` returns a list after discovery and
analysis. `generate_batch_report()` and `generate_site_report()` aggregate page
records. Use the completed report for link health: streamed pages may precede
observations of their linked targets. Reusing an analyzer starts a fresh run
while retaining its bounded analysis cache.

## Interpreting results

Results carry `schema_version: "1.0"`; compatible dictionary contracts are
defined in [models.py](tfq0seo/core/models.py).

- Page `status` is `complete`, `partial`, `error`, or `skipped`. Fetch failures
  retain their URL, status, and error. Analyzer failures have an error and a
  `null` score. Truncated HTML produces partial coverage.
- `coverage` identifies enabled/completed/failed analyzers and content
  completeness. Site `summary` records page outcomes, crawl completeness,
  limits, and discovery failures. Successful static analysis does not mean
  every linked URL was checked.
- Site `pages.detailed` retains every usable page; `pages.failed` and
  `pages.skipped` retain other outcomes. HTML pagination does not truncate the
  underlying report. CSV and XLSX include all page outcomes.
- Scores are weighted static-rule heuristics, not search ranking predictions,
  validated business KPIs, or an exhaustive accessibility audit. Informational
  content heuristics do not lower scores.
- `load_time` and `html_fetch_time` describe observed HTTP HTML retrieval.
  Browser load time, Core Web Vitals, TTFB, asset download sizes, and other
  unobserved measurements are `null`/not measured. JavaScript is not rendered.
- Broken links require an observed HTTP error. Unvisited targets remain
  unchecked. External checks are opt-in and bounded; connection failures are
  retained separately from HTTP error evidence.
- JSON-LD checks inspect local syntax/shape. Language/readability checks are
  conservative and may be unavailable. They do not validate eligibility for
  search-engine features or infer authority and link velocity.
  Readability never downloads dictionaries at runtime. If the installed
  textstat backend needs unavailable local NLTK `corpora/cmudict` data, estimates
  remain `null`, with an explicit unavailable status and missing-resource reason.

HTML escapes page-supplied text and restricts clickable URLs to HTTP(S). CSV and
XLSX neutralize formula-like text. The enhanced HTML report uses optional
Chart.js from a CDN for charts; its page table remains usable without it.

## Site-wide canonical and link analysis

Completed site reports include `site_analysis`, derived from the supplied page
inventory without additional network requests. Canonical observations include
eligible HTML declarations and HTTP `Link` headers. HTML targets use the
document base; header targets use the response URL. Declarations outside the
HTML head, alternate qualifiers, and other header anchor contexts remain
recorded as ineligible. Malformed headers, missing facts, and incomplete HTML
retain uncertainty.

The report identifies conflicting targets, canonical chains and cycles,
observed redirects, HTTP errors at declared targets, and observed `noindex`
directives at targets. A self-reference is not a cycle. Unfetched and
unavailable destinations are unverified. Chain records store the immediate
target, terminal, hop count, and cycle identifier; shared cycles are stored
once, avoiding repeated full paths in large reports.

The internal-link graph retains distinct source/target pairs, nofollow hints,
incoming/outgoing counts, connected groups, and shortest observed link depth.
Redirect aliases resolve to observed final URLs; query strings remain distinct.
Depth starts at the crawl's entry URL, or observed homepages when aggregating a
batch. Without an entry page, depth and reachability remain unavailable. A page
with no observed incoming links is a candidate for investigation, not proof of
an orphan page. Self links do not count as incoming links, and nofollow hints
do not remove edges from this observational graph.

Site findings have registered `site.*` rule IDs, evidence, references, and zero
penalty. They appear in site issues and recommendations without changing page
scores or rewriting historical page evidence. Page rule coverage remains
separate from graph coverage. HTML includes the complete observations table;
CSV/XLSX page rows include canonical and link metrics; JSON retains the graph
and cycle records. These checks do not determine a search engine's selected
canonical or a page's actual index status. The supporting guidance is
[Google's canonical documentation](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
and [link guidance](https://developers.google.com/search/docs/crawling-indexing/links-crawlable).

## Shared facts and result contracts

Each page analysis extracts one `PageFacts` snapshot before dispatching the five
analyzers. They reuse its metadata, headings, robots directives, document base,
images, scripts, links, and text. Specialized checks remain in their existing
analyzer modules. The snapshot is immutable, and collection access returns
independent values so concurrent analyzers cannot alter one another's evidence.

The original analyzer call signatures remain supported. Standalone callers can
also share extraction explicitly:

```python
from bs4 import BeautifulSoup
from tfq0seo.page_facts import extract_page_facts
from tfq0seo.analyzers.seo import analyze_seo
from tfq0seo.analyzers.content import analyze_content

soup = BeautifulSoup('<html lang="en"><title>Example</title><h1>Example</h1></html>', 'html.parser')
url = 'https://example.test/'
facts = extract_page_facts(soup, url, headers=None)
seo = analyze_seo(soup, url, facts=facts)
content = analyze_content(soup, url, facts=facts)
```

Keep the source document unchanged while using its snapshot. A supplied
snapshot must belong to the same document, URL, and explicit header/bot context.
`headers=None` means unavailable; `{}` means an observed empty header mapping.
Repeated response headers retain every value. Fetch timings can remain `null`
and describe their existing network stages rather than browser measurements.

Page results include an additive `page_facts` record with extraction version,
provenance, hashes, counts, and shared observations. Its default export omits raw
response-header values, full HTML/text, and script bodies. The extraction
version also participates in cache identity.

[models.py](tfq0seo/core/models.py) defines fetch, rule, analyzer, page, and site
contracts and re-exports `PageFacts`. Malformed supplied fields raise
`ContractError` with a field path before analysis or export. Invalid analyzer
outputs become explicit analyzer errors with unavailable scores and are not
cached. Rule validation checks evidence, provenance, applicability, and nested
observations before merging or scoring.

Report validation checks present fields without rewriting historical rule IDs,
scores, or unknown extension fields. New producer envelopes receive stricter
checks. Non-finite numbers and unsupported Python objects are rejected rather
than silently converted to strings; invalid reports are rejected before opening
an output file. JSON schema version `1.0` and existing report layouts remain
supported. Validators are available in
[report_contracts.py](tfq0seo/core/report_contracts.py).

## Rules, applicability, and scoring

The rule registry in [rules.py](tfq0seo/rules.py) contains immutable definitions
registered by each analyzer. Every active rule has a stable ID, a category owner,
severity, recommendation, applicability description, supporting reference URLs,
and a review date. The reference supports the observation or guidance; numeric
penalties are TFQ0SEO policy, not weights supplied by search engines.

Each analyzer returns `rule_results` with structured evidence and explicit
`pass`, `fail`, `informational`, `unknown`, `not_applicable`, or `error` outcomes.
`issues` contains failed checks and informational observations. Unknown and
inapplicable evaluations include a reason and remain visible in rule coverage;
they are never silently counted as passes. Disabling an analyzer does not imply
that its rules passed. A rule execution error makes the page partial and avoids
caching that incomplete analysis.

Scoring policy **2.0** deducts 15, 7, or 3 points for a failed, applicable,
scored critical, warning, or notice rule. Each rule is deducted once per page,
even when multiple analyzers observe it. Its registered owner receives the
deduction; if that analyzer is unavailable, the first reporting analyzer in the
fixed order `seo, content, technical, performance, links` receives it. Category
scores start at 100 and floor at zero. The overall score uses the configured
category weights, normalized across available categories. Zero weights are
respected. Site scores average the available page scores.

Page `scoring.deductions` records rule IDs, observers, category attribution, and
penalties. Recommendations use the registry ID rather than matching message
text. Duplicate findings retain all observations, and site issue groups retain
evidence for every affected page. Diagnostic sub-scores inside analyzer data are
not additive components of the overall score.

Informational, unknown, inapplicable, and errored evaluations incur no penalty.
For example, an observed `noindex` directive is reported without assuming it is
unintentional. Optional social metadata, keyword-density targets, metadata
length heuristics, and unmeasured browser effects are not universal failures.
A high score therefore describes the scored observations and must be read
alongside coverage; it does not establish that unavailable checks passed.

JSON keeps schema version `1.0` with additive rule fields and records independent
ruleset/scoring versions. Scores from policy 2.0 are not directly comparable to
older reports. Cache identity includes both versions. Reference review dates
record an actual review, not automatic proof that a document is still current.

When extending an analyzer, register the definition, evaluate it with
`RuleCollector.check`, supply the observed evidence and applicability, and derive
findings/recommendations/scores through the shared helpers. Test positive,
negative, unavailable, and inapplicable cases. Reuse shared IDs for the same
underlying condition and increment the ruleset version when changing rule
behavior; increment the scoring version when changing the deduction policy.

## Development and verification

```bash
python -m venv .venv
# Activate .venv using your shell's command, then:
python -m pip install -e ".[test,full]" "setuptools>=61" build wheel twine
python -m pytest

python -m build --no-isolation
python -m twine check dist/*
# Install the generated .whl with --no-deps --force-reinstall, then:
python -I tests/wheel_smoke.py

# Reproducible offline analysis/report workload; no HTTP requests:
python -m tfq0seo.benchmark --pages 500 --output benchmark.json
# Compare varied fixtures and retain repeated measurements and environment:
python -m tfq0seo.benchmark --suite --pages 500 2000 --repetitions 3 --timeout-seconds 600 --output scale.json
```

Tests cover analyzers, configuration precedence, crawl scope/robots/retries,
timeouts and cancellation, report completeness, CLI failure handling, export
safety, and a real 500-page crawl against a local HTTP fixture. Tests block
non-loopback socket connections and do not depend on public websites.

The benchmark measures fixture parsing, static analysis, and aggregation with
the analysis cache disabled. It reports complete/partial/failed/skipped counts,
successful-page throughput, elapsed time, and sampled process RSS. A sampled
maximum can miss short memory peaks. Results depend on the machine and fixture;
they are not browser-performance measurements or a production-site capacity
guarantee. Basic, content-heavy, link-dense, and mixed scenarios retain every
raw measurement, workload/source fingerprints, full effective configuration,
dependency versions, and per-case summaries. See the
[scale validation guide and recorded measurements](docs/scale-validation.md)
for workload definitions, resource limits, and measured results. Network
benchmark functions remain explicit opt-in Python APIs.

GitHub Actions runs regression tests and distribution checks across Python 3.8,
3.12, and 3.14, with Windows and Linux jobs and base/optional dependencies. The
release workflow requires these checks and a release tag matching `v` plus the
package version before publishing.

## Publishing to PyPI

Releases use [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
through GitHub Actions. No PyPI API token or password is used by the workflow.
Tests and the package build run without OIDC permission. The separate `deploy`
job downloads the validated distributions and is the only job with
`id-token: write`, which allows it to request a short-lived publishing identity.

Complete this one-time setup before publishing a release:

1. In the `TFQ0/tfq0seo` GitHub repository, open **Settings → Environments**
   and create or verify the environment named `pypi`. Restrict its deployment
   tags to `v*`; optionally require a reviewer if available for the repository.
2. On PyPI, open **Your projects → tfq0seo → Manage → Publishing** and add a
   GitHub publisher to the existing project with these exact values:

   | PyPI field | Value |
   | --- | --- |
   | Owner | `TFQ0` |
   | Repository name | `tfq0seo` |
   | Workflow name | `tfq0seo-publish.yml` |
   | Environment name | `pypi` |

   The workflow field is the filename, without `.github/workflows/`, rather
   than the display name `Publish to PyPI`. The environment must match the
   workflow. See [PyPI's publisher setup guide](https://docs.pypi.org/trusted-publishers/adding-a-publisher/).
3. Commit and push the release workflow and its reusable
   `.github/workflows/tests.yml` together with the intended package changes.
   Keep the registered workflow filename unchanged.

For each release, update `tfq0seo/__init__.py` to a new, unused package version,
commit it, then create and push a tag that is `v` followed by that version
(for example, `v3.0.0`). Pushing a `v*` tag triggers the workflow; no package-name
prefix or GitHub release is required. Branch pushes, other tag names, and tag
deletions do not publish. The version check reads the built wheel's metadata
without installing or hard-coding the package name. Approve the `pypi`
deployment if a reviewer is required. Tests and distribution checks must pass
before the upload starts.

After the first successful Trusted Publishing release, revoke the old PyPI
upload token and remove its GitHub Actions secret if it is no longer used by
another workflow. Do not add `username` or `password` inputs to the publishing
action; they would select credential-based authentication instead of OIDC.

Local tests cannot exercise GitHub's OIDC exchange with PyPI. The first release
run verifies the registered publisher end to end. If PyPI reports an invalid
publisher, compare the repository owner, repository name, workflow filename,
and environment against the values above before retrying. PyPI does not allow
an uploaded distribution filename to be reused, so retries after a successful
upload require checking what was already published.


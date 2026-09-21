# TFQ0SEO

TFQ0SEO is a Python library and CLI for crawling HTML and producing static SEO
reports. It checks metadata, content, technical markup, resource hints, and
links. Reports distinguish failed analyses from unavailable measurements.

## Installation

Python 3.8 or newer is required. Install or upgrade the published package from
PyPI:

```bash
python -m pip install --upgrade tfq0seo
```

The base installation supports JSON, HTML, and CSV reports. For Excel (XLSX)
export and the optional lxml parser, install the `full` extra instead:

```bash
python -m pip install --upgrade "tfq0seo[full]"
```

The `full` extra includes `openpyxl`, `lxml`, and the pandas compatibility
dependency. Keep the quotes around the package name with extras.

To isolate dependencies, optionally create and activate a virtual environment
**before** running either install command:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux with Bash or Zsh:

```bash
source .venv/bin/activate
```

Verify the installation:

```bash
tfq0seo --version
tfq0seo --help
```

If your shell cannot find `tfq0seo`, use `python -m tfq0seo.cli` in place of
`tfq0seo` in any command below, using the same Python environment where you
installed the package:

```bash
python -m tfq0seo.cli --help
```

This README describes the current source checkout, which can include improvements
not yet published to PyPI. To use this checkout, run the following from the
repository root; omit `[full]` if you only need the base dependencies:

```bash
python -m pip install ".[full]"
```

## Quick start

Replace `https://example.com` with your site's URL. Analyze one page and open
the resulting `page.html` in a browser:

```bash
tfq0seo analyze https://example.com --format html --output page.html
```

For an initial site audit, start with a modest page budget and concurrency:

```bash
tfq0seo crawl https://example.com --depth 3 --max-pages 100 --concurrent 5 --format html --output site.html
```

Inspect the report's coverage and failed/skipped pages before interpreting its
scores. Increase the limits when you need broader coverage. TFQ0SEO analyzes
the HTML returned by the server; it does not render JavaScript.

## CLI

Choose the command according to the URLs you want to analyze:

| Command | Use it for |
| --- | --- |
| `analyze URL` | One page, such as a landing page or a page you just changed. |
| `crawl URL` | Discovering and analyzing pages within a site's configured scope. |
| `batch urls.txt` | A specific list of pages, such as product pages or a regression checklist. |
| `sitemap URL` | Analyzing eligible URLs from an XML sitemap or sitemap index. |
| `export` | Converting a saved JSON report to HTML, CSV, or XLSX without crawling again. |

Use `--format` to select the report type and `--output` to select its destination;
the filename extension does not select the format. `crawl`, `batch`, and
`sitemap` require an output path. For a single page, explicit JSON output goes
to stdout when `--output` is omitted:

```bash
tfq0seo analyze https://example.com --format json
```

All commands accept `--config config.yaml` (JSON configuration is also
supported). Profiles, keywords, timeouts, HTML templates, and external-link
checks are configured in that file. For the available options:

```bash
tfq0seo crawl --help
tfq0seo analyze --help
tfq0seo batch --help
tfq0seo sitemap --help
tfq0seo export --help
```

Incomplete analyses and request failures return a nonzero exit code; an
explicitly requested report is written first so that failures remain inspectable.
A low SEO score alone does not cause a nonzero exit code. In scripts and CI,
retain generated reports even when the analysis command fails.

## Practical audit commands

### Audit once, create several report formats

Save the full JSON report as your reusable audit record, then create a browser
report and spreadsheet exports from the same results:

```bash
tfq0seo crawl https://example.com --depth 5 --max-pages 500 --concurrent 5 --format json --output audit.json
tfq0seo export --input audit.json --format html --output audit.html
tfq0seo export --input audit.json --format csv --output audit.csv
tfq0seo export --input audit.json --format xlsx --output audit.xlsx
```

The export commands do not fetch pages again. Install `tfq0seo[full]` for an
actual XLSX workbook; without `openpyxl`, the exporter falls back to CSV. JSON
preserves detailed evidence and graph data; CSV/XLSX provide page-oriented rows.

### Check a selected set of important pages

Save this as `urls.txt`, replacing the example URLs with your own. The file must
be UTF-8, with one URL per line; blank lines and `#` comments are ignored:

```text
# Priority pages
https://example.com/
https://example.com/products/widget
https://example.com/contact
```

```bash
tfq0seo batch urls.txt --concurrent 5 --format json --output priority-pages.json
tfq0seo export --input priority-pages.json --format html --output priority-pages.html
```

This analyzes the supplied URLs rather than discovering a site through links.
For lists larger than the configured page budget, set `crawler.max_pages` in a
configuration file and pass it with `--config`.

### Audit URLs listed in a sitemap

Use the sitemap workflow to include eligible listed pages that a link-based
crawl might not discover:

```bash
tfq0seo sitemap https://example.com/sitemap.xml --max-pages 500 --format json --output sitemap-audit.json
tfq0seo export --input sitemap-audit.json --format html --output sitemap-audit.html
```

Sitemap indexes are supported. Scope, robots rules, and resource limits still
apply. Set `crawler.max_concurrent` in a configuration file to control this
command's concurrency.

### Run a deeper audit with keyword and external-link checks

Save the following as `deep-audit.yaml`. It uses all five analyzers, bypasses
the analysis cache, and sets explicit crawl limits. Replace the example keywords
with phrases relevant to your content:

```yaml
profile: deep
crawler:
  max_pages: 1000
  max_depth: 10
  max_concurrent: 5
  max_connections_per_host: 2
  delay_between_requests: 0.5
  max_crawl_time: 3600
  respect_robots_txt: true
analysis:
  max_analysis_threads: 4
  target_keywords: [technical SEO, site audit]
  check_broken_links: true
  check_internal_links: true
  check_external_links: true
  max_external_links_per_page: 20
  external_link_timeout: 10
export:
  html_template: optimized
```

```bash
tfq0seo crawl https://example.com --config deep-audit.yaml --format json --output deep-audit.json
tfq0seo export --input deep-audit.json --config deep-audit.yaml --format html --output deep-audit.html
```

External-link checks make additional HTTP requests and can increase runtime;
set `check_external_links: false` when they are unnecessary. The `deep` profile
expands static analysis coverage through its crawl limits and cache policy; it
does not enable browser rendering. Larger page budgets also need more memory
for retained results and report creation.

### Crawl scope and limits

Crawling follows eligible HTTP(S) links in the starting site's hostname/port
scope, including standard HTTP-to-HTTPS transitions. Redirect destinations are
checked against that scope. Explicit `allowed_domains` can expand it.
Robots rules and TLS verification are enabled by default. Queries are retained,
fragments do not create separate crawl targets, and excluded patterns still
apply. Page, depth, response-size, request, and site crawl-time limits bound work.
Reaching a limit is reported; it is not proof that the entire site was analyzed.

Robots path matching supports `*`, terminal `$`, percent-encoded paths, and
case-sensitive longest-match precedence, with `Allow` winning ties. Matching
user-agent groups are combined; `*` groups apply when no specific group matches.
Sitemap discovery, robots caching, and crawl pacing retain their existing behavior.

## Configuration

CLI precedence is: built-in/profile defaults, configuration file, `TFQ0SEO_`
environment variables, then explicitly supplied command options. An omitted
CLI option does not overwrite a configuration-file value.

For a reusable standard audit, save this as `audit.yaml` and pass
`--config audit.yaml` to an analysis or export command:

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
  html_template: optimized
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
settings in [config.py](https://github.com/TFQ0/tfq0seo/blob/main/tfq0seo/core/config.py).

Site analysis bounds the fetch-to-analysis handoff to effective crawler
concurrency plus `analysis.max_analysis_threads`. A slot remains occupied until
analysis releases the parsed HTML. Slow analysis therefore pauses new fetches;
`crawl_stats.result_buffer_capacity` and `result_buffer_peak` expose this bound.
Standalone `Crawler.crawl_site()` still returns its collected fetch records.

`max_memory_mb` is a sampled process-RSS guard checked during page-analysis
progress, not a hard allocation limit. Complete analyzed results and report
snapshots still grow with site size, and synchronous report assembly can exceed
the guard. Budget for the complete report; see the scale validation results below.

Unknown keys, invalid types, conflicting aliases, and retired configuration
fields fail validation. Active dataclasses and saved configurations expose
supported settings only. JavaScript execution, HTTP/2 selection, background
monitoring, webhooks, email delivery, PDF export, and `dry_run` remain
unimplemented. Use the explicit `Config.migrate_dict()` migration for older
configuration files; it removes only retired values matching their historical
defaults and rejects unsupported requested behavior. See the
[configuration migration guide](https://github.com/TFQ0/tfq0seo/blob/main/docs/configuration-migration.md) before upgrading.

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
defined in [models.py](https://github.com/TFQ0/tfq0seo/blob/main/tfq0seo/core/models.py).

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
  Provision the `cmudict` corpus during environment setup if you need those
  estimates; see [NLTK's data installation guide](https://www.nltk.org/data.html).

HTML escapes page-supplied text and restricts clickable URLs to HTTP(S). CSV and
XLSX neutralize formula-like text. The enhanced HTML report uses optional
Chart.js from a CDN for charts; its page table remains usable without it.

The optimized site template keeps a short issue summary and adds **All findings**:
search messages, rule IDs, categories, and affected URLs; filter by severity;
and browse 20 findings per page. Details expose complete evidence on demand.
This view runs locally in the report and requires JavaScript, without Chart.js
or network access. JSON retains every finding as well.

JSON, HTML, CSV, and XLSX exports write a temporary file beside the destination,
close it successfully, and then atomically replace the destination. Rendering,
serialization, write, and replacement failures preserve an existing report and
remove the temporary file. JSON and HTML stream their output to reduce memory
use. Atomic replacement does not promise durability through a power failure.

Generated site reports remain independent of their input page records. Views
within one report can share nested evidence to avoid redundant copies; treat
report evidence as read-only or deep-copy a view before editing it independently.

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


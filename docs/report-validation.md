# HTML reporting and crawl-speed verification

Measured on 25 September 2026 using the local source checkout, Python 3.14.6,
Windows, and the owner's authorized site `https://siwar.ksaa.gov.sa/`.
These observations describe this run and environment, not a capacity guarantee.

## Reproducing the reported fast exit

The supplied command omitted the required URL:

```sh
tfq0seo crawl --depth 5 --max-pages 500 --concurrent 5 --format json --output audit.json
```

Invoking it through `python -m tfq0seo.cli` exited with code **2** after **1.56
seconds**, with `Error: Missing argument 'URL'.` No crawl or report write occurs
in that case. This explains the command as supplied; it does not establish what
happened in a different invocation that included a URL.

## Live-site observations

Two real, unauthenticated crawls respected robots.txt and disabled analysis
caching. The first used a 110-page ceiling, concurrency 3, and a 120-second
crawl deadline. It completed 18 pages in 110.76 seconds; report assembly took
0.44 seconds and JSON/HTML exports 0.84 seconds (112.04 seconds overall).

The second used the supplied depth, page ceiling, and concurrency with the URL
added:

```sh
python -m tfq0seo.cli crawl https://siwar.ksaa.gov.sa/ --depth 5 --max-pages 500 --concurrent 5 --config reports/siwar-validation/live-config.yaml --format json --output reports/siwar-validation/audit.json
python -m tfq0seo.cli export --input reports/siwar-validation/audit.json --format html --output reports/siwar-validation/audit.html
```

The local verification configuration limited requests to 15 seconds (10 seconds
for connecting), one retry, and a 180-second crawl deadline, with caching off.
No robots or TLS safeguards were disabled.

To reproduce it, save this as `reports/siwar-validation/live-config.yaml`:

```yaml
crawler:
  max_crawl_time: 180
  timeout: 15
  connect_timeout: 10
  read_timeout: 15
  max_retries: 1
  cache_enabled: false
```

| Observation | Second run |
| --- | ---: |
| Configured page ceiling | 500 |
| Recorded URLs / analyzed HTML pages | 18 / 18 |
| Complete / partial / failed / skipped pages | 18 / 0 / 0 / 0 |
| HTTP requests | 23: 18 pages, 4 sitemap requests, 1 robots request |
| Analysis cache hits | 0 |
| Distinct recorded text hashes | 14 |
| Crawl + analysis elapsed | 110.67 s |
| Applied robots crawl delay | 5 s |
| Mean / median HTML network time | 0.100 / 0.064 s |
| Minimum / maximum HTML network time | 0.035 / 0.444 s |
| HTML export from saved JSON | 0.41 s |

The five-second delay came from the site's robots.txt. Fast HTTP responses do
not imply a two-second audit: pacing, discovery, and analysis are separate work.
The page ceiling is not an inventory of the website, and static crawling does
not render JavaScript or enumerate every dictionary/search result.

Both runs recorded discovery gaps: an excluded `/login` sitemap entry and
document-type parse errors at the three guessed sitemap locations
`/sitemap_index.xml`, `/sitemap-index.xml`, and `/sitemaps/sitemap.xml`. The report
therefore remains **partial**, despite all 18 fetched HTML pages completing
analysis. No claim of complete site coverage is made.

The second crawl saved its JSON successfully. The surrounding measurement
script then failed while decoding UTF-8 console output with Windows cp1252, so
its total CLI wall time was not retained. The HTML was subsequently exported
from that saved JSON without recrawling; elapsed crawl time above is the tool's
monotonic measurement. Local artifacts are in `reports/siwar-validation/`
(ignored by Git), including `audit.html`, `audit.json`, `measurements.json`,
`before-measurements.json`, and the observed `robots.txt`.

## Regression checks

- A 110-page loopback crawl compares every reported request with the HTTP
  server log, verifies URL retention, and includes a failed response and a
  skipped non-HTML response. Neither inflates analyzed-page throughput.
- Separate sitemap discovery and page-fetch sessions contribute to request
  totals. Imported report records inherit neither stale timings nor budgets.
- HTML checks preserve all 506 records in a large report across all three
  templates, retain missing measurements, and escape untrusted page content.
- Browser checks exercise 45-record pagination (20/20/5), search, outcome
  filtering, numeric sorting, empty results, and expanded page details.
  Injected HTML remains text and unsafe URL schemes are not clickable.

```sh
python -m pytest tests/test_app.py tests/test_exporters.py tests/test_cli.py
```

The complete suite passed **921 tests** in 239.04 seconds on Python 3.14.6.
Wheel and source builds passed Twine validation; the installed wheel passed
the isolated smoke test, including all report templates and shared partials.
Packaged Python/HTML files matched the working tree byte-for-byte. Modified
Python modules also passed Python 3.8 grammar parsing (not a Python 3.8 runtime
test). Interactive browser checks used a loopback HTTP preview; a direct
`file://` preview was blocked by the browser tool's URL policy.

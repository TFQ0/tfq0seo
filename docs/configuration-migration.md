# Configuration migration for 3.0.0

The configuration schema now contains only settings used by the application.
Previously, saved configurations included options for unimplemented features.
Those fields have been removed from the dataclass constructors, validated input,
and serialized configuration. The `MonitoringConfig` class and the entire
`monitoring` section have also been removed.

Normal loading does not silently discard these fields. `Config.from_dict()`,
`Config.from_file()`, `Config.from_env()`, and `Config.merge()` reject retired keys,
including keys set to their historical defaults. Errors identify the setting and
point to explicit migration. Remove corresponding retired environment variables
before running the CLI; the CLI does not migrate configuration automatically.

## Explicit migration

`Config.migrate_dict(data)` returns `(canonical_data, warnings)`:

- `canonical_data` is a new dictionary containing validated, canonical overrides.
  It preserves supplied active settings and profile selection without inserting
  unspecified defaults. It can be passed to `Config.from_dict()` or serialized.
- `warnings` is a list of strings identifying removed retired defaults and
  canonicalized aliases. Messages do not include supplied values.
- Retired fields are removed **only when their supplied value matches the
  historical default below and has a valid historical type**. For example,
  `false` is not accepted as an integer zero, and `0` is not accepted as `false`.
  Float settings accept finite integer equivalents; integer settings reject
  floats. Lists and dictionaries must match their complete historical contents.
- Unknown keys, malformed sections, conflicting aliases, invalid active settings,
  and nondefault retired values raise `ValueError`. No partial result is returned.
- The input is not modified. Migration performs no file writes, network requests,
  directory creation, or delivery actions.

Read the warnings before using the migrated configuration. Write a separate file
to keep the original available for review:

```python
import json
from pathlib import Path
from tfq0seo.core.config import Config

legacy_path = Path("config.json")
legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
canonical, warnings = Config.migrate_dict(legacy)
for warning in warnings:
    print(warning)

# Exclusive creation prevents overwriting an existing configuration.
with Path("config.v3.json").open("x", encoding="utf-8") as handle:
    json.dump(canonical, handle, indent=2, allow_nan=False)

config = Config.from_dict(canonical)
```

For YAML, use `yaml.safe_load()` to obtain the input dictionary and
`yaml.safe_dump()` to serialize `canonical`. `Config.save()` remains available
for saving a fully resolved configuration; serializing `canonical` instead keeps
unspecified profile defaults unspecified for subsequent profile changes.

Migration does not discard a nondefault retired field just because its parent
feature is disabled. For example, an old `export.smtp_password` value causes an
error even when `export.send_email` is `false`. Review the unsupported behavior,
remove it explicitly from a copy of the input, and rerun migration. Credentials
in active settings such as `crawler.custom_headers` and `crawler.proxy` remain in
the returned data; value-free diagnostics do not redact the configuration itself.

## Supported settings and aliases

The active global settings are `crawler`, `analysis`, `export`, `profile`,
`version`, `debug`, `continue_on_error`, and `max_memory_mb`. `debug` is preserved
as profile metadata, including the development profile default. It does not
configure Python logging. `version` is configuration/report metadata, not a
package version override.

Working crawler aliases remain accepted by dictionary, file, environment, and
merge entry points. Serialized configurations use canonical keys:

| Alias in `crawler` | Canonical key | Notes |
| --- | --- | --- |
| `concurrent_requests` | `max_concurrent` | `null` means no alias override; still accepted by `CrawlerConfig` directly. |
| `max_content_length` | `max_page_size` | Maximum response bytes. |
| `retry_attempts` | `max_retries` | Number of retries. |
| `adaptive_throttle` | `adaptive_delay` | Boolean. |
| `follow_sitemap` | `use_sitemap` | Boolean. |

Supplying an alias and its canonical key with different values is an error.
Migration reports alias normalization; ordinary loading continues to accept these
aliases without requiring migration.

Active analysis settings are `enabled_analyzers`, `analysis_mode`,
`parallel_analysis`, `max_analysis_threads`, `check_external_links`,
`check_internal_links`, `check_broken_links`, `max_external_links_per_page`,
`external_link_timeout`, `target_keywords`, `check_content_uniqueness`, and
`score_weights`. Analyzer selection and supported modes remain available;
individual retired check flags do not control rule execution or thresholds.

Active export settings are `formats`, `primary_format`, `html_template`,
`output_directory`, and `filename_pattern`. Supported formats are `html`, `json`,
`csv`, and `xlsx`; `OutputFormat.PDF`, `OutputFormat.MARKDOWN`, and
`OutputFormat.XML` were removed. Unsupported format requests are rejected and
are not rewritten by migration.

`Config.SUPPORTED_FIELDS` lists the active fields for each component. The crawler
entry includes the working `concurrent_requests` constructor alias; the
serialized crawler configuration contains `max_concurrent` instead.

## Retired crawler settings

Every key in this table is under `crawler`. Values use JSON notation.

| Removed key | Historical default |
| --- | --- |
| `semaphore_limit` | `30` |
| `total_timeout` | `300` |
| `rotate_user_agents` | `false` |
| `user_agent_list` | `[]` |
| `redirect_cache_ttl` | `3600` |
| `include_query_strings`, `normalize_urls` | `true` |
| `parse_javascript`, `execute_javascript` | `false` |
| `wait_for_javascript` | `0.0` |
| `compress_stored_html`, `prioritize_sitemap_urls` | `true` |
| `use_http2` | `false` |

Use the existing `max_concurrent` to control concurrency and `max_crawl_time` for
the crawl deadline. These are not automatic renames of `semaphore_limit` or
`total_timeout`: the retired options never controlled the crawler, and the active
settings may already be present with different values. URL identity follows the
shared URL resolver; there is no toggle to remove query strings. JavaScript
execution, user-agent rotation, HTTP/2 selection, and the other removed behaviors
have no configuration replacement.

## Retired analysis settings

Every key in this table is under `analysis`.

| Removed key | Historical default |
| --- | --- |
| `validate_anchors` | `true` |
| `check_images`, `check_image_optimization`, `check_alt_text`, `check_image_dimensions` | `true` |
| `max_image_size_kb` | `500` |
| `min_content_length` | `100` |
| `max_content_length` | `100000` |
| `optimal_content_length` | `1500` |
| `check_readability` | `true` |
| `target_reading_level` | `8` |
| `check_keyword_density`, `keyword_variations` | `true` |
| `min_unique_content_ratio` | `0.7` |
| `check_meta_tags`, `check_structured_data`, `validate_structured_data` | `true` |
| `check_open_graph`, `check_twitter_cards`, `check_canonical_urls`, `check_hreflang` | `true` |
| `check_sitemaps`, `check_robots_txt` | `true` |
| `check_https`, `check_security_headers`, `check_mixed_content` | `true` |
| `check_mobile_friendly`, `check_page_speed`, `check_core_web_vitals` | `true` |
| `check_compression`, `check_caching`, `check_minification`, `check_http2` | `true` |
| `max_page_load_time` | `3.0` |
| `max_ttfb` | `0.8` |
| `max_fcp` | `1.8` |
| `max_lcp` | `2.5` |
| `max_fid` | `100.0` |
| `max_cls` | `0.1` |
| `max_page_size_mb` | `3.0` |
| `check_accessibility` | `true` |
| `wcag_level` | `"AA"` |

Removing these inert settings does not turn checks on or off. Findings are
controlled by the implemented analyzers and rule registry. In particular,
declaring a Core Web Vitals threshold or WCAG level never provided browser
measurements or a conformance assessment. `crawler.use_sitemap`,
`crawler.discover_sitemaps`, and `crawler.respect_robots_txt` remain separate,
implemented crawler controls.

## Retired export settings

Every key in this table is under `export`.

| Removed key | Historical default |
| --- | --- |
| `include_inline_css`, `include_inline_js`, `minify_html` | `true` |
| `html_theme` | `"light"` |
| `include_charts` | `true` |
| `charts_library` | `"chartjs"` |
| `include_raw_data`, `include_page_content`, `include_screenshots`, `include_har_files` | `false` |
| `data_sampling_rate` | `1.0` |
| `max_issues_per_page` | `100` |
| `max_pages_in_report` | `1000` |
| `create_subdirectories` | `true` |
| `compress_output` | `false` |
| `compression_format` | `"zip"` |
| `split_large_reports` | `true` |
| `split_threshold_mb` | `50` |
| `generate_summary`, `generate_executive_report` | `true` |
| `send_email` | `false` |
| `email_recipients` | `[]` |
| `email_subject_template` | `"SEO Report for {domain}"` |
| `smtp_server`, `smtp_username`, `smtp_password` | `null` |
| `smtp_port` | `587` |
| `upload_to_cloud` | `false` |
| `cloud_provider`, `cloud_bucket`, `cloud_path_prefix` | `null` |
| `send_to_api` | `false` |
| `api_endpoint`, `api_key` | `null` |
| `api_method` | `"POST"` |

Select a supported template using `html_template` and a supported output format
using `formats`. Report content comes from the report schema and template; the
removed flags did not alter it. Email, cloud/API delivery, screenshots, HAR
capture, compression, and report splitting have no built-in replacement.

## Retired monitoring and global settings

Every key in the next table is under the removed `monitoring` section.

| Removed key | Historical default |
| --- | --- |
| `enabled` | `false` |
| `collect_metrics` | `true` |
| `metrics_interval` | `60` |
| `metrics_retention_days` | `30` |
| `enable_alerts` | `false` |
| `alert_thresholds` | `{"error_rate": 0.05, "avg_response_time": 5.0, "memory_usage_mb": 500.0, "broken_links_ratio": 0.1}` |
| `log_level` | `"info"` |
| `log_to_file` | `true` |
| `log_file_path` | `"./logs/tfq0seo.log"` |
| `log_rotation` | `"daily"` |
| `log_retention_days` | `7` |
| `log_format` | `"json"` |
| `show_progress` | `true` |
| `progress_update_interval` | `1.0` |
| `detailed_progress`, `webhook_enabled` | `false` |
| `webhook_url` | `null` |
| `webhook_events` | `["analysis_complete", "error", "threshold_exceeded"]` |

An empty `monitoring` section, or a section containing only matching historical
defaults, is removed during explicit migration. There is no background monitoring,
alerting, webhook, or log-rotation service configured by the application. Configure
Python logging in the calling program if needed; `debug` does not replace the
retired logging settings.

The following top-level settings were also removed:

| Removed key | Historical default | Migration meaning |
| --- | --- | --- |
| `dry_run` | `false` | No dry-run mode exists. Review and remove a `true` request explicitly. |
| `temp_directory` | `"./temp"` | No configurable application temporary directory exists. |
| `features` | `{}` | No feature-flag mechanism consumes this mapping. |
| `metadata` | `{}` | No custom metadata mapping is consumed; `version` remains available. |

Retired attributes assigned dynamically to a configuration object are rejected by
validation and serialization. Use the migration API on the old dictionary before
constructing an active configuration, rather than attaching removed attributes
to a dataclass instance.

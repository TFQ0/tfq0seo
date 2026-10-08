"""Export analysis results through a shared, presentation-only adapter."""

import csv
import json
import math
import os
import re
import tempfile
from contextlib import contextmanager
from string import Formatter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from markupsafe import Markup
from ..core.report_contracts import validate_report
from ..core.report_optimizer import generate_performance_metrics

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


class ExportManager:
    """Manages JSON, CSV, Excel and HTML exports without changing source results."""

    ANALYZERS = ('seo', 'content', 'technical', 'performance', 'links')

    def __init__(self, config: Optional[Any] = None):
        self.config = dict(vars(config) if hasattr(config, '__dict__') else config or {})
        self.output_dir = Path(self.config.get('output_directory', './reports'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        template_dir = Path(__file__).parent.parent / 'templates'
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'], default_for_string=True),
        )
        self.jinja_env.filters.update(number=self._display_number, score_color=self._score_color,
                                     safe_url=self._safe_url, json_text=self._json_text,
                                     json_chunks=self._json_chunks)
        self.jinja_env.policies['json.dumps_kwargs'] = {'default': str, 'sort_keys': False}

    @staticmethod
    def _number(value):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            try:
                return value if math.isfinite(value) else None
            except OverflowError:
                pass
        return None

    @classmethod
    def _display_number(cls, value, digits=0, suffix=''):
        number = cls._number(value)
        if number is None:
            return 'Not measured'
        return (str(round(number)) if digits == 0 else f'{number:.{digits}f}') + suffix

    @classmethod
    def _score_color(cls, value):
        number = cls._number(value)
        if number is None:
            return 'var(--color-gray, #666)'
        return 'var(--color-pass)' if number >= 80 else 'var(--color-average)' if number >= 50 else 'var(--color-fail)'

    @staticmethod
    def _safe_url(value):
        """Only allow complete HTTP(S) destinations in clickable report links."""
        if not isinstance(value, str) or any(ord(char) < 32 for char in value):
            return ''
        try:
            parsed = urlsplit(value)
            if parsed.scheme.lower() in ('http', 'https') and parsed.hostname:
                return value
        except ValueError:
            pass
        return ''

    @staticmethod
    def _json_text(value):
        """Return plain JSON text for autoescaped HTML evidence, never trusted markup."""
        return json.dumps(value, indent=2, ensure_ascii=False, default=str)

    @staticmethod
    def _json_chunks(value):
        """Stream script-safe JSON without materializing the full findings text."""
        for chunk in json.JSONEncoder(ensure_ascii=False, allow_nan=False).iterencode(value):
            yield Markup(chunk.replace('&', '\\u0026').replace('<', '\\u003c')
                         .replace('>', '\\u003e').replace("'", '\\u0027'))

    @staticmethod
    def _cell(value):
        """Keep cells scalar and prevent untrusted strings becoming formulas."""
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False, default=str)
        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)
        if value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n')):
            value = "'" + value
        return value

    @staticmethod
    def _records(value):
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    @classmethod
    def _page_records(cls, data):
        pages = data.get('pages')
        if isinstance(pages, dict):
            records = cls._records(pages.get('detailed')) or cls._records(pages.get('summary'))
            return records + cls._records(pages.get('failed')) + cls._records(pages.get('skipped'))
        if isinstance(pages, list):
            return cls._records(pages)
        return [data]

    @staticmethod
    def _recommendation_text(rec):
        if isinstance(rec, dict):
            return str(rec.get('recommendation') or rec.get('description') or rec.get('title') or '')
        return str(rec)

    @classmethod
    def _recommendations(cls, data):
        recs = data.get('recommendations', [])
        if isinstance(recs, dict):
            recs = recs.get('specific', [])
        return recs if isinstance(recs, list) else []

    @classmethod
    def _scores(cls, data):
        scores = data.get('scores', {})
        overall = cls._number(scores.get('overall', data.get('overall_score')))
        categories = scores.get('categories', data.get('category_scores'))
        if not isinstance(categories, dict):
            categories = {name: data.get(name, {}).get('score') for name in cls.ANALYZERS}
        return overall, {name: cls._number(value) for name, value in categories.items()}

    @classmethod
    def _issues(cls, data):
        issues = data.get('issues', data.get('aggregated_issues', []))
        if isinstance(issues, dict):
            issues = issues.get('aggregated', issues.get('top_issues', []))
        issues = cls._records(issues)
        return sorted(issues, key=lambda issue: {'critical': 0, 'warning': 1, 'notice': 2}.get(issue.get('severity'), 3))

    @classmethod
    def _issue_counts(cls, data, issues=None):
        issues = cls._issues(data) if issues is None else issues
        counts = {severity: sum(issue.get('severity') == severity for issue in issues)
                  for severity in ('critical', 'warning', 'notice')}
        counts.update(total=len(issues), unique=len(issues))
        issue_data = data.get('issues')
        supplied = issue_data.get('counts', {}) if isinstance(issue_data, dict) else data.get('issue_counts', {})
        counts.update({key: value for key, value in supplied.items() if cls._number(value) is not None})
        return counts

    def export(self, data: Dict[str, Any], format: str, output_path: Optional[str] = None) -> str:
        if format not in ('json', 'csv', 'xlsx', 'html'):
            raise ValueError(f'Unsupported export format: {format}')
        validate_report(data)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        if output_path:
            output_file = Path(output_path)
        else:
            pattern = self.config.get('filename_pattern', '{domain}_{timestamp}_{format}')
            for _, field, spec, conversion in Formatter().parse(pattern):
                if field is not None and (field not in ('domain', 'timestamp', 'format') or spec or conversion):
                    raise ValueError('filename_pattern supports only {domain}, {timestamp}, and {format}')
            records = self._page_records(data)
            try:
                domain = urlsplit(records[0].get('url', '')).hostname if records else None
            except ValueError:
                domain = None
            domain = re.sub(r'[^A-Za-z0-9.-]', '_', domain or 'site')[:120]
            filename = pattern.format(domain=domain, timestamp=timestamp, format=format)
            device_name = filename.split('.')[0].rstrip(' ').upper()
            reserved = device_name in {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$'} or re.fullmatch(
                r'(?:COM|LPT)[1-9¹²³]', device_name)
            if (not filename or filename in ('.', '..') or Path(filename).name != filename
                    or re.search(r'[<>:"/\\|?*\x00-\x1f]', filename) or reserved):
                raise ValueError('filename_pattern must produce a portable filename without directories or reserved names')
            if not filename.endswith('.' + format):
                filename += '.' + format
            output_file = self.output_dir / filename
        output_file.parent.mkdir(parents=True, exist_ok=True)
        return getattr(self, f'export_{format}')(data, output_file)

    def export_json(self, data: Dict[str, Any], output_file: Path) -> str:
        validate_report(data)
        with self._atomic_output(output_file, encoding='utf-8') as stream:
            json.dump(data, stream, indent=2, default=str, ensure_ascii=False, allow_nan=False)
        return str(output_file)

    @staticmethod
    @contextmanager
    def _atomic_output(output_file, mode='w', **options):
        """Replace a report only after its sibling temporary file closes cleanly."""
        output_file = Path(output_file)
        descriptor, temporary = tempfile.mkstemp(
            prefix='.tfq0seo-', suffix='.tmp', dir=output_file.parent)
        try:
            with os.fdopen(descriptor, mode, **options) as stream:
                yield stream
            os.replace(temporary, output_file)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def export_csv(self, data: Dict[str, Any], output_file: Path) -> str:
        validate_report(data)
        pages = self._page_records(data)
        fieldnames = sorted({key for page in pages for key in self._flatten_page_data(page)}) or ['error']
        rows = (self._flatten_page_data(page) for page in pages) if pages else [{'error': 'No data to export'}]
        with self._atomic_output(output_file, newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows({key: self._cell(value) for key, value in row.items()} for row in rows)
        return str(output_file)

    def _flatten_page_data(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        flat = {key: page_data.get(key) for key in ('url', 'status_code', 'load_time', 'error', 'status')}
        flat['overall_score'] = self._number(page_data.get('overall_score', page_data.get('score')))
        for name in self.ANALYZERS:
            analyzer = page_data.get(name, {})
            flat[f'{name}_score'] = self._number(analyzer.get('score'))
            flat[f'{name}_error'] = analyzer.get('error')
        counts = page_data.get('issue_counts', page_data.get('issues', {}))
        if isinstance(counts, dict):
            flat.update({f'issues_{key}': value for key, value in counts.items()})
        seo_data = page_data.get('seo', {}).get('data', {})
        for key in ('title', 'description'):
            value = seo_data.get(key, '')
            flat[key] = value.get('text', '') if isinstance(value, dict) else value
        content = page_data.get('content', {}).get('data', {})
        flat['word_count'] = content.get('metrics', {}).get('word_count', content.get('word_count'))
        flat['flesch_reading_ease'] = content.get('readability', {}).get('flesch_reading_ease', content.get('flesch_reading_ease'))
        performance = page_data.get('performance', {}).get('data', {})
        for key in ('total_resources', 'content_size_mb'):
            flat[key] = performance.get(key, performance.get('metrics', {}).get(key))
        site = page_data.get('site_analysis', {})
        for key in ('canonical_targets', 'canonical_status', 'canonical_terminal', 'canonical_hops',
                    'canonical_cycle_id', 'incoming_links', 'outgoing_links', 'nofollow_links',
                    'link_depth', 'reachable', 'component'):
            if key in site:
                flat[key] = site[key]
        return flat

    def export_xlsx(self, data: Dict[str, Any], output_file: Path) -> str:
        validate_report(data)
        if not OPENPYXL_AVAILABLE:
            return self.export_csv(data, output_file.with_suffix('.csv'))
        workbook = Workbook()
        summary = workbook.active
        summary.title = 'Summary'
        self._write_summary_sheet(summary, data)
        self._write_issues_sheet(workbook.create_sheet('Issues'), data)
        self._write_pages_sheet(workbook.create_sheet('Pages'), self._page_records(data))
        self._write_recommendations_sheet(workbook.create_sheet('Recommendations'), self._recommendations(data))
        try:
            with self._atomic_output(output_file, mode='wb') as stream:
                workbook.save(stream)
        finally:
            workbook.close()
        return str(output_file)

    def _append_row(self, sheet, values):
        sheet.append([self._cell(value) for value in values])

    @staticmethod
    def _style_header(sheet):
        for cell in sheet[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color='CCCCCC', end_color='CCCCCC', fill_type='solid')
        sheet.freeze_panes = 'A2'

    def _write_summary_sheet(self, sheet, data):
        overall, categories = self._scores(data)
        self._append_row(sheet, ['SEO Analysis Report'])
        self._append_row(sheet, [])
        self._append_row(sheet, ['Overall Score', overall if overall is not None else 'Not measured'])
        self._append_row(sheet, ['Assessment', data.get('status', '')])
        for name, score in categories.items():
            self._append_row(sheet, [name.title(), score if score is not None else 'Not measured'])
        counts = self._issue_counts(data)
        for severity in ('critical', 'warning', 'notice', 'total'):
            self._append_row(sheet, [severity.title() + ' Issues', counts[severity]])
        if data.get('error'):
            self._append_row(sheet, ['Error', data['error']])
        self._style_header(sheet)
        sheet.column_dimensions['A'].width = 24
        sheet.column_dimensions['B'].width = 30

    def _write_issues_sheet(self, sheet, data):
        self._append_row(sheet, ['Severity', 'Category', 'Message', 'URL', 'Occurrences', 'Affected Pages'])
        issues = self._issues(data)
        if not issues and 'pages' in data:
            issues = [dict(issue, url=page.get('url')) for page in self._page_records(data) for issue in self._issues(page)]
        for issue in issues:
            self._append_row(sheet, [issue.get('severity'), issue.get('category'), issue.get('message'),
                                     issue.get('url', data.get('url')), issue.get('count', 1),
                                     issue.get('pages', issue.get('pages_affected'))])
        self._style_header(sheet)

    def _write_pages_sheet(self, sheet, pages: List[Dict[str, Any]]):
        rows = [self._flatten_page_data(page) for page in pages]
        keys = ['url', 'overall_score', 'status_code', 'load_time']
        keys += sorted({key for row in rows for key in row} - set(keys))
        self._append_row(sheet, [key.replace('_', ' ').title() for key in keys])
        for row in rows:
            self._append_row(sheet, [row.get(key) for key in keys])
        self._style_header(sheet)

    def _write_recommendations_sheet(self, sheet, recommendations):
        if isinstance(recommendations, dict):
            recommendations = recommendations.get('specific', [])
        self._append_row(sheet, ['Recommendation', 'Priority', 'Category', 'Impact', 'Effort'])
        for rec in recommendations:
            metadata = rec if isinstance(rec, dict) else {}
            self._append_row(sheet, [self._recommendation_text(rec)] + [metadata.get(key) for key in ('priority', 'category', 'impact', 'effort')])
        self._style_header(sheet)

    def export_html(self, data: Dict[str, Any], output_file: Path) -> str:
        validate_report(data)
        requested = self.config.get('html_template')
        template_names = {'report': 'report.html', 'enhanced': 'enhanced_report.html', 'optimized': 'optimized_report.html'}
        if requested is not None and requested not in template_names:
            raise ValueError(f'Unsupported HTML template: {requested}')
        default = 'optimized' if 'pages' in data or 'aggregated_issues' in data else 'report'
        try:
            template = self.jinja_env.get_template(template_names[requested or default])
        except TemplateNotFound:
            try:
                template = self.jinja_env.get_template('report.html')
            except TemplateNotFound:
                template = self.jinja_env.from_string(self._get_basic_html_template())
        with self._atomic_output(output_file, encoding='utf-8') as stream:
            stream.writelines(template.generate(**self._prepare_html_data(data)))
        return str(output_file)

    def _prepare_html_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        overall, categories = self._scores(data)
        issues = self._issues(data)
        issue_data = data.get('issues', {}) if isinstance(data.get('issues'), dict) else {}
        counts = self._issue_counts(data, issues)
        recs = self._recommendations(data)
        recommendations = data.get('recommendations', {}) if isinstance(data.get('recommendations'), dict) else {}
        pages = self._page_records(data) if 'pages' in data or 'url' in data else []
        summaries = []
        for page in pages:
            count_data = page.get('issue_counts', page.get('issues', {}))
            issue_count = count_data.get('total', 0) if isinstance(count_data, dict) else len(count_data)
            flat = self._flatten_page_data(page)
            facts = page.get('page_facts', {})
            timings = page.get('timings', {})
            context = page.get('context', {})
            site = page.get('site_analysis', {})
            links = page.get('links', {}).get('data', {})
            status = page.get('status') or ('error' if page.get('error') else
                                           'skipped' if page.get('skipped') else 'not_recorded')
            summaries.append({'url': str(page.get('url', '')), 'score': self._number(page.get('overall_score', page.get('score'))),
                              'status_code': page.get('status_code'), 'load_time': self._number(page.get('load_time')),
                              'issue_count': issue_count, 'error': page.get('error'), 'status': status,
                              'reason': page.get('reason'), 'title': flat['title'], 'description': flat['description'],
                              'word_count': flat['word_count'], 'content_length': page.get('content_length'),
                              'requested_url': page.get('requested_url'), 'depth': context.get('depth', page.get('depth')),
                              'parent_url': context.get('parent_url'), 'cached': page.get('cached', False),
                              'headers_seconds': self._number(timings.get('headers_seconds')),
                              'download_seconds': self._number(timings.get('download_seconds')),
                              'fetch_elapsed_seconds': self._number(timings.get('total_seconds')),
                              'analysis_time': self._number(page.get('analysis_time')),
                              'category_scores': self._scores(page)[1], 'coverage': page.get('coverage', {}),
                              'analyzer_errors': page.get('analyzer_errors', {}),
                              'canonical_status': site.get('canonical_status'),
                              'canonical_targets': site.get('canonical_targets'),
                              'robots': facts.get('robots', {}), 'language': facts.get('language'),
                              'h1': [heading.get('text', '') for heading in facts.get('headings', {}).get('headings', {}).get('h1', [])],
                              'internal_links': len(links['internal_links']) if isinstance(links.get('internal_links'), list) else None,
                              'external_links': len(links['external_links']) if isinstance(links.get('external_links'), list) else None,
                              'redirect_chain': page.get('redirect_chain', []),
                              'findings': [{key: issue.get(key) for key in ('rule_id', 'severity', 'message', 'recommendation')}
                                           for issue in self._issues(page)],
                              'recommendations': [self._recommendation_text(rec) for rec in self._recommendations(page)]})
        summary = data.get('summary', {})
        crawl_stats = data.get('crawl_stats', {})
        states = {status: sum(page['status'] == status for page in summaries)
                  for status in ('complete', 'partial', 'error', 'skipped', 'not_recorded')}
        observed_duration = self._number(summary.get('analysis_duration'))
        # Old imported reports used zero for missing run timing. Do not call it a fast crawl.
        if observed_duration == 0 and not summary.get('duration_scope'):
            observed_duration = None
        audit = {'recorded': len(summaries), 'analyzed': states['complete'] + states['partial'],
                 'complete': states['complete'], 'partial': states['partial'], 'failed': states['error'],
                 'skipped': states['skipped'], 'unknown': states['not_recorded'],
                 'page_limit': summary.get('page_limit'), 'duration': observed_duration,
                 'requests': crawl_stats.get('requests_made'),
                 'requests_by_kind': crawl_stats.get('requests_by_kind', {}),
                 'robots_delays': crawl_stats.get('robots_delays', {}),
                 'cache_hits': crawl_stats.get('cache_hits'),
                 'throughput': crawl_stats.get('pages_per_second') if observed_duration is not None else None,
                 'unique_content': crawl_stats.get('unique_content_count'),
                 'limits': summary.get('limits_reached', []),
                 'discovery_errors': summary.get('discovery_errors', []),
                 'config': data.get('metadata', {}).get('config', {}) if summary.get('page_limit') is not None else {},
                 'completion_reason': summary.get('completion_reason', 'not_recorded')}
        executive_defaults = {
            'overview': {'total_pages_analyzed': summary.get('total_pages', len(pages)),
                         'successful_pages': summary.get('successful_pages', sum(not page.get('error') for page in pages)),
                         'overall_health': 'Not measured' if overall is None else 'Good' if overall >= 80 else 'Needs improvement'},
            'key_metrics': {'critical_issues': counts['critical']}, 'quick_wins': [],
        }
        supplied_executive = recommendations.get('executive', data.get('executive_summary')) or {}
        executive = {**executive_defaults, **supplied_executive}
        for key in ('overview', 'key_metrics'):
            executive[key] = {**executive_defaults[key], **supplied_executive.get(key, {})}
        performance = dict(data.get('performance', {}).get('data', {}))
        performance.update(performance.get('metrics', {}))
        performance.setdefault('html_fetch_time', data.get('load_time'))
        content = dict(data.get('content', {}).get('data', {}))
        content.update(content.get('metrics', {}))
        content.update(content.get('readability', {}))
        content.setdefault('average_grade_level', content.get('consensus_grade'))
        content.setdefault('image_count', content.get('image_analysis', {}).get('total_images'))
        technical = dict(data.get('technical', {}).get('data', {}))
        technical.setdefault('has_viewport', technical.get('mobile', {}).get('viewport_configured'))
        technical.setdefault('compression', technical.get('performance', {}).get('compression'))
        seo = dict(data.get('seo', {}).get('data', {}))
        for key in ('title', 'description'):
            if isinstance(seo.get(key), dict):
                seo[key] = seo[key].get('text', '')
        scoring = data.get('scoring') if isinstance(data.get('scoring'), dict) else {}
        scoring_policies = [scoring] if scoring else []
        if not scoring_policies:
            for page in pages:
                policy = page.get('scoring')
                if isinstance(policy, dict) and policy and policy not in scoring_policies:
                    scoring_policies.append(policy)
        versions = data.get('scores', {}).get('scoring_versions', [])
        scoring_versions = list(versions) if isinstance(versions, list) else []
        for policy in scoring_policies:
            if policy.get('version') is not None and policy['version'] not in scoring_versions:
                scoring_versions.append(policy['version'])
        rule_coverage = data.get('rule_coverage')
        if not isinstance(rule_coverage, dict):
            coverage = data.get('coverage', {})
            rule_coverage = coverage.get('rules', {}) if isinstance(coverage, dict) else {}
        if not isinstance(rule_coverage, dict):
            rule_coverage = {}
        enhanced_recommendations = recommendations.get('specific', data.get('enhanced_recommendations', []))
        enhanced_recommendations = [rec if isinstance(rec, dict) else {'title': rec, 'description': rec}
                                    for rec in enhanced_recommendations]
        aggregation_stats = issue_data.get('stats', data.get('aggregation_stats', {}))
        if self._number(aggregation_stats.get('reduction_ratio')) is None:
            aggregation_stats = {}
        performance_metrics = data.get('performance_metrics') or generate_performance_metrics(pages)
        fetch_distribution = {label: 0 for label in ('Under 0.1 s', '0.1–0.5 s', '0.5–1 s', '1–3 s', '3 s or more')}
        for item in performance_metrics.get('load_times', []):
            seconds = self._number(item.get('time'))
            if seconds is not None:
                bucket = sum(seconds >= threshold for threshold in (0.1, 0.5, 1, 3))
                fetch_distribution[list(fetch_distribution)[bucket]] += 1
        return {
            'data': data,
            'url': data.get('url') or data.get('metadata', {}).get('start_url') or
                   (pages[0].get('url') if pages else None) or 'Multiple Pages',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'audit': audit,
            'error': data.get('error'), 'overall_score': overall, 'category_scores': categories,
            'report_status': data.get('status'),
            'scoring_policies': scoring_policies, 'scoring_versions': scoring_versions,
            'rule_coverage': rule_coverage,
            'score_source': data.get('scores', {}).get('source', data.get('coverage', {}).get('measurement_source')),
            'analysis_errors': [{'analyzer': name, 'error': data[name]['error']} for name in self.ANALYZERS
                                if isinstance(data.get(name), dict) and data[name].get('error')],
            'score_chart_values': [overall, 100 - overall] if overall is not None else [],
            'issues': issues, 'issue_counts': counts,
            'issues_by_severity': {severity: [issue for issue in issues if issue.get('severity') == severity]
                                   for severity in ('critical', 'warning', 'notice')},
            'recommendations': [self._recommendation_text(rec) for rec in recs],
            'enhanced_recommendations': enhanced_recommendations,
            'executive_summary': executive,
            'aggregated_issues': issue_data.get('aggregated', data.get('aggregated_issues', [])),
            'aggregation_stats': aggregation_stats,
            'performance_metrics': performance_metrics, 'fetch_distribution': fetch_distribution,
            'pages': pages, 'pages_summary': summaries, 'pages_truncated': data.get('pages_truncated', False),
            'pages_truncated_count': data.get('pages_truncated_count', 0), 'summary': summary,
            'seo_data': seo, 'content_data': content, 'technical_data': technical,
            'performance_data': performance,
        }

    def _get_basic_html_template(self) -> str:
        return '''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<title>SEO Analysis Report</title></head><body><h1>SEO Analysis Report</h1>
<p>{{ url }}</p><p>Overall score: {{ overall_score|number }}</p>
{% if error %}<p>Analysis failed: {{ error }}</p>{% endif %}
{% for issue in issues %}<p>{{ issue.category }}: {{ issue.message }}</p>{% endfor %}
{% for rec in recommendations %}<p>{{ rec }}</p>{% endfor %}
<table>{% for page in pages_summary %}<tr><td>{{ page.url }}</td><td>{{ page.score|number }}</td>
<td>{{ page.error or '' }}</td></tr>{% endfor %}</table></body></html>'''

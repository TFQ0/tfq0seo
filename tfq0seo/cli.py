"""Click commands for analysis, complete reports, and explicit failure statuses."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from . import __version__
from .core.app import SEOAnalyzer
from .core.config import Config
from .core.models import ANALYZER_NAMES
from .exporters.base import ExportManager

console = Console()
FORMATS = click.Choice(['json', 'html', 'csv', 'xlsx'])
CONFIG_PATH = click.Path(exists=True, dir_okay=False)


def _reject_json_constant(value):
    raise ValueError(f'Non-finite JSON number {value} is not allowed')


def create_summary_table(results: dict) -> Table:
    table = Table(title='Analysis Summary', show_header=True)
    table.add_column('Metric', style='cyan')
    table.add_column('Value')
    scores = results.get('scores', {})
    overall = scores.get('overall', results.get('overall_score'))
    table.add_row('Overall Score', 'Unavailable' if overall is None else f'{overall:.1f}/100')
    categories = scores.get('categories', results.get('category_scores', {}))
    if not categories:
        categories = {name: results[name].get('score') for name in ANALYZER_NAMES if name in results}
    for name, score in categories.items():
        table.add_row(name, 'Unavailable' if score is None else f'{score:.1f}')
    issues = results.get('issues', [])
    counts = issues.get('counts', {}) if isinstance(issues, dict) else SEOAnalyzer._count_issues(issues)
    for severity in ('critical', 'warning', 'notice'):
        table.add_row(severity.title(), str(counts.get(severity, 0)))
    timings = results.get('performance_metrics', {}).get('load_time_stats', {})
    if 'average' in timings:
        table.add_row('Avg HTML Fetch Time', f"{timings['average']:.2f}s")
    elif results.get('load_time') is not None:
        table.add_row('HTML Fetch Time', f"{results['load_time']:.2f}s")
    for name in ('total_pages', 'successful_pages', 'partial_pages', 'failed_pages', 'skipped_pages'):
        if name in results.get('summary', {}):
            table.add_row(name.replace('_', ' ').title(), str(results['summary'][name]))
    table.add_row('Status', results.get('status', 'complete'))
    return table


def create_issues_table(issues: List[dict], limit: int = 10) -> Table:
    table = Table(title=f'Top {limit} Issues')
    for name in ('Severity', 'Category', 'Issue'):
        table.add_column(name)
    ordered = sorted(issues, key=lambda issue: {'critical': 0, 'warning': 1, 'notice': 2}.get(issue.get('severity'), 3))
    for issue in ordered[:limit]:
        table.add_row(Text(issue.get('severity', 'notice')), Text(issue.get('category', 'General')),
                      Text(issue.get('message', '')))
    return table


def _configuration(path: Optional[str], **crawler_overrides) -> Config:
    cfg = Config.from_file(path) if path else Config()
    environment = Config.environment_overrides()
    if environment:
        cfg = cfg.merge(environment)
    changes = {name: value for name, value in crawler_overrides.items() if value is not None}
    if changes:
        cfg = cfg.merge({'crawler': changes})
    cfg.require_valid()
    return cfg


def _report(data, cfg, format, output):
    format = format or cfg.export.primary_format
    if format == 'json' and output is None:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False))
    else:
        console.print(create_summary_table(data))
        issues = data.get('issues', [])
        if isinstance(issues, dict):
            issues = issues.get('aggregated', [])
        if issues:
            console.print(create_issues_table(issues))
        if output is not None or not data.get('error'):
            destination = ExportManager(cfg.export).export(data, format, output)
            console.print(f'Report saved to: {destination}', markup=False)
    if data.get('error'):
        raise click.ClickException(data['error'])
    if data.get('skipped'):
        raise click.ClickException('Page was not analyzed: ' + data.get('reason', 'Skipped'))
    if data.get('status') == 'partial' or data.get('analyzer_errors'):
        errors = '; '.join(data.get('analyzer_errors', {}).values())
        raise click.ClickException('Analysis is incomplete; inspect the report for failures.' + (' ' + errors if errors else ''))
    if data.get('status') == 'error':
        raise click.ClickException('No pages were analyzed successfully; inspect the report for failures.')


@click.group()
@click.version_option(version=__version__, prog_name='tfq0seo')
def cli():
    """Static SEO analysis with evidence and explicit coverage."""


@cli.command()
@click.argument('url')
@click.option('--config', '-c', type=CONFIG_PATH)
@click.option('--format', '-f', type=FORMATS, default=None)
@click.option('--output', '-o', type=click.Path(dir_okay=False))
@click.option('--verbose', '-v', is_flag=True)
def analyze(url, config, format, output, verbose):
    """Analyze a single URL."""
    try:
        if verbose:
            logging.basicConfig(level=logging.INFO)
        cfg = _configuration(config)
        result = asyncio.run(SEOAnalyzer(cfg).analyze_url(url))
        _report(result, cfg, format, output)
    except click.ClickException:
        raise
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command()
@click.argument('url')
@click.option('--depth', '-d', type=click.IntRange(min=0), default=None)
@click.option('--max-pages', '-m', type=click.IntRange(min=1), default=None)
@click.option('--concurrent', type=click.IntRange(min=1), default=None)
@click.option('--config', '-c', type=CONFIG_PATH)
@click.option('--format', '-f', type=FORMATS, default=None)
@click.option('--output', '-o', type=click.Path(dir_okay=False), required=True)
@click.option('--follow-redirects/--no-follow-redirects', default=None)
@click.option('--respect-robots/--ignore-robots', default=None)
def crawl(url, depth, max_pages, concurrent, config, format, output, follow_redirects, respect_robots):
    """Crawl pages within the configured scope and export a complete report."""
    try:
        cfg = _configuration(config, max_depth=depth, max_pages=max_pages, max_concurrent=concurrent,
                             follow_redirects=follow_redirects, respect_robots_txt=respect_robots)
        analyzer = SEOAnalyzer(cfg)
        async def run():
            return [page async for page in analyzer.crawl_site(url)]
        results = asyncio.run(run())
        _report(analyzer.generate_site_report(results), cfg, format, output)
    except click.ClickException:
        raise
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command()
@click.argument('urls_file', type=CONFIG_PATH)
@click.option('--concurrent', type=click.IntRange(min=1), default=None)
@click.option('--config', '-c', type=CONFIG_PATH)
@click.option('--format', '-f', type=FORMATS, default=None)
@click.option('--output', '-o', type=click.Path(dir_okay=False), required=True)
def batch(urls_file, concurrent, config, format, output):
    """Analyze URLs from a UTF-8 file (one per line)."""
    try:
        urls = [line.strip() for line in Path(urls_file).read_text(encoding='utf-8').splitlines()
                if line.strip() and not line.lstrip().startswith('#')]
        if not urls:
            raise ValueError('The input file contains no URLs')
        cfg = _configuration(config, max_concurrent=concurrent)
        analyzer = SEOAnalyzer(cfg)
        async def run():
            return [page async for page in analyzer.analyze_urls(urls)]
        results = asyncio.run(run())
        _report(analyzer.generate_batch_report(results), cfg, format, output)
    except click.ClickException:
        raise
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command()
@click.argument('sitemap_url')
@click.option('--max-pages', '-m', type=click.IntRange(min=1), default=None)
@click.option('--config', '-c', type=CONFIG_PATH)
@click.option('--format', '-f', type=FORMATS, default=None)
@click.option('--output', '-o', type=click.Path(dir_okay=False), required=True)
def sitemap(sitemap_url, max_pages, config, format, output):
    """Analyze eligible URLs from an XML sitemap or sitemap index."""
    try:
        cfg = _configuration(config, max_pages=max_pages)
        analyzer = SEOAnalyzer(cfg)
        results = asyncio.run(analyzer.analyze_sitemap(sitemap_url))
        _report(analyzer.generate_site_report(results), cfg, format, output)
    except click.ClickException:
        raise
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command()
@click.option('--input', '-i', 'input_file', type=CONFIG_PATH, required=True)
@click.option('--format', '-f', type=click.Choice(['html', 'csv', 'xlsx']), required=True)
@click.option('--output', '-o', type=click.Path(dir_okay=False), required=True)
@click.option('--config', '-c', type=CONFIG_PATH)
def export(input_file, format, output, config):
    """Convert a page or site JSON report to another format."""
    try:
        data = json.loads(Path(input_file).read_text(encoding='utf-8'), parse_constant=_reject_json_constant)
        if not isinstance(data, dict):
            raise ValueError('A report must be a JSON object')
        cfg = _configuration(config)
        destination = ExportManager(cfg.export).export(data, format, output)
        console.print(f'Exported to: {destination}', markup=False)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc


def main():
    cli()


if __name__ == '__main__':
    main()

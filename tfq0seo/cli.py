"""CLI module for tfq0seo using Click and Rich for beautiful output."""

import asyncio
import json
import time
import sys
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich import print as rprint

from .core.app import SEOAnalyzer
from .core.config import Config
from .exporters.base import ExportManager

console = Console()


def create_summary_table(results: dict) -> Table:
    """Create a summary table for the results."""
    table = Table(title="Analysis Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", width=20)
    table.add_column("Value", style="green")
    
    # Overall score - handle both old and new formats
    score = 0
    if 'scores' in results and isinstance(results['scores'], dict):
        score = results['scores'].get('overall', 0)
    else:
        score = results.get('overall_score', 0)
    
    score_style = "green" if score >= 80 else "yellow" if score >= 50 else "red"
    table.add_row("Overall Score", f"[{score_style}]{score:.1f}/100[/{score_style}]")
    
    # Category scores - handle both formats
    category_scores = {}
    if 'scores' in results and isinstance(results['scores'], dict):
        category_scores = results['scores'].get('categories', {})
    elif 'category_scores' in results:
        category_scores = results['category_scores']
    
    if category_scores:
        for category, cat_score in category_scores.items():
            cat_style = "green" if cat_score >= 80 else "yellow" if cat_score >= 50 else "red"
            table.add_row(f"  {category}", f"[{cat_style}]{cat_score:.1f}[/{cat_style}]")
    
    # Issue counts - handle both old and new formats
    if 'issues' in results:
        if isinstance(results['issues'], dict):
            # New format with nested structure
            if 'counts' in results['issues']:
                counts = results['issues']['counts']
                critical = counts.get('critical', 0)
                warnings = counts.get('warning', 0)
                notices = counts.get('notice', 0)
            else:
                # Try to extract from aggregated issues
                issues_list = results['issues'].get('aggregated', [])
                critical = sum(1 for i in issues_list if isinstance(i, dict) and i.get('severity') == 'critical')
                warnings = sum(1 for i in issues_list if isinstance(i, dict) and i.get('severity') == 'warning')
                notices = sum(1 for i in issues_list if isinstance(i, dict) and i.get('severity') == 'notice')
        else:
            # Old format - issues is a list
            issues_list = results['issues']
            critical = sum(1 for i in issues_list if isinstance(i, dict) and i.get('severity') == 'critical')
            warnings = sum(1 for i in issues_list if isinstance(i, dict) and i.get('severity') == 'warning')
            notices = sum(1 for i in issues_list if isinstance(i, dict) and i.get('severity') == 'notice')
        
        table.add_row("Critical Issues", f"[red]{critical}[/red]")
        table.add_row("Warnings", f"[yellow]{warnings}[/yellow]")
        table.add_row("Notices", f"[blue]{notices}[/blue]")
    elif 'issue_counts' in results:
        # Fallback to issue_counts if available
        counts = results['issue_counts']
        table.add_row("Critical Issues", f"[red]{counts.get('critical', 0)}[/red]")
        table.add_row("Warnings", f"[yellow]{counts.get('warning', 0)}[/yellow]")
        table.add_row("Notices", f"[blue]{counts.get('notice', 0)}[/blue]")
    
    # Performance metrics - handle both formats
    if 'performance_metrics' in results:
        # New format with detailed metrics
        perf = results['performance_metrics']
        if 'load_time_stats' in perf:
            table.add_row("Avg Load Time", f"{perf['load_time_stats'].get('mean', 0):.2f}s")
        if 'pages_by_status' in perf:
            successful = perf['pages_by_status'].get('2xx', 0)
            table.add_row("Successful Pages", str(successful))
    elif 'performance' in results:
        # Old format
        perf = results['performance']
        if 'average_load_time' in perf:
            table.add_row("Avg Load Time", f"{perf['average_load_time']:.2f}s")
        elif 'load_time' in perf:
            table.add_row("Load Time", f"{perf.get('load_time', 0):.2f}s")
        if 'content_size' in perf:
            table.add_row("Content Size", f"{perf.get('content_size', 0) / 1024:.1f}KB")
    
    # Summary information if available
    if 'summary' in results:
        summary = results['summary']
        table.add_row("Total Pages", str(summary.get('total_pages', 0)))
        table.add_row("Successful Pages", str(summary.get('successful_pages', 0)))
        if summary.get('failed_pages', 0) > 0:
            table.add_row("Failed Pages", f"[red]{summary['failed_pages']}[/red]")
    
    return table


def create_issues_table(issues: List[dict], limit: int = 10) -> Table:
    """Create a table showing top issues."""
    table = Table(title=f"Top {limit} Issues", show_header=True, header_style="bold magenta")
    table.add_column("Severity", width=10)
    table.add_column("Category", width=15)
    table.add_column("Issue", width=50)
    
    # Sort issues by severity
    severity_order = {'critical': 0, 'warning': 1, 'notice': 2}
    sorted_issues = sorted(issues, key=lambda x: severity_order.get(x.get('severity', 'notice'), 3))
    
    for issue in sorted_issues[:limit]:
        severity = issue.get('severity', 'notice')
        severity_style = "red" if severity == 'critical' else "yellow" if severity == 'warning' else "blue"
        
        table.add_row(
            f"[{severity_style}]{severity.upper()}[/{severity_style}]",
            issue.get('category', 'General'),
            issue.get('message', 'No description')[:50]
        )
    
    return table


@click.group()
@click.version_option(version='2.3.0', prog_name='tfq0seo')
def cli():
    """TFQ0SEO - Fast SEO analysis tool with reports."""
    pass


@cli.command()
@click.argument('url')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file (JSON/YAML)')
@click.option('--format', '-f', type=click.Choice(['json', 'html', 'csv', 'xlsx']), default='html', help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def analyze(url: str, config: Optional[str], format: str, output: Optional[str], verbose: bool):
    """Analyze a single URL."""
    with console.status(f"[bold green]Analyzing {url}...") as status:
        # Load configuration
        if config:
            cfg = Config.from_file(config)
        else:
            cfg = Config()
        
        # Run analysis
        analyzer = SEOAnalyzer(cfg)
        
        try:
            # Run async analysis
            results = asyncio.run(analyzer.analyze_url(url))
            
            if not results:
                console.print("[red]Analysis failed![/red]")
                sys.exit(1)
            
            # Display summary
            console.print("\n")
            console.print(create_summary_table(results))
            
            # Display top issues
            if 'issues' in results and results['issues']:
                console.print("\n")
                console.print(create_issues_table(results['issues']))
            
            # Export results
            if output:
                exporter = ExportManager(cfg.export)
                exported_file = exporter.export(results, format, output)
                console.print(f"\n[green]✓[/green] Report saved to: {exported_file}")
            elif format != 'html':
                # For non-HTML formats without output file, print to console
                if format == 'json':
                    rprint(json.dumps(results, indent=2, default=str))
            
            # Print recommendations
            if verbose and 'recommendations' in results:
                console.print("\n[bold]Recommendations:[/bold]")
                for i, rec in enumerate(results['recommendations'][:5], 1):
                    console.print(f"{i}. {rec}")
                    
        except Exception as e:
            console.print(f"[red]Error during analysis: {e}[/red]")
            if verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)


@cli.command()
@click.argument('url')
@click.option('--depth', '-d', type=int, default=5, help='Maximum crawl depth')
@click.option('--max-pages', '-m', type=int, default=100, help='Maximum pages to crawl')
@click.option('--concurrent', type=int, default=10, help='Concurrent requests')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file')
@click.option('--format', '-f', type=click.Choice(['json', 'html', 'csv', 'xlsx']), default='html')
@click.option('--output', '-o', type=click.Path(), required=True, help='Output file path')
@click.option('--follow-redirects/--no-follow-redirects', default=True, help='Follow redirects')
@click.option('--respect-robots/--ignore-robots', default=True, help='Respect robots.txt')
def crawl(url: str, depth: int, max_pages: int, concurrent: int, config: Optional[str], 
         format: str, output: str, follow_redirects: bool, respect_robots: bool):
    """Crawl and analyze an entire website."""
    
    # Load configuration
    if config:
        cfg = Config.from_file(config)
    else:
        cfg = Config()
    
    # Override with CLI options
    cfg.crawler.max_depth = depth
    cfg.crawler.max_pages = max_pages
    cfg.crawler.max_concurrent = concurrent
    cfg.crawler.follow_redirects = follow_redirects
    cfg.crawler.respect_robots_txt = respect_robots
    
    analyzer = SEOAnalyzer(cfg)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        # Add crawling task
        crawl_task = progress.add_task(
            f"[cyan]Crawling {url}...", 
            total=max_pages
        )
        
        async def run_crawl():
            """Run the crawl with progress updates."""
            results = []
            analyzed = 0
            
            async for page_result in analyzer.crawl_site(url):
                analyzed += 1
                progress.update(crawl_task, advance=1, description=f"[cyan]Analyzed {analyzed}/{max_pages} pages")
                
                # Update with current URL
                if 'url' in page_result:
                    progress.update(crawl_task, description=f"[cyan]Analyzing: {page_result['url'][:50]}...")
                
                results.append(page_result)
                
                # Show live stats
                if analyzed % 10 == 0:
                    stats = analyzer.get_crawl_statistics()
                    console.print(f"[dim]Speed: {stats.get('pages_per_second', 0):.1f} pages/sec | "
                                f"Memory: {stats.get('memory_usage', 0):.1f}MB[/dim]")
            
            return results
        
        try:
            # Run the crawl
            results = asyncio.run(run_crawl())
            
            if not results:
                console.print("[red]No pages were analyzed![/red]")
                sys.exit(1)
            
            # Generate report
            progress.add_task("[green]Generating report...", total=None)
            
            # Aggregate results
            report = analyzer.generate_site_report(results)
            
            # Export
            exporter = ExportManager(cfg.export)
            exported_file = exporter.export(report, format, output)
            
            # Show summary
            console.print("\n")
            console.print(Panel.fit(
                f"[green]✓[/green] Crawl completed!\n"
                f"Pages analyzed: {len(results)}\n"
                f"Report saved to: {exported_file}",
                title="Success",
                border_style="green"
            ))
            
            # Display summary table
            console.print("\n")
            console.print(create_summary_table(report))
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Crawl interrupted by user[/yellow]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error during crawl: {e}[/red]")
            import traceback
            traceback.print_exc()
            sys.exit(1)


@cli.command()
@click.argument('urls_file', type=click.Path(exists=True))
@click.option('--concurrent', type=int, default=10, help='Concurrent requests')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file')
@click.option('--format', '-f', type=click.Choice(['json', 'html', 'csv', 'xlsx']), default='html')
@click.option('--output', '-o', type=click.Path(), required=True, help='Output file path')
def batch(urls_file: str, concurrent: int, config: Optional[str], format: str, output: str):
    """Analyze a batch of URLs from a file."""
    
    # Load URLs
    with open(urls_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    if not urls:
        console.print("[red]No valid URLs found in file![/red]")
        sys.exit(1)
    
    console.print(f"[cyan]Found {len(urls)} URLs to analyze[/cyan]")
    
    # Load configuration
    if config:
        cfg = Config.from_file(config)
    else:
        cfg = Config()
    
    cfg.crawler.max_concurrent = concurrent
    
    analyzer = SEOAnalyzer(cfg)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        # Add task
        batch_task = progress.add_task(
            f"[cyan]Analyzing {len(urls)} URLs...", 
            total=len(urls)
        )
        
        async def run_batch():
            """Run batch analysis."""
            results = []
            
            async for page_result in analyzer.analyze_urls(urls):
                progress.update(batch_task, advance=1)
                results.append(page_result)
                
                # Update description
                if 'url' in page_result:
                    progress.update(batch_task, description=f"[cyan]Analyzed: {page_result['url'][:50]}...")
            
            return results
        
        try:
            # Run batch analysis
            results = asyncio.run(run_batch())
            
            # Generate report
            report = analyzer.generate_batch_report(results)
            
            # Export
            exporter = ExportManager(cfg.export)
            exported_file = exporter.export(report, format, output)
            
            # Show summary
            console.print("\n")
            console.print(Panel.fit(
                f"[green]✓[/green] Batch analysis completed!\n"
                f"URLs analyzed: {len(results)}\n"
                f"Report saved to: {exported_file}",
                title="Success",
                border_style="green"
            ))
            
            # Display summary
            console.print("\n")
            console.print(create_summary_table(report))
            
        except Exception as e:
            console.print(f"[red]Error during batch analysis: {e}[/red]")
            sys.exit(1)


@cli.command()
@click.argument('sitemap_url')
@click.option('--max-pages', '-m', type=int, default=100, help='Maximum pages to analyze')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file')
@click.option('--format', '-f', type=click.Choice(['json', 'html', 'csv', 'xlsx']), default='html')
@click.option('--output', '-o', type=click.Path(), required=True, help='Output file path')
def sitemap(sitemap_url: str, max_pages: int, config: Optional[str], format: str, output: str):
    """Analyze URLs from a sitemap."""
    
    # Load configuration
    if config:
        cfg = Config.from_file(config)
    else:
        cfg = Config()
    
    cfg.crawler.max_pages = max_pages
    
    analyzer = SEOAnalyzer(cfg)
    
    with console.status(f"[bold green]Fetching sitemap from {sitemap_url}...") as status:
        try:
            # Analyze sitemap
            results = asyncio.run(analyzer.analyze_sitemap(sitemap_url))
            
            if not results:
                console.print("[red]No URLs found in sitemap![/red]")
                sys.exit(1)
            
            # Generate report
            report = analyzer.generate_site_report(results)
            
            # Export
            exporter = ExportManager(cfg.export)
            exported_file = exporter.export(report, format, output)
            
            # Show summary
            console.print("\n")
            console.print(Panel.fit(
                f"[green]✓[/green] Sitemap analysis completed!\n"
                f"URLs analyzed: {len(results)}\n"
                f"Report saved to: {exported_file}",
                title="Success",
                border_style="green"
            ))
            
            # Display summary
            console.print("\n")
            console.print(create_summary_table(report))
            
        except Exception as e:
            console.print(f"[red]Error during sitemap analysis: {e}[/red]")
            sys.exit(1)


@cli.command()
@click.option('--input', '-i', 'input_file', type=click.Path(exists=True), required=True, help='Input JSON file')
@click.option('--format', '-f', type=click.Choice(['html', 'csv', 'xlsx']), required=True, help='Output format')
@click.option('--output', '-o', type=click.Path(), required=True, help='Output file path')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file')
def export(input_file: str, format: str, output: str, config: Optional[str]):
    """Convert analysis results to different formats."""
    
    # Load data
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Load configuration
    if config:
        cfg = Config.from_file(config)
    else:
        cfg = Config()
    
    # Export
    exporter = ExportManager(cfg.export)
    exported_file = exporter.export(data, format, output)
    
    console.print(f"[green]✓[/green] Exported to: {exported_file}")


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()
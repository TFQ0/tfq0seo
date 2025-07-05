"""
Command-line interface for tfq0seo
"""
import click
import asyncio
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from .core.app import SEOAnalyzerApp
from .core.config import Config
from .exporters.base import ExportManager
import sys
import json
import os
import yaml
import validators
from pathlib import Path
import logging
from urllib.parse import urlparse

console = Console()

# Version should be imported from package
try:
    from . import __version__
except ImportError:
    __version__ = '2.1.0'

def setup_logging(verbose: bool, quiet: bool) -> None:
    """Setup logging based on verbosity settings"""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def validate_url(url: str) -> str:
    """Validate and normalize URL"""
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'
    
    # Validate URL
    if not validators.url(url):
        raise click.BadParameter(f'Invalid URL: {url}')
    
    return url

def validate_output_path(path: str, format: str) -> str:
    """Validate and prepare output path"""
    if not path:
        path = f'seo_report.{format}'
    
    # Ensure correct extension
    if not path.endswith(f'.{format}'):
        path = f'{path}.{format}'
    
    # Check if directory exists
    output_dir = os.path.dirname(path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            raise click.BadParameter(f'Cannot create output directory: {e}')
    
    return path

def load_config_file(config_path: str) -> dict:
    """Load configuration from file"""
    if not os.path.exists(config_path):
        raise click.BadParameter(f'Config file not found: {config_path}')
    
    with open(config_path, 'r') as f:
        if config_path.endswith('.json'):
            return json.load(f)
        elif config_path.endswith(('.yml', '.yaml')):
            return yaml.safe_load(f)
        else:
            raise click.BadParameter('Config file must be JSON or YAML')

def create_progress():
    """Create a rich progress bar"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    )

@click.group()
@click.version_option(version=__version__, prog_name='tfq0seo')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Quiet mode (errors only)')
@click.pass_context
def cli(ctx, verbose, quiet):
    """tfq0seo - Professional SEO Analysis Toolkit"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    setup_logging(verbose, quiet)

@cli.command()
@click.argument('url')
@click.option('--depth', '-d', default=3, type=click.IntRange(1, 10), help='Crawl depth (1-10)')
@click.option('--max-pages', '-m', default=500, type=int, help='Maximum pages to crawl')
@click.option('--concurrent', '-c', default=10, type=click.IntRange(1, 50), help='Concurrent requests')
@click.option('--delay', default=0.5, type=float, help='Delay between requests (seconds)')
@click.option('--format', '-f', type=click.Choice(['json', 'csv', 'xlsx', 'html']), default='json', help='Output format')
@click.option('--output', '-o', help='Output file path')
@click.option('--exclude', multiple=True, help='Path patterns to exclude')
@click.option('--no-robots', is_flag=True, help='Ignore robots.txt')
@click.option('--include-external', is_flag=True, help='Include external links')
@click.option('--user-agent', default=None, help='Custom user agent')
@click.option('--config', '-C', help='Configuration file (JSON/YAML)')
@click.option('--resume', help='Resume from previous crawl state')
@click.option('--dry-run', is_flag=True, help='Show what would be crawled without actually crawling')
@click.option('--sitemap-only', is_flag=True, help='Only crawl URLs from sitemap.xml')
@click.pass_context
def crawl(ctx, url, depth, max_pages, concurrent, delay, format, output, exclude, 
         no_robots, include_external, user_agent, config, resume, dry_run, sitemap_only):
    """Crawl entire website and analyze SEO"""
    verbose = ctx.obj.get('verbose', False)
    quiet = ctx.obj.get('quiet', False)
    
    try:
        # Validate URL
        url = validate_url(url)
        
        # Load config file if provided
        if config:
            config_data = load_config_file(config)
            # Override with command line arguments
            url = url or config_data.get('url')
            depth = config_data.get('depth', depth)
            max_pages = config_data.get('max_pages', max_pages)
            concurrent = config_data.get('concurrent_requests', concurrent)
            delay = config_data.get('delay', delay)
            exclude = exclude or config_data.get('exclude_patterns', [])
            no_robots = config_data.get('ignore_robots', no_robots)
            include_external = config_data.get('include_external', include_external)
            user_agent = user_agent or config_data.get('user_agent')
        
        # Validate output path
        output_path = validate_output_path(output, format)
        
        # Validate concurrent requests
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        if concurrent > cpu_count * 4:
            console.print(f"[yellow]Warning: High concurrent requests ({concurrent}) for {cpu_count} CPUs[/yellow]")
        
        if not quiet:
            console.print(f"[bold green]Starting crawl of {url}[/bold green]")
            console.print(f"Depth: {depth}, Max pages: {max_pages}, Concurrent: {concurrent}")
            if dry_run:
                console.print("[yellow]DRY RUN MODE - No actual crawling will be performed[/yellow]")
        
        config = Config(
            url=url,
            depth=depth,
            max_pages=max_pages,
            concurrent_requests=concurrent,
            delay=delay,
            exclude_patterns=list(exclude),
            respect_robots=not no_robots,
            include_external=include_external,
            user_agent=user_agent,
            sitemap_only=sitemap_only
        )
        
        app = SEOAnalyzerApp(config)
        
        # Resume functionality
        crawl_state = None
        if resume and os.path.exists(resume):
            with open(resume, 'r') as f:
                crawl_state = json.load(f)
            if not quiet:
                console.print(f"[green]Resuming from {len(crawl_state.get('visited', []))} visited URLs[/green]")
        
        if dry_run:
            # Just show what would be crawled
            console.print("\n[bold]Would crawl:[/bold]")
            console.print(f"- Starting URL: {url}")
            console.print(f"- Depth: {depth}")
            console.print(f"- Max pages: {max_pages}")
            console.print(f"- Excluded patterns: {', '.join(exclude) if exclude else 'None'}")
            return
        
        with create_progress() as progress:
            task = progress.add_task("Crawling website...", total=max_pages)
            
            def update_progress(current, total):
                progress.update(task, completed=current)
            
            try:
                results = asyncio.run(app.crawl(
                    progress_callback=update_progress,
                    crawl_state=crawl_state
                ))
                
                # Save crawl state for resume
                state_file = f"{url.replace('https://', '').replace('http://', '').replace('/', '_')}_crawl_state.json"
                with open(state_file, 'w') as f:
                    json.dump({
                        'visited': [p['url'] for p in results.get('pages', [])],
                        'config': config.to_dict()
                    }, f)
                
                # Export results
                exporter = ExportManager()
                
                if format == 'json':
                    exporter.export_json(results, output_path)
                elif format == 'csv':
                    exporter.export_csv(results, output_path)
                elif format == 'xlsx':
                    exporter.export_xlsx(results, output_path)
                elif format == 'html':
                    exporter.export_html(results, output_path)
                
                if not quiet:
                    console.print(f"\n[bold green]✅ Crawl complete![/bold green]")
                    console.print(f"📊 Analyzed {len(results.get('pages', []))} pages")
                    console.print(f"💾 Results saved to: {output_path}")
                    console.print(f"📌 Crawl state saved to: {state_file}")
                    
                    # Show summary
                    show_summary(results)
                
            except asyncio.CancelledError:
                console.print("\n[yellow]Crawl cancelled by user[/yellow]")
                sys.exit(0)
            except Exception as e:
                console.print(f"[bold red]❌ Crawl error: {str(e)}[/bold red]")
                if verbose:
                    import traceback
                    console.print(traceback.format_exc())
                sys.exit(1)
                
    except click.BadParameter as e:
        console.print(f"[bold red]❌ {str(e)}[/bold red]")
        sys.exit(1)

@cli.command()
@click.argument('url')
@click.option('--comprehensive', '-c', is_flag=True, help='Run all analysis modules')
@click.option('--target-keyword', '-k', help='Primary keyword for optimization')
@click.option('--competitors', help='Comma-separated competitor URLs')
@click.option('--depth', type=click.Choice(['basic', 'advanced', 'complete']), default='advanced')
@click.option('--format', '-f', type=click.Choice(['json', 'csv', 'xlsx', 'html']), default='json')
@click.option('--output', '-o', help='Output file path')
@click.pass_context
def analyze(ctx, url, comprehensive, target_keyword, competitors, depth, format, output):
    """Analyze single URL for SEO"""
    verbose = ctx.obj.get('verbose', False)
    quiet = ctx.obj.get('quiet', False)
    
    try:
        # Validate URL
        url = validate_url(url)
        
        # Validate competitors
        competitor_urls = []
        if competitors:
            for comp_url in competitors.split(','):
                competitor_urls.append(validate_url(comp_url.strip()))
        
        # Validate output path
        output_path = validate_output_path(output, format)
        
        if not quiet:
            console.print(f"[bold green]Analyzing {url}[/bold green]")
        
        config = Config(
            url=url,
            comprehensive=comprehensive,
            target_keyword=target_keyword,
            competitors=competitor_urls,
            analysis_depth=depth
        )
        
        app = SEOAnalyzerApp(config)
        
        with console.status("Analyzing page..."):
            try:
                results = asyncio.run(app.analyze_single(url))
                
                # Export results
                exporter = ExportManager()
                
                if format == 'json':
                    exporter.export_json(results, output_path)
                elif format == 'csv':
                    exporter.export_csv(results, output_path)
                elif format == 'xlsx':
                    exporter.export_xlsx(results, output_path)
                elif format == 'html':
                    exporter.export_html(results, output_path)
                
                if not quiet:
                    console.print(f"\n[bold green]✅ Analysis complete![/bold green]")
                    console.print(f"💾 Results saved to: {output_path}")
                    
                    # Show analysis results
                    show_analysis_results(results)
                
            except Exception as e:
                console.print(f"[bold red]❌ Analysis error: {str(e)}[/bold red]")
                if verbose:
                    import traceback
                    console.print(traceback.format_exc())
                sys.exit(1)
                
    except click.BadParameter as e:
        console.print(f"[bold red]❌ {str(e)}[/bold red]")
        sys.exit(1)

@cli.command()
@click.argument('urls_file', type=click.Path(exists=True))
@click.option('--format', '-f', type=click.Choice(['json', 'csv', 'xlsx', 'html']), default='json')
@click.option('--output', '-o', help='Output file path')
@click.option('--concurrent', '-c', default=5, type=click.IntRange(1, 20), help='Concurrent analyses')
@click.pass_context
def batch(ctx, urls_file, format, output, concurrent):
    """Batch analyze multiple URLs from file"""
    verbose = ctx.obj.get('verbose', False)
    quiet = ctx.obj.get('quiet', False)
    
    try:
        # Read URLs from file
        with open(urls_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        # Validate URLs
        valid_urls = []
        for url in urls:
            try:
                valid_urls.append(validate_url(url))
            except click.BadParameter as e:
                console.print(f"[yellow]Skipping invalid URL: {url}[/yellow]")
        
        if not valid_urls:
            console.print("[bold red]No valid URLs found in file[/bold red]")
            sys.exit(1)
        
        # Validate output path
        output_path = validate_output_path(output, format)
        
        if not quiet:
            console.print(f"[bold green]Batch analyzing {len(valid_urls)} URLs[/bold green]")
        
        config = Config()
        app = SEOAnalyzerApp(config)
        
        with create_progress() as progress:
            task = progress.add_task("Analyzing URLs...", total=len(valid_urls))
            
            async def analyze_batch():
                results = []
                semaphore = asyncio.Semaphore(concurrent)
                
                async def analyze_with_semaphore(url):
                    async with semaphore:
                        try:
                            result = await app.analyze_single(url)
                            progress.update(task, advance=1)
                            return result
                        except Exception as e:
                            console.print(f"[red]Error analyzing {url}: {str(e)}[/red]")
                            return {'url': url, 'error': str(e)}
                
                tasks = [analyze_with_semaphore(url) for url in valid_urls]
                results = await asyncio.gather(*tasks)
                return results
            
            try:
                results = asyncio.run(analyze_batch())
                
                # Prepare batch results
                batch_results = {
                    'batch_analysis': True,
                    'total_urls': len(valid_urls),
                    'successful': sum(1 for r in results if 'error' not in r),
                    'failed': sum(1 for r in results if 'error' in r),
                    'results': results
                }
                
                # Export results
                exporter = ExportManager()
                
                if format == 'json':
                    exporter.export_json(batch_results, output_path)
                elif format == 'csv':
                    # Flatten results for CSV
                    flattened = []
                    for result in results:
                        if 'error' not in result:
                            flattened.append(result)
                    exporter.export_csv({'pages': flattened}, output_path)
                elif format == 'xlsx':
                    exporter.export_xlsx({'pages': results}, output_path)
                elif format == 'html':
                    exporter.export_html(batch_results, output_path)
                
                if not quiet:
                    console.print(f"\n[bold green]✅ Batch analysis complete![/bold green]")
                    console.print(f"📊 Analyzed {batch_results['successful']} URLs successfully")
                    if batch_results['failed'] > 0:
                        console.print(f"⚠️  {batch_results['failed']} URLs failed")
                    console.print(f"💾 Results saved to: {output_path}")
                
            except Exception as e:
                console.print(f"[bold red]❌ Batch analysis error: {str(e)}[/bold red]")
                if verbose:
                    import traceback
                    console.print(traceback.format_exc())
                sys.exit(1)
                
    except Exception as e:
        console.print(f"[bold red]❌ Error: {str(e)}[/bold red]")
        sys.exit(1)

@cli.command()
@click.argument('sitemap_url')
@click.option('--format', '-f', type=click.Choice(['json', 'csv', 'txt']), default='json')
@click.option('--output', '-o', help='Output file path')
@click.option('--analyze', is_flag=True, help='Analyze URLs from sitemap')
@click.pass_context
def sitemap(ctx, sitemap_url, format, output, analyze):
    """Extract and optionally analyze URLs from sitemap.xml"""
    verbose = ctx.obj.get('verbose', False)
    quiet = ctx.obj.get('quiet', False)
    
    try:
        # Validate URL
        sitemap_url = validate_url(sitemap_url)
        
        # Ensure it's a sitemap URL
        if not sitemap_url.endswith('.xml'):
            # Try common sitemap locations
            base_url = sitemap_url.rstrip('/')
            sitemap_url = f"{base_url}/sitemap.xml"
        
        if not quiet:
            console.print(f"[bold green]Processing sitemap: {sitemap_url}[/bold green]")
        
        config = Config(url=sitemap_url)
        app = SEOAnalyzerApp(config)
        
        with console.status("Fetching sitemap..."):
            try:
                # Use the crawler to fetch and parse sitemap
                urls = asyncio.run(app.extract_sitemap_urls(sitemap_url))
                
                if not urls:
                    console.print("[yellow]No URLs found in sitemap[/yellow]")
                    sys.exit(0)
                
                if not quiet:
                    console.print(f"[green]Found {len(urls)} URLs in sitemap[/green]")
                
                # Prepare output
                output_path = validate_output_path(output or 'sitemap_urls', format)
                
                if analyze:
                    # Analyze all URLs
                    console.print("[bold]Analyzing sitemap URLs...[/bold]")
                    
                    with create_progress() as progress:
                        task = progress.add_task("Analyzing URLs...", total=len(urls))
                        
                        async def analyze_sitemap_urls():
                            results = []
                            for url in urls:
                                try:
                                    result = await app.analyze_single(url['url'])
                                    result['lastmod'] = url.get('lastmod', '')
                                    result['priority'] = url.get('priority', '')
                                    results.append(result)
                                    progress.update(task, advance=1)
                                except Exception as e:
                                    results.append({
                                        'url': url['url'],
                                        'error': str(e),
                                        'lastmod': url.get('lastmod', ''),
                                        'priority': url.get('priority', '')
                                    })
                            return results
                        
                        results = asyncio.run(analyze_sitemap_urls())
                        
                        # Export analysis results
                        if format == 'json':
                            with open(output_path, 'w') as f:
                                json.dump({'sitemap_analysis': results}, f, indent=2)
                        elif format == 'csv':
                            import csv
                            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                                if results:
                                    writer = csv.DictWriter(f, fieldnames=results[0].keys())
                                    writer.writeheader()
                                    writer.writerows(results)
                else:
                    # Just export URLs
                    if format == 'json':
                        with open(output_path, 'w') as f:
                            json.dump({'sitemap_urls': urls}, f, indent=2)
                    elif format == 'csv':
                        import csv
                        with open(output_path, 'w', newline='', encoding='utf-8') as f:
                            writer = csv.DictWriter(f, fieldnames=['url', 'lastmod', 'priority'])
                            writer.writeheader()
                            writer.writerows(urls)
                    elif format == 'txt':
                        with open(output_path, 'w') as f:
                            for url in urls:
                                f.write(url['url'] + '\n')
                
                if not quiet:
                    console.print(f"[bold green]✅ Sitemap processed![/bold green]")
                    console.print(f"💾 Results saved to: {output_path}")
                
            except Exception as e:
                console.print(f"[bold red]❌ Sitemap error: {str(e)}[/bold red]")
                if verbose:
                    import traceback
                    console.print(traceback.format_exc())
                sys.exit(1)
                
    except click.BadParameter as e:
        console.print(f"[bold red]❌ {str(e)}[/bold red]")
        sys.exit(1)

@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'csv', 'xlsx', 'html']), required=True)
@click.option('--output', '-o', required=True, help='Output file path')
@click.option('--input', '-i', help='Input file (if converting formats)')
def export(format, output, input):
    """Export results to different formats"""
    try:
        exporter = ExportManager()
        
        if input:
            # Load data from input file
            if not os.path.exists(input):
                console.print(f"[bold red]Input file not found: {input}[/bold red]")
                sys.exit(1)
            
            with open(input, 'r') as f:
                data = json.load(f)
        else:
            console.print("[bold red]Please specify an input file with --input[/bold red]")
            sys.exit(1)
        
        # Validate output path
        output_path = validate_output_path(output, format)
        
        if format == 'json':
            exporter.export_json(data, output_path)
        elif format == 'csv':
            exporter.export_csv(data, output_path)
        elif format == 'xlsx':
            exporter.export_xlsx(data, output_path)
        elif format == 'html':
            exporter.export_html(data, output_path)
        
        console.print(f"[bold green]✅ Exported to {output_path}[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error: {str(e)}[/bold red]")
        sys.exit(1)

@cli.command()
def list():
    """List all available features"""
    table = Table(title="tfq0seo Features", style="bold blue")
    table.add_column("Feature", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    
    features = [
        ("Site Crawling", "Crawl entire websites with configurable depth and concurrency"),
        ("SEO Analysis", "Analyze meta tags, content, technical SEO, and performance"),
        ("Link Analysis", "Check internal/external links and find broken links"),
        ("Content Analysis", "Readability scores, keyword density, content structure"),
        ("Image Optimization", "Alt text, compression, formats, dimensions"),
        ("Performance Metrics", "Load times, Core Web Vitals, resource optimization"),
        ("Technical SEO", "HTTPS, mobile-friendly, structured data, canonical URLs"),
        ("Competitive Analysis", "Compare SEO metrics with competitors"),
        ("Batch Processing", "Analyze multiple URLs from file"),
        ("Sitemap Support", "Extract and analyze URLs from sitemap.xml"),
        ("Export Formats", "JSON, CSV, XLSX, HTML reports"),
        ("Configuration Files", "Load settings from JSON/YAML files"),
        ("Resume Capability", "Resume interrupted crawls"),
        ("Real-time Progress", "Live progress tracking with rich console output"),
    ]
    
    for feature, description in features:
        table.add_row(feature, description)
    
    console.print(table)

def show_summary(results):
    """Display crawl summary"""
    pages = results.get('pages', [])
    summary = results.get('summary', {})
    
    table = Table(title="SEO Summary", style="bold blue")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    
    table.add_row("Total Pages", str(len(pages)))
    table.add_row("Average SEO Score", f"{summary.get('average_seo_score', 0):.1f}")
    table.add_row("Average Load Time", f"{summary.get('average_load_time', 0):.2f}s")
    
    # Issue counts
    issue_counts = {}
    for page in pages:
        for issue in page.get('issues', []):
            severity = issue.get('severity', 'notice')
            issue_counts[severity] = issue_counts.get(severity, 0) + 1
    
    table.add_row("Critical Issues", str(issue_counts.get('critical', 0)))
    table.add_row("Warnings", str(issue_counts.get('warning', 0)))
    table.add_row("Notices", str(issue_counts.get('notice', 0)))
    
    # Page stats
    missing_titles = sum(1 for p in pages if not p.get('meta_tags', {}).get('title'))
    missing_descriptions = sum(1 for p in pages if not p.get('meta_tags', {}).get('description'))
    https_pages = sum(1 for p in pages if p.get('url', '').startswith('https://'))
    
    table.add_row("Missing Titles", str(missing_titles))
    table.add_row("Missing Descriptions", str(missing_descriptions))
    table.add_row("HTTPS Pages", f"{https_pages}/{len(pages)}")
    
    console.print(table)
    
    # Show top issues
    if summary.get('top_issues'):
        issue_table = Table(title="Top Issues", style="bold yellow")
        issue_table.add_column("Issue", style="yellow")
        issue_table.add_column("Count", style="white")
        issue_table.add_column("Severity", style="white")
        
        for issue in summary.get('top_issues', [])[:10]:
            issue_table.add_row(
                issue['message'][:60] + '...' if len(issue['message']) > 60 else issue['message'],
                str(issue['count']),
                issue['severity']
            )
        
        console.print(issue_table)

def show_analysis_results(results):
    """Display single page analysis results"""
    table = Table(title="SEO Analysis Results", style="bold blue")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Status", style="white")
    table.add_column("Details", style="white")
    
    # Meta tags
    meta = results.get('meta_tags', {})
    title_len = meta.get('title_length', 0)
    desc_len = meta.get('description_length', 0)
    
    title_status = "✅" if 30 <= title_len <= 60 else "⚠️"
    desc_status = "✅" if 120 <= desc_len <= 160 else "⚠️"
    
    table.add_row("Title Tag", title_status, f"{title_len} chars")
    table.add_row("Meta Description", desc_status, f"{desc_len} chars")
    
    # Content
    content = results.get('content', {})
    word_count = content.get('word_count', 0)
    readability = content.get('readability_scores', {}).get('flesch_reading_ease', 0)
    
    content_status = "✅" if word_count >= 300 else "⚠️"
    read_status = "✅" if readability >= 60 else "⚠️"
    
    table.add_row("Content Length", content_status, f"{word_count} words")
    table.add_row("Readability", read_status, f"Score: {readability:.1f}")
    
    # Technical
    technical = results.get('technical', {})
    https = technical.get('https', False)
    mobile = technical.get('mobile_friendly', False)
    
    table.add_row("HTTPS", "✅" if https else "❌", "Secure" if https else "Not secure")
    table.add_row("Mobile Friendly", "✅" if mobile else "❌", "Yes" if mobile else "No")
    
    # Performance
    performance = results.get('performance', {})
    load_time = performance.get('load_time', 0)
    
    perf_status = "✅" if load_time < 3 else "⚠️" if load_time < 5 else "❌"
    table.add_row("Load Time", perf_status, f"{load_time:.2f}s")
    
    # Overall score
    score = results.get('score', 0)
    score_status = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
    table.add_row("SEO Score", score_status, f"{score:.1f}/100")
    
    console.print(table)
    
    # Show issues if any
    issues = results.get('issues', [])
    if issues:
        issue_table = Table(title="Issues Found", style="bold yellow")
        issue_table.add_column("Type", style="yellow")
        issue_table.add_column("Severity", style="white")
        issue_table.add_column("Message", style="white")
        
        for issue in issues[:15]:  # Show first 15 issues
            issue_table.add_row(
                issue['type'],
                issue['severity'],
                issue['message'][:80] + '...' if len(issue['message']) > 80 else issue['message']
            )
        
        console.print(issue_table)

def main():
    """Main entry point"""
    cli(obj={})

if __name__ == '__main__':
    main() 
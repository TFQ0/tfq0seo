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

console = Console()

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
@click.version_option(version='2.1.0', prog_name='tfq0seo')
def cli():
    """tfq0seo - Professional SEO Analysis Toolkit"""
    pass

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
def crawl(url, depth, max_pages, concurrent, delay, format, output, exclude, no_robots, include_external, user_agent):
    """Crawl entire website and analyze SEO"""
    console.print(f"[bold green]Starting crawl of {url}[/bold green]")
    console.print(f"Depth: {depth}, Max pages: {max_pages}, Concurrent: {concurrent}")
    

    
    config = Config(
        url=url,
        depth=depth,
        max_pages=max_pages,
        concurrent_requests=concurrent,
        delay=delay,
        exclude_patterns=[*exclude],  # Convert tuple to list without using list()
        respect_robots=not no_robots,
        include_external=include_external,
        user_agent=user_agent
    )
    
    app = SEOAnalyzerApp(config)
    
    with create_progress() as progress:
        task = progress.add_task("Crawling website...", total=max_pages)
        
        def update_progress(current, total):
            progress.update(task, completed=current)
        
        try:
            results = asyncio.run(app.crawl(progress_callback=update_progress))
            
            # Export results
            exporter = ExportManager()
            output_path = output or f"seo_report.{format}"
            
            if format == 'json':
                exporter.export_json(results, output_path)
            elif format == 'csv':
                exporter.export_csv(results, output_path)
            elif format == 'xlsx':
                exporter.export_xlsx(results, output_path)
            elif format == 'html':
                exporter.export_html(results, output_path)
            
            console.print(f"\n[bold green]✅ Crawl complete![/bold green]")
            console.print(f"📊 Analyzed {len(results.get('pages', []))} pages")
            console.print(f"💾 Results saved to: {output_path}")
            
            # Show summary
            show_summary(results)
            
        except Exception as e:
            console.print(f"[bold red]❌ Error: {str(e)}[/bold red]")
            sys.exit(1)

@cli.command()
@click.argument('url')
@click.option('--comprehensive', '-c', is_flag=True, help='Run all analysis modules')
@click.option('--target-keyword', '-k', help='Primary keyword for optimization')
@click.option('--competitors', help='Comma-separated competitor URLs')
@click.option('--depth', type=click.Choice(['basic', 'advanced', 'complete']), default='advanced')
@click.option('--format', '-f', type=click.Choice(['json', 'csv', 'xlsx', 'html']), default='json')
@click.option('--output', '-o', help='Output file path')
def analyze(url, comprehensive, target_keyword, competitors, depth, format, output):
    """Analyze single URL for SEO"""
    console.print(f"[bold green]Analyzing {url}[/bold green]")
    
    config = Config(
        url=url,
        comprehensive=comprehensive,
        target_keyword=target_keyword,
        competitors=competitors.split(',') if competitors else [],
        analysis_depth=depth
    )
    
    app = SEOAnalyzerApp(config)
    
    with console.status("Analyzing page..."):
        try:
            results = asyncio.run(app.analyze_single(url))
            
            # Export results
            exporter = ExportManager()
            output_path = output or f"seo_analysis.{format}"
            
            if format == 'json':
                exporter.export_json(results, output_path)
            elif format == 'csv':
                exporter.export_csv(results, output_path)
            elif format == 'xlsx':
                exporter.export_xlsx(results, output_path)
            elif format == 'html':
                exporter.export_html(results, output_path)
            
            console.print(f"\n[bold green]✅ Analysis complete![/bold green]")
            console.print(f"💾 Results saved to: {output_path}")
            
            # Show analysis results
            show_analysis_results(results)
            
        except Exception as e:
            console.print(f"[bold red]❌ Error: {str(e)}[/bold red]")
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
            with open(input, 'r') as f:
                data = json.load(f)
        else:
            console.print("[bold red]Please specify an input file with --input[/bold red]")
            sys.exit(1)
        
        if format == 'json':
            exporter.export_json(data, output)
        elif format == 'csv':
            exporter.export_csv(data, output)
        elif format == 'xlsx':
            exporter.export_xlsx(data, output)
        elif format == 'html':
            exporter.export_html(data, output)
        
        console.print(f"[bold green]✅ Exported to {output}[/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error: {str(e)}[/bold red]")
        sys.exit(1)

@cli.command()
@click.option('--file', '-f', required=True, help='Content file to analyze')
@click.option('--keyword', '-k', required=True, help='Target keyword')
@click.option('--format', type=click.Choice(['json', 'txt']), default='json')
def analyze_content(file, keyword, format):
    """Analyze content for SEO optimization"""
    console.print(f"[bold green]Analyzing content for keyword: {keyword}[/bold green]")
    
    try:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        app = SEOAnalyzerApp(Config())
        results = app.analyze_content(content, keyword)
        
        if format == 'json':
            console.print_json(data=results)
        else:
            show_content_analysis(results)
        
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
        ("Competitive Analysis", "Compare SEO metrics with competitors"),
        ("Export Formats", "JSON, CSV, XLSX, HTML reports"),
        ("Robots.txt Support", "Respect crawl directives and sitemap.xml"),
        ("Real-time Progress", "Live progress tracking with rich console output"),
    ]
    
    for feature, description in features:
        table.add_row(feature, description)
    
    console.print(table)

def show_summary(results):
    """Display crawl summary"""
    pages = results.get('pages', [])
    issues = results.get('issues', {})
    
    table = Table(title="SEO Summary", style="bold blue")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    
    table.add_row("Total Pages", str(len(pages)))
    table.add_row("Critical Issues", str(issues.get('critical', 0)))
    table.add_row("Warnings", str(issues.get('warnings', 0)))
    table.add_row("Notices", str(issues.get('notices', 0)))
    
    # Page stats
    missing_titles = sum(1 for p in pages if not p.get('title'))
    missing_descriptions = sum(1 for p in pages if not p.get('meta_description'))
    https_pages = sum(1 for p in pages if p.get('url', '').startswith('https://'))
    
    table.add_row("Missing Titles", str(missing_titles))
    table.add_row("Missing Descriptions", str(missing_descriptions))
    table.add_row("HTTPS Pages", f"{https_pages}/{len(pages)}")
    
    console.print(table)

def show_analysis_results(results):
    """Display single page analysis results"""
    table = Table(title="SEO Analysis Results", style="bold blue")
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Status", style="white")
    table.add_column("Details", style="white")
    
    # Meta tags
    meta = results.get('meta_tags', {})
    title_len = len(meta.get('title', ''))
    desc_len = len(meta.get('description', ''))
    
    title_status = "✅" if 30 <= title_len <= 60 else "⚠️"
    desc_status = "✅" if 120 <= desc_len <= 160 else "⚠️"
    
    table.add_row("Title Tag", title_status, f"{title_len} chars")
    table.add_row("Meta Description", desc_status, f"{desc_len} chars")
    
    # Content
    content = results.get('content', {})
    word_count = content.get('word_count', 0)
    readability = content.get('readability_score', 0)
    
    content_status = "✅" if word_count >= 300 else "⚠️"
    read_status = "✅" if readability >= 60 else "⚠️"
    
    table.add_row("Content Length", content_status, f"{word_count} words")
    table.add_row("Readability", read_status, f"Score: {readability}")
    
    # Technical
    technical = results.get('technical', {})
    https = technical.get('https', False)
    mobile = technical.get('mobile_friendly', False)
    
    table.add_row("HTTPS", "✅" if https else "❌", "Secure" if https else "Not secure")
    table.add_row("Mobile Friendly", "✅" if mobile else "❌", "Yes" if mobile else "No")
    
    console.print(table)

def show_content_analysis(results):
    """Display content analysis results"""
    table = Table(title="Content Analysis", style="bold blue")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    table.add_column("Recommendation", style="yellow")
    
    table.add_row("Word Count", str(results.get('word_count', 0)), 
                  "Good" if results.get('word_count', 0) >= 300 else "Add more content")
    table.add_row("Keyword Density", f"{results.get('keyword_density', 0):.1f}%",
                  "Good" if results.get('keyword_density', 0) <= 3 else "Reduce keyword usage")
    table.add_row("Readability Score", str(results.get('readability_score', 0)),
                  "Good" if results.get('readability_score', 0) >= 60 else "Simplify text")
    table.add_row("Sentences", str(results.get('sentence_count', 0)), "")
    table.add_row("Paragraphs", str(results.get('paragraph_count', 0)), "")
    
    console.print(table)

def main():
    """Main entry point"""
    cli()

if __name__ == '__main__':
    main() 
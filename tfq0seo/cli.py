#!/usr/bin/env python3

import argparse
import sys
import asyncio
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from colorama import init, Fore, Style
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text

from .seo_analyzer_app import SEOAnalyzerApp, CrawlConfig
from .reporting.detailed_report import DetailedReport

def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser with all available options."""
    parser = argparse.ArgumentParser(
        description="Advanced SEO Analysis Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single URL and generate an HTML report
  %(prog)s analyze https://example.com --format html --output report.html

  # Analyze multiple URLs and generate JSON reports
  %(prog)s analyze https://site1.com https://site2.com --format json --output reports/

  # Analyze a URL with custom options
  %(prog)s analyze https://example.com --depth 3 --competitors 5 --format html
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Crawl command - NEW ENHANCED FEATURE
    crawl_parser = subparsers.add_parser(
        'crawl',
        help='Crawl and analyze an entire website (like Screaming Frog)'
    )
    crawl_parser.add_argument(
        'url',
        help='Starting URL to crawl'
    )
    crawl_parser.add_argument(
        '--depth',
        type=int,
        default=3,
        help='Maximum crawl depth (default: 3)'
    )
    crawl_parser.add_argument(
        '--max-pages',
        type=int,
        default=500,
        help='Maximum number of pages to crawl (default: 500)'
    )
    crawl_parser.add_argument(
        '--concurrent',
        type=int,
        default=10,
        help='Number of concurrent requests (default: 10)'
    )
    crawl_parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='Delay between requests in seconds (default: 0.5)'
    )
    crawl_parser.add_argument(
        '--format',
        choices=['json', 'csv', 'xlsx', 'html'],
        default='html',
        help='Output format (default: html)'
    )
    crawl_parser.add_argument(
        '--output',
        help='Output file path'
    )
    crawl_parser.add_argument(
        '--exclude',
        action='append',
        help='Path patterns to exclude (can be used multiple times)'
    )
    crawl_parser.add_argument(
        '--no-robots',
        action='store_true',
        help='Ignore robots.txt restrictions'
    )
    crawl_parser.add_argument(
        '--include-external',
        action='store_true',
        help='Include external links in analysis'
    )

    # Analyze command
    analyze_parser = subparsers.add_parser(
        'analyze', 
        help='Analyze URLs for SEO optimization'
    )
    analyze_parser.add_argument(
        'urls',
        nargs='+',
        help='One or more URLs to analyze'
    )
    analyze_parser.add_argument(
        '--format',
        choices=['html', 'json', 'csv'],
        default='html',
        help='Output format for the report (default: html)'
    )
    analyze_parser.add_argument(
        '--output',
        help='Output file or directory for the report(s)'
    )
    analyze_parser.add_argument(
        '--depth',
        type=int,
        default=2,
        help='Maximum crawl depth for analysis (default: 2)'
    )
    analyze_parser.add_argument(
        '--competitors',
        type=int,
        default=3,
        help='Number of competitors to analyze (default: 3)'
    )
    analyze_parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress progress output'
    )

    # Export command - NEW ENHANCED FEATURE
    export_parser = subparsers.add_parser(
        'export',
        help='Export crawl results to various formats'
    )
    export_parser.add_argument(
        '--format',
        choices=['json', 'csv', 'xlsx'],
        default='json',
        help='Export format (default: json)'
    )
    export_parser.add_argument(
        '--output',
        required=True,
        help='Output file path'
    )

    # Insights command - NEW ENHANCED FEATURE  
    insights_parser = subparsers.add_parser(
        'insights',
        help='Get quick insights from previous crawl'
    )
    insights_parser.add_argument(
        '--summary',
        action='store_true',
        help='Show summary statistics'
    )
    insights_parser.add_argument(
        '--recommendations',
        action='store_true',
        help='Show prioritized recommendations'
    )

    # List command for showing available features
    list_parser = subparsers.add_parser(
        'list',
        help='List available analysis features'
    )
    list_parser.add_argument(
        '--format',
        choices=['plain', 'rich'],
        default='rich',
        help='Output format for the feature list'
    )

    return parser

def format_output_path(url: str, base_path: Optional[str], format: str) -> Path:
    """Generate an appropriate output path for the report."""
    if not base_path:
        # Use current directory if no output path specified
        base_path = '.'
    
    base = Path(base_path)
    
    # If base_path is a directory or doesn't have an extension, create a filename
    if base.is_dir() or not base.suffix:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        filename = f"seo_report_{domain}_{format}"
        return base / f"{filename}.{format}"
    
    return base

def display_features(format: str = 'rich'):
    """Display available analysis features in a formatted table."""
    features = [
        ("Site Crawling", "Full site crawl with configurable depth and concurrency"),
        ("Technical SEO", "Meta tags, URLs, sitemaps, robots.txt"),
        ("Content Analysis", "Keywords, readability, structure, duplicate content"),
        ("Link Analysis", "Internal/external links, broken links, redirects"),
        ("Image Analysis", "Alt text, optimization, accessibility"),
        ("Performance", "Load time, resources, optimization"),
        ("User Experience", "Mobile-friendly, navigation, accessibility"),
        ("Competitive Analysis", "Feature comparison, market positioning"),
        ("Security", "HTTPS, certificates, vulnerabilities"),
        ("Rich Results", "Schema markup, structured data"),
        ("Site Structure", "URL analysis, orphaned pages, depth analysis"),
        ("Export Options", "JSON, CSV, XLSX, HTML reports")
    ]
    
    if format == 'rich':
        console = Console()
        table = Table(title="Available Analysis Features")
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        
        for category, description in features:
            table.add_row(category, description)
        
        console.print(Panel.fit(table, title="SEO Analyzer Features", border_style="cyan"))
    else:
        # Plain text output
        print("\nAvailable Analysis Features:")
        print("-" * 50)
        for category, description in features:
            print(f"\n{category}:")
            print(f"  {description}")

def run_analysis(args: argparse.Namespace):
    """Run the SEO analysis with progress reporting."""
    console = Console()
    analyzer = SEOAnalyzerApp()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        disable=args.quiet
    ) as progress:
        for url in args.urls:
            try:
                # Show analysis progress
                if not args.quiet:
                    console.print(f"\n[cyan]Analyzing[/cyan] {url}")
                
                task_id = progress.add_task(f"Analyzing {url}...", total=None)
                
                # Run the analysis
                results = analyzer.analyze_url(url)
                
                progress.update(task_id, completed=True)
                
                # Check if analysis was successful
                if 'error' in results:
                    console.print(f"[red]Error analyzing {url}:[/red] {results['error']}")
                    continue
                
                # Format and save the report
                output_path = format_output_path(url, args.output, args.format)
                
                # Ensure output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Generate the report based on format
                if args.format == 'json':
                    report = json.dumps(results, indent=2, default=str)
                elif args.format == 'html':
                    report = generate_simple_html_report(results)
                else:  # csv
                    report = generate_simple_csv_report(results)
                
                # Save the report to a file
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(report)
                
                if not args.quiet:
                    console.print(f"[green]Report saved:[/green] {output_path}")
                
            except Exception as e:
                console.print(f"[red]Error analyzing {url}:[/red] {str(e)}")
                continue

async def run_crawl(args: argparse.Namespace):
    """Run the enhanced site crawling with real-time progress."""
    console = Console()
    analyzer = SEOAnalyzerApp()
    
    # Create crawl configuration
    crawl_config = CrawlConfig(
        max_depth=args.depth,
        max_pages=args.max_pages,
        concurrent_requests=args.concurrent,
        delay_between_requests=args.delay,
        respect_robots_txt=not args.no_robots,
        include_external_links=args.include_external,
        excluded_paths=args.exclude or []
    )
    
    # Progress tracking
    crawl_progress = {}
    
    def progress_callback(data: Dict[str, Any]):
        crawl_progress.update(data)
    
    try:
        console.print(f"\n[cyan]🕷️  Starting comprehensive crawl of[/cyan] [bold]{args.url}[/bold]")
        console.print(f"[dim]Max depth: {args.depth} | Max pages: {args.max_pages} | Concurrent: {args.concurrent}[/dim]\n")
        
        # Create progress layout
        layout = Layout(name="root")
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="progress", size=10),
            Layout(name="footer", size=3)
        )
        
        with Live(layout, refresh_per_second=2) as live:
            # Start crawl
            results = await analyzer.crawl_and_analyze_site(
                args.url, 
                crawl_config, 
                progress_callback
            )
            
            # Update final progress
            layout["header"].update(Panel("[green]✅ Crawl completed![/green]", style="green"))
            
            # Generate report
            if args.output:
                output_path = Path(args.output)
            else:
                from urllib.parse import urlparse
                domain = urlparse(args.url).netloc
                output_path = Path(f"crawl_report_{domain}.{args.format}")
            
            # Export results
            if args.format == 'json':
                output_content = json.dumps(results, indent=2, default=str)
                # Save report
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(output_content)
            elif args.format == 'csv':
                output_content = analyzer.export_crawl_results('csv')
                # Save report
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(output_content)
            elif args.format == 'xlsx':
                # XLSX export handles file saving internally
                analyzer.export_crawl_results('xlsx', str(output_path))
            else:  # HTML
                output_content = generate_html_report(results)
                # Save report
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(output_content)
            
            # Display summary
            summary = results.get('crawl_summary', {})
            console.print(f"\n[green]🎉 Crawl completed successfully![/green]")
            console.print(f"[cyan]📊 Summary:[/cyan]")
            console.print(f"  • Pages crawled: {summary.get('total_urls_crawled', 0)}")
            console.print(f"  • Failed URLs: {summary.get('total_urls_failed', 0)}")
            console.print(f"  • Duration: {summary.get('crawl_duration', 0):.2f} seconds")
            console.print(f"  • Report saved: [bold]{output_path}[/bold]")
            
    except Exception as e:
        console.print(f"[red]❌ Crawl failed:[/red] {str(e)}")
        sys.exit(1)

def run_export(args: argparse.Namespace):
    """Export crawl results to specified format."""
    console = Console()
    analyzer = SEOAnalyzerApp()
    
    try:
        output = analyzer.export_crawl_results(args.format, args.output)
        console.print(f"[green]✅ Results exported to:[/green] {args.output}")
    except Exception as e:
        console.print(f"[red]❌ Export failed:[/red] {str(e)}")
        sys.exit(1)

def run_insights(args: argparse.Namespace):
    """Display insights from crawl results."""
    console = Console()
    analyzer = SEOAnalyzerApp()
    
    try:
        insights = analyzer.get_crawl_insights()
        
        if not insights:
            console.print("[yellow]⚠️  No crawl data available. Run a crawl first.[/yellow]")
            return
        
        # Display overview
        overview = insights.get('overview', {})
        console.print("\n[cyan]📊 Crawl Overview[/cyan]")
        console.print(f"  • Total pages: {overview.get('total_pages', 0)}")
        console.print(f"  • Total issues: {overview.get('total_issues', 0)}")
        console.print(f"  • Coverage: {overview.get('crawl_coverage', 'Unknown')}")
        
        # Display critical issues
        if args.summary:
            critical = insights.get('critical_issues', {})
            console.print("\n[red]🚨 Critical Issues[/red]")
            console.print(f"  • Broken links: {critical.get('broken_links', 0)}")
            console.print(f"  • Duplicate content: {critical.get('duplicate_content', 0)}")
            console.print(f"  • Failed URLs: {critical.get('failed_urls', 0)}")
        
        if args.recommendations:
            console.print("\n[yellow]💡 Recommendations[/yellow]")
            console.print("  • Fix broken links to improve user experience")
            console.print("  • Address duplicate content issues")
            console.print("  • Optimize page load times")
            console.print("  • Add missing meta descriptions")
            
    except Exception as e:
        console.print(f"[red]❌ Insights failed:[/red] {str(e)}")

def generate_html_report(results: Dict[str, Any]) -> str:
    """Generate HTML report from crawl results."""
    summary = results.get('crawl_summary', {})
    analysis = results.get('analysis_results', {})
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>TFQ0SEO Crawl Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; }}
            .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
            .metric {{ background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #007bff; }}
            .metric h3 {{ margin: 0 0 10px 0; color: #333; }}
            .metric .value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
            .issues {{ background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            .recommendations {{ background: #d1ecf1; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🕷️ TFQ0SEO Crawl Report</h1>
            <p>Comprehensive site analysis completed on {results.get('analysis_metadata', {}).get('timestamp', 'Unknown')}</p>
        </div>
        
        <div class="summary">
            <div class="metric">
                <h3>Pages Crawled</h3>
                <div class="value">{summary.get('total_urls_crawled', 0)}</div>
            </div>
            <div class="metric">
                <h3>Failed URLs</h3>
                <div class="value">{summary.get('total_urls_failed', 0)}</div>
            </div>
            <div class="metric">
                <h3>Duration</h3>
                <div class="value">{summary.get('crawl_duration', 0):.1f}s</div>
            </div>
            <div class="metric">
                <h3>Sitemap URLs</h3>
                <div class="value">{summary.get('sitemap_urls_found', 0)}</div>
            </div>
        </div>
        
        <div class="issues">
            <h2>🚨 Issues Found</h2>
            <ul>
                <li>Broken links: {len(analysis.get('site_wide_analysis', {}).get('broken_links', []))}</li>
                <li>Duplicate content: {len(analysis.get('site_wide_analysis', {}).get('duplicate_content', []))}</li>
                <li>Orphaned pages: {len(analysis.get('site_wide_analysis', {}).get('orphaned_pages', []))}</li>
            </ul>
        </div>
        
        <div class="recommendations">
            <h2>💡 Recommendations</h2>
            <ul>
                <li>Fix broken links to improve user experience and SEO</li>
                <li>Address duplicate content issues</li>
                <li>Optimize internal linking structure</li>
                <li>Add missing meta descriptions and titles</li>
            </ul>
        </div>
        
        <footer style="margin-top: 40px; text-align: center; color: #666;">
            <p>Generated by TFQ0SEO v2.0 - Enhanced SEO Analysis Tool</p>
        </footer>
    </body>
    </html>
    """
    
    return html_template

def generate_simple_html_report(results: Dict[str, Any]) -> str:
    """Generate a simple HTML report from analyze_url results."""
    url = results.get('url', 'Unknown URL')
    seo_score = results.get('seo_score', 0)
    insights = results.get('insights', {})
    timestamp = results.get('timestamp', 'Unknown')
    
    critical_issues = insights.get('critical_issues', [])
    opportunities = insights.get('opportunities', [])
    strengths = insights.get('strengths', [])
    recommendations = insights.get('recommendations', [])
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SEO Analysis Report - {url}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .score {{ font-size: 48px; font-weight: bold; color: #007bff; text-align: center; }}
        .section {{ margin: 30px 0; padding: 20px; border-radius: 8px; }}
        .critical {{ background: #f8d7da; border-left: 4px solid #dc3545; }}
        .opportunities {{ background: #fff3cd; border-left: 4px solid #ffc107; }}
        .strengths {{ background: #d4edda; border-left: 4px solid #28a745; }}
        .recommendations {{ background: #d1ecf1; border-left: 4px solid #17a2b8; }}
        h1, h2 {{ color: #333; }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 8px 0; }}
        .timestamp {{ color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>SEO Analysis Report</h1>
        <p><strong>URL:</strong> {url}</p>
        <p class="timestamp">Generated: {timestamp}</p>
        <div class="score">{seo_score}/100</div>
    </div>
    
    {f'''
    <div class="section critical">
        <h2>🚨 Critical Issues ({len(critical_issues)})</h2>
        <ul>
            {''.join(f'<li>{issue}</li>' for issue in critical_issues)}
        </ul>
    </div>
    ''' if critical_issues else ''}
    
    {f'''
    <div class="section opportunities">
        <h2>💡 Opportunities ({len(opportunities)})</h2>
        <ul>
            {''.join(f'<li>{opp}</li>' for opp in opportunities)}
        </ul>
    </div>
    ''' if opportunities else ''}
    
    {f'''
    <div class="section strengths">
        <h2>✅ Strengths ({len(strengths)})</h2>
        <ul>
            {''.join(f'<li>{strength}</li>' for strength in strengths)}
        </ul>
    </div>
    ''' if strengths else ''}
    
    {f'''
    <div class="section recommendations">
        <h2>📋 Recommendations ({len(recommendations)})</h2>
        <ul>
            {''.join(f'<li>{rec}</li>' for rec in recommendations)}
        </ul>
    </div>
    ''' if recommendations else ''}
    
</body>
</html>
"""
    return html

def generate_simple_csv_report(results: Dict[str, Any]) -> str:
    """Generate a simple CSV report from analyze_url results."""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Metric', 'Value'])
    
    # Basic info
    writer.writerow(['URL', results.get('url', 'Unknown')])
    writer.writerow(['SEO Score', results.get('seo_score', 0)])
    writer.writerow(['Timestamp', results.get('timestamp', 'Unknown')])
    
    # Insights summary
    insights = results.get('insights', {})
    writer.writerow(['Critical Issues', len(insights.get('critical_issues', []))])
    writer.writerow(['Opportunities', len(insights.get('opportunities', []))])
    writer.writerow(['Strengths', len(insights.get('strengths', []))])
    writer.writerow(['Recommendations', len(insights.get('recommendations', []))])
    
    # Add empty row
    writer.writerow([])
    
    # Critical Issues
    writer.writerow(['Critical Issues Detail', ''])
    for issue in insights.get('critical_issues', []):
        writer.writerow(['', issue])
    
    # Opportunities
    writer.writerow(['Opportunities Detail', ''])
    for opp in insights.get('opportunities', []):
        writer.writerow(['', opp])
    
    # Strengths
    writer.writerow(['Strengths Detail', ''])
    for strength in insights.get('strengths', []):
        writer.writerow(['', strength])
    
    # Recommendations
    writer.writerow(['Recommendations Detail', ''])
    for rec in insights.get('recommendations', []):
        writer.writerow(['', rec])
    
    return output.getvalue()

def main():
    """Main entry point for the SEO analyzer CLI."""
    # Initialize colorama for Windows color support
    init()
    
    # Parse command line arguments
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'crawl':
            asyncio.run(run_crawl(args))
        elif args.command == 'analyze':
            run_analysis(args)
        elif args.command == 'export':
            run_export(args)
        elif args.command == 'insights':
            run_insights(args)
        elif args.command == 'list':
            display_features(args.format)
    except KeyboardInterrupt:
        print("\nAnalysis cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == '__main__':
    main() 
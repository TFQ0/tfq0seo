#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path
from typing import List, Optional
from colorama import init, Fore, Style
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from seo_analyzer_app import SEOAnalyzerApp
from reporting.report_formatter import ReportFormatter

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
        ("Technical SEO", "Meta tags, URLs, sitemaps, robots.txt"),
        ("Content Analysis", "Keywords, readability, structure"),
        ("Performance", "Load time, resources, optimization"),
        ("User Experience", "Mobile-friendly, navigation, accessibility"),
        ("Competitive Analysis", "Feature comparison, market positioning"),
        ("Security", "HTTPS, certificates, vulnerabilities"),
        ("Rich Results", "Schema markup, structured data"),
        ("Link Architecture", "Internal/external links, anchor text")
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
                results = analyzer.analyze_url(
                    url,
                    max_depth=args.depth,
                    num_competitors=args.competitors
                )
                
                progress.update(task_id, completed=True)
                
                # Format and save the report
                formatter = ReportFormatter(results)
                output_path = format_output_path(url, args.output, args.format)
                
                # Ensure output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Generate the report
                report = formatter.format_report(args.format, str(output_path))
                
                if not args.quiet:
                    console.print(f"[green]Report saved:[/green] {output_path}")
                
            except Exception as e:
                console.print(f"[red]Error analyzing {url}:[/red] {str(e)}")
                continue

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
        if args.command == 'analyze':
            run_analysis(args)
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
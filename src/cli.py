import argparse
import sys
from typing import List, Optional
from pathlib import Path

from .seo_analyzer_app import SEOAnalyzerApp
from .utils.error_handler import TFQ0SEOError

def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser for tfq0seo.
    
    Sets up the CLI interface with commands for:
    - URL analysis
    - Content analysis
    - Educational resources
    
    Returns:
        Configured argument parser with all commands and options
    """
    parser = argparse.ArgumentParser(
        description='tfq0seo - Modern SEO analysis and optimization toolkit'
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # URL analysis command
    url_parser = subparsers.add_parser(
        'analyze-url',
        help='Analyze a URL for SEO optimization'
    )
    url_parser.add_argument('url', help='Target URL to analyze')
    url_parser.add_argument(
        '--keyword',
        help='Focus keyword for targeted analysis'
    )
    url_parser.add_argument(
        '--format',
        choices=['json', 'html', 'markdown'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    
    # Content analysis command
    content_parser = subparsers.add_parser(
        'analyze-content',
        help='Analyze text content for SEO optimization'
    )
    content_parser.add_argument(
        '--file',
        type=str,
        help='Path to file containing content to analyze'
    )
    content_parser.add_argument(
        '--text',
        type=str,
        help='Direct text input for analysis'
    )
    content_parser.add_argument(
        '--keyword',
        help='Focus keyword for targeted analysis'
    )
    content_parser.add_argument(
        '--format',
        choices=['json', 'html', 'markdown'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    
    # Educational resources command
    edu_parser = subparsers.add_parser(
        'education',
        help='Access SEO educational resources and best practices'
    )
    edu_parser.add_argument(
        '--topic',
        choices=['meta_tags', 'content_optimization', 'technical_seo'],
        help='Specific SEO topic to learn about'
    )
    
    return parser

def analyze_url(app: SEOAnalyzerApp, args: argparse.Namespace) -> None:
    """Handle URL analysis command for tfq0seo.
    
    Performs comprehensive SEO analysis on the specified URL:
    - Technical SEO validation
    - Content optimization check
    - Mobile-friendliness
    - Performance metrics
    - Security analysis
    
    Args:
        app: SEOAnalyzerApp instance
        args: Command line arguments
    
    Exits with status code 1 on error
    """
    try:
        analysis = app.analyze_url(args.url, args.keyword)
        print(app.export_report(analysis, args.format))
    except TFQ0SEOError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def analyze_content(app: SEOAnalyzerApp, args: argparse.Namespace) -> None:
    """Handle content analysis command for tfq0seo.
    
    Analyzes content for SEO optimization:
    - Keyword optimization
    - Readability analysis
    - Content structure
    - SEO best practices
    
    Args:
        app: SEOAnalyzerApp instance
        args: Command line arguments
    
    Exits with status code 1 on error
    """
    try:
        # Get content from file or direct input
        if args.file:
            with open(args.file, 'r') as f:
                content = f.read()
        elif args.text:
            content = args.text
        else:
            print("Error: Either --file or --text must be provided", file=sys.stderr)
            sys.exit(1)
        
        analysis = app.analyze_content(content, args.keyword)
        print(app.export_report(analysis, args.format))
    except TFQ0SEOError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

def show_education(app: SEOAnalyzerApp, args: argparse.Namespace) -> None:
    """Handle educational resources command for tfq0seo.
    
    Provides access to SEO learning resources:
    - Best practices
    - Implementation guides
    - Optimization tips
    - Technical explanations
    
    Args:
        app: SEOAnalyzerApp instance
        args: Command line arguments
    """
    resources = app.get_educational_resources(args.topic)
    
    if args.topic:
        # Show specific topic
        topic_resources = resources[args.topic]
        print(f"\n{args.topic.replace('_', ' ').title()} Resources:")
        for resource in topic_resources:
            print(f"\n{resource['title']}")
            print(f"Description: {resource['description']}")
            print("Key Points:")
            for point in resource['key_points']:
                print(f"  • {point}")
    else:
        # Show all topics
        print("\ntfq0seo Educational Resources:")
        for topic, topic_resources in resources.items():
            print(f"\n{topic.replace('_', ' ').title()}:")
            for resource in topic_resources:
                print(f"  • {resource['title']}")
                print(f"    {resource['description']}")

def main(argv: Optional[List[str]] = None) -> None:
    """Main entry point for tfq0seo CLI.
    
    Handles command line interface:
    - Argument parsing
    - Command routing
    - Error handling
    - Output formatting
    
    Args:
        argv: Optional list of command line arguments
    
    Exits with status code 1 on error
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        app = SEOAnalyzerApp()
        
        if args.command == 'analyze-url':
            analyze_url(app, args)
        elif args.command == 'analyze-content':
            analyze_content(app, args)
        elif args.command == 'education':
            show_education(app, args)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main() 
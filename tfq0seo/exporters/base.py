"""
Export manager for different output formats
"""
import json
import csv
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
import jinja2
from datetime import datetime

class ExportManager:
    """Manager for exporting SEO analysis results"""
    
    def __init__(self):
        self.template_dir = Path(__file__).parent.parent / 'templates'
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir))
        )
    
    def export_json(self, data: Dict[str, Any], output_path: str):
        """Export results as JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def export_csv(self, data: Dict[str, Any], output_path: str):
        """Export results as CSV"""
        # Check if this is single page analysis or crawl data
        is_single_page = 'pages' not in data and 'url' in data
        
        if is_single_page:
            pages = [data]  # Wrap single page in list
        else:
            pages = data.get('pages', [])
        
        if not pages:
            return
        
        # Flatten page data for CSV
        rows = []
        for page in pages:
            row = {
                'url': page.get('url', ''),
                'title': page.get('title', ''),
                'title_length': page.get('meta_tags', {}).get('title_length', 0),
                'description': page.get('meta_description', ''),
                'description_length': page.get('meta_tags', {}).get('description_length', 0),
                'status_code': page.get('status_code', 0),
                'load_time': page.get('load_time', 0),
                'word_count': page.get('content', {}).get('word_count', 0),
                'readability_score': page.get('content', {}).get('readability_score', 0),
                'h1_count': page.get('meta_tags', {}).get('h1_count', 0),
                'internal_links': page.get('links', {}).get('internal_links', 0),
                'external_links': page.get('links', {}).get('external_links', 0),
                'images': page.get('content', {}).get('images', {}).get('total', 0),
                'score': page.get('score', 0),
                'issues_count': len(page.get('issues', []))
            }
            rows.append(row)
        
        # Write CSV
        if rows:
            fieldnames = rows[0].keys()
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
    
    def export_xlsx(self, data: Dict[str, Any], output_path: str):
        """Export results as Excel file with multiple sheets"""
        # Check if this is single page analysis or crawl data
        is_single_page = 'pages' not in data and 'url' in data
        
        if is_single_page:
            # Convert single page data to crawl format
            page_data = data
            data = {
                'config': {'url': page_data.get('url', 'Unknown')},
                'pages': [page_data],
                'summary': {
                    'total_pages': 1,
                    'average_seo_score': page_data.get('score', 0),
                    'average_load_time': page_data.get('load_time', 0),
                    'average_word_count': page_data.get('content', {}).get('word_count', 0)
                },
                'issues': {
                    'critical': sum(1 for i in page_data.get('issues', []) if i.get('severity') == 'critical'),
                    'warnings': sum(1 for i in page_data.get('issues', []) if i.get('severity') == 'warning'),
                    'notices': sum(1 for i in page_data.get('issues', []) if i.get('severity') == 'notice')
                }
            }
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = self._prepare_summary_sheet(data)
            if summary_data:
                pd.DataFrame([summary_data]).to_excel(
                    writer, sheet_name='Summary', index=False
                )
            
            # Pages sheet
            pages_df = self._prepare_pages_dataframe(data.get('pages', []))
            if not pages_df.empty:
                pages_df.to_excel(writer, sheet_name='Pages', index=False)
            
            # Issues sheet
            issues_df = self._prepare_issues_dataframe(data.get('pages', []))
            if not issues_df.empty:
                issues_df.to_excel(writer, sheet_name='Issues', index=False)
            
            # Top issues sheet
            top_issues = data.get('summary', {}).get('top_issues', [])
            if top_issues:
                pd.DataFrame(top_issues).to_excel(
                    writer, sheet_name='Top Issues', index=False
                )
    
    def export_html(self, data: Dict[str, Any], output_path: str):
        """Export results as HTML report"""
        # Check if this is single page analysis or crawl data
        is_single_page = 'pages' not in data and 'url' in data
        
        if is_single_page:
            # Convert single page data to crawl format
            page_data = data
            data = {
                'config': {'url': page_data.get('url', 'Unknown')},
                'pages': [page_data],
                'summary': {
                    'total_pages': 1,
                    'average_seo_score': page_data.get('score', 0),
                    'average_load_time': page_data.get('load_time', 0),
                    'average_word_count': page_data.get('content', {}).get('word_count', 0),
                    'top_issues': []
                },
                'issues': {
                    'critical': sum(1 for i in page_data.get('issues', []) if i.get('severity') == 'critical'),
                    'warnings': sum(1 for i in page_data.get('issues', []) if i.get('severity') == 'warning'),
                    'notices': sum(1 for i in page_data.get('issues', []) if i.get('severity') == 'notice')
                }
            }
            
            # Group issues for top issues
            issue_counts = {}
            for issue in page_data.get('issues', []):
                key = (issue['type'], issue['message'], issue['severity'])
                if key not in issue_counts:
                    issue_counts[key] = 0
                issue_counts[key] += 1
            
            data['summary']['top_issues'] = [
                {
                    'type': k[0],
                    'message': k[1],
                    'severity': k[2],
                    'count': v
                }
                for k, v in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
            ][:10]
        
        # Create template if it doesn't exist
        template_path = self.template_dir / 'report.html'
        if not template_path.exists():
            self._create_default_template()
        
        # Load template
        template = self.jinja_env.get_template('report.html')
        
        # Prepare data
        report_data = {
            'title': f"SEO Report - {data.get('config', {}).get('url', 'Website')}",
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data': data,
            'summary': data.get('summary', {}),
            'pages': data.get('pages', []),
            'issues': data.get('issues', {}),
            'config': data.get('config', {})
        }
        
        # Render template
        html_content = template.render(**report_data)
        
        # Write file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _prepare_summary_sheet(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare summary data for Excel"""
        summary = data.get('summary', {})
        config = data.get('config', {})
        issues = data.get('issues', {})
        
        return {
            'Website': config.get('url', ''),
            'Total Pages': summary.get('total_pages', 0),
            'Average Load Time': summary.get('average_load_time', 0),
            'Average Word Count': summary.get('average_word_count', 0),
            'Average SEO Score': summary.get('average_seo_score', 0),
            'Critical Issues': issues.get('critical', 0),
            'Warnings': issues.get('warnings', 0),
            'Notices': issues.get('notices', 0),
            'Pages Missing Title': summary.get('pages_missing_title', 0),
            'Pages Missing Description': summary.get('pages_missing_description', 0),
            'Slow Loading Pages': summary.get('slow_loading_pages', 0),
            'Thin Content Pages': summary.get('thin_content_pages', 0)
        }
    
    def _prepare_pages_dataframe(self, pages: List[Dict]) -> pd.DataFrame:
        """Prepare pages data for Excel"""
        if not pages:
            return pd.DataFrame()
        
        rows = []
        for page in pages:
            row = {
                'URL': page.get('url', ''),
                'Title': page.get('title', ''),
                'Title Length': page.get('meta_tags', {}).get('title_length', 0),
                'Description': page.get('meta_description', ''),
                'Description Length': page.get('meta_tags', {}).get('description_length', 0),
                'Status Code': page.get('status_code', 0),
                'Load Time (s)': round(page.get('load_time', 0), 2),
                'Word Count': page.get('content', {}).get('word_count', 0),
                'Readability Score': page.get('content', {}).get('readability_score', 0),
                'H1 Count': page.get('meta_tags', {}).get('h1_count', 0),
                'Internal Links': page.get('links', {}).get('internal_links', 0),
                'External Links': page.get('links', {}).get('external_links', 0),
                'Images': page.get('content', {}).get('images', {}).get('total', 0),
                'SEO Score': page.get('score', 0),
                'Issues': len(page.get('issues', []))
            }
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def _prepare_issues_dataframe(self, pages: List[Dict]) -> pd.DataFrame:
        """Prepare issues data for Excel"""
        all_issues = []
        
        for page in pages:
            url = page.get('url', '')
            for issue in page.get('issues', []):
                all_issues.append({
                    'URL': url,
                    'Type': issue.get('type', ''),
                    'Severity': issue.get('severity', ''),
                    'Message': issue.get('message', '')
                })
        
        return pd.DataFrame(all_issues)
    
    def _create_default_template(self):
        """Create default HTML template"""
        template_dir = self.template_dir
        template_dir.mkdir(parents=True, exist_ok=True)
        
        template_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .header {
            background: #2c3e50;
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
        }
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .card h3 {
            margin-top: 0;
            color: #2c3e50;
        }
        .metric {
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }
        .issues-summary {
            display: flex;
            gap: 20px;
            margin: 20px 0;
        }
        .issue-badge {
            padding: 10px 20px;
            border-radius: 5px;
            color: white;
            font-weight: bold;
        }
        .critical { background: #e74c3c; }
        .warning { background: #f39c12; }
        .notice { background: #95a5a6; }
        table {
            width: 100%;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #34495e;
            color: white;
        }
        tr:hover {
            background: #f5f5f5;
        }
        .score {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
        }
        .score-good { background: #2ecc71; color: white; }
        .score-medium { background: #f39c12; color: white; }
        .score-poor { background: #e74c3c; color: white; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p>Generated: {{ generated_at }}</p>
        <p>Website: {{ config.url }}</p>
    </div>
    
    <div class="summary-cards">
        <div class="card">
            <h3>Total Pages</h3>
            <div class="metric">{{ summary.total_pages }}</div>
        </div>
        <div class="card">
            <h3>Average SEO Score</h3>
            <div class="metric">{{ "%.1f"|format(summary.average_seo_score) }}</div>
        </div>
        <div class="card">
            <h3>Average Load Time</h3>
            <div class="metric">{{ "%.2f"|format(summary.average_load_time) }}s</div>
        </div>
        <div class="card">
            <h3>Average Word Count</h3>
            <div class="metric">{{ summary.average_word_count }}</div>
        </div>
    </div>
    
    <div class="card">
        <h2>Issues Summary</h2>
        <div class="issues-summary">
            <div class="issue-badge critical">{{ issues.critical }} Critical</div>
            <div class="issue-badge warning">{{ issues.warnings }} Warnings</div>
            <div class="issue-badge notice">{{ issues.notices }} Notices</div>
        </div>
    </div>
    
    <div class="card">
        <h2>Top Issues</h2>
        <table>
            <thead>
                <tr>
                    <th>Type</th>
                    <th>Message</th>
                    <th>Severity</th>
                    <th>Count</th>
                </tr>
            </thead>
            <tbody>
                {% for issue in summary.top_issues %}
                <tr>
                    <td>{{ issue.type }}</td>
                    <td>{{ issue.message }}</td>
                    <td><span class="issue-badge {{ issue.severity }}">{{ issue.severity }}</span></td>
                    <td>{{ issue.count }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    <div class="card">
        <h2>Pages Analysis</h2>
        <table>
            <thead>
                <tr>
                    <th>URL</th>
                    <th>Title</th>
                    <th>Load Time</th>
                    <th>Word Count</th>
                    <th>Score</th>
                    <th>Issues</th>
                </tr>
            </thead>
            <tbody>
                {% for page in pages[:50] %}
                <tr>
                    <td><a href="{{ page.url }}" target="_blank">{{ page.url[:50] }}...</a></td>
                    <td>{{ page.title[:40] }}...</td>
                    <td>{{ "%.2f"|format(page.load_time) }}s</td>
                    <td>{{ page.content.word_count }}</td>
                    <td>
                        <span class="score {% if page.score >= 80 %}score-good{% elif page.score >= 60 %}score-medium{% else %}score-poor{% endif %}">
                            {{ page.score }}
                        </span>
                    </td>
                    <td>{{ page.issues|length }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>'''
        
        template_path = template_dir / 'report.html'
        template_path.write_text(template_content) 
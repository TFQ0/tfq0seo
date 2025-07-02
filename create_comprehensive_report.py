import json
import datetime
from pathlib import Path

def get_score_class(score):
    """Determine CSS class based on score"""
    if score >= 80: return 'excellent'
    elif score >= 60: return 'good'
    elif score >= 40: return 'warning'
    else: return 'poor'

def create_comprehensive_report():
    print('=== CREATING COMPREHENSIVE HTML REPORT ===')
    
    # Read the detailed JSON data
    with open('test_example.json') as f:
        data = json.load(f)
    
    # Extract data
    url = data.get('url', 'N/A')
    timestamp = data.get('timestamp', 'N/A')
    version = '2.1.0'
    scores = data.get('scores', {})
    overall_score = scores.get('overall_score', 0)
    category_scores = scores.get('category_scores', {})
    insights = data.get('insights', {})
    summary = data.get('summary', {}).get('overview', {})
    modules = data.get('analysis_modules', {})
    
    # Generate HTML sections
    critical_issues_html = '\n'.join([f'<li class="issue-item critical">🚨 {issue}</li>' for issue in insights.get('critical_issues', [])])
    opportunities_html = '\n'.join([f'<li class="issue-item warning">💡 {issue}</li>' for issue in insights.get('opportunities', [])])
    strengths_html = '\n'.join([f'<li class="issue-item success">✅ {issue}</li>' for issue in insights.get('strengths', [])])
    recommendations_html = '\n'.join([f'<li class="issue-item info">📌 {rec}</li>' for rec in insights.get('recommendations', [])])
    
    # Generate module analysis
    module_analysis_html = ''
    for module_name, module_data in modules.items():
        strengths_list = '\n'.join([f'<li class="success">✅ {item}</li>' for item in module_data.get('strengths', [])])
        weaknesses_list = '\n'.join([f'<li class="warning">⚠️ {item}</li>' for item in module_data.get('weaknesses', [])])
        recs_list = '\n'.join([f'<li class="info">💡 {item}</li>' for item in module_data.get('recommendations', [])])
        
        module_analysis_html += f'''
        <div class="module-section">
            <div class="module-title">{module_name.replace('_', ' ').title()} Analysis</div>
            <div><strong>Strengths ({len(module_data.get('strengths', []))}):</strong></div>
            <ul>{strengths_list}</ul>
            <div><strong>Issues Found ({len(module_data.get('weaknesses', []))}):</strong></div>
            <ul>{weaknesses_list}</ul>
            <div><strong>Recommendations ({len(module_data.get('recommendations', []))}):</strong></div>
            <ul>{recs_list}</ul>
        </div>
        '''
    
    # Create comprehensive HTML
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comprehensive SEO Analysis Report - {url}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6; 
            color: #333; 
            background: #f8f9fa;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 12px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header p {{ font-size: 1.2em; opacity: 0.9; }}
        .score-container {{ 
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .score-card {{ 
            background: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .score-number {{ font-size: 3em; font-weight: bold; }}
        .score-label {{ font-size: 1.1em; color: #666; margin-top: 10px; }}
        .excellent {{ color: #28a745; }}
        .good {{ color: #20c997; }}
        .warning {{ color: #ffc107; }}
        .poor {{ color: #dc3545; }}
        .section {{ 
            background: white;
            margin: 30px 0;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .section h2 {{ 
            font-size: 1.8em;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 3px solid #007bff;
        }}
        .issue-list {{ list-style: none; }}
        .issue-item {{ 
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            border-left: 4px solid;
        }}
        .critical {{ background: #f8d7da; border-color: #dc3545; }}
        .warning {{ background: #fff3cd; border-color: #ffc107; }}
        .info {{ background: #d1ecf1; border-color: #17a2b8; }}
        .success {{ background: #d4edda; border-color: #28a745; }}
        .module-section {{ 
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border: 1px solid #dee2e6;
        }}
        .module-title {{ 
            font-size: 1.3em;
            color: #495057;
            margin-bottom: 15px;
            font-weight: 600;
            padding: 10px;
            background: white;
            border-radius: 6px;
        }}
        .module-section ul {{ padding-left: 20px; }}
        .module-section li {{ margin: 5px 0; }}
        .recommendations {{ background: #e3f2fd; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Comprehensive SEO Analysis Report</h1>
            <p><strong>Website:</strong> {url}</p>
            <p><strong>Analysis Date:</strong> {timestamp}</p>
            <p><strong>Tool Version:</strong> tfq0seo v{version} (Enhanced Accuracy)</p>
        </div>

        <!-- Score Overview -->
        <div class="score-container">
            <div class="score-card">
                <div class="score-number {get_score_class(overall_score)}">{overall_score}</div>
                <div class="score-label">Overall SEO Score</div>
            </div>
            <div class="score-card">
                <div class="score-number {get_score_class(category_scores.get('technical_seo', 0))}">{category_scores.get('technical_seo', 0)}</div>
                <div class="score-label">Technical SEO</div>
            </div>
            <div class="score-card">
                <div class="score-number {get_score_class(category_scores.get('content_quality', 0))}">{category_scores.get('content_quality', 0)}</div>
                <div class="score-label">Content Quality</div>
            </div>
            <div class="score-card">
                <div class="score-number {get_score_class(category_scores.get('user_experience', 0))}">{category_scores.get('user_experience', 0)}</div>
                <div class="score-label">User Experience</div>
            </div>
            <div class="score-card">
                <div class="score-number {get_score_class(category_scores.get('security', 0))}">{category_scores.get('security', 0)}</div>
                <div class="score-label">Security</div>
            </div>
        </div>

        <!-- Executive Summary -->
        <div class="section">
            <h2>📊 Executive Summary</h2>
            <div class="issue-item info">
                <strong>Total Issues Found:</strong> {summary.get('total_issues', 0)}<br>
                <strong>Critical Issues:</strong> {summary.get('critical_issues', 0)}<br>
                <strong>Strongest Category:</strong> {summary.get('strongest_category', 'N/A')}<br>
                <strong>Weakest Category:</strong> {summary.get('weakest_category', 'N/A')}<br>
                <strong>Analysis Modules:</strong> {len(modules)} comprehensive modules analyzed<br>
                <strong>Recommendations Generated:</strong> {len(insights.get('recommendations', []))}
            </div>
        </div>

        <!-- Critical Issues -->
        <div class="section">
            <h2>🚨 Critical Issues Requiring Immediate Attention ({len(insights.get('critical_issues', []))})</h2>
            <ul class="issue-list">
                {critical_issues_html}
            </ul>
        </div>

        <!-- Opportunities -->
        <div class="section">
            <h2>💡 Optimization Opportunities ({len(insights.get('opportunities', []))})</h2>
            <ul class="issue-list">
                {opportunities_html}
            </ul>
        </div>

        <!-- Strengths -->
        <div class="section">
            <h2>✅ Strengths & Good Practices ({len(insights.get('strengths', []))})</h2>
            <ul class="issue-list">
                {strengths_html}
            </ul>
        </div>

        <!-- Detailed Module Analysis -->
        <div class="section">
            <h2>🔬 Detailed Analysis by Module ({len(modules)} Modules)</h2>
            <p style="margin-bottom: 20px; color: #666;">
                Each module provides specialized analysis with enhanced accuracy algorithms:
            </p>
            {module_analysis_html}
        </div>

        <!-- Recommendations -->
        <div class="section recommendations">
            <h2>📋 Priority Recommendations ({len(insights.get('recommendations', []))})</h2>
            <ul class="issue-list">
                {recommendations_html}
            </ul>
        </div>

        <!-- Enhanced Features Info -->
        <div class="section">
            <h2>🎯 Enhanced Accuracy Features</h2>
            <div class="issue-item info">
                <strong>✅ This analysis includes enhanced v2.1.0 features:</strong><br>
                • Improved content analysis with technical term filtering<br>
                • Enhanced HTTPS/SSL validation with certificate checking<br>
                • Advanced keyword analysis with adaptive thresholds<br>
                • Cross-module consistency validation<br>
                • Professional-grade scoring algorithms<br>
                • Comprehensive error handling and data validation<br>
                • Real-time accuracy warnings and insights
            </div>
        </div>

        <!-- Footer -->
        <div class="section">
            <p style="text-align: center; color: #666;">
                Generated by <strong>tfq0seo v{version}</strong> - Enhanced SEO Analysis Toolkit<br>
                <em>Professional-grade analysis with enhanced accuracy and reliability</em><br>
                <small>Competitive with Screaming Frog SEO Spider • Open Source • Extensible</small>
            </p>
        </div>
    </div>
</body>
</html>'''
    
    # Write the comprehensive report
    with open('COMPREHENSIVE_DETAILED_SEO_REPORT.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print('✅ Comprehensive HTML report created: COMPREHENSIVE_DETAILED_SEO_REPORT.html')
    print('🎯 This report includes:')
    print('   - Executive summary with key metrics')
    print('   - Color-coded scoring system with 5 categories')
    print('   - Detailed module-by-module analysis (5 specialized modules)')
    print('   - Professional styling and responsive layout')
    print('   - Enhanced accuracy insights and features')
    print('   - Prioritized recommendations with counts')
    print('   - Modern design with gradients and cards')

if __name__ == '__main__':
    create_comprehensive_report() 
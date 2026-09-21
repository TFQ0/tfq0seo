"""Pure report aggregation over recorded evidence; no synthetic measurements."""

import copy
import math
from collections import Counter, OrderedDict
from statistics import mean, median
from typing import Any, Dict, List, Tuple
from ..rules import RULESET_VERSION, get_rule


def aggregate_issues(issues: List[Dict[str, Any]], *, copy_evidence=True) -> Tuple[List[Dict], Dict]:
    # Default callers receive independent evidence. A report builder may share
    # its own snapshot across page and aggregated views without another copy.
    memo = {}
    snapshot = (lambda value: copy.deepcopy(value, memo)) if copy_evidence else (lambda value: value)
    grouped = OrderedDict()
    page_sets = {}
    for issue in issues:
        key = ('rule', issue['rule_id'], issue.get('rule_version')) if issue.get('rule_id') else (
            'legacy', issue.get('message'), issue.get('category'), issue.get('severity'))
        if key not in grouped:
            grouped[key] = {**snapshot(issue), 'count': 0, 'pages': [], 'evidence_by_page': []}
            grouped[key].pop('url', None)
            page_sets[key] = set()
        item = grouped[key]
        item['count'] += 1
        if issue.get('url') and issue['url'] not in page_sets[key]:
            item['pages'].append(issue['url'])
            page_sets[key].add(issue['url'])
        if issue.get('url') and 'evidence' in issue:
            item['evidence_by_page'].append({field: snapshot(issue.get(field)) for field in
                                             ('url', 'evidence', 'observations', 'status', 'applicability', 'score_owner')})
    aggregated = list(grouped.values())
    for item in aggregated:
        item['pages_affected'] = len(item['pages'])
        item['example_pages'] = item['pages'][:5]
    order = {'critical': 0, 'warning': 1, 'notice': 2}
    aggregated.sort(key=lambda item: (order.get(item.get('severity'), 3), -item['count']))
    return aggregated, {
        'total_issues': len(issues), 'unique_issues': len(aggregated),
        'reduction_ratio': 1 - len(aggregated) / len(issues) if issues else 0,
        'most_common': max(aggregated, key=lambda item: item['count']) if aggregated else None,
        'pages_with_issues': len({item['url'] for item in issues if item.get('url')}),
    }


def generate_specific_recommendations(report: Dict[str, Any]) -> List[Dict]:
    raw = report.get('issues', {})
    issues = raw.get('aggregated', []) if isinstance(raw, dict) else raw
    issues = report.get('aggregated_issues', issues)
    recommendations = []
    for issue in issues:
        recommendation = issue.get('fix') or issue.get('message', 'Review the recorded evidence.')
        if issue.get('rule_version') == RULESET_VERSION:
            try:
                recommendation = get_rule(issue['rule_id']).recommendation
            except ValueError:
                pass  # An imported archive may contain a rule unavailable in this installation.
        recommendations.append({
            'rule_id': issue.get('rule_id'),
            'priority': {'critical': 'HIGH', 'warning': 'MEDIUM', 'notice': 'LOW'}.get(issue.get('severity'), 'LOW'),
            'category': issue.get('category', 'General'), 'title': issue.get('message', 'Review finding'),
            'description': recommendation,
            'implementation': recommendation,
            'references': issue.get('references', []), 'reviewed_on': issue.get('reviewed_on'),
            'applicability': issue.get('rule_applicability'),
            'effort': issue.get('effort', 'Unknown'),
            'impact': issue.get('impact', 'Review the evidence and applicability for your site.'),
            'affected_pages': issue.get('pages_affected', issue.get('count', 0)),
            'example_pages': issue.get('example_pages', []),
        })
    return recommendations


def create_executive_summary(report: Dict[str, Any]) -> Dict:
    scores = report.get('scores', {})
    overall = scores.get('overall', report.get('overall_score'))
    categories = scores.get('categories', report.get('category_scores', {}))
    counts = report.get('issues', {}).get('counts', {}) if isinstance(report.get('issues'), dict) else report.get('issue_counts', {})
    summary = report.get('summary', {})
    specific = report.get('recommendations', {}).get('specific', [])
    health = 'Unknown' if overall is None else 'Good' if overall >= 80 else 'Average' if overall >= 60 else 'Poor'
    return {
        'overview': {'total_pages_analyzed': summary.get('total_pages', 0),
                     'successful_pages': summary.get('successful_pages', 0),
                     'partial_pages': summary.get('partial_pages', 0),
                     'failed_pages': summary.get('failed_pages', 0),
                     'overall_health': health, 'overall_score': overall,
                     'assessment_source': 'static_rule_heuristics'},
        'key_metrics': {**{name + '_score': categories.get(name) for name in
                           ('seo', 'content', 'technical', 'performance', 'links')},
                        'critical_issues': counts.get('critical', 0), 'total_issues': counts.get('total', 0)},
        'top_issues': report.get('issues', {}).get('top_issues', []) if isinstance(report.get('issues'), dict) else [],
        'quick_wins': [item for item in specific if item.get('effort') == 'Low' and item['priority'] == 'HIGH'][:3],
        'action_items': [item['description'] for item in specific[:5]],
    }


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def generate_performance_metrics(pages: List[Dict[str, Any]]) -> Dict:
    metrics = {'load_times': [], 'status_codes': dict(Counter(page.get('status_code') or 0 for page in pages)),
               'content_sizes': [], 'issues_per_page': [], 'scores_per_page': [],
               'measurement_source': 'http_fetch', 'browser_metrics_status': 'not_measured'}
    for page in pages:
        url = page.get('url', '')
        if _number(page.get('load_time')):
            metrics['load_times'].append({'url': url, 'time': page['load_time']})
        if _number(page.get('content_length')):
            metrics['content_sizes'].append({'url': url, 'bytes': page['content_length']})
        if _number(page.get('overall_score')):
            metrics['scores_per_page'].append({'url': url, 'score': page['overall_score']})
        if not page.get('error'):
            metrics['issues_per_page'].append({'url': url, 'count': len(page.get('issues', []))})
    for source, field, target in (('load_times', 'time', 'load_time_stats'), ('scores_per_page', 'score', 'score_stats')):
        values = [item[field] for item in metrics[source]]
        if values:
            metrics[target] = {'average': mean(values), 'median': median(values), 'min': min(values), 'max': max(values)}
    metrics['slowest_pages'] = sorted(metrics['load_times'], key=lambda item: item['time'], reverse=True)[:10]
    metrics['lowest_scoring_pages'] = sorted(metrics['scores_per_page'], key=lambda item: item['score'])[:10]
    return metrics

"""Reviewed rule definitions, explicit evaluations, and one scoring policy.

Reference documents support observations and guidance, not the numeric weights.
Penalties are a versioned TFQ0SEO checklist policy, not search ranking factors.
"""

import copy
import json
import re
from collections import Counter, OrderedDict
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlsplit


RULESET_VERSION = '2026.09.14'
SCORING_VERSION = '2.0'
ANALYZERS = ('seo', 'content', 'technical', 'performance', 'links')
PENALTIES = MappingProxyType({'critical': 15, 'warning': 7, 'notice': 3})
STATUSES = ('pass', 'fail', 'informational', 'unknown', 'not_applicable', 'error')


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    owner: str
    severity: str
    recommendation: str
    applicability: str
    references: Tuple[str, ...]
    reviewed_on: str
    scored: bool = True
    title: str = ''

    def __post_init__(self):
        if not re.fullmatch(r'[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+', self.rule_id):
            raise ValueError('Rule IDs must be stable dotted identifiers')
        if self.owner not in ANALYZERS or self.severity not in PENALTIES:
            raise ValueError('Unknown rule owner or severity')
        if not self.recommendation.strip() or not self.applicability.strip():
            raise ValueError('Rules require a recommendation and applicability description')
        if not isinstance(self.references, tuple) or not self.references:
            raise ValueError('Rules require a tuple of reviewed reference URLs')
        for reference in self.references:
            parsed = urlsplit(reference)
            if parsed.scheme != 'https' or not parsed.hostname:
                raise ValueError('Rule references must be complete HTTPS URLs')
        date.fromisoformat(self.reviewed_on)
        if type(self.scored) is not bool:
            raise ValueError('scored must be a boolean')


_RULES: Dict[str, RuleDefinition] = {}
RULES = MappingProxyType(_RULES)


def register_rules(definitions: Iterable[RuleDefinition]):
    """Register module-owned definitions once; conflicting IDs are programming errors."""
    definitions = tuple(definitions)
    proposed = dict(_RULES)
    for definition in definitions:
        if not isinstance(definition, RuleDefinition):
            raise TypeError('Expected RuleDefinition')
        previous = proposed.get(definition.rule_id)
        if previous is not None and previous != definition:
            raise ValueError('Conflicting rule definition: ' + definition.rule_id)
        proposed[definition.rule_id] = definition
    _RULES.update(proposed)
    return MappingProxyType({item.rule_id: item for item in definitions})


def get_rule(rule_id: str) -> RuleDefinition:
    try:
        return _RULES[rule_id]
    except (KeyError, TypeError) as exc:
        raise ValueError('Unregistered rule: ' + str(rule_id)) from exc


def rule_result(rule_id: str, evidence: Any, *, message: str = '', category: Optional[str] = None,
                status: str = 'fail', applicable: Optional[bool] = True, reason: str = '',
                source: str = 'html', confidence: str = 'high', details: Any = None) -> Dict:
    definition = get_rule(rule_id)
    if status not in STATUSES:
        raise ValueError('Unknown rule status: ' + str(status))
    if applicable is not None and type(applicable) is not bool:
        raise ValueError('applicable must be true, false, or None')
    if not isinstance(evidence, (dict, list)):
        raise ValueError('Rule evidence must be structured observations, including unavailable fields')
    # Fail before emitting non-portable or non-finite evidence into JSON reports.
    json.dumps(evidence, allow_nan=False, ensure_ascii=False)
    if applicable is False:
        status = 'not_applicable'
    elif applicable is None and status != 'error':
        status = 'unknown'
    elif status == 'fail' and (not definition.scored or confidence == 'low'):
        status = 'informational'
    if status in ('unknown', 'not_applicable', 'error') and not reason:
        raise ValueError('Unknown, inapplicable, and failed evaluations need an explanation')
    result = {
        'rule_id': rule_id, 'rule_version': RULESET_VERSION, 'scope': 'page',
        'title': definition.title or rule_id,
        'owner': definition.owner, 'category': category or definition.owner.title(),
        'severity': definition.severity, 'message': message or definition.title or rule_id,
        'status': status, 'applicability': ('applicable' if applicable is True else
                                           'not_applicable' if applicable is False else 'unknown'),
        'rule_applicability': definition.applicability, 'reason': reason,
        'evidence': copy.deepcopy(evidence), 'source': source, 'confidence': confidence,
        'references': list(definition.references), 'reviewed_on': definition.reviewed_on,
        'fix': definition.recommendation,
        'penalty': PENALTIES[definition.severity] if status == 'fail' and definition.scored else 0,
        **({'details': copy.deepcopy(details)} if details is not None else {}),
    }
    from .core.models import validate_rule_result
    validate_rule_result(result)
    return result


class RuleCollector:
    def __init__(self, analyzer: str):
        if analyzer not in ANALYZERS:
            raise ValueError('Unknown analyzer')
        self.analyzer = analyzer
        self.results: List[Dict] = []

    def check(self, rule_id: str, failed: Optional[bool], evidence: Any, *, message: str = '',
              category: Optional[str] = None, applicable: Optional[bool] = True, reason: str = '',
              source: str = 'html', confidence: str = 'high', status: Optional[str] = None) -> Dict:
        if failed is not None and type(failed) is not bool:
            raise ValueError('A check condition must be true, false, or None')
        outcome = status or ('unknown' if failed is None else 'fail' if failed else 'pass')
        result = rule_result(rule_id, evidence, message=message, category=category, status=outcome,
                             applicable=applicable, reason=reason, source=source, confidence=confidence)
        result['reported_by'] = [self.analyzer]
        self.results.append(result)
        return result

    @property
    def issues(self):
        return [result for result in self.results if result['status'] in ('fail', 'informational')]

    @property
    def coverage(self):
        return rule_coverage(self.results)


def rule_coverage(results):
    merged = merge_rule_results(results)
    counts = Counter(result['status'] for result in merged)
    has_errors = any(observation.get('status') == 'error' for result in merged
                     for observation in result.get('observations', [result]))
    assessed = sum(counts[status] for status in ('pass', 'fail', 'informational'))
    applicable = assessed + counts['unknown'] + counts['error']
    return {'total': sum(counts.values()), 'counts': {status: counts[status] for status in STATUSES},
            'has_errors': has_errors,
            'assessed': assessed, 'ratio': assessed / applicable if applicable else None,
            'scope': 'Evaluations actually attempted; disabled rules and analyzers are not assumed to pass.'}


def merge_rule_results(results):
    """Merge duplicate evaluations without discarding their evidence or observers."""
    from .core.models import validate_rule_result
    merged = OrderedDict()
    precedence = {'not_applicable': 0, 'pass': 1, 'informational': 2, 'unknown': 3, 'error': 4, 'fail': 5}
    for original in results:
        validate_rule_result(original)
        rule_id = original.get('rule_id')
        get_rule(rule_id)
        result = copy.deepcopy(original)
        if result.get('status') not in STATUSES:
            raise ValueError('Invalid rule evaluation status')
        observation = {key: copy.deepcopy(result.get(key)) for key in
                       ('status', 'applicability', 'evidence', 'source', 'reason', 'reported_by')}
        if rule_id not in merged:
            result['observations'] = result.get('observations') or [observation]
            merged[rule_id] = result
            continue
        previous = merged[rule_id]
        observations = previous['observations'] + (result.get('observations') or [observation])
        unique_observations = []
        for item in observations:
            if item not in unique_observations:
                unique_observations.append(item)
        reporters = sorted(set(previous.get('reported_by', [])) | set(result.get('reported_by', [])))
        if precedence[result['status']] > precedence[previous['status']]:
            previous = result
            merged[rule_id] = previous
        previous['observations'] = unique_observations
        previous['reported_by'] = reporters
    return list(merged.values())


def finding_penalty(result):
    definition = get_rule(result.get('rule_id'))
    if (result.get('status') != 'fail' or result.get('applicability') != 'applicable'
            or result.get('confidence') == 'low' or not definition.scored):
        return 0
    return PENALTIES[definition.severity]


def score_findings(issues, owner: Optional[str] = None):
    penalties = {}
    for issue in issues:
        definition = get_rule(issue.get('rule_id'))
        if owner is None or definition.owner == owner:
            penalties[definition.rule_id] = max(penalties.get(definition.rule_id, 0), finding_penalty(issue))
    return max(0, 100 - sum(penalties.values()))


def recommendations_for(issues):
    seen, recommendations = set(), []
    for issue in issues:
        rule_id = issue.get('rule_id')
        definition = get_rule(rule_id)
        if issue.get('status') in ('fail', 'informational') and rule_id not in seen:
            seen.add(rule_id)
            recommendations.append(definition.recommendation)
    return recommendations


# Shared facts have one owner even when several analyzers observe them.
_REVIEWED = '2026-09-14'
_ROBOTS = ('https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag',)
_HEADINGS = ('https://www.w3.org/WAI/tutorials/page-structure/headings/',)
_VIEWPORT = ('https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/meta/name/viewport',)
register_rules([
    RuleDefinition('robots.noindex', 'seo', 'critical',
                   'Confirm whether this page should appear in search. Remove noindex only if indexing is intended.',
                   'Observed indexing directives; a restriction may be intentional.', _ROBOTS, _REVIEWED, scored=False),
    RuleDefinition('robots.nofollow', 'seo', 'warning',
                   'Review the page-wide nofollow directive against the intended link-following policy.',
                   'Observed link-following directives; publisher intent is not inferred.', _ROBOTS, _REVIEWED, scored=False),
    RuleDefinition('robots.nosnippet', 'seo', 'notice',
                   'Confirm the snippet restriction is intentional before changing it.',
                   'Observed snippet directives.', _ROBOTS, _REVIEWED, scored=False),
    RuleDefinition('headings.missing_h1', 'content', 'warning',
                   'Review whether a descriptive top-level heading would clarify the page structure.',
                   'HTML documents; absence alone does not establish a ranking or accessibility failure.',
                   _HEADINGS, _REVIEWED, scored=False),
    RuleDefinition('headings.empty', 'content', 'warning',
                   'Give each heading meaningful text or remove the empty heading element.',
                   'Observed HTML heading elements.', _HEADINGS, _REVIEWED),
    RuleDefinition('headings.skipped_level', 'content', 'notice',
                   'Review heading levels in document order so they communicate the intended hierarchy.',
                   'Observed heading hierarchy; review the document context.', _HEADINGS, _REVIEWED, scored=False),
    RuleDefinition('images.missing_alt', 'content', 'warning',
                   'Provide an appropriate text alternative; use alt="" for a purely decorative image.',
                   'HTML img elements without an alt attribute; content purpose determines its value.',
                   ('https://www.w3.org/WAI/tutorials/images/decorative/',), _REVIEWED),
    RuleDefinition('images.missing_dimensions', 'performance', 'notice',
                   'Check reserved image space in the rendered layout; use dimensions or an appropriate CSS aspect ratio.',
                   'Image dimension attributes only; CSS and layout are not measured.',
                   ('https://web.dev/articles/optimize-cls',), _REVIEWED, scored=False),
    RuleDefinition('mobile.viewport_missing', 'technical', 'warning',
                   'Configure a viewport appropriate for the responsive layout, then test it in a browser.',
                   'HTML documents intended for browser display.', _VIEWPORT, _REVIEWED),
    RuleDefinition('mobile.viewport_zoom_disabled', 'technical', 'warning',
                   'Remove viewport restrictions that prevent users from zooming the page.',
                   'An observed viewport declaration restricting user zoom.', _VIEWPORT, _REVIEWED),
    RuleDefinition('language.missing', 'technical', 'warning',
                   'Declare the primary document language with an appropriate lang attribute.',
                   'HTML documents with human-readable content.',
                   ('https://www.w3.org/WAI/WCAG22/Techniques/html/H57',), _REVIEWED),
    RuleDefinition('security.https_missing', 'technical', 'critical',
                   'Serve the page over HTTPS with a valid certificate and update navigation to the secure URL.',
                   'Observed HTTP document URLs; local development may intentionally use HTTP.',
                   ('https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Transport_Layer_Security',), _REVIEWED),
])

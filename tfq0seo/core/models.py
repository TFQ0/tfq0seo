"""Versioned dictionary contracts shared by analysis and report consumers.

Dictionary payloads remain compatible with the public library API. Optional
scores represent unavailable results, never a measured zero.
"""

import copy
import math
from collections.abc import Mapping
from datetime import date
from typing import Any, Dict, List, Optional, TypedDict, Union
from ..page_facts import PageFacts

SCHEMA_VERSION = '1.0'
ANALYZER_NAMES = ('seo', 'content', 'technical', 'performance', 'links')
HeaderValue = Union[str, List[str]]


class RedirectHop(TypedDict):
    url: str
    status_code: int
    location: str


class RuleCoverage(TypedDict):
    total: int
    counts: Dict[str, int]
    assessed: int
    ratio: Optional[float]
    scope: str


class PageSummary(TypedDict, total=False):
    url: str
    score: Optional[float]
    status: str
    status_code: int
    load_time: Optional[float]
    issues: Dict[str, int]
    priority: Optional[int]
    depth: Optional[int]


class ReportPages(TypedDict):
    summary: List[PageSummary]
    detailed: List['PageResult']
    failed: List['PageResult']
    skipped: List['PageResult']


class Issue(TypedDict, total=False):
    rule_id: str
    category: str
    severity: str
    message: str
    source: str
    status: str
    details: Dict[str, Any]
    evidence: Union[Dict[str, Any], List[Any]]
    url: str
    rule_version: str
    owner: str
    applicability: str
    rule_applicability: str
    references: List[str]
    reviewed_on: str
    confidence: str
    penalty: int
    reason: str
    scope: str
    title: str
    fix: str


class _RuleEnvelope(TypedDict):
    rule_id: str
    rule_version: str
    scope: str
    title: str
    owner: str
    category: str
    severity: str
    message: str
    status: str
    applicability: str
    rule_applicability: str
    reason: str
    evidence: Union[Dict[str, Any], List[Any]]
    source: str
    confidence: str
    references: List[str]
    reviewed_on: str
    fix: str
    penalty: int


class RuleResult(_RuleEnvelope, total=False):
    """A complete outcome with optional aggregate provenance and presentation detail."""
    reported_by: List[str]
    observations: List[Dict[str, Any]]
    score_owner: Optional[str]
    details: Any
    url: str


class _FetchIdentity(TypedDict):
    url: str


class FetchResult(_FetchIdentity, total=False):
    requested_url: str
    status_code: int
    error: str
    soup: Any
    headers: Optional[Dict[str, HeaderValue]]
    redirect_chain: List[RedirectHop]
    load_time: Optional[float]
    timings: Dict[str, Optional[float]]
    content_length: int
    truncated: bool
    outcome: str
    skipped: bool
    reason: str
    content_type: str
    encoding: str
    html: str
    depth: int
    parent_url: Optional[str]
    timestamp: float
    redirected_from: Optional[str]
    needs_javascript: bool


class AnalyzerResult(TypedDict, total=False):
    status: str
    score: Optional[float]
    issues: List[Issue]
    data: Dict[str, Any]
    error: str
    rule_results: List[RuleResult]
    rule_coverage: Dict[str, Any]
    recommendations: List[str]


class SitePageObservation(TypedDict, total=False):
    url: str
    canonical_targets: List[str]
    canonical_status: str
    canonical_terminal: Optional[str]
    canonical_hops: Optional[int]
    canonical_cycle_id: Optional[int]
    incoming_links: int
    outgoing_links: Optional[int]
    nofollow_links: Optional[int]
    link_depth: Optional[int]
    reachable: Optional[bool]
    component: Optional[int]
    facts_available: bool
    content_complete: bool
    canonical_headers_checked: bool


class SiteAnalysis(TypedDict, total=False):
    version: str
    scope: str
    coverage: Dict[str, Any]
    canonicals: Dict[str, Any]
    links: Dict[str, Any]
    pages: List[SitePageObservation]
    findings: List[RuleResult]


class PageResult(TypedDict, total=False):
    schema_version: str
    url: str
    requested_url: str
    status_code: int
    status: str
    overall_score: Optional[float]
    issues: List[Issue]
    issue_counts: Dict[str, int]
    coverage: Dict[str, Any]
    analyzer_errors: Dict[str, str]
    error: str
    rule_results: List[RuleResult]
    rule_coverage: Dict[str, Any]
    scoring: Dict[str, Any]
    page_facts: Dict[str, Any]
    site_analysis: SitePageObservation
    recommendations: List[Dict[str, Any]]
    load_time: Optional[float]
    timings: Dict[str, Optional[float]]
    redirect_chain: List[RedirectHop]
    content_length: int
    truncated: bool
    timestamp: float
    skipped: bool
    reason: str
    context: Dict[str, Any]
    content_hash: str
    analysis_time: float
    cached: bool
    seo: AnalyzerResult
    content: AnalyzerResult
    technical: AnalyzerResult
    performance: AnalyzerResult
    links: AnalyzerResult


class SiteReport(TypedDict, total=False):
    schema_version: str
    status: str
    summary: Dict[str, Any]
    scores: Dict[str, Any]
    issues: Dict[str, Any]
    pages: ReportPages
    recommendations: Dict[str, Any]
    technical_health: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    metadata: Dict[str, Any]
    rule_coverage: Dict[str, Any]
    scoring: Dict[str, Any]
    site_analysis: SiteAnalysis


class ContractError(ValueError):
    """Invalid boundary data, identified by its field path rather than its contents."""

    def __init__(self, path: str, message: str):
        self.path = path
        super().__init__(f'{path}: {message}')


def validate_json_value(value, path='$', _parents=None):
    """Reject nonportable objects, cycles, and non-finite numbers without coercion.

    Integer dictionary keys are retained for existing HTTP-status histograms;
    JSON encoders represent those keys as strings. Unknown extension fields are
    allowed, but their values must obey the same contract.
    """
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ContractError(path, 'must be a finite number or null')
        return value
    if not isinstance(value, (dict, list)):
        raise ContractError(path, 'must contain JSON values, not ' + type(value).__name__)
    parents = set() if _parents is None else _parents
    if id(value) in parents:
        raise ContractError(path, 'must not contain a circular reference')
    parents.add(id(value))
    try:
        entries = value.items() if isinstance(value, dict) else enumerate(value)
        for key, item in entries:
            if isinstance(value, dict) and not (isinstance(key, str) or type(key) is int):
                raise ContractError(path, 'object keys must be strings or integer status codes')
            child = f'{path}[{key}]' if isinstance(value, list) else f'{path}.{key}'
            validate_json_value(item, child, parents)
    finally:
        parents.remove(id(value))
    return value


def _mapping(value, path):
    if not isinstance(value, dict):
        raise ContractError(path, 'must be an object')


def _string(value, path, *, nonempty=False):
    if not isinstance(value, str) or (nonempty and not value.strip()):
        raise ContractError(path, 'must be a nonempty string' if nonempty else 'must be a string')


def _number(value, path, *, nullable=False, maximum=None, integer=False):
    if value is None and nullable:
        return
    valid = type(value) is int if integer else type(value) in (int, float)
    if not valid or value < 0 or (isinstance(value, float) and not math.isfinite(value)):
        raise ContractError(path, 'must be a nonnegative finite ' + ('integer' if integer else 'number'))
    if maximum is not None and value > maximum:
        raise ContractError(path, f'must not exceed {maximum}')


def normalize_fetch_result(value, path='$') -> FetchResult:
    """Validate fetch input and detach metadata while keeping the parsed DOM.

    Missing observations stay unavailable. Legacy partial dictionaries are
    supported; malformed supplied fields are never silently coerced.
    """
    if not isinstance(value, Mapping):
        raise ContractError(path, 'fetch result must be an object')
    _string(value.get('url'), path + '.url', nonempty=True)
    for key in ('requested_url', 'error', 'reason', 'content_type', 'encoding', 'html', 'outcome'):
        if key in value:
            _string(value[key], path + '.' + key)
    for key in ('parent_url', 'redirected_from'):
        if value.get(key) is not None:
            _string(value[key], path + '.' + key)
    for key in ('load_time', 'timestamp'):
        if key in value:
            _number(value[key], path + '.' + key, nullable=(key == 'load_time'))
    for key in ('content_length', 'depth'):
        if key in value:
            _number(value[key], path + '.' + key, integer=True)
    if 'status_code' in value:
        _number(value['status_code'], path + '.status_code', integer=True, maximum=599)
        if 0 < value['status_code'] < 100:
            raise ContractError(path + '.status_code', 'must be zero or an HTTP status from 100 to 599')
    for key in ('truncated', 'skipped', 'needs_javascript'):
        if key in value and type(value[key]) is not bool:
            raise ContractError(path + '.' + key, 'must be a boolean')
    timings = value.get('timings', {})
    _mapping(timings, path + '.timings')
    for key, duration in timings.items():
        _string(key, path + '.timings key')
        _number(duration, path + '.timings.' + key, nullable=True)
    chain = value.get('redirect_chain', [])
    if not isinstance(chain, list):
        raise ContractError(path + '.redirect_chain', 'must be a list')
    for index, hop in enumerate(chain):
        hop_path = f'{path}.redirect_chain[{index}]'
        _mapping(hop, hop_path)
        _string(hop.get('url'), hop_path + '.url', nonempty=True)
        _string(hop.get('location'), hop_path + '.location', nonempty=True)
        _number(hop.get('status_code'), hop_path + '.status_code', integer=True, maximum=399)
        if hop['status_code'] < 300:
            raise ContractError(hop_path + '.status_code', 'must be an HTTP redirect status')
    headers = value.get('headers')
    if headers is not None:
        if not isinstance(headers, Mapping):
            raise ContractError(path + '.headers', 'must be a header mapping or null')
        detached_headers = {}
        for key in headers:
            _string(key, path + '.headers key', nonempty=True)
            header = headers.getall(key) if hasattr(headers, 'getall') else headers[key]
            values = header if isinstance(header, (list, tuple)) else [header]
            for part in values:
                _string(part, path + '.headers.' + key)
            detached_headers[str(key)] = list(values) if isinstance(header, (list, tuple)) else header
        headers = detached_headers
    soup = value.get('soup')
    if soup is not None:
        from bs4 import BeautifulSoup
        if not isinstance(soup, BeautifulSoup):
            raise ContractError(path + '.soup', 'must be a BeautifulSoup document or null')
    result = {key: copy.deepcopy(item) for key, item in value.items() if key not in ('soup', 'headers')}
    result['headers'] = headers
    if 'soup' in value:
        result['soup'] = soup
    validate_json_value({key: item for key, item in result.items() if key != 'soup'}, path)
    outcome = result.get('outcome')
    if outcome is not None and outcome not in ('success', 'failed', 'skipped'):
        raise ContractError(path + '.outcome', 'must be success, failed, or skipped')
    if outcome == 'failed' and not result.get('error'):
        result['error'] = 'Fetch failed without an error description'
    if outcome == 'skipped':
        result['skipped'] = True
        result.setdefault('reason', result.get('error') or 'Fetch was skipped')
    if outcome == 'success' and (result.get('error') or result.get('skipped')):
        raise ContractError(path + '.outcome', 'success conflicts with error or skipped state')
    if outcome == 'failed' and result.get('skipped'):
        raise ContractError(path + '.outcome', 'failed conflicts with skipped state')
    result.setdefault('requested_url', result.get('redirected_from') or result['url'])
    result.setdefault('status_code', 0)
    result.setdefault('load_time', None)
    result.setdefault('timings', {})
    result.setdefault('redirect_chain', [])
    result.setdefault('truncated', False)
    return result


def validate_rule_result(value, path='$', *, registered=True):
    """Validate a complete live rule outcome before merging or scoring it."""
    from ..rules import ANALYZERS, STATUSES, RULESET_VERSION, finding_penalty, get_rule
    _mapping(value, path)
    for key in ('rule_id', 'rule_version', 'scope', 'title', 'owner', 'category', 'severity',
                'message', 'status', 'applicability', 'rule_applicability', 'source',
                'confidence', 'reviewed_on', 'fix'):
        _string(value.get(key), path + '.' + key, nonempty=True)
    _string(value.get('reason'), path + '.reason')
    if value['status'] not in STATUSES:
        raise ContractError(path + '.status', 'unknown rule outcome')
    if value['applicability'] not in ('applicable', 'unknown', 'not_applicable'):
        raise ContractError(path + '.applicability', 'unknown applicability')
    if value['confidence'] not in ('high', 'medium', 'low'):
        raise ContractError(path + '.confidence', 'must be high, medium, or low')
    if value['scope'] not in ('page', 'site'):
        raise ContractError(path + '.scope', 'must be page or site')
    if value['status'] in ('pass', 'fail', 'informational') and value['applicability'] != 'applicable':
        raise ContractError(path + '.applicability', 'assessed outcomes must be applicable')
    if (value['status'] == 'not_applicable') != (value['applicability'] == 'not_applicable'):
        raise ContractError(path + '.applicability', 'not_applicable must match the outcome')
    if value['status'] in ('unknown', 'not_applicable', 'error') and not value['reason'].strip():
        raise ContractError(path + '.reason', 'unavailable outcomes require an explanation')
    if not isinstance(value.get('evidence'), (dict, list)):
        raise ContractError(path + '.evidence', 'must be structured observations')
    references = value.get('references')
    if not isinstance(references, list) or not references:
        raise ContractError(path + '.references', 'must be a nonempty list')
    for index, reference in enumerate(references):
        _string(reference, f'{path}.references[{index}]', nonempty=True)
    try:
        date.fromisoformat(value['reviewed_on'])
    except ValueError:
        raise ContractError(path + '.reviewed_on', 'must be an ISO calendar date') from None
    _number(value.get('penalty'), path + '.penalty', integer=True)
    if value['status'] != 'fail' and value['penalty'] != 0:
        raise ContractError(path + '.penalty', 'only failed rules can have a deduction')
    if registered:
        try:
            definition = get_rule(value['rule_id'])
        except ValueError:
            raise ContractError(path + '.rule_id', 'must identify a registered rule') from None
        if value['owner'] != definition.owner or value['severity'] != definition.severity:
            raise ContractError(path, 'owner and severity must match the registered rule')
        expected = {'rule_version': RULESET_VERSION, 'fix': definition.recommendation,
                    'references': list(definition.references), 'reviewed_on': definition.reviewed_on,
                    'rule_applicability': definition.applicability}
        for key, recorded in expected.items():
            if value[key] != recorded:
                raise ContractError(path + '.' + key, 'must match the registered live rule')
        if value['status'] == 'fail' and (not definition.scored or value['confidence'] == 'low'):
            raise ContractError(path + '.status', 'advisory findings must be informational')
        if value['penalty'] != finding_penalty(value):
            raise ContractError(path + '.penalty', 'must match the rule scoring policy')
    for key in ('reported_by',):
        if key in value and (not isinstance(value[key], list) or
                             any(item not in ANALYZERS for item in value[key])):
            raise ContractError(path + '.' + key, 'must list known analyzers')
    if value.get('score_owner') is not None and value['score_owner'] not in ANALYZERS:
        raise ContractError(path + '.score_owner', 'must identify an analyzer or be null')
    if 'observations' in value:
        if not isinstance(value['observations'], list):
            raise ContractError(path + '.observations', 'must be a list')
        for index, observation in enumerate(value['observations']):
            observation_path = f'{path}.observations[{index}]'
            _mapping(observation, observation_path)
            if observation.get('status') not in STATUSES:
                raise ContractError(observation_path + '.status', 'unknown observation outcome')
            if not isinstance(observation.get('evidence'), (dict, list)):
                raise ContractError(observation_path + '.evidence', 'must be structured observations')
            if observation.get('applicability') not in ('applicable', 'unknown', 'not_applicable'):
                raise ContractError(observation_path + '.applicability', 'unknown applicability')
            if (observation['status'] in ('pass', 'fail', 'informational') and
                    observation['applicability'] != 'applicable'):
                raise ContractError(observation_path + '.applicability', 'assessed outcomes must be applicable')
            if (observation['status'] == 'not_applicable') != (observation['applicability'] == 'not_applicable'):
                raise ContractError(observation_path + '.applicability', 'not_applicable must match the outcome')
            reporters = observation.get('reported_by')
            if reporters is not None and (not isinstance(reporters, list) or any(item not in ANALYZERS for item in reporters)):
                raise ContractError(observation_path + '.reported_by', 'must list known analyzers or be null')
            _string(observation.get('source'), observation_path + '.source', nonempty=True)
            if observation['status'] in ('unknown', 'not_applicable', 'error'):
                _string(observation.get('reason'), observation_path + '.reason', nonempty=True)
    validate_json_value(value, path)
    return value


def validate_analyzer_result(value, path='$') -> AnalyzerResult:
    """Validate live analyzer output, including every nested issue and outcome."""
    _mapping(value, path)
    if not isinstance(value.get('issues'), list):
        raise ContractError(path + '.issues', 'must be a list')
    if 'score' in value:
        _number(value['score'], path + '.score', nullable=True, maximum=100)
    if 'status' in value and value['status'] not in ('complete', 'partial', 'error'):
        raise ContractError(path + '.status', 'must be complete, partial, or error')
    if value.get('status') == 'error' and not value.get('error'):
        raise ContractError(path + '.error', 'errored analyzers require an explanation')
    if 'error' in value:
        _string(value['error'], path + '.error')
    if value.get('error'):
        _string(value['error'], path + '.error', nonempty=True)
        if value.get('score') is not None:
            raise ContractError(path + '.score', 'errored analyzers must have an unavailable score')
        if value.get('status') in ('complete', 'partial'):
            raise ContractError(path + '.status', 'conflicts with the analyzer error')
    if 'data' in value:
        _mapping(value['data'], path + '.data')
    for index, issue in enumerate(value['issues']):
        issue_path = f'{path}.issues[{index}]'
        _mapping(issue, issue_path)
        if 'rule_version' in issue:
            validate_rule_result(issue, issue_path)
        else:
            for key in ('message', 'category', 'severity'):
                _string(issue.get(key), issue_path + '.' + key, nonempty=True)
            if issue['severity'] not in ('critical', 'warning', 'notice'):
                raise ContractError(issue_path + '.severity', 'unknown issue severity')
    if 'rule_results' in value:
        if not isinstance(value['rule_results'], list):
            raise ContractError(path + '.rule_results', 'must be a list')
        for index, result in enumerate(value['rule_results']):
            validate_rule_result(result, f'{path}.rule_results[{index}]')
        expected_issues = [result for result in value['rule_results']
                           if result['status'] in ('fail', 'informational')]
        if (len(value['issues']) != len(expected_issues) or
                any(issue not in expected_issues for issue in value['issues']) or
                any(issue not in value['issues'] for issue in expected_issues)):
            raise ContractError(path + '.issues', 'must contain the failed and informational rule evaluations')
    if 'recommendations' in value:
        if not isinstance(value['recommendations'], list):
            raise ContractError(path + '.recommendations', 'must be a list')
        for index, recommendation in enumerate(value['recommendations']):
            _string(recommendation, f'{path}.recommendations[{index}]')
    validate_json_value(value, path)
    return value

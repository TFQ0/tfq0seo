"""Validate report dictionaries without rewriting historical evidence or scores.

Producer envelopes are stricter than imported archives. Unknown extension fields
remain intact, and archived rule identifiers are not checked against today's
registry. Presentation code must still escape strings and restrict link schemes.
"""

from .models import ANALYZER_NAMES, ContractError, validate_json_value


def _mapping(value, path):
    if not isinstance(value, dict):
        raise ContractError(path, 'must be an object')


def _list(value, path):
    if not isinstance(value, list):
        raise ContractError(path, 'must be an array')


def _text(value, path, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str):
        raise ContractError(path, 'must be a string' + (' or null' if nullable else ''))


def _number(value, path, nullable=True):
    if value is None and nullable:
        return
    if type(value) not in (int, float):
        raise ContractError(path, 'must be a number' + (' or null' if nullable else ''))


def _score(value, path):
    _number(value, path)
    if value is not None and not 0 <= value <= 100:
        raise ContractError(path, 'must be between 0 and 100 or null')


def _count(value, path):
    if type(value) is not int or value < 0:
        raise ContractError(path, 'must be a nonnegative integer')


def _fields(data, names, validator, path):
    for name in names:
        if name in data:
            validator(data[name], path + '.' + name)


def _required(data, names, path):
    for name in names:
        if name not in data:
            raise ContractError(path + '.' + name, 'is required')


def _records(value, path, validator):
    _list(value, path)
    for index, item in enumerate(value):
        validator(item, f'{path}[{index}]')


def _counts(value, path):
    _mapping(value, path)
    for name, count in value.items():
        _text(name, path + '.<key>')
        _count(count, path + '.' + name)


def _scores(value, path):
    _mapping(value, path)
    for name, score in value.items():
        _text(name, path + '.<key>')
        _score(score, path + '.' + name)


def _issue(value, path):
    _mapping(value, path)
    _fields(value, ('rule_id', 'rule_version', 'category', 'severity', 'message', 'source',
                    'status', 'fix', 'url', 'owner', 'applicability', 'rule_applicability',
                    'reviewed_on', 'confidence', 'reason', 'title'),
            lambda item, name: _text(item, name, nullable=True), path)
    _fields(value, ('count', 'pages_affected'), _count, path)
    _fields(value, ('observations', 'evidence_by_page'), lambda item, name: _records(item, name, _mapping), path)
    _fields(value, ('references', 'reported_by', 'pages', 'example_pages'),
            lambda item, name: _records(item, name, _text), path)
    # Legacy detail/evidence structures may be arbitrary JSON values. Their
    # portability is checked once at the public boundary, not reinterpreted here.


def _recommendation(value, path):
    if isinstance(value, str):
        return
    _mapping(value, path)
    _fields(value, ('recommendation', 'description', 'title', 'priority', 'category', 'effort', 'rule_id'),
            lambda item, name: _text(item, name, nullable=True), path)


def _executive(value, path):
    _mapping(value, path)
    _fields(value, ('overview', 'key_metrics'), _mapping, path)
    _fields(value, ('quick_wins', 'action_items'), lambda item, name: _records(item, name, _recommendation), path)
    _fields(value, ('top_issues',), lambda item, name: _records(item, name, _issue), path)


def _recommendations(value, path):
    if isinstance(value, dict):
        _fields(value, ('specific',), lambda item, name: _records(item, name, _recommendation), path)
        _fields(value, ('executive',), _executive, path)
    else:
        _records(value, path, _recommendation)


def _coverage(value, path):
    _mapping(value, path)
    _fields(value, ('counts',), _counts, path)
    _fields(value, ('total', 'assessed'), _count, path)
    _fields(value, ('ratio',), _number, path)


def _analyzer(value, path):
    _mapping(value, path)
    _fields(value, ('score',), _score, path)
    _fields(value, ('error', 'status'), _text, path)
    _fields(value, ('issues', 'rule_results'), lambda item, name: _records(item, name, _issue), path)
    _fields(value, ('rule_coverage',), _coverage, path)
    _fields(value, ('recommendations',), lambda item, name: _records(item, name, _recommendation), path)
    if 'data' not in value:
        return
    data, data_path = value['data'], path + '.data'
    _mapping(data, data_path)
    _fields(data, ('metrics', 'readability', 'image_analysis', 'mobile', 'performance',
                   'quality_assessment', 'scores', 'network_metrics', 'metric_sources', 'open_graph'), _mapping, data_path)
    _fields(data, ('structured_data',), lambda item, name: _records(item, name, _mapping), data_path)
    for container, container_path in ((data, data_path), (data.get('metrics', {}), data_path + '.metrics')):
        _fields(container, ('word_count', 'image_count', 'total_resources'),
                lambda item, name: None if item is None else _count(item, name), container_path)
        _fields(container, ('html_fetch_time', 'content_size_mb', 'lcp', 'inp', 'fid', 'cls', 'fcp', 'tti', 'tbt', 'ttfb'), _number, container_path)
    for key in ('title', 'description'):
        if key in data:
            if isinstance(data[key], dict):
                _fields(data[key], ('text',), _text, data_path + '.' + key)
                _fields(data[key], ('length',), _count, data_path + '.' + key)
            else:
                _text(data[key], data_path + '.' + key)
    for key in ('internal_links', 'external_links', 'non_http_links'):
        if key in data:
            _records(data[key], data_path + '.' + key, _link)
    _fields(data, ('recommendations',), lambda item, name: _records(item, name, _recommendation), data_path)


def _link(value, path):
    _mapping(value, path)
    _fields(value, ('url', 'href', 'text', 'anchor_text'), _text, path)


def _common(data, path):
    _fields(data, ('schema_version', 'url', 'requested_url', 'status', 'error', 'reason'), _text, path)
    _fields(data, ('overall_score', 'score'), _score, path)
    _fields(data, ('issue_counts',), _counts, path)
    _fields(data, ('category_scores',), _scores, path)
    _fields(data, ('rule_results', 'aggregated_issues'), lambda item, name: _records(item, name, _issue), path)
    _fields(data, ('rule_coverage',), _coverage, path)
    _fields(data, ('coverage', 'scoring', 'aggregation_stats', 'summary', 'technical_health', 'metadata'), _mapping, path)
    _fields(data, ('executive_summary',), _executive, path)
    _fields(data, ('enhanced_recommendations',), lambda item, name: _records(item, name, _recommendation), path)
    _fields(data, ('recommendations',), _recommendations, path)
    if 'coverage' in data:
        _fields(data['coverage'], ('rules',), _coverage, path + '.coverage')
    if 'scores' in data:
        scores = data['scores']
        _mapping(scores, path + '.scores')
        _fields(scores, ('overall',), _score, path + '.scores')
        _fields(scores, ('categories',), _scores, path + '.scores')
        _fields(scores, ('scoring_versions',), lambda item, name: _records(item, name, _text), path + '.scores')
    if 'aggregation_stats' in data:
        _fields(data['aggregation_stats'], ('reduction_ratio',), _number, path + '.aggregation_stats')
    if 'performance_metrics' in data:
        metrics = data['performance_metrics']
        metrics_path = path + '.performance_metrics'
        _mapping(metrics, metrics_path)
        _fields(metrics, ('load_time_stats', 'score_stats', 'status_codes'), _mapping, metrics_path)
        _fields(metrics, ('load_times', 'content_sizes', 'issues_per_page', 'scores_per_page', 'slowest_pages', 'lowest_scoring_pages'),
                lambda item, name: _records(item, name, _mapping), metrics_path)


def _optional_count(value, path):
    if value is not None:
        _count(value, path)


def _boolean(value, path):
    if type(value) is not bool:
        raise ContractError(path, 'must be a boolean')


def _page_facts(value, path):
    """Validate fields consumed during site aggregation, without inventing them."""
    _mapping(value, path)
    _fields(value, ('facts_version', 'url', 'base_url'), _text, path)
    if 'robots' in value:
        _mapping(value['robots'], path + '.robots')
        _fields(value['robots'], ('noindex', 'nofollow'), _boolean, path + '.robots')
    if 'anchors' in value:
        _records(value['anchors'], path + '.anchors', _mapping)
        for index, anchor in enumerate(value['anchors']):
            anchor_path = f'{path}.anchors[{index}]'
            _required(anchor, ('url', 'attrs'), anchor_path)
            _fields(anchor, ('url',), lambda item, name: _text(item, name, nullable=True), anchor_path)
            if 'attrs' in anchor:
                _mapping(anchor['attrs'], anchor_path + '.attrs')
                if 'rel' in anchor['attrs']:
                    rel = anchor['attrs']['rel']
                    if isinstance(rel, list):
                        _records(rel, anchor_path + '.attrs.rel', _text)
                    elif rel is not None:
                        _text(rel, anchor_path + '.attrs.rel')
    if 'canonical' in value:
        canonical_path = path + '.canonical'
        canonical = value['canonical']
        _mapping(canonical, canonical_path)
        _fields(canonical, ('headers_checked',), _boolean, canonical_path)
        _fields(canonical, ('parse_errors',), _count, canonical_path)
        if 'declarations' in canonical:
            _records(canonical['declarations'], canonical_path + '.declarations', _mapping)
            for index, declaration in enumerate(canonical['declarations']):
                declaration_path = f'{canonical_path}.declarations[{index}]'
                _required(declaration, ('url', 'eligible'), declaration_path)
                _fields(declaration, ('url', 'href'), lambda item, name: _text(item, name, nullable=True), declaration_path)
                _fields(declaration, ('eligible',), _boolean, declaration_path)
                _fields(declaration, ('source', 'reason'), _text, declaration_path)


def _site_page(value, path):
    _mapping(value, path)
    _required(value, ('url', 'canonical_targets', 'canonical_status', 'canonical_terminal', 'canonical_hops',
                      'incoming_links', 'outgoing_links', 'link_depth'), path)
    _fields(value, ('url', 'canonical_status'), _text, path)
    _fields(value, ('canonical_terminal',), lambda item, name: _text(item, name, nullable=True), path)
    _fields(value, ('canonical_targets',), lambda item, name: _records(item, name, _text), path)
    _fields(value, ('incoming_links',), _count, path)
    _fields(value, ('canonical_hops', 'canonical_cycle_id', 'outgoing_links', 'nofollow_links', 'link_depth', 'component'), _optional_count, path)
    _fields(value, ('facts_available', 'content_complete', 'canonical_headers_checked'), _boolean, path)
    if value.get('reachable') is not None:
        _boolean(value['reachable'], path + '.reachable')


def _site_analysis(value, path):
    _mapping(value, path)
    _required(value, ('version', 'scope', 'coverage', 'canonicals', 'links', 'pages', 'findings'), path)
    _fields(value, ('version', 'scope'), _text, path)
    _records(value['pages'], path + '.pages', _site_page)
    _records(value['findings'], path + '.findings', _issue)
    _mapping(value['coverage'], path + '.coverage')
    _fields(value['coverage'], ('inventory_pages', 'pages_with_facts', 'complete_html_pages'), _count, path + '.coverage')
    _fields(value['coverage'], ('crawl_complete',), _boolean, path + '.coverage')
    _fields(value['coverage'], ('note',), _text, path + '.coverage')
    _mapping(value['canonicals'], path + '.canonicals')
    _fields(value['canonicals'], ('status_counts',), _counts, path + '.canonicals')
    _fields(value['canonicals'], ('unchecked_targets',), lambda item, name: _records(item, name, _text), path + '.canonicals')
    _mapping(value['links'], path + '.links')
    links = value['links']
    _required(links, ('node_count', 'edge_count', 'roots', 'components', 'unfetched_targets', 'edges', 'depth_method'), path + '.links')
    _fields(links, ('node_count', 'edge_count'), _count, path + '.links')
    _fields(links, ('root_source', 'depth_method'), _text, path + '.links')
    _fields(links, ('roots', 'unfetched_targets'), lambda item, name: _records(item, name, _text), path + '.links')
    for collection, collection_path in ((links['components'], path + '.links.components'),
                                        (value['canonicals'].get('cycles', []), path + '.canonicals.cycles')):
        _records(collection, collection_path, _mapping)
        for index, group in enumerate(collection):
            group_path = f'{collection_path}[{index}]'
            _required(group, ('id', 'urls'), group_path)
            _count(group['id'], group_path + '.id')
            _records(group['urls'], group_path + '.urls', _text)
    _records(links['edges'], path + '.links.edges', _mapping)
    for index, edge in enumerate(links['edges']):
        edge_path = f'{path}.links.edges[{index}]'
        _required(edge, ('source', 'target', 'nofollow', 'target_observed'), edge_path)
        _fields(edge, ('source', 'target'), _text, edge_path)
        _fields(edge, ('nofollow', 'target_observed'), _boolean, edge_path)
    if links['edge_count'] != len(links['edges']) or links['node_count'] != len(value['pages']):
        raise ContractError(path + '.links', 'node and edge counts must match the recorded graph')


def _page(data, path, strict=False):
    _mapping(data, path)
    if strict:
        _required(data, ('schema_version', 'url', 'status', 'status_code', 'overall_score', 'issues', 'issue_counts', 'recommendations'), path)
        if data['status'] not in ('complete', 'partial', 'error', 'skipped'):
            raise ContractError(path + '.status', 'must be complete, partial, error, or skipped')
    _common(data, path)
    _fields(data, ('page_facts',), _page_facts, path)
    _fields(data, ('site_analysis',), _site_page, path)
    for key in ('status_code', 'content_length'):
        if key in data and (strict or data[key] is not None):
            _count(data[key], path + '.' + key)
    _fields(data, ('load_time', 'analysis_time'), _number, path)
    _fields(data, ('analyzer_errors', 'timings', 'context'), _mapping, path)
    _fields(data, ('redirect_chain',), lambda item, name: _records(item, name, _mapping), path)
    _fields(data, ANALYZER_NAMES, _analyzer, path)
    if 'issues' in data:
        issues = data['issues']
        if isinstance(issues, dict) and not strict:
            # Historical site page summaries contain issue-count dictionaries.
            _counts(issues, path + '.issues')
        else:
            _records(issues, path + '.issues', _issue)
    if strict:
        _list(data['recommendations'], path + '.recommendations')
        if not data['url'].strip():
            raise ContractError(path + '.url', 'must not be empty')
        if data['status'] in ('error', 'skipped') and data['overall_score'] is not None:
            raise ContractError(path + '.overall_score', 'must be null for an error or skipped page')
        if data['status'] == 'error' and not data.get('error', '').strip():
            raise ContractError(path + '.error', 'an error page requires an explanation')
        if data.get('error') and data['status'] != 'error':
            raise ContractError(path + '.status', 'must be error when the page has an error')


def _site(data, path, strict=False):
    _mapping(data, path)
    if strict:
        _required(data, ('schema_version', 'status'), path)
        if data['status'] not in ('complete', 'partial', 'error'):
            raise ContractError(path + '.status', 'must be complete, partial, or error')
        if not (data['status'] == 'error' and data.get('error') and 'pages' not in data):
            _required(data, ('summary', 'scores', 'issues', 'pages', 'recommendations'), path)
            for key, required in (
                ('summary', ('total_pages', 'successful_pages', 'partial_pages', 'failed_pages', 'skipped_pages')),
                ('scores', ('overall', 'categories')),
                ('issues', ('aggregated', 'stats', 'counts', 'top_issues')),
                ('pages', ('summary', 'detailed', 'failed', 'skipped')),
                ('recommendations', ('specific', 'executive')),
            ):
                _mapping(data[key], path + '.' + key)
                _required(data[key], required, path + '.' + key)
    _common(data, path)
    _fields(data, ('site_analysis',), _site_analysis, path)
    if 'summary' in data:
        _fields(data['summary'], ('total_pages', 'successful_pages', 'partial_pages', 'failed_pages', 'skipped_pages'), _count, path + '.summary')
    if 'issues' in data:
        issues = data['issues']
        if isinstance(issues, dict):
            _fields(issues, ('aggregated', 'top_issues'), lambda item, name: _records(item, name, _issue), path + '.issues')
            _fields(issues, ('stats',), _mapping, path + '.issues')
            if 'stats' in issues:
                _fields(issues['stats'], ('reduction_ratio',), _number, path + '.issues.stats')
            _fields(issues, ('counts',), _counts, path + '.issues')
        else:
            _records(issues, path + '.issues', _issue)
    if 'pages' in data:
        pages = data['pages']
        if isinstance(pages, dict):
            for key in ('summary', 'detailed', 'failed', 'skipped'):
                if key in pages:
                    _records(pages[key], path + '.pages.' + key, _page)
        else:
            _records(pages, path + '.pages', _page)


def validate_page_result(data, *, strict=False, path='$'):
    """Validate a page or historical page summary and return the same object."""
    validate_json_value(data, path)
    _page(data, path, strict)
    return data


def validate_site_report(data, *, strict=False, path='$'):
    """Validate a site envelope; archived nested pages keep compatible validation."""
    validate_json_value(data, path)
    _site(data, path, strict)
    return data


def validate_report(data, *, strict=False):
    """Validate either report shape before any export writer opens a file."""
    _mapping(data, '$')
    if any(key in data for key in ('pages', 'aggregated_issues')) or ('summary' in data and 'scores' in data):
        return validate_site_report(data, strict=strict)
    if data.get('status') == 'error' and 'url' not in data:
        return validate_site_report(data, strict=strict)
    return validate_page_result(data, strict=strict)

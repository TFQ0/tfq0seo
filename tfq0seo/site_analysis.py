"""Cross-page observations over fetched evidence, with no additional requests.

Graph traversal is iterative and memoized. Canonical paths retain their next
hop and terminal instead of copying every suffix of a long chain into reports.
"""

from collections import Counter, defaultdict, deque
from urllib.parse import urlsplit

from .rules import RuleDefinition, register_rules, rule_result
from .urls import is_internal_url, resolve_url


SITE_ANALYSIS_VERSION = '1.0'
_CANONICAL_REFERENCE = 'https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls'
_LINK_REFERENCE = 'https://developers.google.com/search/docs/crawling-indexing/links-crawlable'

register_rules([
    RuleDefinition('site.canonical_' + name, 'seo', severity, recommendation,
                   'Canonical declarations and target observations within the supplied page inventory.',
                   (_CANONICAL_REFERENCE,), '2026-09-21', scored=False, title=title)
    for name, severity, title, recommendation in (
        ('conflict', 'warning', 'Conflicting canonical targets',
         'Reconcile the observed canonical declarations so they identify one intended representative URL.'),
        ('cycle', 'warning', 'Canonical cycle',
         'Break the recorded cycle and point each duplicate directly to its intended representative URL.'),
        ('chain', 'notice', 'Canonical chain',
         'Review the recorded chain and point directly to the intended terminal canonical URL.'),
        ('target_error', 'warning', 'Canonical target returned an HTTP error',
         'Fix the observed target response or select an accessible canonical URL.'),
        ('target_noindex', 'warning', 'Canonical target declares noindex',
         'Reconcile the canonical preference with the target page\'s observed noindex directive.'),
        ('target_redirect', 'notice', 'Canonical target redirects',
         'Review the observed redirect and use the intended final canonical URL directly.'),
    )
])
register_rules([
    RuleDefinition('site.links_' + name, 'links', 'notice', recommendation,
                   'Observed internal HTML links; this is not a complete site inventory or a ranking metric.',
                   (_LINK_REFERENCE,), '2026-09-21', scored=False, title=title)
    for name, title, recommendation in (
        ('no_incoming', 'No incoming links observed',
         'Check whether this page should be linked from relevant pages. Expand crawl coverage before calling it orphaned.'),
        ('unreachable', 'No link path observed from the entry pages',
         'Review navigation from the recorded entry pages; unfetched pages may contain additional paths.'),
    )
])


def url_identity(url):
    """Reuse HTTP URL resolution, preserving queries and removing fragments."""
    resolved = resolve_url(url, url)
    if not resolved or urlsplit(resolved).scheme not in ('http', 'https'):
        return None
    return resolved.split('#', 1)[0]


def _walk_canonicals(next_hops, endings):
    """Resolve a functional graph in O(V + E), including redirect aliases."""
    resolved = dict(endings)
    cycles = []
    for start in sorted(next_hops):
        path, positions = [], {}
        current = start
        while current not in resolved and current not in positions:
            positions[current] = len(path)
            path.append(current)
            if current not in next_hops:
                resolved[current] = (current, 'unchecked', 0, None)
                break
            current = next_hops[current]
        if current in positions and current not in resolved:
            members = path[positions[current]:]
            first = members.index(min(members))
            members = members[first:] + members[:first]
            cycle_id = len(cycles)
            cycles.append({'id': cycle_id, 'urls': members})
            for member in members:
                resolved[member] = (None, 'cycle', None, cycle_id)
        for node in reversed(path):
            if node not in resolved:
                terminal, status, hops, cycle_id = resolved[next_hops[node]]
                resolved[node] = (terminal, status, hops + 1 if hops is not None else None, cycle_id)
    return resolved, cycles


def analyze_site(pages, *, start_url=None, crawl_complete=False):
    """Build additive, unscored site findings from validated page dictionaries.

    Missing facts and unfetched targets remain unknown. Self links do not count
    as incoming links. Reachability uses observed hrefs, including nofollow
    hints, and never claims to model a search engine's chosen crawl paths.
    """
    groups = defaultdict(list)
    for page in pages:
        identity = url_identity(page.get('url'))
        if identity:
            groups[identity].append(page)

    aliases = defaultdict(set)
    for url, records in groups.items():
        for page in records:
            # A terminal HTTP error or skipped non-HTML response still proves
            # its redirect destination. Network/loop/limit failures do not.
            status = page.get('status_code') or 0
            if not (200 <= status < 300 or 400 <= status <= 599):
                continue
            sources = [page.get('requested_url')]
            sources.extend(hop.get('url') for hop in page.get('redirect_chain', []))
            for source in sources:
                alias = url_identity(source)
                if alias and alias != url:
                    aliases[alias].add(url)
    redirects = {alias: next(iter(targets)) for alias, targets in aliases.items()
                 if len(targets) == 1 and alias not in groups}

    facts_by_url, rows, endings, next_hops = {}, {}, {}, dict(redirects)
    links_observed = {}
    declarations = {}
    noindex = set()
    statuses = {}
    complete_facts = set()
    for url in sorted(groups):
        records = groups[url]
        status_codes = {page.get('status_code') or 0 for page in records}
        statuses[url] = next(iter(status_codes)) if len(status_codes) == 1 else 0
        usable = [page for page in records if not page.get('error') and not page.get('skipped')
                  and 200 <= (page.get('status_code') or 0) < 300 and isinstance(page.get('page_facts'), dict)]
        facts = [page['page_facts'] for page in usable]
        facts_by_url[url] = facts
        links_observed[url] = bool(facts) and all('anchors' in fact for fact in facts)
        if (usable and all(not page.get('truncated') for page in records) and len(usable) == len(records)
                and all({'anchors', 'robots', 'canonical'} <= fact.keys() and
                        {'declarations', 'headers_checked', 'parse_errors'} <= fact['canonical'].keys() and
                        {'noindex', 'nofollow'} <= fact['robots'].keys() for fact in facts)):
            complete_facts.add(url)
        if any(fact.get('robots', {}).get('noindex') is True for fact in facts):
            noindex.add(url)
        canonical = [fact.get('canonical') for fact in facts]
        observed = bool(canonical) and all(isinstance(item, dict) and
                                           {'declarations', 'headers_checked', 'parse_errors'} <= item.keys()
                                           for item in canonical)
        declarations[url] = [declaration for item in canonical if isinstance(item, dict)
                             for declaration in item.get('declarations', [])]
        declarations[url].sort(key=lambda item: tuple(str(item.get(key, '')) for key in
                                                       ('url', 'href', 'source', 'eligible', 'reason')))
        targets = sorted({target for declaration in declarations[url] if declaration.get('eligible')
                          for target in [url_identity(declaration.get('url'))] if target})
        invalid = any(item.get('eligible') and not url_identity(item.get('url')) for item in declarations[url])
        uncertain = (not observed or url not in complete_facts or
                     any(item.get('parse_errors', 0) for item in canonical if isinstance(item, dict)))
        headers_checked = observed and all(item.get('headers_checked') is True for item in canonical)
        rows[url] = {'url': url, 'canonical_targets': targets, 'canonical_status': 'unknown',
                     'canonical_terminal': None, 'canonical_hops': None, 'canonical_cycle_id': None,
                     'incoming_links': 0, 'outgoing_links': 0 if facts else None,
                     'nofollow_links': 0 if facts else None, 'link_depth': None, 'reachable': None,
                     'component': None, 'facts_available': bool(facts),
                     'content_complete': url in complete_facts, 'canonical_headers_checked': headers_checked}
        status = ('http_error' if statuses[url] >= 400 else 'conflict' if len(targets) > 1 else
                  'invalid' if invalid else 'unknown' if uncertain else
                  'self' if targets == [url] else 'none' if not targets and headers_checked else
                  'unknown' if not targets else None)
        if status is not None:
            endings[url] = (url, status, 0, None)
        else:
            next_hops[url] = targets[0]

    resolved, cycles = _walk_canonicals(next_hops, endings)
    findings = []

    def finding(rule_id, url, evidence):
        result = rule_result(rule_id, evidence, source='fetched_site_inventory')
        result.update(scope='site', url=url)
        findings.append(result)

    for url, row in rows.items():
        terminal, status, hops, cycle_id = resolved[url]
        row.update(canonical_terminal=terminal, canonical_hops=hops, canonical_cycle_id=cycle_id)
        if hops and status in ('self', 'none'):
            status = 'chain' if hops > 1 else 'resolved'
        row['canonical_status'] = status
        evidence = {key: row[key] for key in ('canonical_targets', 'canonical_terminal', 'canonical_hops', 'canonical_cycle_id')}
        # Conflicts are attributed to their source; callers leading to one keep
        # the terminal status without duplicating the target's conflict evidence.
        if len(row['canonical_targets']) > 1:
            finding('site.canonical_conflict', url, {'declarations': declarations[url], **evidence})
        if status == 'cycle':
            finding('site.canonical_cycle', url, evidence)
        if hops is not None and hops > 1:
            finding('site.canonical_chain', url, evidence)
        for target in row['canonical_targets']:
            destination = redirects.get(target, target)
            if target in redirects:
                finding('site.canonical_target_redirect', url, {'target': target, 'destination': destination})
            elif statuses.get(target) in (301, 302, 303, 307, 308):
                finding('site.canonical_target_redirect', url, {'target': target, 'destination': None,
                                                               'status_code': statuses[target],
                                                               'reason': 'The redirect destination was not observed.'})
            if statuses.get(destination, 0) >= 400:
                finding('site.canonical_target_error', url, {'target': target, 'destination': destination,
                                                            'status_code': statuses[destination]})
            if destination in noindex:
                finding('site.canonical_target_noindex', url, {'target': target, 'destination': destination})

    outgoing = {url: set() for url in rows}
    incoming = {url: set() for url in rows}
    edges, unknown_targets = [], set()
    for url, facts in facts_by_url.items():
        links = {}
        for fact in facts:
            for anchor in fact.get('anchors', []):
                target = url_identity(anchor.get('url'))
                if not target or not is_internal_url(target, url):
                    continue
                target = redirects.get(target, target)
                rel = anchor.get('attrs', {}).get('rel', [])
                rel = rel if isinstance(rel, list) else str(rel).split()
                nofollow = fact.get('robots', {}).get('nofollow') is True or 'nofollow' in {str(item).lower() for item in rel}
                # Any observed ordinary link makes the pair non-nofollow.
                links[target] = links.get(target, True) and nofollow
        for target, nofollow in sorted(links.items()):
            edges.append({'source': url, 'target': target, 'nofollow': nofollow, 'target_observed': target in rows})
            outgoing[url].add(target)
            if target in incoming and target != url:
                incoming[target].add(url)
            if target not in rows:
                unknown_targets.add(target)
        rows[url]['outgoing_links'] = len(links) if links_observed[url] else None
        rows[url]['nofollow_links'] = sum(links.values()) if links_observed[url] else None

    root = url_identity(start_url)
    root = redirects.get(root, root)
    roots = [root] if root in rows else []
    root_source = 'crawl_start' if roots else 'unavailable'
    if start_url is None:
        roots = [url for url in rows if urlsplit(url).path == '/' and not urlsplit(url).query]
        root_source = 'observed_homepages' if roots else 'unavailable'
    depth = dict.fromkeys(roots, 0)
    queue = deque(roots)
    while queue:
        source = queue.popleft()
        for target in sorted(outgoing[source]):
            if target in rows and target not in depth:
                depth[target] = depth[source] + 1
                queue.append(target)

    components = []
    remaining = set(rows)
    for start in rows:
        if start not in remaining:
            continue
        component_id = len(components)
        members, queue = [], deque([start])
        remaining.remove(start)
        while queue:
            current = queue.popleft()
            members.append(current)
            rows[current]['component'] = component_id
            for neighbor in (outgoing[current] | incoming[current]) & remaining:
                remaining.remove(neighbor)
                queue.append(neighbor)
        components.append({'id': component_id, 'urls': sorted(members)})
    for url, row in rows.items():
        row['incoming_links'] = len(incoming[url])
        row['link_depth'] = depth.get(url)
        row['reachable'] = url in depth if roots else None
        if facts_by_url[url] and url not in roots:
            if not incoming[url]:
                finding('site.links_no_incoming', url, {'incoming_links': 0, 'inventory_pages': len(rows),
                                                       'interpretation': 'Candidate only; unobserved pages may link here.'})
            elif roots and url not in depth:
                finding('site.links_unreachable', url, {'roots': roots, 'component': row['component'],
                                                       'interpretation': 'No path in the observed graph.'})

    return {
        'version': SITE_ANALYSIS_VERSION,
        'scope': 'Observed HTML links, canonical declarations and HTTP responses; no extra fetches or page-score deductions.',
        'coverage': {'inventory_pages': len(rows), 'pages_with_facts': sum(bool(facts) for facts in facts_by_url.values()),
                     'complete_html_pages': len(complete_facts), 'crawl_complete': bool(crawl_complete),
                     'note': 'A completed crawl still obeys its configured scope. Missing targets and paths remain unverified.'},
        'canonicals': {'status_counts': dict(Counter(row['canonical_status'] for row in rows.values())),
                       'cycles': cycles, 'unchecked_targets': sorted({terminal for terminal, status, _, _ in resolved.values()
                                                                   if status == 'unchecked' and terminal is not None})},
        'links': {'node_count': len(rows), 'edge_count': len(edges), 'roots': roots, 'root_source': root_source,
                  'unfetched_targets': sorted(unknown_targets), 'components': components, 'edges': edges,
                  'depth_method': 'Shortest observed href path, including nofollow hints; not search-engine crawl depth.'},
        'pages': list(rows.values()), 'findings': findings,
    }

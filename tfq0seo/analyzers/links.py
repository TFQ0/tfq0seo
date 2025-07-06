"""
Link analyzer for internal/external links and broken links
"""
from typing import Dict, List, Optional, Any, Set, Tuple
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urlparse, urljoin, parse_qs
import re
import logging
from ..core.issue_helper import IssueHelper

logger = logging.getLogger(__name__)

class LinkAnalyzer:
    """Analyzer for link structure and quality"""
    
    def __init__(self, config):
        self.config = config
        self.affiliate_patterns = [
            r'amzn\.to', r'amazon\..*\/(dp|gp)', r'affiliate', r'partner',
            r'click\.linksynergy', r'go\.redirectingat', r'shareasale',
            r'clickbank', r'cj\.com', r'dpbolvw\.net', r'kqzyfj\.com',
            r'commission', r'ref=', r'utm_source=.*affiliate'
        ]
        
    def analyze(self, page_data: Dict, soup: Optional[BeautifulSoup]) -> Dict[str, Any]:
        """Analyze links on the page"""
        if not soup:
            return {
                'issues': [{
                    'type': 'no_content',
                    'severity': 'critical',
                    'message': 'No content to analyze links'
                }]
            }
        
        # Validate page_data
        if not isinstance(page_data, dict):
            return {
                'issues': [{
                    'type': 'invalid_data',
                    'severity': 'critical',
                    'message': 'Invalid page data for link analysis'
                }]
            }
        
        issues = []
        
        # Get all links from page data
        links_data = page_data.get('links', [])
        if not isinstance(links_data, list):
            links_data = []
        
        # Get current URL safely
        current_url = page_data.get('url', '')
        if not current_url:
            return {
                'issues': [{
                    'type': 'missing_url',
                    'severity': 'critical',
                    'message': 'Missing URL for link analysis'
                }]
            }
        
        # Analyze link structure
        link_analysis = self._analyze_link_structure(links_data, current_url)
        
        # Check for broken links
        broken_links = self._identify_broken_links(links_data, page_data)
        if broken_links:
            issues.append(IssueHelper.create_issue(
                'broken_internal_links',
                additional_info={
                    'count': len(broken_links),
                    'details': broken_links[:5]  # First 5 for context
                }
            ))
        
        # Analyze anchor text
        anchor_analysis = self._analyze_anchor_text(links_data, soup)
        issues.extend(anchor_analysis['issues'])
        
        # Check for link attributes
        link_attributes = self._analyze_link_attributes(soup)
        issues.extend(link_attributes['issues'])
        
        # Analyze internal link structure
        internal_link_analysis = self._analyze_internal_links(
            link_analysis['internal_links'], 
            current_url
        )
        issues.extend(internal_link_analysis['issues'])
        
        # Check for affiliate links
        affiliate_analysis = self._detect_affiliate_links(link_analysis['external_links'])
        issues.extend(affiliate_analysis['issues'])
        
        # Analyze link depth and distribution
        link_distribution = self._analyze_link_distribution(soup, link_analysis)
        issues.extend(link_distribution['issues'])
        
        # Check for orphan pages (based on internal links)
        orphan_check = self._check_for_orphan_indicators(
            link_analysis['internal_links'],
            page_data
        )
        issues.extend(orphan_check['issues'])
        
        # Analyze follow/nofollow distribution
        follow_analysis = self._analyze_follow_distribution(link_attributes)
        issues.extend(follow_analysis['issues'])
        
        # Check redirect chains
        redirect_analysis = self._analyze_redirect_chains(page_data)
        issues.extend(redirect_analysis['issues'])
        
        # Calculate link score
        link_score = self._calculate_link_score(issues, link_analysis)
        
        return {
            'total_links': link_analysis['total_count'],
            'internal_links': link_analysis['internal_count'],
            'external_links': link_analysis['external_count'],
            'unique_links': link_analysis['unique_count'],
            'broken_links': len(broken_links),
            'nofollow_links': link_attributes['nofollow_count'],
            'sponsored_links': link_attributes['sponsored_count'],
            'ugc_links': link_attributes['ugc_count'],
            'affiliate_links': affiliate_analysis['count'],
            'link_depth': internal_link_analysis.get('max_depth', 0),
            'link_distribution': link_distribution['distribution'],
            'link_details': {
                'internal': link_analysis['internal_links'][:20],  # Top 20
                'external': link_analysis['external_links'][:20],  # Top 20
                'broken': broken_links[:10],  # Top 10
                'affiliate': affiliate_analysis['links'][:10]  # Top 10
            },
            'anchor_text_analysis': anchor_analysis['summary'],
            'follow_distribution': follow_analysis['distribution'],
            'redirect_chains': redirect_analysis['chains'],
            'link_score': link_score,
            'issues': issues
        }
    
    def _analyze_link_structure(self, links_data: List[Dict], current_url: str) -> Dict[str, Any]:
        """Analyze link structure and categorize links"""
        current_parsed = urlparse(current_url)
        current_domain = current_parsed.netloc
        
        internal_links = []
        external_links = []
        unique_urls = set()
        subdomain_links = []
        
        for link in links_data:
            url = link.get('url', '')
            if not url:
                continue
            
            # Make URL absolute
            absolute_url = urljoin(current_url, url)
            parsed = urlparse(absolute_url)
            unique_urls.add(absolute_url)
            
            # Categorize link
            if parsed.netloc == current_domain:
                internal_links.append({
                    'url': absolute_url,
                    'text': link.get('text', '').strip(),
                    'tag': link.get('tag', 'a'),
                    'attributes': link.get('attributes', {}),
                    'context': link.get('context', '')
                })
            elif parsed.netloc.endswith('.' + current_domain.split('.')[-1]):
                # Subdomain
                subdomain_links.append({
                    'url': absolute_url,
                    'text': link.get('text', '').strip(),
                    'subdomain': parsed.netloc.split('.')[0]
                })
            else:
                external_links.append({
                    'url': absolute_url,
                    'text': link.get('text', '').strip(),
                    'tag': link.get('tag', 'a'),
                    'domain': parsed.netloc,
                    'attributes': link.get('attributes', {})
                })
        
        return {
            'total_count': len(links_data),
            'internal_count': len(internal_links),
            'external_count': len(external_links),
            'subdomain_count': len(subdomain_links),
            'unique_count': len(unique_urls),
            'internal_links': internal_links,
            'external_links': external_links,
            'subdomain_links': subdomain_links
        }
    
    def _identify_broken_links(self, links_data: List[Dict], page_data: Dict) -> List[Dict]:
        """Identify potentially broken links"""
        broken_links = []
        
        # Check crawl results if available
        crawl_results = page_data.get('crawl_results', {})
        
        for link in links_data:
            url = link.get('url', '')
            if not url:
                continue
            
            absolute_url = urljoin(page_data['url'], url)
            
            # Check crawl results for status codes
            if absolute_url in crawl_results:
                status_code = crawl_results[absolute_url].get('status_code', 0)
                if status_code >= 400:
                    broken_links.append({
                        'url': absolute_url,
                        'text': link.get('text', ''),
                        'status_code': status_code,
                        'reason': f'HTTP {status_code}'
                    })
                    continue
            
            # Check for obviously broken patterns
            broken_patterns = [
                (r'/404(\.|/|$)', 'Contains 404 in URL'),
                (r'error\.html?$', 'Error page URL'),
                (r'not[-_]?found', 'Contains not-found in URL'),
                (r'^#$', 'Empty hash link'),
                (r'^javascript:void', 'JavaScript void link'),
                (r'^\s*$', 'Empty URL')
            ]
            
            for pattern, reason in broken_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    broken_links.append({
                        'url': url,
                        'text': link.get('text', ''),
                        'reason': reason
                    })
                    break
            
            # Check for malformed URLs
            try:
                parsed = urlparse(absolute_url)
                if not parsed.netloc and not parsed.path:
                    broken_links.append({
                        'url': url,
                        'text': link.get('text', ''),
                        'reason': 'Malformed URL'
                    })
            except:
                broken_links.append({
                    'url': url,
                    'text': link.get('text', ''),
                    'reason': 'Invalid URL format'
                })
        
        return broken_links
    
    def _analyze_anchor_text(self, links_data: List[Dict], soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze anchor text quality and diversity"""
        issues = []
        
        # Common generic anchors to avoid
        generic_anchors = [
            'click here', 'here', 'read more', 'more', 'link', 'this',
            'learn more', 'continue', 'go', 'visit', 'download', 'click'
        ]
        
        empty_anchors = 0
        generic_count = 0
        image_only_links = 0
        duplicate_anchors = {}
        over_optimized = 0
        
        anchor_texts = []
        keyword_rich_anchors = []
        
        # Also analyze actual link elements in soup for better context
        all_links = soup.find_all('a', href=True)
        
        for link_elem in all_links:
            # Get anchor text
            text = link_elem.get_text(strip=True)
            
            # Check if link contains only image
            if not text and link_elem.find('img'):
                img = link_elem.find('img')
                alt_text = img.get('alt', '').strip()
                if alt_text:
                    text = f'[IMG: {alt_text}]'
                else:
                    image_only_links += 1
            
            anchor_texts.append(text.lower())
            
            # Track duplicates
            if text:
                if text in duplicate_anchors:
                    duplicate_anchors[text] += 1
                else:
                    duplicate_anchors[text] = 1
            
            # Check for issues
            if not text:
                empty_anchors += 1
            elif text.lower() in generic_anchors:
                generic_count += 1
            elif len(text.split()) > 5:  # Long anchor text
                over_optimized += 1
            
            # Check if keyword-rich (contains common SEO keywords)
            seo_keywords = ['best', 'top', 'cheap', 'buy', 'review', 'guide']
            if any(keyword in text.lower() for keyword in seo_keywords):
                keyword_rich_anchors.append(text)
        
        # Issue checks
        if empty_anchors > 0:
            issues.append({
                'type': 'empty_anchor_text',
                'severity': 'critical',
                'message': f'{empty_anchors} links with empty anchor text'
            })
        
        if image_only_links > 0:
            issues.append({
                'type': 'image_links_no_alt',
                'severity': 'warning',
                'message': f'{image_only_links} image links without alt text'
            })
        
        if generic_count > 5:
            issues.append({
                'type': 'generic_anchor_text',
                'severity': 'warning',
                'message': f'{generic_count} links with generic anchor text'
            })
        
        # Check for over-optimization
        if over_optimized > 10:
            issues.append({
                'type': 'over_optimized_anchors',
                'severity': 'notice',
                'message': f'{over_optimized} links with long anchor text (>5 words)'
            })
        
        # Check for excessive duplicate anchors
        excessive_duplicates = {k: v for k, v in duplicate_anchors.items() if v > 5}
        if excessive_duplicates:
            issues.append({
                'type': 'duplicate_anchor_text',
                'severity': 'notice',
                'message': f'Excessive duplicate anchor texts found',
                'details': excessive_duplicates
            })
        
        # Calculate anchor text diversity
        unique_anchors = len(set(anchor_texts))
        total_anchors = len(anchor_texts)
        diversity_ratio = unique_anchors / total_anchors if total_anchors > 0 else 0
        
        if diversity_ratio < 0.5 and total_anchors > 20:
            issues.append({
                'type': 'low_anchor_diversity',
                'severity': 'notice',
                'message': f'Low anchor text diversity: {diversity_ratio:.2%}'
            })
        
        return {
            'summary': {
                'total_anchors': total_anchors,
                'empty_anchors': empty_anchors,
                'generic_anchors': generic_count,
                'unique_anchors': unique_anchors,
                'diversity_ratio': diversity_ratio,
                'keyword_rich_count': len(keyword_rich_anchors),
                'image_only_links': image_only_links
            },
            'issues': issues
        }
    
    def _analyze_link_attributes(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze link attributes like nofollow, sponsored, ugc, etc."""
        issues = []
        
        all_links = soup.find_all('a', href=True)
        
        nofollow_count = 0
        sponsored_count = 0
        ugc_count = 0
        target_blank_count = 0
        missing_rel_opener = 0
        download_links = 0
        
        rel_combinations = {}
        
        for link in all_links:
            href = link.get('href', '')
            rel = link.get('rel', [])
            if isinstance(rel, str):
                rel = rel.split()
            
            # Count rel attributes
            if 'nofollow' in rel:
                nofollow_count += 1
            if 'sponsored' in rel:
                sponsored_count += 1
            if 'ugc' in rel:
                ugc_count += 1
            
            # Track rel combinations
            rel_combo = ' '.join(sorted(rel))
            if rel_combo:
                rel_combinations[rel_combo] = rel_combinations.get(rel_combo, 0) + 1
            
            # Check target="_blank" security
            target = link.get('target', '')
            if target == '_blank':
                target_blank_count += 1
                
                # Check for security issue
                if 'noopener' not in rel and 'noreferrer' not in rel:
                    missing_rel_opener += 1
            
            # Check for download attribute
            if link.get('download') is not None:
                download_links += 1
            
            # Check external links without appropriate rel
            base_element = soup.find('base', href=True)
            base_href = base_element.get('href') if base_element else ''
            parsed = urlparse(urljoin(base_href, href))
            
            # Get current domain safely
            current_domain = ''
            if hasattr(soup, 'base') and soup.base is not None:
                current_domain = urlparse(str(soup.base.get('href', ''))).netloc
            else:
                # Fallback - extract domain from first link or use empty string
                current_domain = ''
            
            if parsed.netloc and parsed.netloc != current_domain:
                # External link checks
                if not any(r in rel for r in ['nofollow', 'sponsored', 'ugc']):
                    # Check if it's likely an affiliate or sponsored link
                    if any(pattern in href.lower() for pattern in ['affiliate', 'partner', 'ref=', 'utm_']):
                        issues.append({
                            'type': 'unmarked_affiliate_link',
                            'severity': 'warning',
                            'message': f'Possible affiliate link without rel="sponsored": {href[:50]}...'
                        })
        
        # Security issues
        if missing_rel_opener > 0:
            issues.append({
                'type': 'security_target_blank',
                'severity': 'warning',
                'message': f'{missing_rel_opener} links with target="_blank" missing rel="noopener"'
            })
        
        # Check rel attribute distribution
        total_external = sum(1 for link in all_links if urlparse(link.get('href', '')).netloc)
        if total_external > 0:
            nofollow_ratio = nofollow_count / total_external
            if nofollow_ratio > 0.8:
                issues.append({
                    'type': 'excessive_nofollow',
                    'severity': 'notice',
                    'message': f'High nofollow ratio on external links: {nofollow_ratio:.1%}'
                })
        
        return {
            'nofollow_count': nofollow_count,
            'sponsored_count': sponsored_count,
            'ugc_count': ugc_count,
            'target_blank_count': target_blank_count,
            'download_links': download_links,
            'rel_combinations': rel_combinations,
            'issues': issues
        }
    
    def _analyze_internal_links(self, internal_links: List[Dict], current_url: str) -> Dict[str, Any]:
        """Analyze internal link structure and depth"""
        issues = []
        
        if not internal_links:
            issues.append({
                'type': 'no_internal_links',
                'severity': 'warning',
                'message': 'Page has no internal links'
            })
            return {'issues': issues, 'max_depth': 0}
        
        # Calculate link depth from homepage
        current_parsed = urlparse(current_url)
        current_depth = len([p for p in current_parsed.path.split('/') if p])
        
        link_depths = []
        deep_links = []
        
        for link in internal_links:
            parsed = urlparse(link['url'])
            depth = len([p for p in parsed.path.split('/') if p])
            link_depths.append(depth)
            
            if depth > 4:  # Links deeper than 4 levels
                deep_links.append(link['url'])
        
        max_depth = max(link_depths) if link_depths else 0
        avg_depth = sum(link_depths) / len(link_depths) if link_depths else 0
        
        # Issues based on depth
        if deep_links:
            issues.append({
                'type': 'deep_internal_links',
                'severity': 'notice',
                'message': f'{len(deep_links)} internal links point to pages deeper than 4 levels'
            })
        
        # Check for internal link distribution
        if len(internal_links) < 3:
            issues.append({
                'type': 'few_internal_links',
                'severity': 'warning',
                'message': f'Only {len(internal_links)} internal links found'
            })
        elif len(internal_links) > 100:
            issues.append(IssueHelper.create_issue(
                'excessive_internal_links',
                current_value=f'{len(internal_links)} internal links',
                recommended_value='100-150 internal links maximum'
            ))
        
        # Check for links to important pages
        important_pages = ['/', '/about', '/contact', '/products', '/services']
        linked_important = sum(1 for link in internal_links 
                              if any(link['url'].endswith(page) for page in important_pages))
        
        if current_depth <= 1 and linked_important < 2:
            issues.append({
                'type': 'missing_important_links',
                'severity': 'notice',
                'message': 'Missing links to important site sections'
            })
        
        return {
            'max_depth': max_depth,
            'avg_depth': avg_depth,
            'deep_links': deep_links[:5],  # First 5
            'issues': issues
        }
    
    def _detect_affiliate_links(self, external_links: List[Dict]) -> Dict[str, Any]:
        """Detect affiliate and monetized links"""
        issues = []
        affiliate_links = []
        
        for link in external_links:
            url = link.get('url', '')
            
            # Check against affiliate patterns
            is_affiliate = any(re.search(pattern, url, re.IGNORECASE) 
                              for pattern in self.affiliate_patterns)
            
            # Check query parameters
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            affiliate_params = ['ref', 'affiliate', 'partner', 'utm_source', 'campaign']
            
            has_affiliate_params = any(param in params for param in affiliate_params)
            
            if is_affiliate or has_affiliate_params:
                affiliate_links.append({
                    'url': url,
                    'text': link.get('text', ''),
                    'domain': link.get('domain', '')
                })
        
        # Check if affiliate links are properly marked
        if affiliate_links:
            # This check would need to cross-reference with the attributes
            # For now, we'll flag if there are many affiliate links
            if len(affiliate_links) > 10:
                issues.append({
                    'type': 'many_affiliate_links',
                    'severity': 'notice',
                    'message': f'{len(affiliate_links)} affiliate links detected'
                })
            
            # Check affiliate disclosure
            # This is a basic check - would need content analysis for proper detection
            
        return {
            'count': len(affiliate_links),
            'links': affiliate_links,
            'issues': issues
        }
    
    def _analyze_link_distribution(self, soup: BeautifulSoup, link_analysis: Dict) -> Dict[str, Any]:
        """Analyze how links are distributed across the page"""
        issues = []
        distribution = {
            'header': 0,
            'navigation': 0,
            'main_content': 0,
            'sidebar': 0,
            'footer': 0,
            'total_sections': 0
        }
        
        # Common selectors for page sections
        section_selectors = {
            'header': ['header', 'nav', '.header', '#header', '.navigation', '#nav'],
            'main_content': ['main', 'article', '.content', '#content', '.main', '#main'],
            'sidebar': ['aside', '.sidebar', '#sidebar', '.widget'],
            'footer': ['footer', '.footer', '#footer']
        }
        
        # Count links in each section
        for section, selectors in section_selectors.items():
            for selector in selectors:
                elements = soup.select(selector)
                for element in elements:
                    links_in_section = element.find_all('a', href=True)
                    distribution[section] += len(links_in_section)
        
        distribution['total_sections'] = sum(1 for v in distribution.values() if v > 0 and v != distribution['total_sections'])
        
        # Check for link distribution issues
        total_links = link_analysis['total_count']
        if total_links > 0:
            # Check if too many links in navigation/header
            nav_ratio = (distribution['header'] + distribution['navigation']) / total_links
            if nav_ratio > 0.5:
                issues.append({
                    'type': 'nav_heavy_linking',
                    'severity': 'notice',
                    'message': f'{nav_ratio:.1%} of links are in navigation/header'
                })
            
            # Check main content links
            content_ratio = distribution['main_content'] / total_links
            if content_ratio < 0.2 and total_links > 20:
                issues.append({
                    'type': 'few_content_links',
                    'severity': 'warning',
                    'message': f'Only {content_ratio:.1%} of links are in main content'
                })
        
        return {
            'distribution': distribution,
            'issues': issues
        }
    
    def _check_for_orphan_indicators(self, internal_links: List[Dict], page_data: Dict) -> Dict[str, Any]:
        """Check for indicators that this might be an orphan page"""
        issues = []
        
        # Check if page has very few or no incoming internal links
        # This is a basic check - full orphan detection requires site-wide analysis
        current_url = page_data.get('url', '')
        current_parsed = urlparse(current_url)
        
        # Check if it's a deep page with no navigation
        depth = len([p for p in current_parsed.path.split('/') if p])
        
        if depth > 2 and len(internal_links) < 3:
            issues.append({
                'type': 'potential_orphan_page',
                'severity': 'warning',
                'message': 'Deep page with very few internal links - might be orphaned'
            })
        
        # Check for breadcrumb links
        has_breadcrumbs = any('breadcrumb' in str(link.get('attributes', {})).lower() 
                             for link in internal_links)
        
        if depth > 1 and not has_breadcrumbs:
            issues.append({
                'type': 'no_breadcrumb_navigation',
                'severity': 'notice',
                'message': 'No breadcrumb navigation detected'
            })
        
        return {'issues': issues}
    
    def _analyze_follow_distribution(self, link_attributes: Dict) -> Dict[str, Any]:
        """Analyze the distribution of follow vs nofollow links"""
        issues = []
        
        total_links = sum(link_attributes.get('rel_combinations', {}).values())
        nofollow = link_attributes.get('nofollow_count', 0)
        sponsored = link_attributes.get('sponsored_count', 0)
        ugc = link_attributes.get('ugc_count', 0)
        
        # Calculate follow links (links without nofollow/sponsored/ugc)
        nofollow_total = nofollow + sponsored + ugc
        follow_links = max(0, total_links - nofollow_total)
        
        distribution = {
            'follow': follow_links,
            'nofollow': nofollow,
            'sponsored': sponsored,
            'ugc': ugc,
            'follow_ratio': follow_links / total_links if total_links > 0 else 0
        }
        
        # Check for PageRank sculpting attempts
        if nofollow > 20 and distribution['follow_ratio'] < 0.5:
            issues.append({
                'type': 'possible_pagerank_sculpting',
                'severity': 'notice',
                'message': 'High number of nofollow links might indicate PageRank sculpting'
            })
        
        return {
            'distribution': distribution,
            'issues': issues
        }
    
    def _analyze_redirect_chains(self, page_data: Dict) -> Dict[str, Any]:
        """Analyze redirect chains in links"""
        issues = []
        redirect_chains = []
        
        # Check if the current page arrived via redirects
        redirect_chain = page_data.get('redirect_chain', [])
        if len(redirect_chain) > 1:
            issues.append(IssueHelper.create_issue(
                'redirect_chains',
                additional_info={
                    'chain_length': len(redirect_chain),
                    'chain': redirect_chain
                }
            ))
        
        # Check for links that might lead to redirects
        # This would need crawl data to properly detect
        
        return {
            'chains': redirect_chains,
            'issues': issues
        }
    
    def _calculate_link_score(self, issues: List[Dict], link_analysis: Dict) -> float:
        """Calculate overall link quality score"""
        score = 100.0
        
        # Define score deductions
        deductions = {
            'critical': 20,
            'warning': 10,
            'notice': 5
        }
        
        # Apply deductions for issues
        for issue in issues:
            severity = issue.get('severity', 'notice')
            score -= deductions.get(severity, 0)
        
        # Bonus for good practices
        if link_analysis['internal_count'] > 5:
            score += 5
        
        if link_analysis['unique_count'] / link_analysis['total_count'] > 0.8:
            score += 5
        
        # Ensure score stays in range
        return max(0, min(100, score)) 
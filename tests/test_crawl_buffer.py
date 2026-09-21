"""Slow or cancelled analysis cannot accumulate an entire crawl of DOMs."""

import asyncio

import pytest
from bs4 import BeautifulSoup

from tfq0seo.core.app import SEOAnalyzer
from tfq0seo.core.config import Config
from tfq0seo.core.crawler import Crawler


@pytest.mark.parametrize('stop', ['complete', 'cancel', 'deadline'])
def test_slow_analysis_bounds_fetches_and_releases_results(monkeypatch, stop):
    async def run():
        config = Config.from_dict({
            'crawler': {'max_concurrent': 2, 'max_pages': 31, 'max_depth': 2,
                        'use_sitemap': False, 'cache_enabled': False,
                        'max_crawl_time': 1 if stop == 'deadline' else 10},
            'analysis': {'max_analysis_threads': 1},
        })
        analyzer = SEOAnalyzer(config)
        capacity = config.crawler.effective_concurrency + config.analysis.max_analysis_threads
        fetched = []
        full = asyncio.Event()
        release = asyncio.Event()

        async def fetch(crawler, url, retry_count=0):
            fetched.append(url)
            if len(fetched) == capacity:
                full.set()
            html = ''.join(f'<a href="/page/{i}">Page</a>' for i in range(30)) if url.endswith('/') else '<p>Page</p>'
            return {'url': url, 'status_code': 200, 'soup': BeautifulSoup(html, 'html.parser'), 'html': html}

        async def analyze(raw, context):
            await release.wait()
            return {'url': raw['url'], 'status': 'error' if raw.get('error') else 'complete',
                    **({'error': raw['error']} if raw.get('error') else {})}

        monkeypatch.setattr(Crawler, 'fetch_page', fetch)
        monkeypatch.setattr(analyzer, '_analyze_with_semaphore', analyze)

        async def collect():
            return [result async for result in analyzer.crawl_site('https://example.test/')]

        task = asyncio.create_task(collect())
        try:
            await asyncio.wait_for(full.wait(), 2)
            await asyncio.sleep(1.2 if stop == 'deadline' else 0.03)
            assert len(fetched) == capacity
            assert analyzer.crawler.result_buffer_peak == capacity
            if stop == 'cancel':
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            else:
                release.set()
                results = await asyncio.wait_for(task, 5)
                if stop == 'complete':
                    assert len(results) == len({page['url'] for page in results}) == 31
                else:
                    assert 'max_crawl_time' in analyzer.crawler.limit_reasons
                    assert any(result.get('error') for result in results)
            assert analyzer.crawler._buffer_in_use == 0
            assert not analyzer.crawler._buffered_results
            assert all('soup' not in raw and 'html' not in raw for raw in analyzer.crawler.results)
        finally:
            release.set()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    asyncio.run(run())

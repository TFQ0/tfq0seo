"""Deadline outcomes depend on cancellation cause, never a second clock reading."""

import asyncio
import time
from types import SimpleNamespace

import pytest

import tfq0seo.core.crawler as crawler_module
from tfq0seo.core.crawler import Crawler


def crawler_config(**options):
    return {'respect_robots_txt': False, 'use_sitemap': False, 'max_retries': 0,
            'adaptive_delay': False, 'max_concurrent': 2, 'max_pages': 2,
            'max_crawl_time': 0.02, **options}


def fake_crawler_clock(monkeypatch):
    clock = [10.0]
    # Do not patch the standard-library time module used by asyncio's real timer.
    monkeypatch.setattr(crawler_module, 'time',
                        SimpleNamespace(monotonic=lambda: clock[0], time=time.time))
    return clock


def test_early_timeout_retains_every_inflight_url_and_awaits_cleanup(monkeypatch):
    clock = fake_crawler_clock(monkeypatch)

    async def run():
        crawler = Crawler(crawler_config())
        started, cleaned = set(), set()

        async def stalled(url):
            started.add(url)
            try:
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                cleaned.add(url)

        crawler.fetch_page = stalled
        urls = ['https://example.test/one', 'https://example.test/two']
        rows = await crawler.crawl_urls(urls)
        assert clock[0] == 10.0  # The crawler's sampled clock still precedes its deadline.
        assert sorted(row['url'] for row in rows) == urls
        assert all(row['error'] == 'Crawl time limit exceeded' for row in rows)
        assert all(row['status_code'] == 0 and row['outcome'] == 'failed' for row in rows)
        assert set(crawler.failed_urls) == set(urls)
        assert 'max_crawl_time' in crawler.limit_reasons
        assert started == cleaned == set(urls)
        assert crawler._deadline is None

    asyncio.run(run())


def test_external_cancellation_after_sampled_deadline_does_not_fabricate_timeouts(monkeypatch):
    clock = fake_crawler_clock(monkeypatch)

    async def run():
        crawler = Crawler(crawler_config(max_crawl_time=30))
        ready = asyncio.Event()
        started, cleaned = set(), set()

        async def stalled(url):
            started.add(url)
            if len(started) == 2:
                ready.set()
            try:
                await asyncio.Event().wait()
            finally:
                await asyncio.sleep(0)
                cleaned.add(url)

        crawler.fetch_page = stalled
        urls = ['https://example.test/one', 'https://example.test/two']
        task = asyncio.create_task(crawler.crawl_urls(urls))
        await asyncio.wait_for(ready.wait(), 1)
        clock[0] = 100.0  # Clock position alone cannot establish the cancellation cause.
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert crawler.results == []
        assert crawler.failed_urls == {}
        assert 'max_crawl_time' not in crawler.limit_reasons
        assert started == cleaned == set(urls)
        assert crawler._deadline is None

    asyncio.run(run())


def test_timeout_preserves_depth_parent_and_preexisting_results(monkeypatch):
    fake_crawler_clock(monkeypatch)

    async def run():
        crawler = Crawler(crawler_config(max_depth=3))
        previous = {'url': 'https://example.test/previous', 'status_code': 200, 'outcome': 'success'}
        crawler.results.append(previous)
        urls = ['https://example.test/child-one', 'https://example.test/child-two']
        parent = 'https://example.test/parent'
        for url in urls:
            crawler._enqueue(url, depth=2, parent_url=parent)

        async def stalled(url):
            await asyncio.Event().wait()

        crawler.fetch_page = stalled
        rows = await crawler._run_with_deadline(crawler._run_queue(2, follow_links=False), parent)
        assert rows[0] is previous
        assert sorted(row['url'] for row in rows[1:]) == urls
        assert all(row['depth'] == 2 and row['parent_url'] == parent for row in rows[1:])
        assert len(rows) == 3

    asyncio.run(run())

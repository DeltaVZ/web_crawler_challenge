import mockito
from challenge.crawler.crawler import Crawler
from unittest import IsolatedAsyncioTestCase
from pathlib import Path


class CrawlerTest(IsolatedAsyncioTestCase):

    def test_init(self):
        site = 'https://mysite.com'
        headers = {'User-Agent': 'test'}
        regex_search = True
        domain_filter = False
        max_runners = 500
        print_in_real_time = True
        max_retries = 7
        sleep_between_retries = 0
        max_depth = 1
        assume_parent_protocol = False
        sleep_after_request = 3.3
        concurrent_requests_limit = 5
        complete_crawler = Crawler(site, headers=headers, regex_search=regex_search, domain_filter=domain_filter,
                                   max_runners=max_runners, print_in_real_time=print_in_real_time,
                                   max_retries=max_retries, sleep_between_retries=sleep_between_retries,
                                   max_depth=max_depth, assume_parent_protocol=assume_parent_protocol,
                                   sleep_after_request=sleep_after_request,
                                   concurrent_requests_limit=concurrent_requests_limit)
        self.assertEqual(complete_crawler.url.string_url, site)
        self.assertEqual(complete_crawler.headers, headers)
        self.assertEqual(complete_crawler.domain_filter, domain_filter)
        self.assertEqual(complete_crawler.max_runners, max_runners)
        self.assertEqual(complete_crawler.print_in_real_time, print_in_real_time)
        self.assertEqual(complete_crawler.max_retries, max_retries)
        self.assertEqual(complete_crawler.sleep_between_retries, sleep_between_retries)
        self.assertEqual(complete_crawler.max_depth, max_depth)
        self.assertEqual(complete_crawler.assume_parent_protocol, assume_parent_protocol)
        self.assertEqual(complete_crawler.sleep_after_request, sleep_after_request)
        self.assertEqual(complete_crawler.concurrent_requests_limit, concurrent_requests_limit)

        crawler = Crawler(site, max_runners=-3, max_retries=-3, sleep_between_retries=-3, max_depth=-3,
                          concurrent_requests_limit=-3)
        self.assertEqual(crawler.max_runners, 1)
        self.assertEqual(crawler.max_retries, 0)
        self.assertEqual(crawler.sleep_between_retries, 0.3)
        self.assertEqual(crawler.max_depth, 0)
        self.assertEqual(crawler.concurrent_requests_limit, None)

    async def test_crawl(self):
        """
        Tests that crawling working as expected, including multiple edge cases. Mockito and multiple HTML example
        files are used to mock the responses resulting from HTTP requests
        """
        site = 'https://mysite.com'
        # Start with using Crawler with all default values
        crawler = Crawler(site, max_runners=10)
        spy(site)
        crawled_urls = await crawler.crawl()
        self.assertEqual(crawled_urls, get_first_expected_crawl_results())

        # Now use set the domain filter to false and verify that the results include URLs with a different domain than
        # the root site
        crawler = Crawler(site, max_runners=10, domain_filter=False)
        spy(site)
        crawled_urls = await crawler.crawl()
        self.assertEqual(crawled_urls, get_second_expected_crawl_results())

        # Now set the depth to 0 and verify that the result is as expected
        crawler = Crawler(site, max_runners=10, max_depth=0)
        spy(site)
        crawled_urls = await crawler.crawl()
        self.assertEqual(len(crawled_urls), 1)
        self.assertEqual(crawled_urls[site], get_first_expected_crawl_results()[site])

        # Now enable regex search and verify that urls outside hrefs are added to the result.
        # It also verifies that links to .jpg, .png and .pdf contents are not considered crawlable
        # but appear in the results
        crawler = Crawler(site, max_runners=10, regex_search=True)
        spy(site)
        crawled_urls = await crawler.crawl()
        self.assertEqual(crawled_urls, get_third_crawled_results())

        # Verify that if assume_parent_protocol is set to False, then http links will be seen as different
        # from https links with the same domain and path. It also verifies that http://mysite.com/rel_link is not found
        # and it has no values in the dict
        crawler = mockito.spy(
            Crawler(site, max_runners=10, assume_parent_protocol=False, max_retries=1, sleep_between_retries=0))
        spy(site)
        crawled_urls = await crawler.crawl()
        mockito.verify(Crawler, times=2)._get(mockito.eq('http://mysite.com/rel_link'))
        self.assertEqual(crawled_urls, get_fourth_crawled_results())


async def read_file(path) -> str:
    with open(path, 'r') as f:
        return f.read()


async def empty_file() -> str:
    return ''


def spy(site):
    base_path = (Path(__file__).parent / 'html_pages/').resolve()
    mockito.when(Crawler)._get(mockito.eq(site)).thenReturn(
        read_file(base_path / 'mysite.com-root.html'))
    mockito.when(Crawler)._get(mockito.eq(site + '/rel_link')).thenReturn(
        read_file(base_path / 'mysite.com-rel-link-depth1.html'))
    mockito.when(Crawler)._get(mockito.eq(site + '/simple-https-link')).thenReturn(
        read_file(base_path / 'mysite.com-simple-https-link-depth1.html'))
    mockito.when(Crawler)._get(mockito.eq(site + '/simple-https-link/another-one')).thenReturn(
        read_file(base_path / 'mysite.com-simple-https-link-another-one-depth2.html'))
    mockito.when(Crawler)._get(mockito.eq(site + '/content')).thenReturn(
        read_file(base_path / 'mysite.com-content-depth1.html'))
    mockito.when(Crawler)._get(mockito.eq('http://mysite.com')).thenReturn(
        read_file(base_path / 'mysite.com-root.html'))

    mockito.when(Crawler)._get(mockito.eq('http://mysite.com/rel_link')).thenRaise(Exception('test_exception'))
    mockito.when(Crawler)._get(mockito.eq('https://mysite.com/simple-https-link/rel_link')).thenReturn(empty_file())


def get_first_expected_crawl_results() -> dict:
    return {
        'https://mysite.com': ['https://mysite.com/simple-https-link', 'https://mysite.com/rel_link',
                               'https://mysite.com/rel_link', 'https://mysite.com/rel_link',
                               'https://mysite.com/simple-https-link', 'https://mysite.com/simple-https-link',
                               'https://mysite.com/rel_link'],
        'https://mysite.com/simple-https-link': ['https://mysite.com/simple-https-link/another-one',
                                                 'https://mysite.com/simple-https-link/another-one',
                                                 'https://mysite.com/rel_link',
                                                 'https://mysite.com/rel_link',
                                                 'https://mysite.com'],
        'https://mysite.com/rel_link': ['https://mysite.com/simple-https-link/another-one',
                                        'https://mysite.com/simple-https-link',
                                        'https://mysite.com/simple-https-link',
                                        'https://mysite.com'],
        'https://mysite.com/simple-https-link/another-one': ['https://mysite.com/simple-https-link',
                                                             'https://mysite.com/simple-https-link',
                                                             'https://mysite.com/rel_link', 'https://mysite.com'],
    }


def get_second_expected_crawl_results() -> dict:
    return {'https://mysite.com': ['https://mysite.com/simple-https-link', 'https://mysite.com/rel_link',
                                   'https://mysite.com/rel_link', 'https://mysite.com/rel_link',
                                   'https://anothersite.com', 'https://mysite.com/simple-https-link',
                                   'https://mysite.com/simple-https-link', 'https://mysite.com/rel_link'],
            'https://mysite.com/simple-https-link': ['https://mysite.com/simple-https-link/another-one',
                                                     'https://mysite.com/simple-https-link/another-one',
                                                     'https://mysite.com/rel_link',
                                                     'https://anothersite.com',
                                                     'https://mysite.com/rel_link', 'https://mysite.com'],
            'https://mysite.com/rel_link': ['https://mysite.com/simple-https-link/another-one',
                                            'https://anothersite.com', 'https://mysite.com/simple-https-link',
                                            'https://mysite.com/simple-https-link', 'https://mysite.com'],
            'https://mysite.com/simple-https-link/another-one': ['https://anothersite.com',
                                                                 'https://mysite.com/simple-https-link',
                                                                 'https://mysite.com/simple-https-link',
                                                                 'https://mysite.com/rel_link', 'https://mysite.com'],
            }


def get_third_crawled_results() -> dict:
    content_url = 'https://mysite.com/content'
    crawled_urls = get_first_expected_crawl_results()
    for crawled_url in set(crawled_urls.keys()):
        if crawled_urls[crawled_url]:
            crawled_urls[crawled_url].append(content_url)
    crawled_urls[content_url] = [content_url + '/pic1.jpg', content_url + '/pic2.png',
                                 content_url + '/document.pdf']
    return crawled_urls


def get_fourth_crawled_results() -> dict:
    http_url = 'http://mysite.com'
    crawled_urls = get_first_expected_crawl_results()
    crawled_urls['https://mysite.com'].append(http_url)
    crawled_urls[http_url] = ['https://mysite.com/simple-https-link', 'http://mysite.com/rel_link',
                              'http://mysite.com/rel_link', 'http://mysite.com/rel_link',
                              'https://mysite.com/simple-https-link',
                              'https://mysite.com/simple-https-link',
                              'https://mysite.com/rel_link', 'https://mysite.com']
    crawled_urls[http_url + '/rel_link'] = []
    return crawled_urls

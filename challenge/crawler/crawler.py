import asyncio
import logging
import re
import aiohttp
from collections import Counter
from bs4 import BeautifulSoup

from challenge.utils.results_printer import print_single_element
from challenge.utils.url_utils import Url, UrlSet

logger = logging.getLogger('crawler')


class Crawler:
    """
    Crawler class to be used to crawl through web pages.
    Usage: instantiate an object of this Class and run "crawl"
    """
    __slots__ = ['url', 'crawled_urls', 'headers', 'domain_filter', 'max_runners', 'print_in_real_time',
                 'max_retries', 'sleep_between_retries', 'max_depth', 'regex_search', 'assume_parent_protocol',
                 'sleep_after_request', 'concurrent_requests_limit', '_session', '_queue', '_limit']

    _default_headers = {
        'User-Agent': 'Mozilla/5.0',
    }

    def __init__(self, url: str, headers: dict = None, regex_search: bool = False, domain_filter: bool = True,
                 max_runners: int = 100, print_in_real_time: bool = False, max_retries: int = 5,
                 sleep_between_retries: float = 0.3, max_depth: int = None, assume_parent_protocol: bool = True,
                 sleep_after_request: float = 0, concurrent_requests_limit: int = None):
        """
        :param url: the root url for crawling
        :param headers: the headers to use for the HTTP requests. A default one
        will be used if None
        :param regex_search: if True, the urls found in a page will be found using regex
        matching on the whole html page. Otherwise, only links present in href attributes of a tags will be
        considered
        :param domain_filter: if True, only urls with the same domain of the root url will be added to
        the list of urls present in a page. If False, also urls with different domains will be considered. In any
        case, no urls with a different domain will be crawled into
        :param max_runners: the max numbers of runners to use for crawling. It must be a positive number, otherwise it is
        set to 1
        :param print_in_real_time: if True, it will print all urls found in a page in real time.
        :param max_retries: the maximum number of retries to execute when an HTTP request fails. It must be 0 or a
        positive number, otherwise it is set to 0
        :param sleep_between_retries: the float number of seconds to wait before retrying an HTTP request
        :param max_depth: the max depth allowed for crawling. It can be None or 0 or a positive number, otherwise it is set to 0
        :param sleep_after_request: number of seconds to sleep after each request. It must be 0 or a positive integer number,
        otherwise it is set to 0
        :param concurrent_requests_limit: the limit of concurrent HTTP requests that the crawler can perform. It's None by default
        """
        self.url = Url(url)
        self.crawled_urls = {}
        self.headers = headers if headers else Crawler._default_headers
        self.domain_filter = domain_filter
        self.max_runners = max_runners if max_runners > 0 else 1
        self.print_in_real_time = print_in_real_time
        self.max_retries = max_retries if max_retries >= 0 else 0
        self.sleep_between_retries = sleep_between_retries if sleep_between_retries >= 0 else 0.3
        if type(max_depth) is int and max_depth < 0:
            max_depth = 0
        self.max_depth = max_depth
        self.regex_search = regex_search
        self.assume_parent_protocol = assume_parent_protocol
        self.sleep_after_request = sleep_after_request if sleep_after_request >= 0 else 0
        self.concurrent_requests_limit = concurrent_requests_limit if concurrent_requests_limit and concurrent_requests_limit > 0 else None
        self._queue = None
        self._session = None
        self._limit = None

    async def crawl(self) -> dict:
        """
        It starts the crawling process
        :return: a dictionary containing the crawled urls as keys and a list of all visited urls as values
        """
        if self.concurrent_requests_limit:
            self._limit = asyncio.Semaphore(self.concurrent_requests_limit)
        async with aiohttp.ClientSession(headers=self.headers) as self._session:
            self._queue = asyncio.Queue()
            logger.info('Start crawling from root URL: {}'.format(self.url.get_basic_url()))
            self._queue.put_nowait((self.url, 0))
            consumers = [asyncio.create_task(self._queue_processor()) for _ in range(self.max_runners)]
            await self._queue.join()
            for consumer in consumers:
                consumer.cancel()
        return self.crawled_urls

    async def _queue_processor(self) -> None:
        """
        Gets elements in the queue and processes them
        :return: None
        """
        while True:
            url_in_queue, depth = await self._queue.get()
            basic_url_in_queue = url_in_queue.get_basic_url()
            if basic_url_in_queue not in self.crawled_urls.keys():
                self.crawled_urls[basic_url_in_queue] = []
                urls = [url for url in await self._get_urls(url_in_queue) if
                        url.get_basic_url() != basic_url_in_queue]
                basic_urls = [url.get_basic_url() for url in urls]
                self.crawled_urls[basic_url_in_queue] = basic_urls
                if self.print_in_real_time:
                    print_single_element(basic_url_in_queue, basic_urls)
                if self.max_depth is None or depth < self.max_depth:
                    self._add_urls_to_queue(UrlSet(urls), depth)
            self._queue.task_done()

    def _add_urls_to_queue(self, urls: UrlSet, depth: int) -> None:
        """
        Adds the given urls to the queue to be processed as long as some conditions are met, which are:
        the url has never been crawled in before, it has the same domain of the root URL defined when constructing the
        object and the result of method url.is_crawlable() is True
        :param urls: the urls to add to the queue
        :param depth: the depth at which those urls were found
        :return: None
        """
        for url in urls.values():
            basic_url = url.get_basic_url()
            if url.domain == self.url.domain and basic_url not in self.crawled_urls.keys() and url.is_crawlable():
                self._queue.put_nowait((url, depth + 1))

    async def _get(self, url: str) -> str:
        """
        Simply make an HTTP request to the given URL with a new session
        :param url: the url of the website to send an HTTP request to
        :return: the HTML page in the response as a single string
        """
        async with self._session.get(url) as r:
            return await r.text()

    async def _get_urls(self, url: Url, retries: int = 0) -> list:
        """
        Calls the __get(url) method to make an HTTP Request and then processes the resulting HTML page and
        returns a list of URLs found in the page. If the HTTP Request was not successful, it will call itself as many
        times as variable self.max_retries indicates
        :param url: the url of the website to send an HTTP request to
        :param retries: the number of retries that have been executed for the url
        :return: a list of URLs found in the page
        """
        try:
            if self._limit:
                async with self._limit:
                    text = await self._get(url.get_basic_url())
            else:
                text = await self._get(url.get_basic_url())
        except UnicodeDecodeError as unicode_decode_error:
            logger.error('Cannot decode text from url: {}'.format(unicode_decode_error))
            return []
        except Exception as e:
            if retries < self.max_retries:
                logger.warning(
                    'Exception triggered when requesting URL {}, will retry. Current retry: {} Exception is {}'.format(
                        url.get_basic_url(), str(retries),
                        e))
                retries += 1
                if self.sleep_between_retries > 0:
                    await asyncio.sleep(self.sleep_between_retries)
                return await self._get_urls(url, retries)
            else:
                logger.error(
                    'Maximum retries reached for url {} because of exception {}, hence the url will not be processed'.format(
                        url.get_basic_url(), e))
                return []
        urls = self._get_urls_from_text(text, url)
        if self.sleep_after_request > 0:
            await asyncio.sleep(self.sleep_after_request)
        return urls

    def _get_urls_from_text(self, html_text: str, parent_url: Url) -> list:
        """
        Gets the URls present in the given string that represents an HTML page. If self.regex_search is True, the urls found
        in a page will be found using regex matching on the whole html page. Otherwise, only links present in href
        attributes of "a" tags will be considered
        :param html_text: the HTML page to get URLs from
        :return: the list of URLs found in the page
        """

        soup = BeautifulSoup(html_text, 'html.parser')
        links = soup.find_all('a')
        urls = [Url(url, parent_url=parent_url, use_parent_protocol=self.assume_parent_protocol) for link in links if
                (url := link.get('href')) is not None]

        if self.regex_search:
            for match in re.finditer(self.url.default_regex, html_text):
                url_to_append = Url(match.group(0), parent_url=parent_url,
                                    use_parent_protocol=self.assume_parent_protocol)
                if url_to_append.get_basic_url() not in UrlSet(urls).keys():
                    urls.append(url_to_append)

        if self.domain_filter:
            urls = [url for url in urls if self.url.domain == url.domain]
        return urls

import asyncio
import os
from datetime import datetime

from challenge.crawler.crawler import Crawler
from challenge.utils.results_printer import print_crawling_results


async def main(root_url: str) -> None:
    crawler = Crawler(root_url, print_in_real_time=True, concurrent_requests_limit=7)
    crawled_urls = await crawler.crawl()
    if not crawler.print_in_real_time:
        print_crawling_results(crawled_urls)


if __name__ == '__main__':
    url = 'https://github.com/DeltaVZ/DevPortfolio'
    start_time = datetime.now()
    if os.name == 'nt':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main(url))
    else:
        asyncio.run(main(url))
    end_time = datetime.now()
    print('Time spent crawling: ' + str(end_time - start_time))

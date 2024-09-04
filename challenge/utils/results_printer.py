from collections import Counter
from typing import Union


def print_single_element(parent_url: str, urls: Union[list, set]) -> None:
    """
    Prints a single crawling result given a parent_url and a list or set of urls
    :param parent_url: the parent_url
    :param urls: the list or set of Urls
    :return: None
    """
    counter = dict(Counter(urls))
    urls_to_print = {url + ' (' + str(counter.get(url)) + ')' for url in urls}
    print("The urls present in " + parent_url + " are: " + ', '.join(urls_to_print))


def print_crawling_results(crawling_results: dict) -> None:
    """
    Prints the crawling results given a dict of crawling_results
    :param crawling_results: the crawling results
    :return: None
    """
    for url in crawling_results.keys():
        print_single_element(url, crawling_results[url])

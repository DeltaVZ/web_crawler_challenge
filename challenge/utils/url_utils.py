import re
from re import Pattern
from typing import Union
from urllib.parse import urlparse


def get_url_info(url: str) -> tuple:
    """
    Gets the protocol and the domain without www. from the url and returns a tuple of them
    :param url: the url to process
    :return: a tuple (protocol, hostname)
    """
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme
    netloc = parsed_url.netloc
    path = parsed_url.path if parsed_url.query == '' else parsed_url.path + '?' + parsed_url.query
    fragment = parsed_url.fragment
    www_subdomain = True if netloc.startswith('www.') else False
    return scheme, www_subdomain, netloc[4::] if netloc.startswith('www.') else netloc, path, fragment


def remove_consecutive_slashes(basic_url: str) -> str:
    """
    Removes duplicated slashes from a URL, which could occur in some cases
    :param basic_url: the url without the protocol, so without e.g. https:// or http://
    :return: the url without duplicated slashes
    """
    previous_url = basic_url
    formatted_url = previous_url.replace('//', '/')
    while formatted_url != previous_url:
        previous_url = formatted_url
        formatted_url = previous_url.replace('//', '/')
    return formatted_url


class Url:
    """
    Class to be used by the crawler to manipulate URLs
    """

    _default_regex = re.compile(("((http|https)://)(www.)?" +
                                 "[a-zA-Z0-9@:%._\\+~#?&//=]" +
                                 "{2,256}\\.[a-z]" +
                                 "{2,6}\\b([-a-zA-Z0-9@:%" +
                                 "._\\+~#?&//=]*)"))

    __slots__ = ['string_url', 'parent_protocol', 'parent_www', 'parent_domain', 'parent_path', 'protocol', 'www',
                 'domain', 'path',
                 'fragment', 'use_parent_protocol']

    def __init__(self, url: str, parent_url: 'Url' = None, use_parent_protocol: bool = True):
        """
        :param url: the url
        :param root_url: the root url. It's the URL from which the crawling process started
        :param use_parent_protocol: if True, the protocol from the parent will always be used if the parent domain is the same as
                                  the url domain
        """
        self._fill_parent_attributes(parent_url)
        self.string_url = url
        self.protocol, self.www, self.domain, self.path, self.fragment = get_url_info(url)
        self._refactor_attributes()
        self._refactor_root_attributes()
        if parent_url and use_parent_protocol:
            self.use_parent_protocol = parent_url.use_parent_protocol
        else:
            self.use_parent_protocol = use_parent_protocol

    def get_full_url(self) -> str:
        """
        Returns the full correctly formatted URL
        :return: the full URL
        """
        www = 'www.' if self.www else ''
        fragment = '/#' + self.fragment if self.fragment else ''
        return self._get_protocol() + '://' + www + self.domain + self.path + fragment

    def get_basic_url(self) -> str:
        """
        Returns a "basic" form of the url, with just the protocol, domain and path, if the protocol is http
        Otherwise, it will return exact representation of the string found for the url
        :return: a basic form of the url
        """
        protocol = self._get_protocol()
        if protocol.startswith('http'):
            return self._get_protocol() + '://' + self.domain + self.path
        else:
            return self.string_url

    def is_valid(self, regex: Union[str, Pattern] = None) -> bool:
        """
        Checks whether the given url is a syntactically valid url or not using a regex expression

        :param regex: the regular expression to use
        :return: True if the url is valid, False if not
        """
        if regex is None:
            regex = self._default_regex
        basic_url = self.get_basic_url()
        return basic_url.startswith('http') and '/../' not in basic_url and re.fullmatch(regex, basic_url) is not None

    def is_crawlable(self, regex: Union[str, Pattern] = None) -> bool:
        """
        Identifies whether the given url is "crawlable" by verifying that the url is valid based on the given or default
        regex and that the url does not represent a .png, .jpg or .pdf file
        :param regex: the regex expression to use to check whether the given url is valid
        :return: True if the url is considered "crawlable", False if not
        """
        if regex is None:
            regex = self._default_regex
        return self.is_valid(regex) and not self._is_content_url()

    @property
    def default_regex(self):
        return self._default_regex

    def _is_content_url(self) -> bool:
        """
        Checks whether the URL represents a png, pdf, jpg, jpeg, txt or xml content
        :return: True if the URL represents a png, pdf, jpg, jpeg, txt or xml content, False otherwise
        """
        basic_url = self.get_basic_url()
        return basic_url.endswith('.png') or basic_url.endswith('.pdf') or basic_url.endswith(
            '.jpg') or basic_url.endswith('.jpeg') or basic_url.endswith('.txt')

    def is_xml(self):
        """
        :return: True if the URL represents an XML, returns False otherwise
        """
        return self.get_basic_url().endswith('.xml')

    def _refactor_ending(self) -> None:
        """
        Refactors the path and/or fragment by deleting incorrect consecutive slashes and the ending slash, if there is one
        :return: None
        """

        def refactor(text: str) -> str:
            refactored_text = text
            if '//' in refactored_text:
                refactored_text = remove_consecutive_slashes(refactored_text)
            if refactored_text == '/':
                refactored_text = ''
            if refactored_text.endswith('/'):
                refactored_text = refactored_text[:-1]
            return refactored_text

        if self.path:
            self.path = refactor(self.path)
        if self.fragment:
            self.fragment = refactor(self.fragment)

    def _fill_parent_attributes(self, parent_url: 'Url') -> None:
        """
        Fills the parent attribute, given the parent URL
        :param parent_url: the parent URL
        :return: None
        """
        if parent_url is not None:
            self.parent_protocol = parent_url.protocol
            self.parent_www = parent_url.www
            self.parent_domain = parent_url.domain
            self.parent_path = parent_url.path
        else:
            self.parent_protocol, self.parent_www, self.parent_domain, self.parent_path = '', None, '', ''

    def _refactor_attributes(self) -> None:
        """
        Refactors the attributes if needed
        :return: None
        """
        if self.domain == '' or self.domain == self.parent_domain:
            if self.protocol == '':
                self.protocol = self.parent_protocol
            if self.domain == '':
                self.domain = self.parent_domain
            if not self.www and self.parent_www is not None:
                self.www = self.parent_www
            self._refactor_path()
        self._refactor_ending()

    def _refactor_path(self):
        if self.path.startswith('./'):
            self.path = self.parent_path + self.path[1::]
        elif self.path and not self.path.startswith('/'):
            self.path = self.parent_path + '/' + self.path
        if self.parent_path and (self.string_url.startswith('#') or self.string_url.startswith('./#')):
            self.path = self.parent_path

    def _refactor_root_attributes(self) -> None:
        """
        Refactors the attributes if needed
        :return: None
        """
        if self.parent_protocol == '':
            self.parent_protocol = self.protocol
        if self.parent_domain == '':
            self.parent_domain = self.domain
        if self.parent_www is None:
            self.parent_www = self.www

    def _get_protocol(self) -> str:
        """
        Gets the protocol to be used in a string representation for the url
        :return: the protocol
        """
        return self.parent_protocol if self.use_parent_protocol and self.domain == self.parent_domain and (
                self.protocol == '' or self.protocol.startswith('http')) else self.protocol


class UrlSet:
    """
    Custom 'Set'-like class to transform a list of Urls in a set of urls with the hash based only on the result
    of the 'get_basic_url()' method
    """
    __slots__ = '_items'

    def __init__(self, urls):
        self._items = {}
        for url in urls:
            self.add(url)

    def add(self, item: 'Url') -> None:
        item_hash = item.get_basic_url()
        if item_hash not in self._items:
            self._items[item_hash] = item

    def keys(self):
        return self._items.keys()

    def values(self):
        return self._items.values()

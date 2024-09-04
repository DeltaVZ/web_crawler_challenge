import unittest
import mockito
from re import Pattern
from challenge.utils import url_utils
from challenge.utils.url_utils import Url, UrlSet


class UrlUtilsTest(unittest.TestCase):
    valid_urls = {'https://mysite.com', 'http://www.mysite.com', 'http://mysite.com', 'https://www.mysite.com',
                  'https://mysite.com/test', 'http://www.mysite.com/test/test/test'}
    invalid_urls = {'mysite.com', 'www.mysite.com', 'h.ttps://invalid.com', '://invalid.com', 'mysite',
                    'mysite.com/', 'mysite.com/about//here', 'https://mysite.com/here/../there'}

    def test_attributes(self):
        """
        It tests that Url objects are initialized as expected and that the result of get_basic_url()
        and get_full_url() is as expected
        """
        parent_url = Url('https://mysite.com')
        self.assertEqual(parent_url.protocol, 'https')
        self.assertEqual(parent_url.parent_protocol, parent_url.protocol)
        self.assertEqual(parent_url.domain, 'mysite.com')
        self.assertEqual(parent_url.parent_domain, parent_url.domain)
        self.assertEqual(parent_url.www, False)
        self.assertEqual(parent_url.www, parent_url.parent_www)
        self.assertEqual(parent_url.path, '')
        self.assertEqual(parent_url.fragment, '')
        self.assertEqual(parent_url.get_basic_url(), parent_url.string_url)
        self.assertEqual(parent_url.get_full_url(), parent_url.string_url)

        url = Url('https://www.mysite.com')
        self.assertEqual(url.protocol, 'https')
        self.assertEqual(url.parent_protocol, url.protocol)
        self.assertEqual(url.domain, 'mysite.com')
        self.assertEqual(url.parent_domain, url.domain)
        self.assertEqual(url.www, True)
        self.assertEqual(url.www, url.parent_www)
        self.assertEqual(url.path, '')
        self.assertEqual(url.fragment, '')
        self.assertEqual(url.get_basic_url(), 'https://mysite.com')
        self.assertEqual(url.get_full_url(), 'https://www.mysite.com')

        url = Url('http://www.mysite.com/test/path//#here/', parent_url)
        self.assertEqual(url.protocol, 'http')
        self.assertEqual(url.parent_protocol, parent_url.protocol)
        self.assertEqual(url.domain, 'mysite.com')
        self.assertEqual(url.parent_domain, parent_url.domain)
        self.assertEqual(url.www, True)
        self.assertEqual(url.parent_www, parent_url.www)
        self.assertEqual(url.path, '/test/path')
        self.assertEqual(url.fragment, 'here')
        self.assertEqual(url.get_basic_url(), 'https://mysite.com/test/path')
        self.assertEqual(url.get_full_url(), 'https://www.mysite.com/test/path/#here')

        url = Url(url.string_url, parent_url=parent_url, use_parent_protocol=False)
        self.assertEqual(url.get_basic_url(), 'http://mysite.com/test/path')
        self.assertEqual(url.get_full_url(), 'http://www.mysite.com/test/path/#here')

        url = Url('#fragment', parent_url=Url('http://www.mysite.com/test'))
        self.assertEqual(url.get_basic_url(), 'http://mysite.com/test')
        self.assertEqual(url.get_full_url(), 'http://www.mysite.com/test/#fragment')

        url = Url('./test2', parent_url=Url('http://www.mysite.com/test'))
        self.assertEqual(url.get_basic_url(), 'http://mysite.com/test/test2')
        self.assertEqual(url.get_full_url(), 'http://www.mysite.com/test/test2')

        url = Url('/test2', parent_url=Url('http://www.mysite.com/test'))
        self.assertEqual(url.get_basic_url(), 'http://mysite.com/test2')
        self.assertEqual(url.get_full_url(), 'http://www.mysite.com/test2')

        url = Url('test2', parent_url=Url('http://www.mysite.com/test'))
        self.assertEqual(url.get_basic_url(), 'http://mysite.com/test/test2')
        self.assertEqual(url.get_full_url(), 'http://www.mysite.com/test/test2')

        url = Url('//mysite.com', parent_url=Url('http://www.mysite.com/test'))
        self.assertEqual(url.get_basic_url(), 'http://mysite.com')
        self.assertEqual(url.get_full_url(), 'http://www.mysite.com')

    def test_is_valid_url(self):
        """
        Tests that urls are correctly seen as valid or invalid
        """
        for valid_url in self.valid_urls:
            self.assertTrue(Url(valid_url).is_valid())

        for invalid_url in self.invalid_urls:
            self.assertFalse(Url(invalid_url).is_valid())

    def test_is_url_crawlable(self):
        """
        Tests that urls are considered crawlable when they represent a valid url and do not represent
        a pdf, png or jpg
        """
        ## Mock so that is_valid_url always returns true (as it is already tested in another test)
        # and we just verify that it is called the correct number of times
        mockito.expect(Url, times=len(self.valid_urls) + 3).is_valid(mockito.any(Pattern)).thenReturn(True)

        for valid_url in self.valid_urls:
            self.assertTrue(mockito.spy(Url(valid_url)).is_crawlable())

        self.assertFalse(mockito.spy(Url('https://mysite.com/content.jpg')).is_crawlable())
        self.assertFalse(mockito.spy(Url('https://mysite.com/content.pdf')).is_crawlable())
        self.assertFalse(mockito.spy(Url('https://mysite.com/content.png')).is_crawlable())

        mockito.unstub()

    def test_get_url_info(self):
        """
        Tests that the URL is correctly disassembled and read
        """
        for url in self.valid_urls:
            info = url_utils.get_url_info(url)
            self.assertEqual(info[2], 'mysite.com')
            if 'www.' in url:
                self.assertTrue(info[1])
            else:
                self.assertFalse(info[1])
            if url.startswith('https'):
                self.assertEqual(info[0], 'https')
            else:
                self.assertEqual(info[0], 'http')

        url = 'https://www.this.that.here/path/#fragment'
        self.assertEqual(url_utils.get_url_info(url), ('https', True, 'this.that.here', '/path/', 'fragment'))

    def test_remove_consecutive_slashes(self):
        """
        Tests that any string with multiple consecutive slashes is returned with only one slash when
        calling remove_consecutive_slashes
        """
        self.assertEqual(url_utils.remove_consecutive_slashes('////'), '/')
        self.assertEqual(url_utils.remove_consecutive_slashes('mysite.com/this//that'), 'mysite.com/this/that')
        self.assertEqual(url_utils.remove_consecutive_slashes('mysite.com///this/that'), 'mysite.com/this/that')

    def test_url_set(self):
        url_set = UrlSet([Url(url) for url in self.valid_urls])
        self.assertEqual(len(url_set.values()), 4)


if __name__ == '__main__':
    unittest.main()

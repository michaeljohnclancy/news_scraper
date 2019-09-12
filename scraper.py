from typing import List
import requests, os, hashlib
from urllib.parse import urlparse
from abc import abstractmethod, ABCMeta
from time import sleep
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

def _get_bbc_frontpage_links():
    resp = requests.get('https://www.bbc.co.uk')
    soup = BeautifulSoup(resp.content)
    article_elements = soup.findAll('a', {'class': 'top-story'})

    articles = []

    for article_element in article_elements:
        if 'bbcthree' in article_element.get('href'):
            articles.append(BBCThreeArticleParser(article_element.get('href')))
        elif 'sport' in article_element.get('href'):
            articles.append(BBCSportArticleParser(article_element.get('href')))
        else:
            articles.append(BBCArticleParser.parse(article_element.get('href')))

    return articles

class BaseArticleParser(metaclass=ABCMeta):

    @abstractmethod
    def get_title(self, soup: BeautifulSoup) -> str:
        return

    @abstractmethod
    def _get_body(self, soup: BeautifulSoup) -> str:
        return

    @classmethod
    def parse(self, href: str) -> str:
        soup = self.get_soup(href)
        return ''.join([self.get_title(soup)] + self.get_paragraphs(soup))

    @classmethod
    def get_soup(self, href: str) -> BeautifulSoup:
        content = BaseArticleParser.get_content(href)
        return BeautifulSoup(content)

    @classmethod
    def get_content(self, href):
        content = BaseArticleParser._check_cache_for_content(href)
        if content is None:
            ua = UserAgent()
            resp = None
            while resp == None or resp.status_code is not 200:
                headers = {'User-Agent': ua.random}
                resp = requests.get(href, headers = headers)
                sleep(5)
            BaseArticleParser._cache_content(href, resp.text)
            return resp.text

        else:
            return content

    @classmethod
    def _cache_content(self, href, content):
        cache_id = BaseArticleParser.get_cache_id(href)
        with open(f'.content_cache/{cache_id}.html', 'w+') as writer:
            writer.write(str(content))

    @classmethod
    def _check_cache_for_content(self, href):
        cache_id = BaseArticleParser.get_cache_id(href)
        cache_location = f'.content_cache/{cache_id}.html'
        if os.path.exists(cache_location) and os.path.getsize(os.path.join(os.getcwd(), cache_location)) > 0:
            with open(cache_location, 'r') as reader:
                return reader.read()
        else:
            return None

    @classmethod
    def _delete_content_from_cache(self, href):
        cache_id = BaseArticleParser.get_cache_id(href)
        os.remove(f'.content_cache/{cache_id}.html')

    @classmethod
    def get_cache_id(self, href):
        return hashlib.md5(href.encode('utf-8')).hexdigest()

class BBCArticleParser(BaseArticleParser):

    @classmethod
    def get_title(self, soup: BeautifulSoup) -> str:
        title_element = soup.find('h1', {'class': 'story-body__h1'})
        return title_element.text if title_element is not None else None

    @classmethod
    def get_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        story_element_div = soup.find('div', {'class': 'story-body__inner'})
        story_elements = story_element_div.findAll('p')
        return list(story_element.text for story_element in story_elements)

class BBCThreeArticleParser(BaseArticleParser):

    @classmethod
    def get_title(self, soup: BeautifulSoup) -> str:
        title_element = soup.find('h1', {'class': 'LongArticleParser-headline'})
        return title_element.text if title_element is not None else None

    @classmethod
    def get_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        story_element_div = soup.find('div', {'class': 'LongArticleParser-body'})
        story_elements = story_element_div.findAll('p')
        return list(story_element.text for story_element in story_elements)

class BBCSportArticleParser(BaseArticleParser):

    @classmethod
    def get_title(self, soup: BeautifulSoup) -> str:
        title_element = soup.find('h1', {'class': 'story-headline'})
        return title_element.text if title_element is not None else None

    @classmethod
    def get_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        story_element_div = soup.find('div', {'id': 'story-body'})
        story_elements = story_element_div.findAll('p')
        return list(story_element.text for story_element in story_elements)

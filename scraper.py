import requests, os
from urllib.parse import urlparse
from abc import abstractmethod, ABCMeta
from time import sleep
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

ua = UserAgent()

def _get_bbc_frontpage_links():
    resp = requests.get('https://www.bbc.co.uk')
    soup = BeautifulSoup(resp.content)
    article_elements = soup.findAll('a', {'class': 'top-story'})

    articles = []

    for article_element in article_elements:
        if 'bbcthree' in article_element.get('href'):
            articles.append(BBCThreeArticle(article_element.get('href')))
        elif 'sport' in article_element.get('href'):
            articles.append(BBCSportArticle(article_element.get('href')))
        else:
            articles.append(BBCArticle(article_element.get('href')))

    return articles


class Article(metaclass=ABCMeta):

    def __init__(self, href: str):
        self.href = href

        self.populate()

        self.title = self.get_title()
        self.body = self.get_body()

    @property
    def content(self):
        if self.soup == None:
            raise AttributeError('Have not downloaded the content of the article')
        return self.soup.content

    def populate(self, refresh_cache = False):
        parsed_href = urlparse(self.href)
        self.domain = parsed_href.netloc

        if refresh_cache:
            ArticleHelper.delete_content_from_cache(self.href)

        self.soup = ArticleHelper.soupify(href = self.href)

    @abstractmethod
    def get_title(self) -> str:
        return

    @abstractmethod
    def get_body(self) -> str:
        return

class BBCArticle(Article):
    def __init__(self, href: str):
        super().__init__(href)

    def get_title(self) -> str:
        title_element = self.soup.find('h1', {'class': 'story-body__h1'})
        return title_element.text if title_element is not None else None

    def get_body(self) -> str:
        story_element_div = self.soup.find('div', {'class': 'story-body__inner'})
        story_elements = story_element_div.findAll('p')
        return ''.join(list(story_element.text for story_element in story_elements))

class BBCThreeArticle(Article):
    def __init__(self, href: str):
        super().__init__(href)

    def get_title(self) -> str:
        title_element = self.soup.find('h1', {'class': 'LongArticle-headline'})
        return title_element.text if title_element is not None else None

    def get_body(self) -> str:
        story_element_div = self.soup.find('div', {'class': 'LongArticle-body'})
        story_elements = story_element_div.findAll('p')
        return ''.join(list(story_element.text for story_element in story_elements))

class BBCSportArticle(Article):
    def __init__(self, href: str):
        super().__init__(href)

    def get_title(self) -> str:
        title_element = self.soup.find('h1', {'class': 'story-headline'})
        return title_element.text if title_element is not None else None

    def get_body(self) -> str:
        story_element_div = self.soup.find('div', {'id': 'story-body'})
        story_elements = story_element_div.findAll('p')
        return ''.join(list(story_element.text for story_element in story_elements))

class ArticleHelper:

    @classmethod
    def soupify(self, content = None, href = None):
        if content is None and href:
            content = ArticleHelper.get_content(href)
        elif content is None and href is None:
            raise ValueError('Need to provide minimum the href')
        return BeautifulSoup(content)

    @classmethod
    def get_content(self, href):
        content = ArticleHelper._check_cache_for_content(href)

        if content is None:
            resp = None
            while resp == None or resp.status_code is not 200:
                headers = {'User-Agent': ua.random}
                resp = requests.get(href, headers = headers)
                sleep(5)
            ArticleHelper._cache_content(href, resp.text)
            return resp.text

        else:
            return content

    @classmethod
    def _cache_content(self, href, content):
        cache_id = ArticleHelper.get_cache_id(href)
        with open(f'.content_cache/{cache_id}.html', 'w+') as writer:
            writer.write(str(content))

    @classmethod
    def _check_cache_for_content(self, href):
        cache_id = ArticleHelper.get_cache_id(href)
        cache_location = f'.content_cache/{cache_id}.html'
        if os.path.exists(cache_location) and os.path.getsize(os.path.join(os.getcwd(), cache_location)) > 0:
            with open(cache_location, 'r') as reader:
                return reader.read()
        else:
            return None

    @classmethod
    def _delete_content_from_cache(self, href):
        cache_id = ArticleHelper.get_cache_id(href)
        os.remove(f'.content_cache/{cache_id}.html')

    @classmethod
    def get_cache_id(self, href):
        return f"{href.split('/')[-2]}-{href.split('/')[-1]}"

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
    blacklist = ['bitesize', 'programmes', 'archive', 'ideas', 'food', 'sounds', 'news/av']

    for article_element in article_elements:
        url = article_element.get('href')
        print(url)

        if any(x for x in blacklist if x in url):
            continue
        article = UniversalArticleParser.parse(url)
        if article != None:
            articles.append(article)

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
        content = self.get_content(href)
        return BeautifulSoup(content)

    @classmethod
    def get_content(self, href):
        content = self._check_cache_for_content(href)
        if content is None:
            ua = UserAgent()
            resp = None
            while resp == None or resp.status_code is not 200:
                headers = {'User-Agent': ua.random}
                resp = requests.get(href, headers = headers)
                sleep(5)
            self._cache_content(href, resp.text)
            return resp.text

        else:
            return content

    @classmethod
    def _cache_content(self, href, content):
        cache_id = self.get_cache_id(href)
        with open(f'.content_cache/{cache_id}.html', 'w+') as writer:
            writer.write(str(content))

    @classmethod
    def _check_cache_for_content(self, href):
        cache_id = self.get_cache_id(href)
        cache_location = f'.content_cache/{cache_id}.html'
        if os.path.exists(cache_location) and os.path.getsize(os.path.join(os.getcwd(), cache_location)) > 0:
            with open(cache_location, 'r') as reader:
                return reader.read()
        else:
            return None

    @classmethod
    def _delete_content_from_cache(self, href):
        cache_id = self.get_cache_id(href)
        os.remove(f'.content_cache/{cache_id}.html')

    @classmethod
    def get_cache_id(self, href):
        return hashlib.md5(href.encode('utf-8')).hexdigest()

class BBCArticleParser(BaseArticleParser):

    @classmethod
    def get_title(self, soup: BeautifulSoup) -> str:
        title_element = soup.find('h1', {'class': 'story-body__h1'})
        if title_element is None:
            title_element = soup.find('span', {'class': 'cta'})
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

class BBCNewsroundArticleParser(BaseArticleParser):

    @classmethod
    def get_title(self, soup: BeautifulSoup) -> str:
        title_element = soup.find('h1', {'class': 'newsround-story-header__title-text'})
        if title_element is None:
            title_element = soup.find('h1', {'class': 'newsround-legacy-story-header__title-text'})
        return title_element.text if title_element is not None else None

    @classmethod
    def get_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        story_element_div = soup.find('section', {'class': 'newsround-story-body'})
        story_elements = story_element_div.findAll(['p', 'span'])
        return list(story_element.text for story_element in story_elements)

class GuardianArticleParser(BaseArticleParser):

    @classmethod
    def get_title(self, soup: BeautifulSoup) -> str:
        title_element = soup.find('h1', {'class': 'content__headline'})
        return title_element.text

    @classmethod
    def get_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        story_element_div = soup.find('div', {'class': 'content__article-body'})
        story_elements = story_element_div.findAll('p')
        return list(story_element.text for story_element in story_elements)

class UniversalArticleParser(BaseArticleParser):

    parser_list = [
                ('www.bbc.co.uk/news/', BBCArticleParser),
                ('www.bbc.co.uk/bbcthree/', BBCThreeArticleParser),
                ('www.bbc.co.uk/sport/', BBCSportArticleParser),
                ('www.bbc.co.uk/newsround/', BBCNewsroundArticleParser),
                ('www.theguardian.com/politics', GuardianArticleParser)
            ]

    @classmethod
    def parse(self, href: str) -> str:

        parser_cost = -1

        for p in self.parser_list:
            cost = href.find(p[0])
            if cost > parser_cost:
                parser = p[1]
                parser_cost = cost

        if parser_cost >= 0:
            print("Chosen parser: " + parser.__name__)
            return parser.parse(href)
        else:
            print("ERROR: No suitable parser found")
            return None


class Source(metaclass=ABCMeta):

    @abstractmethod
    def get_hrefs(self):
        return

    @abstractmethod
    def get_blacklist(self):
        return

    @classmethod
    def fetch_new(self) -> str:
        articles = []
        hrefs = self.get_hrefs()
        for href in hrefs:
            if any(x for x in self.get_blacklist() if x in href):
                continue
            article = UniversalArticleParser.parse(href)
            if article is not None:
                articles.append(article)
        return articles

class BBC(Source):

    @classmethod
    def get_hrefs(self):
        home_page = requests.get('https://www.bbc.co.uk')
        soup = BeautifulSoup(home_page.content)
        article_elements = soup.findAll('a', {'class': 'top-story'})
        return [element.get('href') for element in article_elements]

    @classmethod
    def get_blacklist(self):
        return ['bitesize', 'programmes', 'archive', 'ideas', 'food', 'sounds', 'news/av']

from typing import List
import requests, os, hashlib, logging
from urllib.parse import urlparse
from abc import abstractmethod, ABCMeta
from time import sleep
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

class BaseArticleParser(metaclass=ABCMeta):

    @abstractmethod
    def get_title(cls, soup: BeautifulSoup) -> str:
        return

    @abstractmethod
    def _get_body(cls, soup: BeautifulSoup) -> str:
        return

    @classmethod
    def parse(cls, href: str) -> str:
        soup = cls.get_soup(href)
        return ' '.join([cls.get_title(soup)] + cls.get_paragraphs(soup))

    @classmethod
    def get_soup(cls, href):
        content = cls._check_cache_for_content(href)
        if content is None:
            ua = UserAgent()
            resp = None
            while resp == None or resp.status_code is not 200:
                headers = {'User-Agent': ua.random}
                resp = requests.get(href, headers = headers)
                logger.debug(f'Href: {href}; Response code: {resp.status_code}')
                sleep(5)

            cls._cache_content(href, resp.text)
            return BeautifulSoup(resp.text)

        else:
            return BeautifulSoup(content)

    @classmethod
    def _cache_content(cls, href, content):
        cache_loc = f'.content_cache/{cls.get_cache_id(href)}.html'
        logger.debug('Writing content to {cache_loc}')
        with open(cache_loc, 'w+') as writer:
            writer.write(str(content))

    @classmethod
    def _check_cache_for_content(cls, href):
        cache_loc = f'.content_cache/{cls.get_cache_id(href)}.html'
        if os.path.exists(cache_loc) and os.path.getsize(os.path.join(os.getcwd(), cache_loc)) > 0:
            logger.debug(f'Reading content from {cache_loc}')
            with open(cache_loc, 'r') as reader:
                return reader.read()
        else:
            return None

    @classmethod
    def _delete_content_from_cache(cls, href):
        cache_loc = f'.content_cache/{cls.get_cache_id(href)}.html'
        logger.debug(f'Deleting content at {cache_loc}')
        os.remove(cache_loc)

    @classmethod
    def get_cache_id(cls, href):
        return hashlib.md5(href.encode('utf-8')).hexdigest()

class BBCArticleParser(BaseArticleParser):

    @classmethod
    def get_title(cls, soup: BeautifulSoup) -> str:
        title_element = soup.find('h1', {'class': 'story-body__h1'})
        if title_element is None:
            title_element = soup.find('span', {'class': 'cta'})
        return title_element.text if title_element is not None else None

    @classmethod
    def get_paragraphs(cls, soup: BeautifulSoup) -> List[str]:
        story_element_div = soup.find('div', {'class': 'story-body__inner'})
        story_elements = story_element_div.findAll('p')
        return list(story_element.text for story_element in story_elements)

class BBCThreeArticleParser(BaseArticleParser):

    @classmethod
    def get_title(cls, soup: BeautifulSoup) -> str:
        title_element = soup.find('h1', {'class': 'LongArticleParser-headline'})
        return title_element.text if title_element is not None else None

    @classmethod
    def get_paragraphs(cls, soup: BeautifulSoup) -> List[str]:
        story_element_div = soup.find('div', {'class': 'LongArticleParser-body'})
        story_elements = story_element_div.findAll('p')
        return list(story_element.text for story_element in story_elements)

class BBCSportArticleParser(BaseArticleParser):

    @classmethod
    def get_title(cls, soup: BeautifulSoup) -> str:
        title_element = soup.find('h1', {'class': 'story-headline'})
        return title_element.text if title_element is not None else None

    @classmethod
    def get_paragraphs(cls, soup: BeautifulSoup) -> List[str]:
        story_element_div = soup.find('div', {'id': 'story-body'})
        story_elements = story_element_div.findAll('p')
        return list(story_element.text for story_element in story_elements)

class BBCNewsroundArticleParser(BaseArticleParser):

    @classmethod
    def get_title(cls, soup: BeautifulSoup) -> str:
        title_element = soup.find('h1', {'class': 'newsround-story-header__title-text'})
        if title_element is None:
            title_element = soup.find('h1', {'class': 'newsround-legacy-story-header__title-text'})
        return title_element.text if title_element is not None else None

    @classmethod
    def get_paragraphs(cls, soup: BeautifulSoup) -> List[str]:
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

class Source(metaclass=ABCMeta):

    parser_list = []

    @abstractmethod
    def get_hrefs(cls):
        return

    @classmethod

    @abstractmethod
    def get_blacklist(cls):
        return

    @classmethod
    def choose_parser(cls, href: str):
        try:
            parser = min(
                [(identifier, parser) for (identifier, parser) in cls.parser_list if identifier in href],
                key = lambda p : href.find(p[0])
            )[1]
            logger.info(f'Chosen parser for {href}: {parser.__name__}')
            return parser
        except ValueError as e:
            logger.error(f'ERROR: No suitable parser found for {href}', e)
            #Put article somewhere for inspection as to why find a parser failed.
            return None

    @classmethod
    def parse_article(cls, href: str):
        parser = cls.choose_parser(href)
        try:
            return parser.parse(href)
        except Exception as e:
            logger.error(f'ERROR: Parse failed for {href}', e)
            return None

    @classmethod
    def fetch_new(cls) -> str:
        logger.info('Fetching hrefs...')

        articles = []
        erroneous_hrefs = []
        hrefs = cls.get_hrefs()

        for href in hrefs:
            if any(x for x in cls.get_blacklist() if x in href):
                continue
            article = cls.parse_article(href)
            if article is not None:
                articles.append(article)
            else:
                erroneous_hrefs.append(href)

        cls._write_erroneous_article_hrefs(erroneous_hrefs)
        return articles

    @classmethod
    def _write_erroneous_article_hrefs(cls, hrefs: List[str]) -> None:
        with open(f'.failed_hrefs/{cls.__name__}', 'a') as writer:
            for href in hrefs:
                writer.write(href + '\n')

    @classmethod
    def _read_erroneous_article_hrefs(cls) -> List[str]:
        with open(f'.failed_hrefs/{cls.__name__}','a') as reader:
            return [str(href) for href in reader.read().split('\n')]


class BBC(Source):

    parser_list = [
                ('www.bbc.co.uk/news/', BBCArticleParser),
                ('www.bbc.co.uk/bbcthree/', BBCThreeArticleParser),
                ('www.bbc.co.uk/sport/', BBCSportArticleParser),
                ('www.bbc.co.uk/newsround/', BBCNewsroundArticleParser),
                ('www.theguardian.com/politics', GuardianArticleParser)
            ]

    @classmethod
    def get_hrefs(cls) -> List[str]:
        home_page = requests.get('https://www.bbc.co.uk')
        soup = BeautifulSoup(home_page.content)
        article_elements = soup.findAll('a', {'class': 'top-story'})
        return [element.get('href') for element in article_elements]

    @classmethod
    def get_blacklist(cls) -> List[str]:
        return ['bbcthree/clips', 'sport', 'bitesize', 'programmes', 'archive', 'ideas', 'food', 'sounds', 'news/av']

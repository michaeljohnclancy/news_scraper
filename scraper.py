import requests, os, hashlib, logging
from typing import List
from urllib.parse import urlparse
from abc import abstractmethod, ABCMeta
from time import sleep
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

class BaseArticleParser(metaclass=ABCMeta):

    subparsers: List[str] = []

    @abstractmethod
    def get_title(cls, soup: BeautifulSoup) -> str:
        return

    @abstractmethod
    def _get_body(cls, soup: BeautifulSoup) -> str:
        return

    @classmethod
    def parse(cls, href: str) -> str:
        soup = cls.get_soup(href)

        parser = cls.choose_subparser(href)

        try:
            return ' '.join([parser.get_title(soup)] + parser.get_paragraphs(soup))
        except Exception as e:
            try:
                return parser.try_subparsers(href)
            except ArticleParseException as e:
                logger.error(e)
            raise ArticleParseException

    @classmethod
    def try_subparsers(cls, href: str):
        logger.debug(f'Parse failed using default parser: {cls.__name__}; trying additional parsers (if any) now...')
        for (identifier, subparser) in cls.subparsers:
            try:
                return subparser.parse(href)
            except:
                logger.debug(f'Parse failed using {subparser.__name__}')
        raise ArticleParseException(f'No subparsers of {cls.__name__} could parse the article as {href}')

    @classmethod
    def choose_subparser(cls, href: str):
        try:
            parser = min(
                [(identifier, parser) for (identifier, parser) in cls.subparsers if identifier in href],
                key = lambda p : href.find(p[0])
            )[1]
            logger.debug(f'Chosen parser for {href}: {parser.__name__}')
            return parser
        except ValueError as e:
            return cls

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

class ArticleParseException(Exception):
    pass

class BBCArticleParser(BaseArticleParser):

    subparsers = [
                ('www.bbc.co.uk/bbcthree/', BBCThreeArticleParser),
                ('www.bbc.co.uk/sport/', BBCSportArticleParser),
                ('www.bbc.co.uk/newsround/', BBCNewsroundArticleParser)
            ]

    #blacklist = ['bbcthree/clips', 'sport', 'bitesize',
    #             'programmes', 'archive', 'ideas',
    #             'food', 'sounds', 'news/av']

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



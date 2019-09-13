import logging, requests
from bs4 import BeautifulSoup
from typing import List
from abc import abstractmethod, ABCMeta
from scraper import BaseArticleParser, BBCArticleParser, ArticleParseException

logger = logging.getLogger(__name__)

class Source(metaclass=ABCMeta):

    parser: BaseArticleParser

    @abstractmethod
    def get_hrefs(cls):
        return

    @classmethod
    def fetch_new(cls) -> str:
        logger.info('Fetching hrefs...')

        articles = []
        erroneous_hrefs = []

        hrefs = cls.get_hrefs()

        for href in hrefs:
            #if any(x for x in cls.get_blacklist() if x in href):
            #    continue
            try:
                article = cls.parser.parse(href)
                articles.append(article)
            except ArticleParseException as e:
                logger.error(f'Could not parse article {href} using available {cls.__name__} parsers.')
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

    parser = BBCArticleParser

    @classmethod
    def get_hrefs(cls) -> List[str]:
        home_page = requests.get('https://www.bbc.co.uk')
        soup = BeautifulSoup(home_page.content)
        article_elements = soup.findAll('a', {'class': 'top-story'})
        return [element.get('href') for element in article_elements]

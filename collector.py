from typing import Generator
from sources import *

class Collector():

    @classmethod
    def article_stream(cls) -> Generator[str, None, None]:
        sources = [ BBC, Guardian, NYTimes ]
        streams = [ s.article_stream() for s in sources ]

        while True:
            for i,stream in enumerate(streams):
                source = sources[i].__name__
                logger.info(f'Fetching article from {source}: ')
                try:
                    (href, article) = next(stream)
                    if not href:
                        continue
                    logger.info(f'Parsed article {href}: ')
                    yield article
                except StopIteration as e:
                    logger.error(f'Source is out of articles: {sources[i].__name__}')
                    streams.remove(s)
                    sources.remove(sources[i])
                    if not streams:
                        return None
                    break


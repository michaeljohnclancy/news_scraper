from typing import Generator
from sources import *

class Collector():

    @classmethod
    def article_stream(cls) -> Generator[str, None, None]:
        sources = [ BBC, Guardian, NYTimes ]

        streams = [ s.article_stream() for s in sources ]

        while True:
            for s in streams:
                try:
                    yield next(s)
                except ArticleParseException as e:
                    continue
                except SourceNotReadyException as e:
                    logger.error(f'Source is not ready: {s.__name__}')
                except OutOfArticlesException as e:
                    streams.remove(s)
                    if not streams:
                        return None
                    break


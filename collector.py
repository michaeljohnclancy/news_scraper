from typing import Generator
from sources import *

class Collector():

    @classmethod
    def article_stream(cls) -> Generator[str, None, None]:
        sources = [ BBC, Guardian, NYTimes ]

        streams = [ s.article_stream() for s in sources ]

        while True:
            for s in streams:
                article = next(s)
                if not article:
                    continue # Next article not ready, move to next source
                if article == None:
                    streams.remove(s)
                    if not streams:
                        return None
                    break
                yield article

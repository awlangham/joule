import numpy as np
import asyncio
from typing import List, Union
from abc import ABC, abstractmethod

from joule.models import Stream

# starting and ending timestamps
Interval = List[int, int]

Data = Union(Interval, np.array)

class StreamInfo:
    def __init__(self, start: int, end: int, rows: int):
        self.start = start
        self.end = end
        self.rows = rows


class DataStore(ABC):

    @abstractmethod
    def initialize(self, streams: List[Stream]):
        pass

    @abstractmethod
    async def insert(self, stream: Stream,
                     data: np.array, start: int, end: int):
        pass

    @abstractmethod
    def extract(self, stream: Stream, start: int, end: int,
                output: asyncio.Queue,
                max_rows: int = None, decimation_level=None):
        pass

    @abstractmethod
    def remove(self, stream: Stream, start: int, end: int):
        pass


    @abstractmethod
    def info(self, stream: Stream) -> StreamInfo:
        pass

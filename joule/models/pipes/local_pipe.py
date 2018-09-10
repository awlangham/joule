import numpy as np
import asyncio
import logging

from joule.models.pipes import Pipe
from joule.models.pipes.errors import PipeError, EmptyPipe

Loop = asyncio.AbstractEventLoop
log = logging.getLogger('joule')


class LocalPipe(Pipe):
    """
           Pipe for intra-module communication.

           Args:
               layout: ``datatype_width``, for example ``float32_3`` for a three element stream
                 must. See Stream.layout
           Keyword Args:
               loop: specify a an event loop, otherwise the default one is used
               name: useful for debugging with multiple pipes
               close_cb: callback coroutine executed when pipe closes
               debug: enable to log pipe usage events
    """

    def __init__(self, layout: str, loop: Loop = None, name: str = None,
                 close_cb = None, debug: bool = False):

        super().__init__(name=name, layout=layout)
        if loop is None:
            loop = asyncio.get_event_loop()
        # tunable constants
        self.TIMEOUT_INTERVAL = 0.5
        self.debug = debug
        self.interval_break = False
        self.closed = False
        self.read_buffer = np.empty((0,), dtype=self.dtype)
        self.close_cb = close_cb
        # initialize buffer and queue
        self.queue = asyncio.Queue(loop=loop)
        self.queued_rows = 0
        self.last_index = 0
        self.direction = Pipe.DIRECTION.TWOWAY
        # caching
        self._caching = False
        self._cache_index = 0
        self._cache = None

    async def read(self, flatten=False):
        """
        Read stream data. By default this method returns a structured
        array with ``timestamp`` and ``data`` fields. This method is a coroutine.

        Args:
            flatten: if ``True`` return an unstructured array (flat 2D matrix) with timestamps
              in the first column

        Returns: Numpy.ndarray

        """
        self.interval_break = False
        # if the queue is empty and we have old data, just return the old data
        if self.queue.empty() and len(self.read_buffer) > 0:
            return self._format_data(self.read_buffer, flatten)

        # otherwise wait for at least one block
        while self.queue.empty():
            # if the buffer is empty and the queue is empty and the pipe is closed
            if self.queue.empty() and len(self.read_buffer) == 0 and self.closed:
                raise EmptyPipe()
            await asyncio.sleep(self.TIMEOUT_INTERVAL)

        return self._read(flatten)

    def read_nowait(self, flatten=False):
        # if the queue is empty and we have old data, just return the old data
        if self.queue.empty() and len(self.read_buffer) > 0:
            return self._format_data(self.read_buffer, flatten)
        # if the buffer is empty and the queue is empty and the pipe is closed
        if self.queue.empty() and len(self.read_buffer) == 0 and self.closed:
            raise EmptyPipe()
        # do not wait for new data, return an empty array if nothing else is available
        return self._read(flatten)

    def _read(self, flatten=False):
        # now put all the queued data together in a single array with the previous data
        # this cannot be interrupted, relies on the total size of data written to the pipe
        start = 0
        end = len(self.read_buffer)
        buffer = np.empty((self.queued_rows + end,), self.dtype)
        if self.debug:
            print("[%s:read] initialized %d row buffer" % (self.name, len(buffer)))
            print("[%s:read] adding %d rows of unconsumed data" % (self.name, len(self.read_buffer)))
        buffer[start:end] = self.read_buffer
        start = end

        while not self.queue.empty():
            block = self.queue.get_nowait()
            if block is None:
                self.interval_break = True
                break
            end = start + len(block)
            buffer[start:end] = block
            start = end
            self.queued_rows -= len(block)

        self.read_buffer = buffer[:end]
        if self.debug:
            print("[%s:read] returning %d rows" % (self.name, len(self.read_buffer)))
        return self._format_data(self.read_buffer, flatten)

    @property
    def end_of_interval(self):
        return self.interval_break

    def consume(self, num_rows):
        """
        Flush data from the read buffer. The next call to :meth:`read` will
        return any unflushed data followed by new incoming data.

        Args:
            num_rows: number of rows to flush from the read buffer

        """
        if num_rows == 0:
            return
        if num_rows < 0:
            raise PipeError("consume called with negative offset: %d" % num_rows)
        if num_rows > len(self.read_buffer):
            raise PipeError("cannot consume %d rows: only %d available"
                            % (num_rows, len(self.read_buffer)))
        if self.debug:
            print("[%s:read] consumed %d rows" % (self.name, num_rows))
        self.read_buffer = self.read_buffer[num_rows:]

    async def write(self, data: np.ndarray):
        """
        Write timestamped data to the pipe. Timestamps must be monotonically increasing
         and should not overlap with existing stream data in the database. This method is a coroutine.
        Args:
            data: Numpy array, may be a structured array with ``timestamp`` and ``data`` fields
              or an unstructured array with timestamps in the first column.

        """
        if not self._validate_data(data):
            return
        # convert into a structured array
        sarray = self._apply_dtype(data)

        if self._caching:
            for row in sarray:
                self._cache[self._cache_index] = row
                self._cache_index += 1
                if self._cache_index >= len(self._cache):
                    await self.flush_cache()
        else:
            await self._write(sarray)

    async def _write(self, sarray):

        # send data to subscribers
        for pipe in self.subscribers:
            await pipe.write(sarray)

        self.queue.put_nowait(sarray)
        self.queued_rows += len(sarray)
        if self.debug:
            print("[%s:write] queueing block with [%d] rows" % (self.name, len(sarray)))

    def write_nowait(self, data):
        if not self._validate_data(data):
            return

        # convert into a structured array
        sarray = self._apply_dtype(data)
        # send data to subscribers
        for pipe in self.subscribers:
            if type(pipe) is LocalPipe:
                p: LocalPipe = pipe  # to appease type checker
                p.write_nowait(sarray)
            else:
                raise PipeError("cannot write_nowait to subscriber [%s]" % pipe.name)

        self.queue.put_nowait(sarray)
        self.queued_rows += len(sarray)
        if self.debug:
            print("[%s:write] queueing block with [%d] rows" % (self.name, len(sarray)))

    def enable_cache(self, lines: int):
        """
        Turn on caching for pipe writes. Data is only transmitted once the cache is full.
        This improves system performance especially if :meth:`write` is called
        rapidly with short arrays. Once enabled, caching cannot be disabled.

        Args:
            lines: cache size

        """
        self._caching = True
        self._cache = np.empty(lines, self.dtype)
        self._cache_index = 0

    async def flush_cache(self):
        """
        Force a pipe flush even if the cache is not full. Raises an error if caching is not
        enabled.

        """
        if self._cache_index > 0:
            await self._write(self._cache[:self._cache_index])
            self._cache_index = 0
            self._cache = np.empty(len(self._cache), self.dtype)

    async def close_interval(self):
        """
        Signal a break in the data stream. This should be used to indicate missing data.
        Data returned from :meth:`read` will be chunked by interval boundaries.

        """
        if self.debug:
            print("[%s:write] closing interval" % self.name)
        if self._caching:
            await self.flush_cache()
        await self.queue.put(None)

    def close_interval_nowait(self):
        if self.debug:
            print("[%s:write] closing interval" % self.name)
        self.queue.put_nowait(None)

    async def close(self):
        """
        Close the pipe. This also closes any subscribers. If ``close_cb`` is defined
        it will be executed before the subscribers are closed.

        """
        self.closed = True
        if self.close_cb is not None:
            await self.close_cb()
        # close any subscribers
        for pipe in self.subscribers:
            await pipe.close()

    def close_nowait(self):
        self.closed = True
        if len(self.subscribers) > 0:
            raise PipeError("cannot close_nowait subscribers, use async")
        if self.close_cb is not None:
            raise PipeError("close_cb cannot be executed, use async")

from aiohttp import web
import os
import sys
import multiprocessing
import numpy as np
from typing import Dict, Optional
from aiohttp.test_utils import unused_port
import time
import signal

from tests import helpers
from joule.models import Stream, StreamInfo, pipes

# from https://github.com/aio-libs/aiohttp/blob/master/examples/fake_server.py


class MockDbEntry:
    def __init__(self, stream: Stream, info: StreamInfo, data: Optional[np.ndarray] = None):
        self.stream = stream
        self.info = info
        self.data = data

    def add_data(self, chunk):
        if self.data is None:
            self.data = chunk
        else:
            self.data = np.hstack((self.data, chunk))


class FakeJoule:

    def __init__(self):
        self.loop = None
        self.runner = None
        self.app = web.Application()
        self.app.router.add_routes(
            [web.get('/streams.json', self.stub_get),
             web.get('/stream.json', self.stream_info),
             web.post('/data', self.data_write),
             web.get('/data', self.data_read),
             web.get('/modules.json', self.stub_get),
             web.get('/module.json', self.stub_get)])
        self.stub_stream_info = False
        self.response = ""
        self.http_code = 200
        self.streams: Dict[str, MockDbEntry] = {}
        self.msgs = None

    def start(self, port, msgs: multiprocessing.Queue):
        sys.stdout = open(os.devnull, 'w')
        self.msgs = msgs
        web.run_app(self.app, host='127.0.0.1', port=port)

    def add_stream(self, path, stream: Stream, info: StreamInfo, data: Optional[np.ndarray]):
        self.streams[path] = MockDbEntry(stream, info, data)

    async def stub_get(self, request: web.Request):
        return web.Response(text=self.response, status=self.http_code)

    async def stream_info(self, request: web.Request):
        if self.stub_stream_info:
            return web.Response(text=self.response, status=self.http_code)

        mock_entry = self.streams[request.query['path']]
        return web.json_response({'stream': mock_entry.stream.to_json(),
                                  'data_info': mock_entry.info.to_json()})

    async def data_read(self, request: web.Request):
        mock_entry = self.streams[request.query['path']]
        resp = web.StreamResponse(status=200,
                                  headers={'joule-layout': mock_entry.stream.layout,
                                           'joule-decimated': str(False)})
        resp.enable_chunked_encoding()
        await resp.prepare(request)
        await resp.write(mock_entry.data.tostring())
        return resp

    async def data_write(self, request: web.Request):
        if 'id' in request.query:
            stream_id = int(request.query['id'])
            mock_entry = [x for x in self.streams.values() if x.stream.id == stream_id][0]
        else:
            mock_entry = self.streams[request.query['path']]
        pipe = pipes.InputPipe(name="inbound", stream=mock_entry.stream, reader=request.content)
        while True:
            try:
                chunk = await pipe.read()
                pipe.consume(len(chunk))
                mock_entry.add_data(chunk)
            except pipes.EmptyPipe:
                break
        self.msgs.put(mock_entry)
        return web.Response(text="ok")


class FakeJouleTestCase(helpers.AsyncTestCase):
    def start_server(self, server):
        port = unused_port()
        self.msgs = multiprocessing.Queue()
        self.server_proc = multiprocessing.Process(target=server.start, args=(port, self.msgs))
        self.server_proc.start()
        time.sleep(0.01)
        return "http://localhost:%d" % port

    def stop_server(self):
        if self.server_proc is None:
            return
        # aiohttp doesn't always quit with SIGTERM
        os.kill(self.server_proc.pid, signal.SIGKILL)
        # join any zombies
        multiprocessing.active_children()
        self.server_proc.join()
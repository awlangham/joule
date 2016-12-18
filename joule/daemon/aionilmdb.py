"""
Asyncio Client for NilmDB
"""
import aiohttp
import json
import joule.utils.time
import requests


class AioNilmdb:

    def __init__(self, server):
        self.server = server
        self.session = aiohttp.ClientSession()

    def close(self):
        self.session.close()

    async def stream_insert(self, path, data, start, end):

        url = "{server}/stream/insert".format(server=self.server)
        params = {"start": "%d" % start,
                  "end": "%d" % end,
                  "path": path,
                  "binary": '1'}

        async with self.session.put(url, params=params,
                                    data=data.tostring()) as resp:
            if(resp.status != 200):
                raise AioNilmdbError(await resp.text())

    async def stream_list(self, path, layout=None, extended=False):
        url = "{server}/stream/list".format(server=self.server)
        params = {"path":   path}
        async with self.session.get(url, params=params) as resp:
            body = await resp.text()
            if(resp.status != 200):
                raise AioNilmdbError(body)
            return json.loads(body)

    async def stream_create(self, path, layout):
        url = "{server}/stream/create".format(server=self.server)
        data = {"path":   path,
                "layout": layout}
        async with self.session.post(url, data=data) as resp:
            if(resp.status != 200):
                raise AioNilmdbError(await resp.text())
        return True

    def stream_create_nowait(self, path, layout):
        url = "{server}/stream/create".format(server=self.server)
        data = {"path":   path,
                "layout": layout}
        r = requests.post(url, data=data)
        if(r.status_code != requests.codes.ok):
            raise AioNilmdbError(r.text)

    def stream_info_nowait(self, path):
        url = "{server}/stream/list".format(server=self.server)
        params = {"path":   path}
        r = requests.get(url, params=params)
        if(r.status_code != requests.codes.ok):
            raise AioNilmdbError(r.text)
        streams = json.loads(r.text)
        if (len(streams) == 0):
            return None
        else:
            return StreamInfo(self.server, streams[0])


class StreamInfo(object):

    def __init__(self, url, info):
        self.url = url
        self.info = info
        try:
            self.path = info[0]
            self.layout = info[1]
            self.layout_type = self.layout.split('_')[0]
            self.layout_count = int(self.layout.split('_')[1])
            self.total_count = self.layout_count + 1
            self.timestamp_min = info[2]
            self.timestamp_max = info[3]
            self.rows = info[4]
            self.seconds = joule.utils.time.timestamp_to_seconds(info[5])
        except IndexError as TypeError:
            pass

    def string(self, interhost):
        """Return stream info as a string.  If interhost is true,
        include the host URL."""
        if interhost:
            return "[%s] " % (self.url) + str(self)
        return str(self)

    def __str__(self):
        """Return stream info as a string."""
        return "%s (%s), %.2fM rows, %.2f hours" % (
            self.path, self.layout, self.rows / 1e6,
            self.seconds / 3600.0)


class AioNilmdbError(Exception):
    pass

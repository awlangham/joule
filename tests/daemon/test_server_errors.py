
import json
import asyncio
import unittest


from joule.daemon import socket_server
from joule.utils import network

ADDR = '127.0.0.1'
PORT = '1234'


class TestSeverErrors(unittest.TestCase):

    """
    Logs error if client closes connection early
    """
    def test_handles_closed_sockets(self):

        async def client():
            r, w = await asyncio.open_connection(ADDR, PORT, loop=loop)
            msg = {'not waiting for response': None}
            await network.send_json(w, msg)
            w.close()

        async def run():
            s = await socket_server.build_server(ADDR, PORT, None, None)
            await client()
            s.close()
            return s

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        with self.assertLogs(level='WARN'):
            s = loop.run_until_complete(run())
            
            loop.run_until_complete(s.wait_closed())
            loop.close()

    def test_handles_corrupt_json(self):
        async def client():
            r, w = await asyncio.open_connection(ADDR, PORT, loop=loop)
            msg = {'not waiting for response': None}
            await network.send_json(w, msg)
            w.close()

        async def run():
            s = await socket_server.build_server(ADDR, PORT, None, None)
            await client()
            s.close()
            return s

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        with self.assertLogs(level='WARN'):
            s = loop.run_until_complete(run())
            
            loop.run_until_complete(s.wait_closed())
            loop.close()
        
        

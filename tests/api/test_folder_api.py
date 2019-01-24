from tests.api import mock_session
import random
import asynctest

from joule.api.node import Node
from joule import errors

from joule.api.stream import Stream
from joule.api.folder import Folder
from joule.utilities import build_stream


class TestFolderApi(asynctest.TestCase):

    async def setUp(self):
        # no URL or event loop
        self.node = Node('mock_url', None)
        self.session = mock_session.MockSession()
        self.node.session = self.session

    async def test_folder_move(self):
        # can move by ID
        await self.node.folder_move(1, 2)
        self.assertEqual(self.session.method, 'PUT')
        self.assertEqual(self.session.path, "/folder/move.json")
        self.assertEqual(self.session.data,
                         {'src_id': 1, 'dest_id': 2})
        # can move by path
        await self.node.folder_move('/a/path', '/b/path')
        self.assertEqual(self.session.method, 'PUT')
        self.assertEqual(self.session.path, "/folder/move.json")
        self.assertEqual(self.session.data,
                         {'src_path': '/a/path', 'dest_path': '/b/path'})

        # can move by Folder
        src = Folder()
        src.id = 1
        dest = Folder()
        dest.id = 2
        await self.node.folder_move(src,dest)
        self.assertEqual(self.session.path, "/folder/move.json")
        self.assertEqual(self.session.data,
                         {'src_id': 1, 'dest_id': 2})

    async def test_folder_move_errors(self):
        self.session.method = None
        with self.assertRaises(errors.ApiError):
            await self.node.folder_move(Stream(), '/b/path')
        self.assertIsNone(self.session.method)

        with self.assertRaises(errors.ApiError):
            await self.node.folder_move('/a/path', Stream())
        self.assertIsNone(self.session.method)

    async def test_folder_delete(self):
        # can delete by ID
        await self.node.folder_delete(1, recursive=False)
        self.assertEqual(self.session.method, 'DELETE')
        self.assertEqual(self.session.path, "/folder.json")
        self.assertEqual(self.session.data, {'id': 1, 'recursive': 0})
        # can delete by path
        await self.node.folder_delete('/a/path', recursive=True)
        self.assertEqual(self.session.method, 'DELETE')
        self.assertEqual(self.session.path, "/folder.json")
        self.assertEqual(self.session.data, {'path': '/a/path', 'recursive': 1})

        # can delete by Folder
        src = Folder()
        src.id = 1
        await self.node.folder_delete(src,recursive=False)
        self.assertEqual(self.session.method, 'DELETE')
        self.assertEqual(self.session.path, "/folder.json")
        self.assertEqual(self.session.data, {'id': 1, 'recursive': 0})

    async def test_folder_delete_errors(self):
        self.session.method = None
        with self.assertRaises(errors.ApiError):
            await self.node.folder_delete(Stream(), recursive=False)
        self.assertIsNone(self.session.method)

    async def test_folder_get(self):
        target = build_folder(3)
        self.session.response = target.to_json()
        folder = await self.node.folder_get(1)
        self.assertEqual(folder.to_json(), target.to_json())
        self.assertEqual(self.session.method, 'GET')
        self.assertEqual(self.session.path, "/folder.json")
        self.assertEqual(self.session.data, {'id': 1})
        # can get by path
        await self.node.folder_get('/a/path')
        self.assertEqual(self.session.method, 'GET')
        self.assertEqual(self.session.path, "/folder.json")
        self.assertEqual(self.session.data, {'path': '/a/path'})

        # can get by Folder
        src = Folder()
        src.id = 1
        await self.node.folder_get(src)
        self.assertEqual(self.session.path, "/folder.json")
        self.assertEqual(self.session.data, {'id': 1})

    async def test_folder_get_errors(self):
        self.session.method = None
        with self.assertRaises(errors.ApiError):
            await self.node.folder_get(Stream())
        self.assertIsNone(self.session.method)

    async def test_local_folder_has_no_id(self):
        folder = Folder()
        with self.assertRaises(errors.ApiError):
            folder.id


def build_folder(depth) -> Folder:
    # can get by ID
    target = Folder()
    target.id = idgen()
    target.name = 'f'
    target.description = ''
    for n in range(random.randint(2, 4)):
        s = build_stream('s%d' % n, 'float32[x,y,z]')
        s.id = idgen()
        target.streams.append(s)
    if depth > 0:
        for n in range(random.randint(2, 3)):
            target.children.append(build_folder(depth-1))
    return target


id_seq = 0


def idgen():
    global id_seq
    id_seq += 1
    return id_seq

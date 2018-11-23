import asynctest
import testing.postgresql
import numpy as np
import asyncpg
import datetime

import time
import asyncio
import pdb

from joule.models import Stream, Element, pipes
from joule.models.data_store.timescale import TimescaleStore
from joule.errors import DataError
from tests import helpers
from joule.models.data_store import psql_helpers
from tests.models.pipes.reader import QueueReader
import psycopg2

class TestTimescaleInserter(asynctest.TestCase):
    use_default_loop = False
    forbid_get_event_loop = True

    async def setUp(self):
        self.postgresql = testing.postgresql.Postgresql(base_dir="psql_data")
        self.db_url = self.postgresql.url()
        #self.db_url = "postgresql://jdonnal@127.0.0.1:5432/jdonnal"
        conn: asyncpg.Connection = await asyncpg.connect(self.db_url)
        await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE ")
        await conn.execute("DROP SCHEMA IF EXISTS joule CASCADE")
        await conn.execute("CREATE SCHEMA joule")
        await conn.execute("GRANT ALL ON SCHEMA joule TO public")
        await conn.close()

        self.store = TimescaleStore(self.db_url, 0, 60, self.loop)
        # make a sample stream with data
        self.test_stream = Stream(id=100, name="stream1", datatype=Stream.DATATYPE.FLOAT32,
                                  keep_us=Stream.KEEP_ALL, decimate=True,
                                  elements=[Element(name="e%d" % x) for x in range(3)])
        pipe = pipes.LocalPipe(self.test_stream.layout)
        self.test_data = helpers.create_data(layout=self.test_stream.layout, length=1000)
        task = self.store.spawn_inserter(self.test_stream, pipe, self.loop)
        await pipe.write(self.test_data)
        await pipe.close()
        runner = await task
        await runner

        await self.store.initialize([])

    async def tearDown(self):
        self.postgresql.stop()
        self.store.close()

    async def test_basic_insert_extract(self):
        stream_id = 1
        self.store.extract_block_size = 500
        for datatype in [Stream.DATATYPE.FLOAT64, Stream.DATATYPE.FLOAT32, Stream.DATATYPE.INT64,
                         Stream.DATATYPE.INT32, Stream.DATATYPE.INT16]:
            for n_elements in range(1,5):
                test_stream = Stream(id=stream_id, name="stream1", datatype=datatype, keep_us=Stream.KEEP_ALL,
                                     elements=[Element(name="e%d" % x) for x in range(n_elements)])
                stream_id += 1
                test_stream.decimate = True
                source = QueueReader()
                pipe = pipes.InputPipe(stream=test_stream, reader=source)
                nrows = 955
                data = helpers.create_data(layout=test_stream.layout, length=nrows)
                task = self.store.spawn_inserter(test_stream, pipe, self.loop)
                for chunk in helpers.to_chunks(data, 300):
                    await source.put(chunk.tostring())
                runner = await task
                await runner

                # extract raw data
                extracted_data = []

                async def callback(rx_data, layout, factor):
                    self.assertEqual(layout, test_stream.layout)
                    self.assertEqual(factor, 1)
                    extracted_data.append(rx_data)

                await self.store.extract(test_stream, start=None, end=None, callback=callback)
                extracted_data = np.hstack(extracted_data)
                np.testing.assert_array_equal(extracted_data, data)

                level = 64
                data_mean = np.mean(extracted_data['data'][:level], axis=0)
                data_max = np.max(extracted_data['data'][:level], axis=0)
                data_min = np.min(extracted_data['data'][:level], axis=0)

                # extract decimated data
                async def d_callback(rx_data, layout, factor):
                    self.assertEqual(layout, test_stream.decimated_layout)
                    self.assertEqual(factor, level)
                    extracted_data.append(rx_data)

                extracted_data = []
                await self.store.extract(test_stream, decimation_level=level,
                                         start=None, end=None, callback=d_callback)
                extracted_data = np.hstack(extracted_data)
                expected = np.hstack((data_mean, data_min, data_max))
                np.testing.assert_array_almost_equal(expected, extracted_data['data'][0])

    async def test_extract_data_with_intervals(self):
        test_stream = Stream(id=1, name="stream1", datatype=Stream.DATATYPE.FLOAT32, keep_us=Stream.KEEP_ALL,
                             decimate=True, elements=[Element(name="e%d" % x) for x in range(3)])
        pipe = pipes.LocalPipe(test_stream.layout)
        nrows = 955
        data = helpers.create_data(layout=test_stream.layout, length=nrows)
        task = self.store.spawn_inserter(test_stream, pipe, self.loop)
        for chunk in helpers.to_chunks(data, 300):
            await pipe.write(chunk)
            await pipe.close_interval()
        await pipe.close()
        runner = await task
        await runner

        # extract data
        extracted_data = []

        async def callback(rx_data, layout, factor):
            self.assertEqual(layout, test_stream.layout)
            self.assertEqual(factor, 1)
            extracted_data.append(rx_data)

        await self.store.extract(test_stream, start=None, end=None, callback=callback)
        extracted_data = np.hstack(extracted_data)
        # check for interval boundaries
        np.testing.assert_array_equal(extracted_data[300], pipes.interval_token(test_stream.layout))
        np.testing.assert_array_equal(extracted_data[601], pipes.interval_token(test_stream.layout))
        np.testing.assert_array_equal(extracted_data[902], pipes.interval_token(test_stream.layout))

    async def test_extract_decimated_data(self):

        extracted_data = []

        async def callback(rx_data, layout, factor):
            self.assertEqual(layout, self.test_stream.decimated_layout)
            self.assertEqual(factor, 4)
            extracted_data.append(rx_data)

        await self.store.extract(self.test_stream, max_rows=16,
                                 start=self.test_data['timestamp'][66],
                                 end=self.test_data['timestamp'][64+4*16],
                                 callback=callback)
        extracted_data = np.hstack(extracted_data)
        self.assertLessEqual(len(extracted_data), 16)
        self.assertGreater(len(extracted_data), 4)

    async def test_nondecimating_inserter(self):
        #TODO
        pass

    async def test_remove(self):

        #  XXXXXXX------XXXXXXX
        #        ^|     ^
        # remove a chunk of data from the middle
        await self.store.remove(self.test_stream,
                                self.test_data['timestamp'][300],
                                self.test_data['timestamp'][400])
        # XXXXXXX------===XXXX
        #       ^|        ^
        # remove another chunk
        await self.store.remove(self.test_stream,
                                self.test_data['timestamp'][350],
                                self.test_data['timestamp'][500])

        # XXX___----===XXX
        #   ^|         ^
        await self.store.remove(self.test_stream,
                                self.test_data['timestamp'][250],
                                self.test_data['timestamp'][300])

        # extract the data, should have an interval gap between 249 and 500
        # and a *single* interval boundary at 250

        extracted_data = []

        async def callback(rx_data, layout, decimated):
            extracted_data.append(rx_data)

        await self.store.extract(self.test_stream, start=None, end =None,
                                 callback=callback)
        extracted_data = np.hstack(extracted_data)

        # beginning is unchanged
        np.testing.assert_array_equal(extracted_data[:249], self.test_data[:249])
        # interval boundary marking missing data
        np.testing.assert_array_equal(extracted_data[250],
                                      pipes.interval_token(self.test_stream.layout))
        # end is unchanged (closing interval boundary ignored)
        np.testing.assert_array_equal(extracted_data[251:], self.test_data[500:])

        # two intervals of data
        intervals = await self.store.intervals(self.test_stream, start=None, end=None)
        ts = self.test_data['timestamp']
        expected = [[ts[0], ts[249]],
                    [ts[500], ts[-1]]]
        self.assertEqual(intervals, expected)

    async def test_intervals(self):

        ts = self.test_data['timestamp']

        async def _insert_boundary(_conn, _ts: int):
            dt = datetime.datetime.fromtimestamp(_ts / 1e6, tz=datetime.timezone.utc)
            query = "INSERT INTO joule.stream100_intervals (time) VALUES ('%s')" % dt
            await _conn.execute(query)

        conn: asyncpg.Connection = await asyncpg.connect(self.db_url)

        # XXXX|XXXXX|XXXXX
        await _insert_boundary(conn, ts[99]+1)
        await _insert_boundary(conn, ts[199]+1)
        expected = [[ts[0], ts[99]],
                    [ts[100], ts[199]],
                    [ts[200], ts[-1]]]
        intervals = await self.store.intervals(self.test_stream, None, None)
        self.assertEqual(expected, intervals)

        # insert an extra boundary that does not create a new interval
        # XXXX||XXXXX|XXXXX
        await _insert_boundary(conn, ts[99]+10)

        intervals = await self.store.intervals(self.test_stream, None, None)
        self.assertEqual(expected, intervals)

        # insert boundaries at the beginning and end of the data,
        # this should also not create any new intervals
        # |XXXX||XXXXX|XXXXX|

        await _insert_boundary(conn, ts[0]-1)
        await _insert_boundary(conn, ts[-1]+1)
        intervals = await self.store.intervals(self.test_stream, None, None)
        self.assertEqual(expected, intervals)

        # insert an actual boundary, this should create a new interval
        # |XXXX||XXXXX|XXX|X|
        await _insert_boundary(conn, ts[780]+1)
        intervals = await self.store.intervals(self.test_stream, None, None)
        expected = [[ts[0], ts[99]],
                    [ts[100], ts[199]],
                    [ts[200], ts[780]],
                    [ts[781], ts[-1]]]
        self.assertEqual(expected, intervals)
        await conn.close()

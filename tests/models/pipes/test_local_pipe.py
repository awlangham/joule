from tests import helpers
import numpy as np
import asyncio

from joule.models.pipes import LocalPipe, PipeError


class TestLocalPipe(helpers.AsyncTestCase):

    def test_pipes_numpy_arrays(self):
        """writes to pipe sends data to reader and any subscribers"""
        LAYOUT = "int8_2"
        LENGTH = 1003
        loop = asyncio.get_event_loop()
        my_pipe = LocalPipe(LAYOUT, loop)
        # test timeouts, since the writer is slow
        my_pipe.TIMEOUT_INTERVAL = 0.05
        subscriber_pipe = LocalPipe(LAYOUT, loop)
        my_pipe.subscribe(subscriber_pipe)
        test_data = helpers.create_data(LAYOUT, length=LENGTH)

        #    print(test_data['data'][:,1])

        async def writer():
            for block in helpers.to_chunks(test_data, 270):
                await asyncio.sleep(0.1)
                await my_pipe.write(block)

        async def reader():
            blk_size = 357
            data_cursor = 0  # index into test_data
            while data_cursor != len(test_data):
                # consume all data in pipe
                data = await my_pipe.read()
                rows_used = min(len(data), blk_size)
                used_data = data[:rows_used]
                # print(used_data['data'][:,1])
                my_pipe.consume(rows_used)
                start_pos = data_cursor
                end_pos = data_cursor + len(used_data)
                np.testing.assert_array_equal(used_data,
                                              test_data[start_pos:end_pos])
                data_cursor += len(used_data)

        async def subscriber():
            blk_size = 493
            data_cursor = 0  # index into test_data
            while data_cursor != len(test_data):
                # consume all data in pipe
                data = await subscriber_pipe.read()
                rows_used = min(len(data), blk_size)
                used_data = data[:rows_used]
                # print(used_data['data'][:,1])
                subscriber_pipe.consume(rows_used)
                start_pos = data_cursor
                end_pos = data_cursor + len(used_data)
                np.testing.assert_array_equal(used_data,
                                              test_data[start_pos:end_pos])
                data_cursor += len(used_data)

        loop = asyncio.get_event_loop()
        tasks = [asyncio.ensure_future(writer()),
                 asyncio.ensure_future(reader()),
                 asyncio.ensure_future(subscriber())]

        loop.run_until_complete(asyncio.gather(*tasks))

    def test_read_data_must_be_consumed(self):
        """writes to pipe sends data to reader and any subscribers"""
        LAYOUT = "float32_2"
        LENGTH = 500
        UNCONSUMED_ROWS = 4
        loop = asyncio.get_event_loop()
        my_pipe = LocalPipe(LAYOUT, loop)
        test_data = helpers.create_data(LAYOUT, length=LENGTH)
        #    print(test_data['data'][:,1])
        my_pipe.write_nowait(test_data)

        async def reader():
            data = await my_pipe.read()
            my_pipe.consume(0)
            # should get the same data back
            repeat = await my_pipe.read()
            np.testing.assert_array_equal(data, repeat)
            my_pipe.consume(len(data) - UNCONSUMED_ROWS)
            next_data = await my_pipe.read()
            np.testing.assert_array_equal(data[-UNCONSUMED_ROWS:],
                                          next_data[:UNCONSUMED_ROWS + 1])

        loop = asyncio.get_event_loop()
        loop.run_until_complete(reader())

    def test_nowait_read_writes(self):
        LAYOUT = "int8_2"
        LENGTH = 500
        loop = asyncio.get_event_loop()
        my_pipe = LocalPipe(LAYOUT, loop)
        my_subscriber = LocalPipe(LAYOUT, loop)
        my_pipe.subscribe(my_subscriber)
        test_data = helpers.create_data(LAYOUT, length=LENGTH)
        my_pipe.write_nowait(test_data)
        result = my_pipe.read_nowait()
        # read data should match written data
        np.testing.assert_array_almost_equal(test_data['data'], result['data'])
        np.testing.assert_array_almost_equal(
            test_data['timestamp'], result['timestamp'])
        # subscriber should have a copy too
        result = my_subscriber.read_nowait()
        np.testing.assert_array_almost_equal(test_data['data'], result['data'])
        np.testing.assert_array_almost_equal(
            test_data['timestamp'], result['timestamp'])

    def test_nowait_read_empties_queue(self):
        LAYOUT = "int8_2"
        LENGTH = 50
        loop = asyncio.get_event_loop()
        my_pipe = LocalPipe(LAYOUT, loop)
        test_data = helpers.create_data(LAYOUT, length=LENGTH)

        async def writer():
            for row in test_data:
                await my_pipe.write(np.array([row]))

        loop = asyncio.get_event_loop()
        loop.run_until_complete(writer())

        result = my_pipe.read_nowait()

        np.testing.assert_array_almost_equal(test_data['data'], result['data'])
        np.testing.assert_array_almost_equal(
            test_data['timestamp'], result['timestamp'])

    def test_handles_flat_and_structured_arrays(self):
        """converts flat arrays to structured arrays and returns
           either flat or structured arrays depending on [flatten] parameter"""
        LAYOUT = "float64_1"
        LENGTH = 1000
        my_pipe = LocalPipe(LAYOUT, loop=asyncio.get_event_loop())
        test_data = helpers.create_data(LAYOUT, length=LENGTH)
        flat_data = np.c_[test_data['timestamp'][:, None], test_data['data']]

        async def reader():
            sdata = await my_pipe.read()
            fdata = await my_pipe.read(flatten=True)
            np.testing.assert_array_almost_equal(
                sdata['timestamp'], test_data['timestamp'])
            np.testing.assert_array_almost_equal(
                sdata['data'], test_data['data'])
            np.testing.assert_array_almost_equal(fdata, flat_data)
            np.testing.assert_array_almost_equal(fdata, flat_data)

        loop = asyncio.get_event_loop()
        tasks = [asyncio.ensure_future(my_pipe.write(flat_data)),
                 asyncio.ensure_future(reader())]
        loop.run_until_complete(asyncio.gather(*tasks))

    def test_breaks_writes_into_queue_blocks(self):
        LAYOUT = "int32_3"
        LENGTH = 1000
        MAX_BLOCK_SIZE = 20
        my_pipe = LocalPipe(LAYOUT, loop=asyncio.get_event_loop())
        my_pipe.MAX_BLOCK_SIZE = MAX_BLOCK_SIZE
        test_data = helpers.create_data(LAYOUT, length=LENGTH)

        loop = asyncio.get_event_loop()
        tasks = [asyncio.ensure_future(my_pipe.write(test_data))]

        loop.run_until_complete(asyncio.gather(*tasks))
        self.assertEqual(my_pipe.queue.qsize(), LENGTH / MAX_BLOCK_SIZE)

    def test_max_buffer_length(self):
        LAYOUT = "int32_3"
        LENGTH = 1000
        BUFFER_SIZE = 60
        my_pipe = LocalPipe(LAYOUT, loop=asyncio.get_event_loop(),
                            buffer_size=BUFFER_SIZE)
        test_data = helpers.create_data(LAYOUT, length=LENGTH)

        async def reader():
            for i in range(5):
                # read 5 times and do not consume so buffer is full
                data = await my_pipe.read()
                self.assertLessEqual(len(data), BUFFER_SIZE)

        loop = asyncio.get_event_loop()
        tasks = [asyncio.ensure_future(my_pipe.write(test_data)),
                 asyncio.ensure_future(reader())]

        loop.run_until_complete(asyncio.gather(*tasks))

        # buffer max is also maintained for nowait reads
        my_pipe = LocalPipe(LAYOUT, loop=asyncio.get_event_loop(),
                            buffer_size=BUFFER_SIZE)
        my_pipe.write_nowait(test_data)
        result = my_pipe.read_nowait()
        self.assertLessEqual(len(result),BUFFER_SIZE)

    def test_raises_consume_errors(self):
        LAYOUT = "int32_3"
        LENGTH = 1000
        my_pipe = LocalPipe(LAYOUT, loop=asyncio.get_event_loop())
        test_data = helpers.create_data(LAYOUT, length=LENGTH)
        my_pipe.write_nowait(test_data)
        read_data = my_pipe.read_nowait()
        # can't consume more than was read
        with self.assertRaises(PipeError) as e:
            my_pipe.consume(len(read_data) + 1)
        self.assertTrue('consume' in str(e.exception))
        # can't consume less than zero
        with self.assertRaises(PipeError) as e:
            my_pipe.consume(-1)
        self.assertTrue('negative' in str(e.exception))

    def test_handles_interval_breaks(self):
        LAYOUT = "int32_3"
        LENGTH = 1000
        my_pipe = LocalPipe(LAYOUT, loop=asyncio.get_event_loop())
        test_data1 = helpers.create_data(LAYOUT, length=LENGTH)
        test_data2 = helpers.create_data(LAYOUT, length=LENGTH)
        my_pipe.write_nowait(test_data1)
        my_pipe.close_interval_nowait()
        my_pipe.write_nowait(test_data2)

        async def reader():
            # read the first interval
            read_data = await my_pipe.read()
            self.assertTrue(my_pipe.end_of_interval)
            my_pipe.consume(len(read_data) - 20)
            np.testing.assert_array_equal(test_data1, read_data)

            # read the second interval
            read_data = await my_pipe.read()
            self.assertFalse(my_pipe.end_of_interval)
            self.assertEqual(len(read_data), len(test_data2) + 20)
            my_pipe.consume(len(read_data))
            np.testing.assert_array_equal(test_data2, read_data[20:])

        loop = asyncio.get_event_loop()
        loop.run_until_complete(reader())
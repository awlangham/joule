from joule.utils.localnumpypipe import LocalNumpyPipe
import asynctest
import asyncio
import numpy as np
import argparse
from joule.client.readers.random import RandomReader


class TestRandomReader(asynctest.TestCase):

    def test_generates_random_values(self):
        WIDTH = 2
        RATE = 100
        my_reader = RandomReader(output_rate=100)
        pipe = LocalNumpyPipe("output", layout="float32_%d" % WIDTH)
        args = argparse.Namespace(width=WIDTH, rate=RATE, pipes="unset")
        # run reader in an event loop
        loop = asyncio.get_event_loop()
        loop.call_later(0.1, my_reader.stop)
        loop.run_until_complete(my_reader.run(args, pipe))
        loop.close()
        # check the results
        result = pipe.read_nowait()
        diffs = np.diff(result['timestamp'])
        self.assertEqual(np.mean(diffs), 1/RATE*1e6)
        self.assertEqual(np.shape(result['data'])[1], WIDTH)

        

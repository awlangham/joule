from joule.utils.time import now as time_now

from joule.client.reader import ReaderModule
import asyncio
import numpy as np


class RandomReader(ReaderModule):
    "Generate a random stream of data"

    def __init__(self, output_rate=4):
        super(RandomReader, self).__init__("Random Reader")
        self.stop_requested = False
        self.output_rate = output_rate  # Hz, how often to push data
        
    def description(self):
        return "generate a random stream of data"

    def help(self):
        return """
        This is a module that generates random numbers.
        Specify width and the rate:
        Example:
            $> joule reader random 3 10
            1234 45 82 -33
            1234 45 82 -33
            1234 45 82 -33
            1234 45 82 -33
            1234 45 82 -33
        """
    
    def custom_args(self, parser):
        parser.add_argument("width", type=int,
                            help="number of elements in output")
        parser.add_argument("rate", type=float,
                            help="rate in Hz")

    async def run(self, parsed_args, output):
        # produce output four times per second
        # figure out how much output will be in each block
        rate = parsed_args.rate
        width = parsed_args.width
        data_ts = time_now()
        data_ts_inc = 1/rate*1e6
        wait_time = 1/self.output_rate
        BLOCK_SIZE = rate/self.output_rate
        fraction_remaining = 0
        i = 0
        while(not self.stop_requested):
            float_block_size = BLOCK_SIZE+fraction_remaining
            int_block_size = int(np.floor(float_block_size))
            fraction_remaining = float_block_size - int_block_size
            data = np.random.rand(int_block_size, width)
            top_ts = data_ts + int_block_size*data_ts_inc
            ts = np.array(np.linspace(data_ts, top_ts,
                                      int_block_size, endpoint=False),
                          dtype=np.uint64)
            data_ts = top_ts
            await output.write(np.hstack((ts[:, None], data)))
            await asyncio.sleep(wait_time)
            i += 1

    def stop(self):
        print("here!!!")
        self.stop_requested = True

if __name__ == "__main__":
    r = RandomReader()
    r.start()
    
from typing import List
import asyncio

from joule.models import Worker, Stream, Subscription
from joule.models.errors import SubscriptionError

Tasks = List[asyncio.Task]
Loop = asyncio.AbstractEventLoop


class Supervisor:

    def __init__(self, workers: List[Worker]):
        self.workers = workers
        self.task: asyncio.Task = None

    def start(self, loop: Loop):
        # returns a co-routine
        tasks: Tasks = []
        for worker in self.workers:
            tasks.append(loop.create_task(worker.run(loop)))
        self.task = asyncio.gather(*tasks, loop=loop)

    async def stop(self, loop: Loop):
        for worker in self.workers:
            await worker.stop(loop)
        await self.task

    def subscribe(self, stream: Stream, loop: Loop) -> Subscription:
        # find a worker producing this stream
        for worker in self.workers:
            try:
                return worker.subscribe(stream, loop)
            except SubscriptionError:
                pass
        else:
            raise SubscriptionError("[%s] has no producer" % stream.name)

    def publish(self, stream: Stream, loop: Loop):
        pass
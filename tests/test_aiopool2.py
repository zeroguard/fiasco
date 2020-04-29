#!/usr/bin/env python3

"""
Input: 1000 items
In/Out system (don't populate the queue if items are waiting to be consumed
etc)

Iterate over each input item
Create task.
"""

import asyncio

from functools import partial

class TaskResult:
    def __init__(self):
        self.result = None
        self.exception = None


class TaskPool:
    def __init__(self, size, loop=None):
        """."""
        self._tasks = set()
        self.loop = loop if loop else asyncio.get_running_loop()

        self._size = size
        self._task_sem = asyncio.Semaphore(size)
        self._tasks = set()
        self._results = []

    async def _create_task(self, awaitable):
        """."""
        await self._task_sem.acquire()
        task = self.loop.create_task(awaitable)

        task.add_done_callback(
            partial(self._handle_task_done, task))

        self._tasks.add(task)
        return task

    def _handle_task_done(self, task, future):
        """."""
        self._task_sem.release()
        self._tasks.remove(task)

        # create empty result
        tr = TaskResult()

        # the task should be done
        assert task.done()

        # did we get an exception?
        exc = task.exception()
        if exc:
            tr.exc = exc
        else:
            tr.result = task.result()

        # put result on the stack

    async def map(self, coroutine, iterable, return_exceptions=False):
        tpm = TaskPoolMap(pool=self, size=self._size, 
            coroutine=coroutine, iterable=iterable,
            return_exceptions=return_exceptions)
        
        async with tpm:
            await asyncio.sleep(100)


class TaskPoolMap:
    """."""

    def __init__(self, pool, size, iterable, coroutine, return_exceptions):
        """."""
        self._out_queue = asyncio.Queue(size)

        self._pool = pool
        self._iterable = iterable
        self._coroutine = coroutine
        self._return_exceptions = return_exceptions
        self._process_iterable_task = None
        self._lock = asyncio.Lock()

    @property
    def loop(self):
        return self._pool.loop

    def __aiter__(self):
        """."""

    async def __aenter__(self, *args, **kwargs):
        """."""
        await self.start()
        return self

    async def __aexit__(self, *args, **kwargs):
        """."""
        await self.stop()

    async def start(self):
        """."""
        await self._lock.acquire()
        self._process_iterable_task = self.loop.create_task(
            self._process_iterable())

    async def stop(self):
        """."""
        self._lock.release()
        if not self._process_iterable_task.done():
            self._process_iterable_task.cancel()
    
    async def _handle_task_done(self, future):
        print(asyncio.Task.current_task())

    async def _process_iterable(self):
        """."""
        # TODO: asyncio/non-async
        for i in self._iterable:
            awaitable = self._coroutine(i)
            t = await self._pool._create_task(awaitable)
            t.add_done_callback(self._handle_task_done)


async def wait_and_echo(x):
    import random
    i = random.random()
    await asyncio.sleep(i)
    print(x, i)


async def main():
    items = range(10)
    tp = TaskPool(32)
    await tp.map(wait_and_echo, items)

asyncio.run(main())

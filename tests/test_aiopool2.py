#!/usr/bin/env python3

"""
Input: 1000 items
In/Out system (don't populate the queue if items are waiting to be consumed
etc)

Iterate over each input item
Create task.
"""

import time
import random
import asyncio

from functools import partial

NoneType = type(None)


class TaskPoolMapResult:
    """."""

    def __init__(self, args, result, exc, start_ts, end_ts, index):
        """."""
        self.args = args
        self._result = result

        assert isinstance(exc, (Exception, NoneType))
        self._exc = exc

        assert isinstance(start_ts, float)
        self.start_ts = start_ts

        assert isinstance(end_ts, float)
        self.end_ts = end_ts

        assert isinstance(index, int)
        self.index = index

    @property
    def exec_time(self):
        """."""
        return (self.end_ts - self.start_ts)

    def __repr__(self):
        return "<{}: index={}, exec_time={:.3f}s>".format(
            self.__class__.__name__, self.index, self.exec_time)

    def result(self):
        """Raise exception or returns result."""
        # should we re-raise as an exception?
        if self._exc is not None:
            raise self._exc
        return self._result

    def exception(self):
        """Returns exception."""
        return self._exc


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

    def map(self, coroutine, iterable, return_exceptions=False):
        """."""
        return TaskPoolMap(pool=self, size=self._size, 
            coroutine=coroutine, iterable=iterable,
            return_exceptions=return_exceptions)


# TODO: not even sure if we need this lol
class TaskPoolMapStats:

    def __init__(self):
        self._counters = []
        self._is_enabled = False

    @property
    def is_enabled(self):
        return self._is_enabled

    def enable(self):
        self._is_enabled = True

    def disable(self):
        self._is_enabled = False

    def add_task_timing(self, ts, secs):
        self._counters += [(ts, secs)]
    
    @property
    def tasks_per_sec(self):
        pass


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
        self._tasks = set()
        self._has_tasks = asyncio.Event()
        self._stats = TaskPoolMapStats()
        self._counters = []

    @property
    def stats(self):
        return self._stats

    @property
    def loop(self):
        return self._pool.loop

    async def __aiter__(self):
        """."""
        # continue until tasks have been processed
        while True:
            # did we finish populating tasks?
            if self._process_iterable_task.done():
                # did we encounter an error during population?
                exc = self._process_iterable_task.exception()
                if exc:
                    print('failed to populate tasks')
                    raise exc

                # do we have any tasks needing to be processing?
                if not self._tasks:
                    print('nothing left to do')
                    return

            # do we have any tasks?
            if not self._tasks:
                # unset flag to prevent cpu spin
                self._has_tasks.clear()

                # wait until we have some tasks
                # XXX: is this in the right place?
                await self._has_tasks.wait()

            # do we have any completed tasks?
            completed, pending = await asyncio.wait(self._tasks,
                loop=self.loop, timeout=0.5, return_when=asyncio.ALL_COMPLETED)

            # process each completed task
            for task in completed:
                # remove task from working set
                self._tasks.remove(task)

                # handle result
                try:
                    # fetch result
                    tpmr = (await task)
                    assert isinstance(tpmr, TaskPoolMapResult)
                except Exception as exc:
                    raise

                # do we need to re-raise exception?
                if not self._return_exceptions:
                    exc = tpmr.exception()
                    if exc:
                        raise exc

                yield tpmr

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
        if not self._lock.locked():
            return

        self._lock.release()

        if not self._process_iterable_task.done():
            self._process_iterable_task.cancel()
    
    async def _process_item(self, i):
        """."""

        t = asyncio.Task.current_task()

        tr_result = None
        tr_exc = None
        tr_start_ts = time.time()

        try:
            tr_result = await self._coroutine(i)
        except Exception as exc:
            tr_exc = exc

        tr_end_ts = time.time()

        # should we increment stats counters?
        if self.stats.is_enabled:
            tr_delta = (tr_end_ts - tr_start_ts)
            self.stats.add_task_timing(tr_end_ts, tr_delta)

        return TaskPoolMapResult(
            args=i,
            result=tr_result,
            exc=tr_exc,
            start_ts=tr_start_ts,
            end_ts=tr_end_ts,
            index=t._index)

    async def _process_iterable(self):
        """."""
        # TODO: asyncio/non-async
        # TODO: handle errors in this iterable processor
        idx = -1
        for i in self._iterable:
            idx += 1
            awaitable = self._process_item(i)

            # create new task
            task = await self._pool._create_task(awaitable)
            task._index = idx

            # add task to working set
            self._tasks.add(task)

            # flag that we are now processing tasks
            self._has_tasks.set()


async def wait_and_echo(x):
    i = random.random()
    await asyncio.sleep(i)
    #print('inside', x, i)
    return i


async def main():
    items = range(10_000_000)
    tp = TaskPool(32)

    async with tp.map(wait_and_echo, items) as results:
        results.stats.enable()
        async for result in results:
            print(result)

asyncio.run(main())

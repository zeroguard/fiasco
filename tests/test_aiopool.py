#!/usr/bin/env python3

import time
import random
import asyncio
import inspect

from collections.abc import Iterable



class TaskResult:
    """."""
    
    def __init__(self, index, args, result, start_ts, end_ts):
        """."""
        self.index = index
        self.args = args
        self.result = result
        self.start_ts = start_ts
        self.end_ts = end_ts

    def __repr__(self):
        return '<{}: index={}>'.format(self.__class__.__name__, self.index)

    def exception(self):
        """."""
        if isinstance(self.result, Exception):
            raise self.result


# TODO: abstract into a class??
class TaskPoolMap:
    """."""

    def __init__(self, *, pool, coroutine, iterable, return_exceptions, starmap):
        """."""
        self._lock = asyncio.Lock()
        self._tasks = set()
        self._has_tasks = asyncio.Event()
        self._populate_task = None

        assert coroutine is not None
        assert inspect.iscoroutinefunction(coroutine)
        self._coroutine = coroutine

        assert iterable is not None
        assert isinstance(iterable, Iterable)
        self._iterable = iterable

        assert pool is not None
        self._pool = pool

        assert return_exceptions is not None
        assert isinstance(return_exceptions, bool)
        self._return_exceptions = return_exceptions

        assert starmap is not None
        assert isinstance(starmap, bool)
        self._starmap = starmap

    @property
    def loop(self):
        """."""
        return self._pool.loop

    async def _populate_tasks(self):
        """."""
        idx = -1
        for i in self._iterable:
            t = await self._pool._create_task(self._coroutine(i))
            t._args = i

            idx += 1
            t._index = idx

            self._tasks.add(t)
            self._has_tasks.set()

    async def __aiter__(self):
        """."""
        # start processing items
        await self.start()

        # continue until all items have been processed
        try:
            while True:
                print('yay')
                # do we have any tasks?
                if not self._tasks:
                    # unset flag to prevent cpu spin
                    self._has_tasks.clear()

                    # are we ready to exit?
                    if self._populate_task.done():
                        print('nothing left to do')
                        return
                    
                # wait until we have some more tasks
                await self._has_tasks.wait()

                # which tasks have completed?
                completed, pending = await asyncio.wait(self._tasks,
                    loop=self.loop, timeout=0.1)

                # process completed tasks
                for t in completed:
                    # remove task from waiting set
                    self._tasks.remove(t)

                    # handle result
                    try:
                        result = (await t)
                    except Exception as exc:
                        if not self._return_exceptions:
                            self.stop()
                            raise
                        result = exc

                    # wrap result
                    yield TaskResult(index=t._index, args=t._args,
                            result=result, start_ts=t._start_ts,
                            end_ts=t._end_ts)

        finally:
            await self.stop()

    async def start(self):
        """."""
        await self._lock.acquire()
        self._populate_task = self.loop.create_task(
            self._populate_tasks())

    async def stop(self):
        """."""
        # stop population task
        self._populate_task.cancel()

        if self._tasks:
            done, pending = await asyncio.wait(self._tasks, loop=self.loop, timeout=0.001)
            for task in pending:
                task.cancel()
        
        # release the lock
        self._lock.release()


class TaskPool:
    """."""

    def __init__(self, size, loop=None):
        """."""
        assert isinstance(size, int)
        self.loop = loop if loop else asyncio.get_running_loop()
        self._tasks = set()
        self._tasksem = asyncio.Semaphore(size)
    
    async def _run_task(self, awaitable):
        """."""
        try:
            return await awaitable
        finally:
            t = asyncio.Task.current_task()
            t._end_ts = time.time()
            self._tasksem.release()

    async def _create_task(self, awaitable):
        """."""
        assert inspect.isawaitable(awaitable)
        await self._tasksem.acquire()

        start_ts = time.time()
        t = self.loop.create_task(self._run_task(awaitable))
        t._start_ts = start_ts
        return t

    async def starmap(self, coroutine, iterable, return_exceptions=False):
        """."""
        results = self.istarmap(coroutine, iterable, return_exceptions)
        return [ result async for result in results ]

    async def map(self, coroutine, iterable, return_exceptions=False):
        """."""
        results = self.imap(coroutine, iterable, return_exceptions)
        return [ result async for result in results ]

    async def istarmap(self, coroutine, iterable, return_exceptions=False):
        """."""
        tpm = TaskPoolMap(pool=self, coroutine=coroutine,
                iterable=iterable, return_exceptions=return_exceptions,
                starmap=True)

        async for result in tpm:
            yield result

    async def imap(self, coroutine, iterable, return_exceptions=False):
        """
        If an exception is raised, then the remaining tasks are cancelled.
        """
        tpm = TaskPoolMap(pool=self, coroutine=coroutine,
                iterable=iterable, return_exceptions=return_exceptions,
                starmap=False)

        async for result in tpm:
            yield result

    async def __aenter__(self, *args, **kwargs):
        return self

    async def __aexit__(self, *args, **kwargs):
        return
    
    def open(self):
        """."""
        raise NotImplementedError()

    def close(self):
        """
        Prevents any more tasks from being submitted to the pool. 
        Once all the tasks have been completed the worker processes will exit.
        """
        raise NotImplementedError()
    
    def terminate(self):
        """
        Stops the worker processes immediately without completing outstanding work. 
        When the pool object is garbage collected terminate() will be called immediately.
        """
        raise NotImplementedError()



async def wait_and_echo(value):
    x =  random.random()
    await asyncio.sleep(100)
    print(x)
    return value

'''
def test_one_shot():
    items = range(10)
    with TaskPool(4) as tp:
        tp.map(wait_and_eco, items)


def test_pool_ctx():

    with Pool(4) as pool:
        pass

def test_pool_no_ctx():
    pool = Pool(4)
    pool.close()

'''

async def test_all():
    items = range(1000)

    async with TaskPool(20) as tp:
        async for i in tp.imap(wait_and_echo, items):
            print(i)

        #[ i async for i in tp.map(wait_and_echo, items) ]


asyncio.run(test_all())

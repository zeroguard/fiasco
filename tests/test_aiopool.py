#!/usr/bin/env python3

#from fiasco.aiopool import Pool

import asyncio
import inspect

from collections.abc import Iterable

# TODO: abstract into a class??
class TaskPoolMap:
    """."""

    def __init__(self, *, loop, pool, coroutine, iterable, return_exceptions=False):
        self._pool = pool
        self._coroutine = coroutine
        self._iterable = iterable
        self._return_exceptions = return_exceptions
        self._run_lock = asyncio.Lock()
        self._tasks = []

    async def create_task(self, awaitable):
        """."""
        assert inspect.isawaitable(awaitable)
        await self.tasksem.acquire()
        return self.loop.create_task(self._run_task(awaitable))

    async def _process_iterable(self):
        """."""
        pass

    async def __aenter__(self):
        """."""
        await self.start()

    async def __aexit__(self):
        """."""
        await self.stop()

    async def start(self):
        """."""
        await self._run_lock.acquire()

    async def stop(self):
        """."""
        await self._run_lock.release()


class TaskPool:
    """."""

    def __init__(self, size, loop=None):
        """."""
        assert isinstance(size, int)
        self.loop = loop if loop else asyncio.get_running_loop()
        self.tasksem = asyncio.Semaphore(size)
        self.tasks = set()
    
    async def _run_task(self, awaitable):
        """."""
        try:
            return await awaitable
        finally:
            self.tasksem.release()

    async def create_task(self, awaitable):
        """."""
        assert inspect.isawaitable(awaitable)
        await self.tasksem.acquire()
        return self.loop.create_task(self._run_task(awaitable))

    async def map(self, coroutine, iterable, return_exceptions=False):
        """
        If an exception is raised, then the remaining tasks are cancelled.
        """
        assert inspect.iscoroutinefunction(coroutine)
        assert isinstance(iterable, Iterable)

        # process each iterable in its own task
        tasks = []
        async def _populate_tasks():
            for i in iterable:
                t = await self.create_task(coroutine(i))
                tasks += [t]

        # run populate in its own task
        task_populate = self.loop.create_task(_populate_tasks())

        # handle cancellation event
        async def _cancel():
            # stop population
            task_populate.cancel()

            # cancel anything in progress
            done, pending = await asyncio.wait(tasks, loop=self.loop, timeout=0.001)
            for task in pending:
                task.cancel()

        # continue until all items have been processed
        while True:
            # yield results as they complete
            completed = asyncio.as_completed(tasks, loop=self.loop)
            for t in completed:
                try:
                    yield (await t)
                except Exception as exc:
                    if not return_exceptions:
                        _cancel()
                        raise
                    yield await exc
            
            # are we still populating the queue?
            if not completed and task_populate.done():
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
    asyncio.sleep(random.random())
    return value


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

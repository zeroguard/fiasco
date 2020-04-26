#!/usr/bin/env python3

import sys
import logging
import time
import coloredlogs
import multiprocessing
import signal
import os

# shared shutdown flag

SHUTDOWN_MODE_SOFT = 1
SHUTDOWN_MODE_HARD = 2
SHUTDOWN_MODE_NUCLEAR = 3


class ProcessContext:
    """."""

    def __init__(self, name, shutdown_flag):
        self.name = name
        self._shutdown_flag = shutdown_flag

    @property
    def is_shutdown(self):
        """."""
        return self._shutdown_flag.is_set()


class MultiProcessGroup:
    """."""

    def __init__(self):
        """."""
        self._procs = []
        self._shutdown_flag = multiprocessing.Event()
        self._shutdown_stage = None
        self.logger = logging.getLogger(__name__)

    def _handle_proc_sigterm(self, signal, frame):
        """."""
        self.logger.info('hard shutdown')
        sys.exit(254)

    def _run_func(self, func, ctx, *args, **kwargs):
        """."""
        signal.signal(signal.SIGTERM, self._handle_proc_sigterm)
        ctx.logger = logging.getLogger(ctx.name)

        try:
            func(ctx, *args, **kwargs)
        except SystemExit:
            self.logger.info('caught hard shutdown')

    def run(self, func, func_args=None, func_kwargs=None, name=None):
        """."""

        ctx = ProcessContext(name, self._shutdown_flag)

        func_args = func_args if func_args else []
        func_kwargs = func_kwargs if func_kwargs else {}

        p = multiprocessing.Process(target=self._run_func,
            args=(func, ctx, *func_args), kwargs=func_kwargs)
        self._procs += [p]

        default_handler = signal.getsignal(signal.SIGINT)
        try:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            p.start()
        finally:
            signal.signal(signal.SIGINT, default_handler)

        return p

    def shutdown(self):
        """."""
        if self._shutdown_stage is None:
            self._shutdown_soft()
        elif self._shutdown_stage == SHUTDOWN_MODE_SOFT:
            self._shutdown_hard()
        elif self._shutdown_stage == SHUTDOWN_MODE_HARD:
            self._shutdown_nuclear()
        else:
            raise RuntimeError('unknown shutdown state')

    def _shutdown_soft(self):
        """."""
        self.logger.info('performing soft shutdown')
        self._shutdown_stage = SHUTDOWN_MODE_SOFT
        self._shutdown_flag.set()

    def _shutdown_hard(self):
        """."""
        self.logger.info('performing hard shutdown')
        self._shutdown_stage = SHUTDOWN_MODE_HARD
        for proc in self._procs:
            try:
                os.kill(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                continue

    def _shutdown_nuclear(self):
        """."""
        self.logger.info('performing nuclear shutdown')
        self._shutdown_stage = SHUTDOWN_MODE_NUCLEAR
        for proc in self._procs:
            os.kill(proc.pid, signal.SIGKILL)
        sys.exit(254)

    def are_procs_running(self):
        """."""
        alive = [w.is_alive() for w in self._procs]
        num_alive = [x for x in alive if x]
        return bool(num_alive)

    def run_forever(self):
        """."""
        # wait forever
        while True:
            try:
                if not self.are_procs_running():
                    return
                time.sleep(0.5)
            except KeyboardInterrupt:
                self.shutdown()




'''
    #default_handler = signal.getsignal(signal.SIGTERM)
    #signal.signal(signal.SIGTERM, signal_handler)
    ctx.send_message('queue1', 28463)

    ctx.send_message # add to queue, only one worker picks it up
    ctx.notify_worker_group('worker') # add to queue, all workers pick it up

    ctx.comms.subscribe
    ctx.comms.publish


    subscribe()


# Worker 1
#   - shutdown everything
#     - send to queue?

# Worker 2

# Main Process
#   -

class Comms:
    """."""

    def publish(self, name, msg):
        pass

    def subscribe(self, name):
        pass



class ProcessWorker:
    """."""

    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger('worker:'+self.name)

    def __str__(self):
        return "<{}: {}>".format(self.__class__.__name__, self.name)
'''

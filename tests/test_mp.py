"""Test for the fiasco.mp module."""
import time
import random

from fiasco.mp import TaskManager


def placeholder_task():
    """."""
    return True


def test_mp():
    """."""
    manager = TaskManager()
    manager.run(
        func=placeholder_task,
    )

    assert manager.are_procs_running()
    manager.shutdown()
    # assert not manager.are_procs_running()

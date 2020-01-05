from .core import ECSShowBase
from .clock import *
from .model import *
from .input import *
from .camera import *
from .character import *
from .ai import *
from .animation import *

#__all__ = ['ECSShowBase']


def panda_clock():
    def read_dt():
        return globalClock.dt
    return read_dt

import sys

from panda3d.core import PStatClient

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.panda3d.input import Input


class DebugTools(System):
    entity_filters = {}
    input_context = 'debug'
    frame_rate_meter = False
    console_open = False

    def update(self, entities_by_filter):
        context = base.device_listener.read_context('debug')
        if context['quit']:
            sys.exit()
        if context['pdb']:
            import pdb
            pdb.set_trace()
        if context['pstats']:
            base.pstats = True
            PStatClient.connect()
        if context['frame_rate_meter']:
            self.frame_rate_meter = not self.frame_rate_meter
            base.set_frame_rate_meter(self.frame_rate_meter)
        if context['console']:
            if not hasattr(base, 'console'):
                print("No console present.")
                return
            self.console_open = not self.console_open
            if self.console_open:
                base.console.node().show()
            else:
                base.console.node().hide()

from panda3d.core import PStatClient
from panda3d.core import PStatCollector

from direct.showbase.ShowBase import ShowBase
from direct.task import Task

from wecs.core import World


class ECSShowBase(ShowBase):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.ecs_world = World()
        self.ecs_system_pstats = {}

    def add_system(self, system, sort):
        self.ecs_world.add_system(system, sort)
        task = base.task_mgr.add(
            self.run_system,
            repr(system),
            extraArgs=[system],
            sort=sort,
        )
        self.ecs_system_pstats[system] = PStatCollector('App:WECS:Systems:{}'.format(system))
        return task

    def run_system(self, system):
        self.ecs_system_pstats[system].start()
        base.ecs_world.update_system(system)
        self.ecs_system_pstats[system].stop()
        return Task.cont

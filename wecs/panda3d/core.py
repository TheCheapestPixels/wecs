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

    def add_system(self, system, wecs_sort, p3d_sort=None, p3d_priority=None):
        self.ecs_world.add_system(system, wecs_sort)
        if p3d_sort is None and p3d_priority is None:
            p3d_sort = wecs_sort
            p3d_priority = 0
        elif p3d_priority is None:
            p3d_priority = 0            
        task = base.task_mgr.add(
            self.run_system,
            repr(system),
            extraArgs=[system],
            sort=p3d_sort,
            priority=p3d_priority,
        )
        self.ecs_system_pstats[system] = PStatCollector('App:WECS:Systems:{}'.format(system))
        return task

    def run_system(self, system):
        self.ecs_system_pstats[system].start()
        base.ecs_world.update_system(system)
        self.ecs_system_pstats[system].stop()
        return Task.cont

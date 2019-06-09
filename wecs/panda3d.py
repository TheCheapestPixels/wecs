from direct.showbase.ShowBase import ShowBase
from direct.task import Task


from wecs.core import World

class ECSShowBase(ShowBase):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.ecs_world = World()

    def add_system(self, system, sort):
        self.ecs_world.add_system(system, sort)
        task = base.task_mgr.add(
            self.run_system,
            repr(system),
            extraArgs=[system],
            sort=sort,
        )
        return task

    def run_system(self, system):
        base.ecs_world.update_system(system)
        return Task.cont

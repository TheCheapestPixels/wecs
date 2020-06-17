import logging

from panda3d.core import PStatCollector
from panda3d.core import PythonTask

from direct.showbase.ShowBase import ShowBase
from direct.task import Task

from wecs.core import World
from wecs.core import System

logging.getLogger().setLevel(logging.INFO)


class ECSShowBase(ShowBase):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.ecs_world = World()
        self.ecs_system_pstats = {}
        self.task_to_data = {}
        self.system_to_data = {}

    def add_system(self, system, sort, priority=None):
        """
        Registers an additional system in the world.
        The world will use the standard panda3D taskManager to ensure the system
        is run on every tick.

        :param system: Instance of a :class:`wecs.core.System`
        :param sort: `sort` parameter for the task running the system
        :param priority: Optional `priority` parameter for the task running the system
        :return: Panda3D PythonTask

        """
        logging.info(f"in {__name__} got {system}, {sort}, {priority}")
        if priority is None:
            priority = 0            
        wecs_sort = (sort, -priority)
            
        self.ecs_world.add_system(system, wecs_sort)
        task = base.task_mgr.add(
            self.run_system,
            repr(system),
            extraArgs=[system],
            sort=sort,
            priority=priority,
        )
        self.ecs_system_pstats[system] = PStatCollector('App:WECS:Systems:{}'.format(system))

        system_type = type(system)
        data = (system_type, task, wecs_sort)
        self.task_to_data[task] = data
        self.system_to_data[system_type] = data
        return task

    def run_system(self, system):
        self.ecs_system_pstats[system].start()
        base.ecs_world._update_system(system)
        self.ecs_system_pstats[system].stop()
        return Task.cont

    def remove_system(self, task_or_system):
        if isinstance(task_or_system, PythonTask):
            data = self.task_to_data[task_or_system]
        elif issubclass(task_or_system, System):
            data = self.system_to_data[task_or_system]
        else:
            raise ValueError(task_or_system, type(task_or_system))
        system_type, task, wecs_sort = data

        self.task_mgr.remove(task)
        self.ecs_world.remove_system(system_type)
        del self.task_to_data[task]
        del self.system_to_data[system_type]

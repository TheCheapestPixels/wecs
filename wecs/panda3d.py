from dataclasses import field

from panda3d.core import Vec3
from panda3d.core import NodePath

from direct.showbase.ShowBase import ShowBase
from direct.task import Task

from wecs.core import World
from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter


class ECSShowBase(ShowBase):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.ecs_world = World()

    def add_system(self, system, sort):
        print("Adding task")
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


@Component()
class Model:
    model_name: str


@Component()
class Actor:
    model_name: str


@Component()
class Scene:
    root: NodePath


@Component()
class Position:
    value: Vec3 = field(default_factory=lambda:Vec3(0,0,0))


class LoadModels(System):
    entity_filters = {
        'model': and_filter([Model, Position, Scene]),
    }

    # TODO
    # Only Model is needed for loading, which then could be done
    # asynchronously.
    def init_entity(self, filter_name, entity):
        # Load
        model_name = entity.get_component(Model).model_name
        print("Loading model {}".format(model_name))
        model = base.loader.load_model(model_name)
        entity.get_component(Model).node = model

        # Add to scene under a new
        root = entity.get_component(Scene).root
        model.reparent_to(root)

    # TODO
    # Destroy node if and only if the Model is removed.
    def destroy_entity(self, filter_name, entity, component):
        # Remove from scene
        if isinstance(component, Model):
            component.node.destroy_node()
        else:
            entity.get_component(Model).node.destroy_node()

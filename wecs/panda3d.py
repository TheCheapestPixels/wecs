from dataclasses import field

from panda3d.core import Vec3
from panda3d.core import NodePath
from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletRigidBodyNode

from direct.showbase.ShowBase import ShowBase
from direct.task import Task

from wecs.core import World
from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.core import or_filter
from wecs.core import UID


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


@Component()
class Model:
    model_name: str
    node: NodePath = None


@Component()
class Actor:
    model_name: str


@Component()
class Scene:
    node: NodePath


@Component()
class Position:
    value: Vec3 = field(default_factory=lambda:Vec3(0,0,0))


# Bullet physics

@Component()
class PhysicsWorld:
    clock: object
    timestep: float = 0.0
    max_timestep: float = 1.0/30
    world: BulletWorld = field(default_factory=BulletWorld)


@Component()
class PhysicsBody:
    node: NodePath = None
    body: NodePath = field(default_factory=BulletRigidBodyNode)
    timestep: float = 0.0
    world: UID = None
    _world: UID = None
    scene: UID = None
    _scene: UID = None


# Loading / reparenting / destroying models

class LoadModels(System):
    entity_filters = {
        'model': and_filter([
            Model,
            Position,
            or_filter([
                Scene,
                PhysicsBody,
            ]),
        ]),
    }

    # TODO
    # Only Model is needed for loading, which then could be done
    # asynchronously.
    def init_entity(self, filter_name, entity):
        # Load
        model_name = entity.get_component(Model).model_name
        model = base.loader.load_model(model_name)
        entity.get_component(Model).node = model

        # Attach to PhysicsBody or Scene; former takes precedence.
        if PhysicsBody in entity:
            parent = entity[PhysicsBody].node
        else:
            parent = entity[Scene].node
        model.reparent_to(parent)

    # TODO
    # Destroy node if and only if the Model is removed.
    def destroy_entity(self, filter_name, entity, component):
        # Remove from scene
        if isinstance(component, Model):
            component.node.destroy_node()
        else:
            entity.get_component(Model).node.destroy_node()


# Bullet physics

class SetUpPhysics(System):
    entity_filters = {
        'world': and_filter([PhysicsWorld]),
        'body': and_filter([PhysicsBody]),
    }

    def init_entity(self, filter_name, entity):
        if filter_name == 'body':
            body = entity[PhysicsBody]
            body.node = NodePath(body.body)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['body']:
            body = entity[PhysicsBody]
            # Has the physics world simulating this entity changed?
            if body.world != body._world:
                if body._world is not None:
                    self.world[body._world][PhysicsWorld].remove_rigid_body()
                    body._world = None
                if body.world is not None:
                    world_cmpt = self.world[body.world][PhysicsWorld]
                    world_cmpt.world.attach_rigid_body(body.body)
                    if Position in entity:
                        body.node.set_pos(entity[Position].value)
                    body._world = body.world
            # Has the scene that this node is attached to changed?
            if body.scene != body._scene:
                scene = self.world[body.scene][Scene]
                body.node.reparent_to(scene.node)
                body._scene = body.scene

    def destroy_entity(self, filter_name, entity, components_by_type):
        pass


class DetermineTimestep(System):
    entity_filters = {
        'world': and_filter([PhysicsWorld]),
        'body': and_filter([PhysicsBody]),
    }

    def update(self, entities_by_filter):
        timesteps = {}
        for entity in entities_by_filter['world']:
            world = entity[PhysicsWorld]
            dt = world.clock.dt
            max_timestep = world.max_timestep
            if dt > max_timestep:
                dt = max_timestep
            world.timestep = dt
            timesteps[entity._uid] = dt
        for entity in entities_by_filter['body']:
            body = entity[PhysicsBody]
            if body.world in timesteps:
                body.timestep = timesteps[body.world]


class DoPhysics(System):
    entity_filters = {
        'world': and_filter([PhysicsWorld]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['world']:
            world = entity.get_component(PhysicsWorld)
            world.world.do_physics(world.timestep)

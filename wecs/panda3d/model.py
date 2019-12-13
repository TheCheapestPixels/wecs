from dataclasses import field

import direct.actor.Actor
from panda3d.core import Vec3
from panda3d.core import NodePath
from panda3d.core import ClockObject
from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletRigidBodyNode

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.core import or_filter
from wecs.core import UID

from wecs.mechanics.clock import Clock


@Component()
class Model:
    model_name: str = ''
    node: NodePath = None


@Component()
class Actor:
    pass


@Component()
class CollidableGeometry:
    collide_mask: int = 1<<0 # bit 0 set


@Component()
class FlattenStrong:
    pass


# Spatial context

@Component()
class Scene:
    node: NodePath = field(default_factory=lambda:base.render)


# This should vanish... It means "Initial position"... I hope.
@Component()
class Position:
    value: Vec3 = field(default_factory=lambda:Vec3(0,0,0))


# Bullet physics

@Component()
class PhysicsWorld:
    timestep: float = 0.0
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
        model = entity[Model]
        if model.node is None:
            if Actor in entity:
                model.node = direct.actor.Actor.Actor(model.model_name)
            else:
                model.node = base.loader.load_model(model.model_name)

        # Load hook
        self.post_load_hook(model.node, entity)

        # Attach to PhysicsBody or Scene; former takes precedence.
        if CollidableGeometry in entity:
            model.node.set_collide_mask(entity[CollidableGeometry].collide_mask)
        if FlattenStrong in entity:
            model.node.flatten_strong()
        if PhysicsBody in entity:
            parent = entity[PhysicsBody].node
        else:
            parent = entity[Scene].node
        model.node.reparent_to(parent)
        model.node.set_pos(entity[Position].value)

    # TODO
    # Destroy node if and only if the Model is removed.
    def destroy_entity(self, filter_name, entity, component):
        # Remove from scene
        if isinstance(component, Model):
            component.node.destroy_node()
        else:
            entity.get_component(Model).node.destroy_node()

    def post_load_hook(self, node, entity):
        pass


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


class DeterminePhysicsTimestep(System):
    entity_filters = {
        # FIXME: PhysicsWorld.clockshould be an entity._uid
        # (or None if the same)
        'world': and_filter([PhysicsWorld, Clock]),
        'body': and_filter([PhysicsBody]),
    }

    def update(self, entities_by_filter):
        timesteps = {}
        for entity in entities_by_filter['world']:
            world = entity[PhysicsWorld]
            world.timestep = entity[Clock].timestep
            timesteps[entity._uid] = world.timestep
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

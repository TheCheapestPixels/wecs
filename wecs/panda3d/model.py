from dataclasses import field

import direct.actor.Actor
from panda3d.core import Vec3
from panda3d.core import NodePath
from panda3d.core import ClockObject
from panda3d.core import CardMaker
from panda3d.core import SamplerState
from panda3d.core import Texture

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
    geometry: NodePath = None
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


# 2d models (aka sprites)

@Component()
class Sprite:
    image_name: str = ""
    texture: Texture = None
    pixelated: bool = True


@Component()
class SpriteAnimation:
    animations: dict = field(default_factory=lambda: {
        "idle" : [0,1],
    })
    animation: str = "idle"
    loop: bool = True
    sprite_width: int = 16
    sprite_height: int = 16
    uv_width: float = 0
    uv_height: float = 0
    frame: int = 0
    framerate: int = 15 #frames-per-second
    timer: int = 0 # accumulated delta-time


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


@Component()
class Billboard:
    pass


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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cardmaker = CardMaker("maker of cards")
        # set frame so the bottom edge is centered on 0
        self.cardmaker.set_frame(-0.5,0.5,0,1)

    # TODO
    # Only Model is needed for loading, which then could be done
    # asynchronously.
    def init_entity(self, filter_name, entity):
        # Load
        model = entity[Model]
        if model.node is None:
            model.node = NodePath(model.model_name)

        if model.geometry is None:
            if Sprite in entity:
                model.geometry = NodePath(self.cardmaker.generate())
            elif Actor in entity:
                model.geometry = direct.actor.Actor.Actor(model.model_name)
            else:
                model.geometry = base.loader.load_model(model.model_name)

        model.geometry.reparent_to(model.node)

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


class UpdateSprites(System):
    entity_filters = {
        'sprite': and_filter([
            Model,
            Sprite,
            Clock,
        ])
    }

    def init_entity(self, filter_name, entity):
        sprite = entity[Sprite]
        model = entity[Model]
        if sprite.texture is None:
            sprite.texture = loader.load_texture(sprite.image_name)
            model.geometry.set_texture(sprite.texture)
        texture = sprite.texture
        stage = model.geometry.find_all_texture_stages()[0]
        # Set minmag filter.
        if sprite.pixelated:
            texture.setMagfilter(SamplerState.FT_nearest)
            texture.setMinfilter(SamplerState.FT_nearest)
        else:
            texture.setMagfilter(SamplerState.FT_linear)
            texture.setMinfilter(SamplerState.FT_linear)
        if SpriteAnimation in entity:
            # Scale texture to display a single tile
            sprite = entity[SpriteAnimation]
            sprite.uv_width = sprite.sprite_width/texture.get_orig_file_x_size()
            sprite.uv_height = sprite.sprite_height/texture.get_orig_file_y_size()
            model.geometry.set_tex_scale(stage, sprite.uv_width, sprite.uv_height)
            model.geometry.set_tex_offset(stage, (0, 1-sprite.uv_height))
        model.geometry.set_transparency(True)


    def animate(self, sprite, model):
        # Increment animation frame
        animation = sprite.animations[sprite.animation]
        sprite.frame += 1
        # Manage end of animation
        if sprite.frame > len(animation)-1:
            if sprite.loop: # Start from beginning
                sprite.frame = 0
            else: # Reshow last frame
                sprite.frame -= 1
        frame = animation[sprite.frame]
        # get transform for cell
        w, h = sprite.uv_width, sprite.uv_height
        rows = 1/w
        collumns = 1/h
        u = (frame%rows)*w
        v = 1-(((frame//collumns)*h)+h)
        # display it
        stage = model.geometry.find_all_texture_stages()[0]
        model.geometry.set_tex_offset(stage, (u, v))

    def update(self, entities_by_filter):
        for entity in entities_by_filter['sprite']:
            sprite = entity[Sprite]
            model = entity[Model]
            clock = entity[Clock]
            if SpriteAnimation in entity:
                sprite = entity[SpriteAnimation]
                animation = sprite.animations[sprite.animation]
                # Increment frame
                sprite.timer += clock.frame_time
                if sprite.timer >= 1/sprite.framerate:
                    sprite.timer -= 1/sprite.framerate
                    self.animate(sprite, model)


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


class UpdateBillboards(System):
    entity_filters = {
        'sprite': and_filter([
            Model,
            Billboard,
        ])
    }

    def init_entity(self, filter_name, entity):
        entity[Model].geometry.setBillboardPointEye()

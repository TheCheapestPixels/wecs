"""
This module is a toolbox for prototyping.

A typical system list:

 - :class:`wecs.panda3d.prototype.ManageModels`
 - :class:`wecs.mechanics.clock.DetermineTimestep`
 - :class:`wecs.panda3d.prototype.DeterminePhysicsTimestep`
 - :class:`wecs.panda3d.prototype.DoPhysics`

TODO

* Components
  * Sprite
  * SpriteSheet
  * SpriteAnimation
  * Billboard
* Teardown
  * Actor
"""

from dataclasses import field

from panda3d.core import Vec3
from panda3d.core import NodePath
from panda3d.core import CardMaker
from panda3d.core import SamplerState
from panda3d.core import Texture
from panda3d.bullet import BulletWorld
from panda3d.bullet import BulletRigidBodyNode

from direct.actor.Actor import Actor as DirectActor

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.core import or_filter
from wecs.core import UID

from wecs.mechanics.clock import Clock


@Component()
class Model:
    """
    node: A NodePath acting as the root for the scene graph of this
      entity with regard to this mechanic.
    parent: The NodePath to attach the node to.
    post_attach: A function that is called after the node is reparented
      to the parent, with the entity as argument. Set to None to do
      nothing.
    """
    node: NodePath = field(default_factory=lambda: NodePath(""))
    parent: NodePath = field(default_factory=lambda: base.render)
    post_attach: object = None


def transform(pos=None, hpr=None, scale=None, component_type=Model):
    def inner(entity):
        if pos is not None:
            entity[component_type].node.set_pos(pos)
        if hpr is not None:
            entity[component_type].node.set_hpr(hpr)
        if scale is not None:
            entity[component_type].node.set_scale(scale)
    return inner


@Component()
class Actor:
    node: NodePath = field(default_factory=lambda: NodePath(""))
    file: str = ''
    animations: dict = field(default_factory=dict)
    animation: str = ''
    post_attach: object = None


@Component()
class Sprite:
    image_name: str = ''
    pixelated: bool = True
    sprite_height: int = 0
    sprite_width: int = 0
    update: bool = False
    animations: dict = field(default_factory=dict)
    animation: str = None
    framerate: float = 0.0
    loop: bool = False
    post_attach: object = None
    node: NodePath = None
    texture: object = None
    timer: float = 0.0
    frame: int = 0


@Component()
class Geometry:
    """
    Geometry that gets attached to the Model. If no NodePath is provided
    (as `node`), the specified file will be loaded.
    """
    node: NodePath = None
    file: str = None
    post_attach: object = None


@Component()
class FlattenStrong:
    """
    Flatten the geometry node.
    """
    pass


@Component()
class CollidableGeometry:
    """
    Set the collide mask on the geometry node.
    """
    mask: int = 0


@Component()
class Billboard:
    """
    Set billboard effect on the sprite node.
    """
    pass


@Component()
class PhysicsWorld:
    timestep: float = 0.0
    world: BulletWorld = field(default_factory=BulletWorld)


@Component()
class PhysicsBody:
    body: NodePath = field(default_factory=BulletRigidBodyNode)
    world: UID = None
    node: NodePath = None
    timestep: float = 0.0


class ManageModels(System):
    entity_filters = {
        'model': and_filter(Model),
        'geometry': and_filter(Model, Geometry),
        'actor': and_filter(Model, Actor),
        'sprite': and_filter(Model, Sprite),
        'flatten': and_filter(Geometry, FlattenStrong),
        'collidable': and_filter(Geometry, CollidableGeometry),
        'billboard': and_filter(Sprite, Billboard),
        'physics': and_filter(Model, PhysicsBody),
    }

    def enter_filter_model(self, entity):
        model = entity[Model]
        assert model.node is not None
        assert model.parent is not None

        if model.node.name == "":
            model.node.name = entity._uid.name

        model.node.reparent_to(model.parent)
        if model.post_attach is not None:
            model.post_attach(entity)

    def enter_filter_geometry(self, entity):
        model = entity[Model]
        geometry = entity[Geometry]

        # Load geometry if required
        if geometry.node is None:
            geometry.node = base.loader.load_model(geometry.file)

        # Attach
        geometry.node.reparent_to(model.node)
        if geometry.post_attach is not None:
            geometry.post_attach(entity)

    def enter_filter_actor(self, entity):
        model = entity[Model]
        actor = entity[Actor]

        actor.node = DirectActor(actor.file, actor.animations)
        actor.node.reparent_to(model.node)
        if actor.post_attach is not None:
            actor.post_attach(entity)

        actor.node.loop(actor.animation)

    def enter_filter_sprite(self, entity):
        model = entity[Model]
        sprite = entity[Sprite]

        cardmaker = CardMaker("sprite")
        cardmaker.set_frame(-1, 1, -1, 1)

        sprite.node = NodePath(cardmaker.generate())
        if sprite.texture is None and sprite.image_name:
            sprite.texture = loader.load_texture(sprite.image_name)
        sprite.node.set_texture(sprite.texture)

        if sprite.pixelated:
            sprite.texture.setMagfilter(SamplerState.FT_nearest)
            sprite.texture.setMinfilter(SamplerState.FT_nearest)
        else:
            sprite.texture.setMagfilter(SamplerState.FT_linear)
            sprite.texture.setMinfilter(SamplerState.FT_linear)
        sprite.node.set_transparency(True)

        sprite.node.reparent_to(model.node)
        if sprite.post_attach is not None:
            sprite.post_attach(entity)

    def enter_filter_flatten(self, entity):
        geometry = entity[Geometry]

        geometry.node.flatten_strong()

    def enter_filter_collidable(self, entity):
        geometry = entity[Geometry]
        collidable = entity[CollidableGeometry]

        geometry.node.set_collide_mask(collidable.mask)

    def enter_filter_billboard(self, entity):
        sprite = entity[Sprite]

        sprite.node.set_billboard_point_eye()

    def enter_filter_physics(self, entity):
        model = entity[Model]
        physics_body = entity[PhysicsBody]
        physics_world = self.world[physics_body.world][PhysicsWorld]

        physics_body.node = NodePath(physics_body.body)

        physics_body.node.reparent_to(model.node)
        physics_body.node.wrt_reparent_to(model.parent)
        model.node.wrt_reparent_to(physics_body.node)

        physics_world.world.attach_rigid_body(physics_body.body)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['sprite']:
            if Clock in entity:
                sprite = entity[Sprite]

                if sprite.animation:
                    self.animate(entity)
                if sprite.update:
                    self.set_frame(entity)

    def animate(self, entity):
        sprite = entity[Sprite]
        clock = entity[Clock]

        animation = sprite.animations[sprite.animation]
        # Increment frame
        sprite.timer += clock.game_time
        frame_time = 1 / sprite.framerate
        if sprite.timer >= frame_time:
            elapsed_frames = int(sprite.timer / frame_time)
            sprite.timer -= elapsed_frames * frame_time
            sprite.frame += elapsed_frames
        # Manage end of animation
        if sprite.frame > len(animation) - 1:
            if sprite.loop:  # Start from beginning
                sprite.frame = sprite.frame % len(animation)
            else:  # Reshow last frame
                sprite.frame = len(animation) - 1
        sprite.update = True

    def set_frame(self, entity):
        sprite = entity[Sprite]

        if sprite.animation is not None:
            animation = sprite.animations[sprite.animation]
            frame = animation[sprite.frame]
        else:
            frame = 0

        # get UV transform for current frame
        w = sprite.sprite_width / sprite.texture.get_orig_file_x_size()
        h = sprite.sprite_height / sprite.texture.get_orig_file_y_size()
        rows = 1 / w
        columns = 1 / h
        u = (frame % rows) * w
        v = 1 - (((frame // columns) * h) + h)
        # display it
        stage = sprite.node.find_all_texture_stages()[0]
        sprite.node.set_tex_scale(stage, w, h)
        sprite.node.set_tex_offset(stage, (u, v))
        sprite.update = False

    def exit_filter_physics(self, entity):
        model = entity[Model]
        physics_body = entity[PhysicsBody]
        physics_world = self.world[physics_body.world][PhysicsWorld]

        physics_world.world.remove_rigid_body(body.body)
        model.node.wrt_reparent_to(model.parent)
        physics_body.node.detach_node()

    def exit_filter_billboard(self, entity):
        # FIXME: Undo geometry.node.set_billboard_point_eye()
        pass

    def exit_filter_collidable(self, entity):
        geometry = entity[Geometry]

        geometry.node.set_collide_mask(0)

    def exit_filter_flatten(self, entity):
        pass

    def exit_filter_geometry(self, entity):
        geometry = entity[Geometry]
        geometry.node.detach_node()

    def exit_filter_model(self, entity):
        model = entity[Model]
        model.node.detach_node()


class DeterminePhysicsTimestep(System):
    """
    Set the `timestep` of all `PhysicsWorld`s and `PhysicsBody`s
    according to `Clock.game_time`.
    """
    entity_filters = {
        'world': and_filter([PhysicsWorld, Clock]),
        'body': and_filter([PhysicsBody]),
    }

    def update(self, entities_by_filter):
        timesteps = {}
        for entity in entities_by_filter['world']:
            clock = entity[Clock]
            world = entity[PhysicsWorld]

            world.timestep = clock.game_time
            timesteps[entity._uid] = world.timestep

        for entity in entities_by_filter['body']:
            body = entity[PhysicsBody]
            if body.world in timesteps:
                body.timestep = timesteps[body.world]


class DoPhysics(System):
    """
    Advance the BulletWorld's simulation by `PhysicsWorld.timestep`
    """
    entity_filters = {
        'world': and_filter([PhysicsWorld]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['world']:
            world = entity.get_component(PhysicsWorld)

            world.world.do_physics(world.timestep)

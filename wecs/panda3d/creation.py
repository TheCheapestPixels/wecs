import wecs.panda3d
from dataclasses import field

from panda3d.core import NodePath

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.core import UID

from wecs.aspects import Aspect
from wecs.aspects import factory

from .model import Model
from .character import CharacterController


def round_node_pos_hpr(node, move_snap, rot_snap):
    x = node.get_x()
    y = node.get_y()
    node.set_x(round(x/move_snap)*move_snap)
    node.set_y(round(y/move_snap)*move_snap)
    node.set_h(round(node.get_h()/rot_snap)*rot_snap)



@Component()
class CursorMovement:
    move_snap: int = 2
    move_speed: float = 10.0
    rot_speed: float = 180.0
    rot_snap: float = 90.0
    snapping: bool = True


class Cursoring(System):
    entity_filters = {
        'cursor' : and_filter([
            CursorMovement,
            CharacterController,
            Model
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['cursor']:
            cursor = entity[CursorMovement]
            model = entity[Model]
            char = entity[CharacterController]
            char.translation *= cursor.move_speed
            char.rotation *= cursor.rot_speed
            char.rotation[1] = 0
            if cursor.snapping:
                if char.move.x == 0 and char.move.y == 0 and char.heading == 0:
                    round_node_pos_hpr(model.node, cursor.move_snap, cursor.rot_snap)


@Component()
class Creator:
    # What model to place.
    tileset: dict = None
    collection: str = field(default_factory="")
    tile_name: str = field(default_factory="")
    tile: NodePath = None

    rebuild: bool = True    # Reload current model.
    place: bool = False     # Drop the entity on the field.
    max_cooldown: int = 10   # Time it takes before another entity can be placed.
    cooldown: int = 0       # Subtract 'till 0, then allow placement.


class Create(System):
    entity_filters = {
        'creator' : and_filter([
            Creator,
            Model,
        ]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['creator']:
            creator = entity[Creator]
            model = entity[Model]
            if creator.rebuild:
                #TODO: if creator.tile: creator.tile.destroy()
                creator.tile = NodePath("currently selected tile")
                creator.tileset[creator.collection][creator.tile_name].copy_to(creator.tile)
                creator.tile.reparent_to(model.node)

            if creator.cooldown > 0:
                creator.cooldown -= 1
            else:
                if creator.place and creator.tile:
                    np = creator.tile.copy_to(render)
                    np.set_pos(model.node.get_pos())
                    np.set_hpr(model.node.get_hpr())
                    if CursorMovement in entity:
                        cursor = entity[CursorMovement]
                        if cursor.snapping:
                            round_node_pos_hpr(np, cursor.move_snap, cursor.rot_snap)

                    creator.place = False
                    creator.built = None
                    creator.cooldown = creator.max_cooldown

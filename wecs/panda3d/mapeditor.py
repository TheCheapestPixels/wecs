import wecs.panda3d
import cefconsole
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
    place: bool = False     # Drop the entity on the field.
    max_cooldown: int = 10  # Time it takes before another entity can be placed.
    cooldown: int = 0       # Subtract 'till 0, then allow placement.
    current_tile: NodePath = field(default_factory=lambda:NodePath("selected"))


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
            console = base.ecs_world.get_system(UpdateMapEditorSubconsole).subconsole
            if console.rebuild:
                if creator.current_tile.getNumChildren() > 0:
                    creator.current_tile.get_child(0).remove_node()
                tileset = console.tilesets[console.tileset]
                collection = tileset[console.collection]
                tile = collection[console.tile]
                tile.copy_to(creator.current_tile)
                creator.current_tile.reparent_to(model.node)
            if creator.cooldown > 0:
                creator.cooldown -= 1
            else:
                if creator.place and creator.tile:
                    np = creator.current_tile.copy_to(render)
                    np.set_pos(model.node.get_pos())
                    np.set_hpr(model.node.get_hpr())
                    if CursorMovement in entity:
                        cursor = entity[CursorMovement]
                        if cursor.snapping:
                            round_node_pos_hpr(np, cursor.move_snap, cursor.rot_snap)

                    creator.place = False
                    creator.built = None
                    creator.cooldown = creator.max_cooldown


## GUI stuff
class MapEditorSubconsole(cefconsole.Subconsole):
    name = "map editor"
    package = 'wecs'
    template_dir = 'templates'
    html = "mapeditor.html"
    funcs = {
        "load_tileset": "load_tileset",
        "update_tile": "update_tile",
    }

    tilesets = {}
    tileset = ""
    collection = ""
    tile = ""
    rebuild = False

    def load_tileset(self, filename, debug=False):
        # Load and store new tileset
        tileset_model = loader.loadModel(filename)
        tileset_name = tileset_model.name
        tileset = {}
        for tile_collection in tileset_model.find_all_matches("**/=wecs_tiles"):
            if debug: print('tileset "{}"'.format(tile_collection.name))
            tileset[tile_collection.name] = {}
            for tile in tile_collection.get_children():
                if debug: print('  tile "{}"'.format(tile.name))
                tile.set_pos(0,0,0)
                tileset[tile_collection.name][tile.name] = tile
        self.tilesets[tileset_name] = tileset

        # Make and send overview of tilesets, collections and tiles to js.
        tilesets = {}
        for tileset in self.tilesets:
            tilesets[tileset] = {}
            for collection in self.tilesets[tileset]:
                # Individual tiles have to be dictionaries too,
                # or they'll show up as numbers
                tilesets[tileset][collection] = {}
                for tile in self.tilesets[tileset][collection]:
                    tilesets[tileset][collection][tile] = 0
        self.console.exec_js_func("tileman.load_tilesets", tilesets)

    def update_tile(self, tileset, collection, tile):
        self.tileset = tileset
        self.collection = collection
        self.tile = tile
        self.rebuild = True


class UpdateMapEditorSubconsole(System):
    entity_filters = {
        'creator': and_filter([Creator]),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subconsole = MapEditorSubconsole()
        base.console.add_subconsole(self.subconsole)

    def update(self, entities_by_filter):
        for entity in entities_by_filter["creator"]:
            creator = entity[Creator]
            creator.tileset = self.subconsole.tileset
            creator.collection = self.subconsole.collection
            creator.tile = self.subconsole.tile
            creator.rebuild = self.subconsole.rebuild

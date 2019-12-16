import wecs.panda3d
import cefconsole
from dataclasses import field

from panda3d.core import NodePath

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.core import UID

from .model import Model
from .character import CharacterController
from .character import CursorMovement
from .helpers import snap_vector


@Component()
class Creator:              # An entity that places models in the scene
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

    def rebuild_cursor(self, entity):
        creator = entity[Creator]
        model = entity[Model]
        console = base.ecs_world.get_system(UpdateMapEditorSubconsole).subconsole
        while creator.current_tile.getNumChildren() > 0:
            creator.current_tile.get_child(0).remove_node()
        tileset = console.tilesets[console.tileset]
        collection = tileset[console.collection]
        tile = collection[console.tile]
        tile.copy_to(creator.current_tile)
        creator.current_tile.reparent_to(model.node)
        console.fresh_tile = False

    def place_tile(self, entity):
        creator = entity[Creator]
        model = entity[Model]
        np = creator.current_tile.copy_to(render)
        np.set_pos(model.node.get_pos())
        np.set_hpr(model.node.get_hpr())
        if CursorMovement in entity:
            cursor = entity[CursorMovement]
            if cursor.snapping:
                np.set_pos(snap_vector(np.get_pos(), cursor.move_snap))
                np.set_hpr(snap_vector(np.get_hpr(), cursor.rot_snap))
        creator.place = False
        creator.built = None
        creator.cooldown = creator.max_cooldown

    def update(self, entities_by_filter):
        for entity in entities_by_filter['creator']:
            console = base.ecs_world.get_system(UpdateMapEditorSubconsole).subconsole
            if console.fresh_tile:
                self.rebuild_cursor(entity)
            creator = entity[Creator]
            if creator.cooldown > 0:
                creator.cooldown -= 1
            else:
                if creator.place:
                    self.place_tile(entity)


## map editor subconsole
class MapEditorSubconsole(cefconsole.Subconsole):
    name = "map editor"
    package = 'wecs'
    template_dir = 'templates'
    html = "mapeditor.html"
    funcs = {
        "load_tileset": "load_tileset",
        "update_tile": "update_tile",
    }
    # Last data recieved from js
    tilesets = {}
    tileset = ""
    collection = ""
    tile = ""
    fresh_tile = False

    def update_tile(self, tileset, collection, tile):
        # JS passes these arguments
        self.tileset = tileset
        self.collection = collection
        self.tile = tile
        self.fresh_tile = True

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
                # or they'll show up in selection as numbers?
                tilesets[tileset][collection] = {}
                for tile in self.tilesets[tileset][collection]:
                    tilesets[tileset][collection][tile] = 0
        self.console.exec_js_func("tileman.load_tilesets", tilesets)


# HEADSUP: All this does is instantiate a subconsole once.
class UpdateMapEditorSubconsole(System):
    entity_filters = {
        'creator': and_filter([Creator]),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subconsole = MapEditorSubconsole()
        base.console.add_subconsole(self.subconsole)

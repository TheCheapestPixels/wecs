import wecs.panda3d
import cefconsole
from dataclasses import field
from collections import defaultdict

from panda3d.core import NodePath
from panda3d.core import Vec3

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.core import UID

from .model import Model
from .character import CharacterController
from .character import CursorMovement
from .helpers import snap_vector


class Chunk(): # A chunk of the map to add tiles to.
    def __init__(self):
        self.node = NodePath("chunk")
        self.cells = defaultdict(list)
        self.geometry = None

    def make_tile(self, pos, tile):
        if self.geometry:
            to_make = self.geometry[tile[0]]
            tile_node = NodePath(to_make.name)
            to_make.copy_to(tile_node)
            tile_node.set_pos(Vec3(pos)+tuple(tile[1]))
            tile_node.set_hpr(tuple(tile[2]))
            tile_node.reparent_to(self.node)

    def flatten(self):
        if self.node:
            if self.node.get_num_children() > 0:
                self.node.flatten_strong()

    def add_tile(self, pos, tile):
        cell = self.cells[pos]
        if not tile in cell:
            cell.append(tile)
            self.make_tile(pos, tile)
            self.flatten()

    def remove_tile(self, pos, tile):
        cell = self.cells[pos]
        if tile in cell:
            cell.remove(tile)
            self.rebuild()

    def destroy(self):
        self.node.remove_node()
        self.node = None

    def rebuild(self):
        self.destroy()
        self.node = NodePath("chunk")
        for cell in self.cells:
            for tile in self.cells[cell]:
                self.make_tile(cell, tile)
        self.flatten()


@Component()
class Tilemap:
    chunks: defaultdict = field(default_factory=lambda:defaultdict(Chunk))
    chunksize: int = 64
    property_index: int = 0
    tile_properties: list = field(default_factory=list)
    geometry: list = field(default_factory=list)
    save: str = ""
    export: str = ""


@Component()
class Creator:              # An entity that places models in the scene
    place: bool = False     # Drop the entity on the field.
    max_cooldown: int = 10  # Time it takes before another entity can be placed.
    cooldown: int = 0       # Subtract 'till 0, then allow placement.
    current_tile: NodePath = field(default_factory=lambda:NodePath("selected"))


class MapEditorSubconsole(cefconsole.Subconsole):
    name = "map editor"
    package = 'wecs'
    template_dir = 'templates'
    html = "mapeditor.html"
    funcs = {
        "load_tileset": "load_tileset",
        "update_tile": "update_tile",
    }
    # data recieved from js
    tilesets = {}
    tile_property = {
        "tileset" : "",
        "collection" : "",
        "name": "",
        "colors": [],
    }
    fresh_tile = False
    original_tiles = [] # Actual geometry

    def update_tile(self, tileset, collection, name):
        # JS passes these arguments
        self.tile_property = {
            "tileset" : tileset,
            "collection" : collection,
            "name" : name,
            "colors" : [],
        }
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
                tile.set_hpr(0,0,0)
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


def geometry_from_property(tilesets, property):
    geometry_node = tilesets[property["tileset"]][property["collection"]][property["name"]]
    new_geometry = NodePath(property["name"])
    geometry_node.copy_to(new_geometry)
    for c, child in enumerate(new_geometry.get_children()):
        if c < len(property["colors"]):
            child.setColor(tuple(property["colors"][c]))
    return new_geometry


class UpdateMapEditor(System):
    entity_filters = {
        'creator': and_filter([Creator, Model]),
        'tilemap': and_filter([Tilemap, Model]),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subconsole = MapEditorSubconsole()
        base.console.add_subconsole(self.subconsole)

    def update_to_tilemap(self, creator_entity, tilemap_entity):
        console = self.subconsole
        creator = creator_entity[Creator]
        model = creator_entity[Model]
        tilemap = tilemap_entity[Tilemap]

        def get_property_index():
            if self.subconsole.tile_property in tilemap.tile_properties:
                property_index = tilemap.tile_properties.index(self.subconsole.tile_property)
            else:
                property = self.subconsole.tile_property
                new_geometry = geometry_from_property(
                    self.subconsole.tilesets, property)
                tilemap.geometry.append(new_geometry)
                tilemap.tile_properties.append(self.subconsole.tile_property)
                property_index = len(tilemap.tile_properties)-1
            return property_index

        def split_translation():
            snapped = False
            cellsize = 1
            if CursorMovement in creator_entity:
                cursor = creator_entity[CursorMovement]
                if cursor.snapping:
                    snapped = True
                    cellsize = cursor.move_snap
            hpr = model.node.get_hpr()
            x, y, z = pos = model.node.get_pos()
            offset = (x%cellsize, y%cellsize, z%cellsize)
            pos = (
                int(x/cellsize)*cellsize,
                int(y/cellsize)*cellsize,
                int(z/cellsize)*cellsize
            )
            if snapped:
                offset = (0,0,0)
                hpr = snap_vector(hpr, cursor.rot_snap)
            return pos, offset, hpr

        def grab_chunk(pos):
            chunksize = tilemap.chunksize
            chunk = tilemap.chunks[(
                int(pos[0]/chunksize),
                int(pos[1]/chunksize),
                int(pos[2]/chunksize))]
            return chunk

        if creator.place:
            # Creator position to tile position
            pos, offset, hpr = split_translation()
            # Get the chunk responsible for this position
            chunk = grab_chunk(pos)
            # Make sure the chunk has acces to loaded geometry
            chunk.geometry = tilemap.geometry
            # make the tile
            property_index = get_property_index()
            tile = (property_index, offset, hpr)
            # add it
            chunk.add_tile(pos, tile)
            chunk.node.reparent_to(render)
            # done
            creator.place = False
            creator.cooldown = creator.max_cooldown

    def update(self, entities_by_filter):
        for entity in entities_by_filter['creator']:
            creator = entity[Creator]
            if creator.cooldown > 0:
                creator.cooldown -= 1
            else:
                for tilemap_entity in entities_by_filter["tilemap"]:
                    self.update_to_tilemap(entity, tilemap_entity)

            # Refresh cursor representation if needed
            if self.subconsole.fresh_tile:
                creator = entity[Creator]
                model = entity[Model]
                while creator.current_tile.getNumChildren() > 0:
                    creator.current_tile.get_child(0).remove_node()
                new_geometry = geometry_from_property(
                    self.subconsole.tilesets, self.subconsole.tile_property)
                new_geometry.reparent_to(creator.current_tile)
                creator.current_tile.reparent_to(model.node)
                self.subconsole.fresh_tile = False

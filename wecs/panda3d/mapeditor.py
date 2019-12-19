import json
import wecs.panda3d
import cefconsole
from dataclasses import field
from collections import defaultdict

from panda3d.core import NodePath
from panda3d.core import Vec3

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter

from .model import Model
from .character import CursorMovement
from .helpers import snap_vector


def grab_chunk(chunks, pos, chunksize):
    x, y, z = pos
    return chunks[(int(x/chunksize), int(y/chunksize), int(z/chunksize))]

def geometry_from_property(tilesets, property):
    tileset = tilesets[property["tileset"]]
    collection = tileset[property["collection"]]
    geometry_node = collection[property["name"]]
    new_geometry = NodePath(property["name"])
    geometry_node.copy_to(new_geometry)
    for c, child in enumerate(new_geometry.get_children()):
        if c < len(property["colors"]):
            child.setColor(tuple(property["colors"][c]))
    return new_geometry

def split_translation(entity, at_node):
    cellsize = 1
    snapped = False
    if CursorMovement in entity:
        cursor = entity[CursorMovement]
        if cursor.snapping:
            cellsize = cursor.move_snap
            snapped = True

    x, y, z = pos = at_node.get_pos()
    s = cellsize
    pos = (int(x/s)*s, int(y/s)*s, int(z/s)*s)
    hpr = at_node.get_hpr()
    if snapped:
        offset = (0,0,0)
        hpr = snap_vector(hpr, cursor.rot_snap)
    else:
        offset = (x%s, y%s, z%s)
    return pos, offset, tuple(hpr)


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

    def remove_cell(self, pos):
        for tile in self.cells[pos]:
            self.cells[pos].remove(tile)
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


class MapEditorSubconsole(cefconsole.Subconsole):
    name = "map editor"
    package = 'wecs'
    template_dir = 'templates'
    html = "mapeditor.html"
    funcs = {
        "load_tileset": "load_tileset",
        "update_tile": "update_tile",
        "save_map": "save_map",
        "load_map": "load_map",
        "export_map": "export_map"
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
    save = load = export = None

    def save_map(self):
        self.save = "my_map"

    def load_map(self):
        self.load = "my_map"

    def export_map(self):
        self.export = "my_map"

    def update_tile(self, tileset, collection, name):
        # JS passes these arguments
        self.tile_property = {
            "tileset" : tileset,
            "collection" : collection,
            "name" : name,
            "colors" : [],
        }
        self.fresh_tile = True

    def clear_tilesets(self):
        for tileset in self.tilesets:
            for collection in self.tilesets[tileset]:
                for tile in self.tilesets[tileset][collection]:
                    self.tilesets[tileset][collection][tile].remove_node()
        self.tilesets = {}
        self.send_tilesets()

    def load_tileset(self, filename, debug=False):
        # Load and store new tileset
        tileset_model = loader.loadModel(filename)
        tileset = {}
        for tile_collection in tileset_model.find_all_matches("**/=wecs_tiles"):
            if debug: print('tileset "{}"'.format(tile_collection.name))
            tileset[tile_collection.name] = {}
            for tile in tile_collection.get_children():
                if debug: print('  tile "{}"'.format(tile.name))
                tile.set_pos(0,0,0)
                tile.set_hpr(0,0,0)
                tileset[tile_collection.name][tile.name] = tile
        self.tilesets[filename] = tileset
        self.send_tilesets()

    def send_tilesets(self):
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

    def get_property_index(self, tilemap):
        current_properties = self.tile_property
        previous_properties = tilemap.tile_properties
        if current_properties in previous_properties:
            property_index = previous_properties.index(current_properties)
        else:
            property = current_properties
            new_geometry = geometry_from_property(
                self.tilesets, property)
            tilemap.geometry.append(new_geometry)
            previous_properties.append(current_properties)
            property_index = len(previous_properties)-1
        return property_index


@Component()
class Tilemap:
    chunks: defaultdict = field(default_factory=lambda:defaultdict(Chunk))
    chunksize: int = 64
    tile_properties: list = field(default_factory=list)
    geometry: list = field(default_factory=list)
    save: str = ""
    export: str = ""


@Component()
class Creator:              # An entity that places models in the scene
    place: bool = False     # Drop the entity on the field.
    remove: bool = False    # Delete the entity from the field
    clear: bool = False     # Clear a cell of entities from the field
    copy: bool = False      # Copy current tile
    max_cooldown: int = 5   # Time it takes before another action can be taken
    cooldown: int = 0       # Subtract 'till 0, then allow edit
    current_tile: NodePath = field(default_factory=lambda:NodePath("selected"))


class UpdateMapEditor(System):
    entity_filters = {
        'creator': and_filter([Creator, Model]),
        'tilemap': and_filter([Tilemap, Model]),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subconsole = MapEditorSubconsole()
        base.console.add_subconsole(self.subconsole)

    def update(self, entities_by_filter):
        for creator_entity in entities_by_filter['creator']:
            creator = creator_entity[Creator]
            for tilemap_entity in entities_by_filter["tilemap"]:
                if creator.cooldown > 0:
                    creator.cooldown -= 1
                else:
                    if not self.subconsole.tile_property["name"] == "":
                        self.edit_map(creator_entity, tilemap_entity)
                self.manage_files(tilemap_entity)
            # Refresh cursor representation if needed
            if self.subconsole.fresh_tile:
                creator = creator_entity[Creator]
                model = creator_entity[Model]
                while creator.current_tile.getNumChildren() > 0:
                    creator.current_tile.get_child(0).remove_node()
                new_geometry = geometry_from_property(
                    self.subconsole.tilesets, self.subconsole.tile_property)
                new_geometry.reparent_to(creator.current_tile)
                creator.current_tile.reparent_to(model.node)
                self.subconsole.fresh_tile = False

    def manage_files(self, tilemap_entity):
        tilemap = tilemap_entity[Tilemap]
        chunks = tilemap.chunks
        properties = tilemap.tile_properties
        if self.subconsole.save:
            self.save_map(self.subconsole.save, chunks, properties)
            self.subconsole.save = None
        elif self.subconsole.load:
            data = self.load_map(self.subconsole.load)
            if data:
                self.destroy(tilemap)
                tilemap.chunks = data[0]
                tilemap.tile_properties = data[1]
                tilemap.geometry = data[2]
            self.subconsole.load = None
        elif self.subconsole.export:
            self.export_map(self.subconsole.export, chunks)
            self.subconsole.export = None

    def destroy(self, tilemap):
        for pos in tilemap.chunks:
            chunk = tilemap.chunks[pos]
            chunk.destroy()

    def edit_map(self, creator_entity, tilemap_entity):
        creator = creator_entity[Creator]
        model = creator_entity[Model]
        tilemap = tilemap_entity[Tilemap]
        if creator.place or creator.remove or creator.clear:
            pos, offset, hpr = split_translation(creator_entity, model.node)
            # Get the chunk responsible for this position
            chunk = grab_chunk(tilemap.chunks, pos, tilemap.chunksize)
            # Make sure the chunk has acces to loaded geometry
            chunk.geometry = tilemap.geometry
            # get current index
            index = self.subconsole.get_property_index(tilemap)
            if creator.clear:
                chunk.remove_cell(pos)
            if creator.remove:
                chunk.remove_tile(pos, (index, offset, hpr))
            if creator.place:
                chunk.add_tile(pos, (index, offset, hpr))
            chunk.node.reparent_to(render)
            creator.place = creator.remove = creator.clear = False
            creator.cooldown = creator.max_cooldown

# File management

    def save_map(self, mapname, chunks, tile_properties):
        print("Saving map to {}.map".format(mapname))
        # make a ginormous list of tiles and their coordinates
        tiles = []
        for chunk_pos in chunks:
            chunk = chunks[chunk_pos]
            for cell_pos in chunk.cells:
                cell = chunk.cells[cell_pos]
                for tile in cell:
                    tiles.append((cell_pos, tile))
        # make a list of tileset names
        tileset_filenames = []
        for key in self.subconsole.tilesets:
            tileset_filenames.append(key)
        # and write them out
        json_data = {
            "tileset_filenames" : tileset_filenames,
            "tile_properties": tile_properties,
            "tiles" : tiles,
        }
        with open("{}.map".format(mapname), 'w') as f:
            json.dump(json_data, f)

    def load_map(self, filename):
        print("Loading {}.map".format(filename))
        json_data = json.load(open("{}.map".format(filename), 'r'))
        tileset_filenames = json_data["tileset_filenames"]
        tile_properties = json_data["tile_properties"]
        tiles = json_data["tiles"]

        # Load tilesets
        for filename in tileset_filenames:
            self.subconsole.clear_tilesets()
            self.subconsole.load_tileset(filename)

        # Rebuild all unique tiles in properties
        geometry = []
        for property in tile_properties:
            geometry.append(geometry_from_property(self.subconsole.tilesets, property))

        # Add all tiles to the chunks
        print("Rebuilding {} tiles. Hold on!".format(len(tiles)))
        chunks = defaultdict(Chunk)
        chunksize = 64
        for t, tile in enumerate(tiles):
            pos = tuple(tile[0])
            tile = tuple(tile[1])
            chunk = grab_chunk(chunks, pos, chunksize)
            chunk.geometry = geometry
            chunk.add_tile(pos, tile)
        for chunk in chunks:
            chunks[chunk].node.reparent_to(render)
        return chunks, tile_properties, geometry

    def export_map(self, mapname, chunks):
        print("Exporting as {}.bam".format(mapname))
        newbam = NodePath(mapname)
        for chunk_pos in chunks:
            chunk = chunks[chunk_pos]
            chunk.node.copy_to(newbam)
        newbam.writeBamFile("{}.bam".format(mapname))

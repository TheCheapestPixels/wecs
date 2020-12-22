from dataclasses import field

from panda3d import core as p3d
from panda3d.core import NodePath
from panda3d.core import Point3
from panda3d.core import Vec3
from panda3d.core import CollisionSphere
from panda3d.core import OrthographicLens

# from wecs import cefconsole
import wecs
from wecs.core import NoSuchUID
from wecs.core import ProxyType
from wecs.aspects import Aspect
from wecs.aspects import factory
# from wecs.panda3d import debug

from wecs.panda3d.constants import FALLING_MASK
from wecs.panda3d.constants import BUMPING_MASK
from wecs.panda3d.constants import CAMERA_MASK


# Break this out into something of its own

from wecs.panda3d.ai import BehaviorAI
from wecs.panda3d.character import CharacterController
from wecs.core import System, Component
from wecs.core import Proxy
from wecs.panda3d.camera import Camera
from wecs.panda3d.input import Input
from wecs.panda3d.mouseover import MouseOverable
from wecs.panda3d.mouseover import MouseOverableGeometry
from wecs.panda3d.mouseover import MouseOveringCamera
from wecs.panda3d.mouseover import UserInterface
from wecs.panda3d.mouseover import Pointable
from wecs.panda3d.mouseover import Targetable
from wecs.panda3d.mouseover import Selectable


lens = OrthographicLens()
lens.setFilmSize(4, 4)  # Or whatever is appropriate for your scene
base.cam.node().setLens(lens)


@Component()
class Inventory:
    node: NodePath = field(default_factory=NodePath)
    items: list = field(default_factory=list)
    dirty: bool = False


@Component()
class Takeable:
    pass


class Take(System):
    entity_filters = {
        'cursor': [Input, MouseOveringCamera, UserInterface, Inventory],
    }
    proxies = {
        'model': ProxyType(wecs.panda3d.prototype.Model, 'node'),
    }
    input_context = 'interface'
    
    def update(self, entities_by_filter):
        for entity in entities_by_filter['cursor']:
            input = entity[Input]
            # Can the player currently take?
            if self.input_context in input.contexts:
                context = base.device_listener.read_context(self.input_context)
                # Does he take?
                if context.get('take', False):
                    ui = entity[UserInterface]
                    target = ui.targeted_entity
                    # Does he point at a targetable entity?
                    if target is not None:
                        target_entity = self.world.get_entity(target)
                        # Can it be taken?
                        if Takeable in target_entity:
                            # Then take it.
                            self.take(entity, target_entity)

    def take(self, entity, target_entity):
        item_node = self.proxies['model'].field(target_entity)
        item_node.detach_node()  # TODO: Reattach to inventory
        del entity[Takeable]
        entity[Inventory].items.append(target_entity._uid)
        entity[Inventory].dirty = True
        print(entity[Inventory].items)


from panda3d.core import CardMaker


INVENTORY_DISPLAY_REGION_SORT = 100
INVENTORY_VERTICAL_FRACTION = 0.2
INVENTORY_HORIZONTAL_FACTOR = 6


class DisplayInventory(System):
    entity_filters = {
        'inventory': [Inventory, Camera],
    }

    def __init__(self):
        super().__init__()

        x = float(base.win.get_x_size())
        y = float(base.win.get_y_size())
        y_aspect = y / x
        inventory_base_width = INVENTORY_VERTICAL_FRACTION * y_aspect
        inventory_half_width = inventory_base_width * INVENTORY_HORIZONTAL_FACTOR * 0.5
        
        self.region = base.win.make_display_region(
            0.5 - inventory_half_width,  # left
            0.5 + inventory_half_width,  # right
            0.0,  # bottom
            INVENTORY_VERTICAL_FRACTION,  # top
        )
        self.region.set_sort(INVENTORY_DISPLAY_REGION_SORT)

        self.cam_node = p3d.Camera('inventory_cam')
        lens = OrthographicLens()
        lens.set_film_size(INVENTORY_HORIZONTAL_FACTOR, 1)
        self.cam_node.set_lens(lens)
        self.cam_np = NodePath(self.cam_node)
        self.region.set_camera(self.cam_np)

        self.inventory = NodePath('inventory')
        self.cam_np.reparentTo(self.inventory)

        background_maker = CardMaker('inventory')
        background_maker.set_frame(-INVENTORY_HORIZONTAL_FACTOR / 2.0, INVENTORY_HORIZONTAL_FACTOR / 2.0, 0, 1)
        background = p3d.NodePath(background_maker.generate())
        background.reparent_to(self.inventory)
        background.set_pos(0, 5, -0.5)

        # for x in range(0, INVENTORY_HORIZONTAL_FACTOR):
        #     m = base.loader.load_model("models/jack")
        #     m.reparent_to(self.inventory)
        #     m.set_pos(x - INVENTORY_HORIZONTAL_FACTOR / 2.0 + 0.5, 4, 0)
        #     m.set_scale(0.5)

    def enter_filter_inventory(self, entity):
        inventory = entity[Inventory]
        camera = entity[Camera]
        
        #inventory.node.reparent_to(camera.node)

                
system_types = [
    # Set up newly added models/camera, tear down removed ones
    wecs.panda3d.prototype.ManageModels,
    wecs.panda3d.camera.PrepareCameras,
    # Interface interactions
    wecs.panda3d.mouseover.MouseOverOnEntity,
    wecs.panda3d.mouseover.UpdateMouseOverUI,
    Take,
    DisplayInventory,
    # Debug keys (`escape` to close, etc.)
    wecs.panda3d.debug.DebugTools,
]


scenery = Aspect(
    [
        wecs.panda3d.prototype.Model,
        wecs.panda3d.prototype.Geometry,
        wecs.panda3d.mouseover.MouseOverableGeometry,
        wecs.panda3d.mouseover.Targetable,
        Takeable,
     ],
)


scenery.add(
    base.ecs_world.create_entity(name="Ball 1"),
    overrides={
        wecs.panda3d.prototype.Model: dict(
            post_attach=lambda: wecs.panda3d.prototype.transform(
                pos=Vec3(-1, 0, 1),
            ),
        ),
        wecs.panda3d.prototype.Geometry: dict(file='models/smiley'),
    },
)


scenery.add(
    base.ecs_world.create_entity(name="Ball 2"),
    overrides={
        wecs.panda3d.prototype.Model: dict(
            post_attach=lambda: wecs.panda3d.prototype.transform(
                pos=Vec3(1, 10, -1),
            ),
        ),
        wecs.panda3d.prototype.Geometry: dict(file='models/smiley'),
    },
)


viewer = Aspect(
    [
        wecs.panda3d.prototype.Model,
        wecs.panda3d.camera.Camera,
        wecs.panda3d.camera.MountedCameraMode,
        wecs.panda3d.input.Input,
        wecs.panda3d.mouseover.MouseOveringCamera,
        wecs.panda3d.mouseover.UserInterface,
        Inventory,
    ],
    overrides={
        wecs.panda3d.prototype.Model: dict(
            post_attach=lambda: wecs.panda3d.prototype.transform(
                pos=Vec3(0, -10, 0),
            ),
        ),
        wecs.panda3d.input.Input: dict(
            contexts={
                'mouse_over',
                'interface',
            },
        ),
    },
)


viewer.add(base.ecs_world.create_entity(name="Viewer"))

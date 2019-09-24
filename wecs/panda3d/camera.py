from panda3d.core import NodePath

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter

from .model import Model


@Component()
class FirstPersonCamera:
    camera: NodePath
    anchor_name: str = None


# TODO:
#   Rotate-around-character support
#   Adjust distance so that the near plane is in front of level geometry
@Component()
class ThirdPersonCamera:
    camera: NodePath
    distance: float = 10.0
    height: float = 3.0
    focus_height: float = 2.0
    dirty: bool = True


class UpdateCameras(System):
    entity_filters = {
        '1stPerson': and_filter([
            FirstPersonCamera,
            Model,
        ]),
        '3rdPerson': and_filter([
            ThirdPersonCamera,
            Model,
        ]),
    }

    def init_entity(self, filter_name, entity):
        model = entity[Model]
        if filter_name == '1stPerson':
            camera = entity[FirstPersonCamera]
            if camera.anchor_name is None:
                camera.camera.reparent_to(model.node)
            else:
                camera.camera.reparent_to(model.node.find(camera.anchor_name))
            camera.camera.set_pos(0, 0, 0)
            camera.camera.set_hpr(0, 0, 0)
        elif filter_name == '3rdPerson':
            camera = entity[ThirdPersonCamera]
            camera.camera.reparent_to(model.node)
            camera.camera.set_pos(0, -camera.distance, camera.height)
            camera.camera.look_at(0, 0, camera.focus_height)

    def update(self, entities_by_filter):
        # If the camera needs to move relative to the model,
        # put the code for the here.
        # for entity in entities_by_filter['camType']:
        pass

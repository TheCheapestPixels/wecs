from dataclasses import field
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
#   Adjust distance so that the near plane is in front of level geometry
@Component()
class ThirdPersonCamera:
    camera: NodePath
    pivot: NodePath = field(default_factory=lambda:NodePath("camfocus"))
    pivot_height: float = 2
    distance: float = 10.0
    dirty: bool = True


class UpdateCameras(System):
    entity_filters = {
        '1stPerson': and_filter([
            FirstPersonCamera,
            Model,
        ]),
        '3rdPerson': and_filter([
            ThirdPersonCamera,
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
            camera.pivot.reparentTo(model.node)
            camera.pivot.set_z(camera.pivot_height)
            camera.camera.reparent_to(camera.pivot)
            camera.camera.set_pos(0, -camera.distance, 0)
            camera.camera.look_at(camera.pivot)

    def update(self, entities_by_filter):
        pass

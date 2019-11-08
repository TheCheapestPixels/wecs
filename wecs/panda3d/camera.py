from dataclasses import field
from panda3d.core import NodePath

from panda3d.core import CollisionTraverser
from panda3d.core import CollisionHandlerQueue
from panda3d.core import CollisionHandlerPusher
from panda3d.core import CollisionNode
from panda3d.core import CollisionSegment

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter

from .model import Model
from .model import Clock


@Component()
class FirstPersonCamera:
    camera: NodePath = field(default_factory=lambda:base.camera)
    anchor_name: str = None


@Component()
class ThirdPersonCamera:
    camera: NodePath = field(default_factory=lambda:base.camera)
    height: float = 2.0
    distance: float = 10.0
    focus_height: float = 1.8


@Component()
class TurntableCamera:
    turning_speed: float = 60.0
    heading: float = 0
    pitch: float = 0
    min_pitch: float = -80.0
    max_pitch: float = 45.0
    pivot: NodePath = field(default_factory=lambda:NodePath("camera pivot"))
    attached: bool = False


@Component()
class CollisionZoom:
    collision: CollisionNode = field(default_factory=lambda:CollisionNode("cam collisions"))
    traverser: CollisionTraverser = field(default_factory=lambda:CollisionTraverser("cam traverser"))
    queue: CollisionHandlerQueue = field(default_factory=lambda:CollisionHandlerQueue())
    body_width: float = 0.5


class UpdateCameras(System):
    entity_filters = {
        '3rdPerson': and_filter([
            ThirdPersonCamera,
            Model,
        ]),
        '1stPerson': and_filter([
            FirstPersonCamera,
            Model,
        ]),
        'turntable': and_filter([
            TurntableCamera,
            Model,
            ThirdPersonCamera,
            Clock,
        ]),
    }

    def init_entity(self, filter_name, entity):
        model = entity[Model]
        if filter_name == "1stPerson":
            camera = entity[FirstPersonCamera]
            if camera.anchor_name is None:
                camera.camera.reparent_to(model.node)
            else:
                camera.camera.reparent_to(model.node.find(camera.anchor_name))
            camera.camera.set_pos(0, 0, 0)
            camera.camera.set_hpr(0, 0, 0)
        elif filter_name == '3rdPerson':
            camera = entity[ThirdPersonCamera]
            if TurntableCamera in entity:
                if not entity[TurntableCamera].attached:
                    self.attach_turntable(entity)
            else:
                camera.camera.reparent_to(model.node)
                camera.camera.set_pos(0, -camera.distance, camera.height)
                camera.camera.look_at(0, 0, camera.focus_height)
        elif filter_name == 'turntable':
            if not entity[TurntableCamera].attached:
                self.attach_turntable(entity)

    def attach_turntable(self, entity):
        turntable = entity[TurntableCamera]
        model = entity[Model]
        camera = entity[ThirdPersonCamera]

        turntable.pivot.reparent_to(model.node)
        camera.camera.reparent_to(turntable.pivot)
        turntable.attached = True

    def update(self, entities_by_filter):
        for entity in entities_by_filter["3rdPerson"]:
            if TurntableCamera in entity and Clock in entity:
                model = entity[Model]
                turntable = entity[TurntableCamera]
                camera = entity[ThirdPersonCamera]
                dt = entity[Clock].timestep

                pivot = turntable.pivot
                pivot.set_pos(0, 0, camera.focus_height)
                camera.camera.set_pos(0, -camera.distance, 0)
                camera.camera.look_at(turntable.pivot)

                # Rotate pivot
                max_angle = turntable.turning_speed * dt
                heading_angle = turntable.heading * max_angle
                pivot.set_h(pivot.get_h() + heading_angle)
                pitch_angle = turntable.pitch * max_angle
                new_pitch = pivot.get_p() + pitch_angle
                new_pitch = max(new_pitch, turntable.min_pitch)
                new_pitch = min(new_pitch, turntable.max_pitch)
                pivot.set_p(new_pitch)


class CollideCamerasWithTerrain(System):
    entity_filters = {
        'camera': and_filter([
            ThirdPersonCamera,
            CollisionZoom,
        ])
    }

    def init_entity(self, filter_name, entity):
        camera = entity[ThirdPersonCamera]
        camera_col = entity[CollisionZoom]
        w = camera_col.body_width/2
        segs = ((0,0,w), (0,0,-w), (w,0,0), (-w,0,0))
        for seg in segs:
            segment = CollisionSegment(seg,(0,-camera.distance,0))
            camera_col.collision.addSolid(segment)
        camera_col.collision.set_into_collide_mask(0)
        cn = camera.camera.parent.attachNewNode(camera_col.collision)
        camera_col.traverser.addCollider(cn, camera_col.queue)

    def update(self, entities_by_filter):
        for entity in entities_by_filter["camera"]:
            camera = entity[ThirdPersonCamera]
            camera_col = entity[CollisionZoom]
            camera_col.traverser.traverse(render)
            entries = list(camera_col.queue.entries)
            if len(entries) > 0:
                hit_pos = entries[0].get_surface_point(camera.camera.parent)
                camera.camera.set_pos(hit_pos)
            else:
                camera.camera.set_pos(0, -camera.distance, 0)

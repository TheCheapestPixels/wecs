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


@Component()
class FirstPersonCamera:
    camera: NodePath
    anchor_name: str = None


@Component()
class ThirdPersonCamera:
    camera: NodePath
    distance: float = 10.0
    focus_height: float = 1.6


@Component()
class TurntableCamera:
    heading : float = 0
    pitch : float = 0
    view_axis_allignment : float = 0
    pivot: NodePath = field(default_factory=lambda:NodePath("camera pivot"))


@Component()
class CameraCollision:
    collision: CollisionNode = field(default_factory=lambda:CollisionNode("cam collisions"))
    traverser: CollisionTraverser = field(default_factory=lambda:CollisionTraverser("cam traverser"))
    queue: CollisionHandlerQueue = field(default_factory=lambda:CollisionHandlerQueue())
    body_width: float = 0.5


class UpdateCameras(System):
    entity_filters = {
        '3rdPerson' : and_filter([
            ThirdPersonCamera,
            Model

        ]),
        '1stPerson' : and_filter([
            FirstPersonCamera,
            Model
        ])
    }

    def init_entity(self, filter_name, entity):
        if filter_name == "3rdPerson":
            if TurntableCamera in entity:
                camera = entity[ThirdPersonCamera]
                turntable = entity[TurntableCamera]
                turntable.pivot.reparent_to(render)
                turntable.pivot.set_z(camera.focus_height)
                camera.camera.reparent_to(turntable.pivot)
                camera.camera.set_pos(0, -camera.distance, 0)
                camera.camera.look_at(turntable.pivot)
            else:
                camera.camera.reparent_to(entity[Model].node)
                camera.camera.look_at(camera.focus_height)
        elif filter_name == "1stPerson":
            camera.camera.reparent_to(entity[Model].node)


    def update(self, entities_by_filter):
        for entity in entities_by_filter["3rdPerson"]:
            model = entity[Model]
            if TurntableCamera in entity:
                camera = entity[TurntableCamera]
                pivot = entity[TurntableCamera].pivot
                pivot.set_pos(model.node.get_pos())
                pivot.set_z(pivot.get_z()+entity[ThirdPersonCamera].focus_height)
                pivot.set_h(pivot.get_h()+camera.heading)
                pivot.set_p(pivot.get_p()+camera.pitch)


class CameraCollisions(System):
    entity_filters = {
        'camera': and_filter([
            ThirdPersonCamera,
            CameraCollision,
        ])
    }

    def init_entity(self, filter_name, entity):
        camera = entity[ThirdPersonCamera]
        camera_col = entity[CameraCollision]
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
            camera_col = entity[CameraCollision]
            camera_col.traverser.traverse(render)
            entries = list(camera_col.queue.entries)
            if len(entries) > 0:
                hit_pos = entries[0].get_surface_point(camera.camera.parent)
                camera.camera.set_pos(hit_pos)
            else:
                camera.camera.set_pos(0, -camera.distance, 0)

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
    pivot: NodePath = field(default_factory=lambda:NodePath("cam pivot"))
    pivot_height: float = 1.6
    distance: float = 10.0
    body_width: float = 0.5


@Component()
class CameraCollision:
    collision: CollisionNode = field(default_factory=lambda:CollisionNode("cam collisions"))
    traverser: CollisionTraverser = field(default_factory=lambda:CollisionTraverser("cam traverser"))
    queue: CollisionHandlerQueue = field(default_factory=lambda:CollisionHandlerQueue())


class UpdateCameras(System):
    entity_filters = {
        '1stPerson': and_filter([
            FirstPersonCamera,
        ]),
        '3rdPerson': and_filter([
            ThirdPersonCamera,
        ]),
    }

    def init_entity(self, filter_name, entity):
        if filter_name == '3rdPerson':
            camera = entity[ThirdPersonCamera]
            camera.pivot.reparent_to(render)
            camera.pivot.set_z(camera.pivot_height)
            camera.camera.reparent_to(camera.pivot)
            camera.camera.set_pos(0, -camera.distance, 0)
            camera.camera.look_at(camera.pivot)


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
        w = camera.body_width/2
        segs = ((0,0,w), (0,0,-w), (w,0,0), (-w,0,0))
        for seg in segs:
            segment = CollisionSegment(seg,(0,-camera.distance,0))
            camera_col.collision.addSolid(segment)

        camera_col.collision.set_into_collide_mask(0)
        cn = camera.pivot.attachNewNode(camera_col.collision)
        camera_col.traverser.addCollider(cn, camera_col.queue)

    def update(self, entities_by_filter):
        for entity in entities_by_filter["camera"]:
            camera = entity[ThirdPersonCamera]
            camera_col = entity[CameraCollision]
            camera_col.traverser.traverse(render)
            entries = list(camera_col.queue.entries)
            if len(entries) > 0:
                hit_pos = entries[0].get_surface_point(camera.pivot)
                camera.camera.set_pos(hit_pos)
            else:
                camera.camera.set_pos(0, -camera.distance, 0)

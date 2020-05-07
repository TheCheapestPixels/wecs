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
from wecs.panda3d.input import Input

from .model import Model
from .model import Clock


@Component()
class Camera:
    camera: NodePath = field(default_factory=lambda:base.camera)
    pivot: NodePath = field(default_factory=lambda:NodePath("camera pivot"))


@Component()
class MountedCameraMode:
    anchor_name: str = None


@Component()
class ObjectCentricCameraMode:
    height: float = 2.0
    focus_height: float = 1.8
    distance: float = 10.0
    turning_speed: float = 60.0
    heading: float = 0
    pitch: float = 0
    min_pitch: float = -80.0
    max_pitch: float = 45.0


@Component()
class CollisionZoom:
    collision: CollisionNode = field(default_factory=lambda:CollisionNode("cam collisions"))
    traverser: CollisionTraverser = field(default_factory=lambda:CollisionTraverser("cam traverser"))
    queue: CollisionHandlerQueue = field(default_factory=lambda:CollisionHandlerQueue())
    body_width: float = 0.5


class PrepareCameras(System):
    entity_filters = {
        'camera': and_filter([
            Camera,
            Model,
        ]),
        'mount': and_filter([
            Camera,
            MountedCameraMode,
        ]),

        'center': and_filter([
            Camera,
            ObjectCentricCameraMode,
        ]),
    }

    def enter_filter_camera(self, entity):
        model = entity[Model]
        camera = entity[Camera]
        model = entity[Model]
        camera.pivot.reparent_to(model.node)
        camera.camera.reparent_to(camera.pivot)

    def enter_filter_mount(self, entity):
        model = entity[Model]
        camera = entity[Camera]
        camera.pivot.set_pos(0, 0, 0)
        camera.pivot.set_hpr(0, 0, 0)
        camera.camera.set_pos(0, 0, 0)
        camera.camera.set_hpr(0, 0, 0)

    def exit_filter_camera(self, entity):
        camera = entity[Camera]
        camera.pivot.detach_node()
        camera.camera.detach_node()

    def update(self, entities_by_filter):
        for entity in entities_by_filter['center']:
            center = entity[ObjectCentricCameraMode]
            center.heading = 0
            center.pitch = 0
            center.zoom = 0


class ResetMountedCamera(System):
    entity_filters = {
        'camera': and_filter([
            Camera,
            MountedCameraMode,
        ]),
    }

    def update(self, entities_by_filter):
        pass


class ReorientObjectCentricCamera(System):
    entity_filters = {
        'camera': and_filter([
            Camera,
            ObjectCentricCameraMode,
            Clock,
        ]),
        'input': and_filter([
            Camera,
            ObjectCentricCameraMode,
            Input,
        ]),
    }
    input_context = 'camera_movement'

    def update(self, entities_by_filter):
        for entity in entities_by_filter['input']:
            input = entity[Input]
            if self.input_context in input.contexts:
                context = base.device_listener.read_context(self.input_context)
                self.process_input(entity, context)

        for entity in entities_by_filter['camera']:
            model = entity[Model]
            camera = entity[Camera]
            center = entity[ObjectCentricCameraMode]
            dt = entity[Clock].timestep

            camera.pivot.set_pos(0, 0, center.focus_height)
            camera.camera.set_pos(0, -center.distance, 0)
            camera.camera.look_at(camera.pivot)

            max_angle = center.turning_speed * dt
            heading_angle = center.heading * max_angle
            camera.pivot.set_h(camera.pivot.get_h() + heading_angle)
            pitch_angle = center.pitch * max_angle
            new_pitch = camera.pivot.get_p() + pitch_angle
            new_pitch = max(new_pitch, center.min_pitch)
            new_pitch = min(new_pitch, center.max_pitch)
            camera.pivot.set_p(new_pitch)

    def process_input(self, entity, context):
        camera = entity[Camera]
        center = entity[ObjectCentricCameraMode]
        if context['rotation'] is not None:
            center.heading += -context['rotation'].x
            center.pitch += context['rotation'].y
        center.distance *= 1 + context['zoom'] * 0.01  # FIXME: Respect actual time!


class CollideCamerasWithTerrain(System):
    entity_filters = {
        'camera': and_filter([
            Camera,
            ObjectCentricCameraMode,
            CollisionZoom,
        ])
    }

    def enter_filter_camera(self, entity):
        camera = entity[Camera]
        center = entity[ObjectCentricCameraMode]
        zoom = entity[CollisionZoom]

        w = zoom.body_width / 2
        segs = ((0, 0, w), (0, 0, -w), (w, 0, 0), (-w, 0, 0))
        for seg in segs:
            segment = CollisionSegment(seg,(0, -center.distance, 0))
            zoom.collision.add_solid(segment)
        zoom.collision.set_into_collide_mask(0)
        cn = camera.camera.parent.attach_new_node(zoom.collision)
        zoom.traverser.add_collider(cn, zoom.queue)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['camera']:
            camera = entity[Camera]
            center = entity[ObjectCentricCameraMode]
            zoom = entity[CollisionZoom]

            zoom.traverser.traverse(render)
            entries = list(zoom.queue.entries)
            if len(entries) > 0:
                hit_pos = entries[0].get_surface_point(camera.camera.parent)
                camera.camera.set_pos(hit_pos)
            else:
                camera.camera.set_pos(0, -center.distance, 0)

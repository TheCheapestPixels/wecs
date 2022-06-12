"""
This mechanic deals with camera placement. Specifically, two modes are
supported:

* mounted mode: The camera is attached to a fixed point on a node,
* object-centric camera: The camera orbits around a point on a node, and
  can be made to zoom in on the node to avoid the camera being behind
  geometry.

The `Camera` consists of the actual camera node, and a 'pivot' that the
camera moves relative to. It is that 'pivot' that gets reparented to
the centered object, and rotated to move the camera around it.

Putting the camera mechanic into a mode is done by adding a
`MountedCameraMode` or `ObjectCentricCameraMode` component. The mounted
mode does currently not offer interactivity.

The object-centric mode can be steered programmatically by setting the
`heading`, `pitch`, and `zoom` fields between `PrepareCameras` and
`ReorientObjectCentricCamera`. If the entity also has an `Input`
component, the latter system will add user-requested camera movement to
those fields as well.

The functionality of all systems in detail:

* `PrepareCameras`: Attach / detach cameras.
  * `Camera` and 'model' proxy: On entry, attach the camera to the
    pivot, and the  pivot to the 'model' proxy's field (default:
    `Model.node`).
  * `Camera` and `MountedCameraMode`: On entry, reset the camera's and
    pivot's position and orientation to `0, 0, 0`.
  * `Camera` and `ObjectCentricCameraMode`: On update, reset the fields
    `heading`, `pitch`, and `zoom` of `ObjectCentricCamera` to 0.
* `ReorientObjectCentricCamera`: Update the camera mount
  * `Camera`, `ObjectCentricCamera`, and `Input`: On update, based on
    the player's input, set the mode's fields which control the camera's
    motion.
  * `Camera`, `ObjectCentricCamera`, and `Clock`: On update, adjust the
    camera's and pivot's position and orientation.
* `CollideCamerasWithTerrain`
  * `Camera`, `ObjectCentricCameraMode`, and `CollisionZoom`: If the
    camera is behind terrain, move it in front of it.
"""

from dataclasses import field
from panda3d.core import NodePath

from panda3d.core import CollisionTraverser
from panda3d.core import CollisionHandlerQueue
from panda3d.core import CollisionHandlerPusher
from panda3d.core import CollisionNode
from panda3d.core import CollisionSegment

from wecs.core import Component
from wecs.core import System
from wecs.core import Proxy
from wecs.core import ProxyType
from wecs.core import and_filter
from wecs.panda3d.input import Input
from wecs.panda3d.prototype import Model
from wecs.panda3d.prototype import Actor
from wecs.mechanics.clock import Clock

from wecs.panda3d.constants import CAMERA_MASK


@Component()
class Camera:
    """
    A camera mount (camera + pivot).

    :param:`fov`: Field of vision; The angle between the view axis and
        the left/right edge of the camera frustum.
    :param:`camera`: Camera, by default `base.camera`
    :param:`pivot`: The pivot node.
    """
    fov: float = 45.0
    camera: NodePath = field(default_factory=lambda: base.cam)
    pivot: NodePath = field(default_factory=lambda: NodePath("camera pivot"))


@Component()
class MountedCameraMode:
    """
    Puts a :class:`Camera` into mounted mode, meaning (for the moment)
    that it gets put at the object node's `0, 0, 0` position and
    orientation.
    """
    pass


@Component()
class ObjectCentricCameraMode:
    """
    Puts the :class:`Camera` into object-centric mode, meaning that it
    orbits around it.

    :param:`focus_height`: Height of the focal point above the model's
        origin.
    :param:`distance`: Distance between the camera and the focal point.
    :param:`turning_speed`: Maximum rotation speed of the pivot (degrees
         per second).
    :param:`heading`: Fraction of the `turning speed` to rotate 
        horizontally.
    :param:`pitch`:  Fraction of the `turning speed` to rotate 
        vertically.
    :param:`min_pitch`: Limit to looking down
    :param:`max_pitch`: Limit to looking up
    """
    focus_height: float = 1.8
    initial_pitch: float = 0.0
    distance: float = 10.0
    turning_speed: float = 60.0
    heading: float = 0
    pitch: float = 0
    min_pitch: float = -80.0
    max_pitch: float = 45.0


@Component()
class CollisionZoom:
    collision: CollisionNode = field(default_factory=lambda: CollisionNode("cam collisions"))
    mask: int = CAMERA_MASK
    traverser: CollisionTraverser = field(default_factory=lambda: CollisionTraverser("cam traverser"))
    queue: CollisionHandlerQueue = field(default_factory=lambda: CollisionHandlerQueue())
    body_width: float = 0.5


class PrepareCameras(System):
    """
    Add a `Camera` to an entity with the `'model`' proxy to attach a 
    camera to its node.

    Add `MountedCameraMode` or `ObjectCentricCameraMode` to specify how
    the camera should place itself. 
    """
    entity_filters = {
        'camera': and_filter([
            Camera,
            Proxy('model'),
        ]),
        'mount': and_filter([
            Camera,
            MountedCameraMode,
        ]),
        'mount_actor': and_filter([
            Camera,
            MountedCameraMode,
            Actor,
        ]),
        'center': and_filter([
            Camera,
            ObjectCentricCameraMode,
        ]),
    }
    proxies = {
        'model': ProxyType(Model, 'node'),
    }

    def enter_filter_camera(self, entity):
        model_node = self.proxies['model'].field(entity)
        camera = entity[Camera]

        camera.camera.reparent_to(camera.pivot)
        camera.pivot.reparent_to(model_node)
        camera.camera.node().get_lens().set_fov(camera.fov)

    def exit_filter_camera(self, entity):
        camera = entity[Camera]

        camera.pivot.detach_node()
        camera.camera.detach_node()

    def enter_filter_mount(self, entity):
        camera = entity[Camera]
        camera.pivot.set_pos(0, 0, 0)
        camera.pivot.set_hpr(0, 0, 0)
        camera.camera.set_pos(0, 0, 0)
        camera.camera.set_hpr(0, 0, 0)

    def enter_filter_mount_actor(self, entity):
        camera = entity[Camera]
        node = entity[Actor].node
        joint = node.expose_joint(None, 'modelRoot', 'camera')
        if joint:
            camera.pivot.set_pos((0, 0, 0))
            camera.pivot.reparent_to(joint)

    def exit_filter_mount(self, entity):
        model_proxy = self.proxies['model']
        model = entity[model_proxy.component_type]
        camera = entity[Camera]

    def enter_filter_center(self, entity):
        camera = entity[Camera]
        center = entity[ObjectCentricCameraMode]
        camera.pivot.set_p(center.initial_pitch)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['center']:
            center = entity[ObjectCentricCameraMode]

            center.heading = 0
            center.pitch = 0
            center.zoom = 0


class ReorientObjectCentricCamera(System):
    """
    For entities with an object-centric camera and `Input`, read the
    context specified in `self.input_context` (default:
    'camera_movement'), and process it (using `self.process_input()`),
    which modifies the mode's `heading`, `pitch`, and `distance` based
    on the context's `rotation` and `zoom`.

    For entities with an object-centric camera and `Clock`, apply the
    intended movement to the camera mount.
    """
    entity_filters = {
        'camera': and_filter([
            Clock,
            Camera,
            ObjectCentricCameraMode,
        ]),
        'input': and_filter([
            Input,
            Camera,
            ObjectCentricCameraMode,
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
        if 'rotation' in context and context['rotation'] is not None:
            center.heading += -context['rotation'].x
            center.pitch += context['rotation'].y


class ZoomObjectCentricCamera(System):
    entity_filters = {
        'camera': and_filter([
            Clock,
            Camera,
            ObjectCentricCameraMode,
        ]),
        'input': and_filter([
            Input,
            Camera,
            ObjectCentricCameraMode,
        ]),
    }
    input_context = 'camera_zoom'

    def update(self, entities_by_filter):
        for entity in entities_by_filter['input']:
            input = entity[Input]
            if self.input_context in input.contexts:
                context = base.device_listener.read_context(self.input_context)
                self.process_input(entity, context)

    def process_input(self, entity, context):
        camera = entity[Camera]
        center = entity[ObjectCentricCameraMode]
        center.distance *= 1 + context['zoom'] * 0.01  # FIXME: Respect actual time!


class CollideCamerasWithTerrain(System):
    """
    Put the `Camera` in front of any collidable geometry. 

    Specifically, four corners of a square (centered around the camera,
    coplanar with its view planes) are used as the starting points of
    collision segments 
    """
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
            segment = CollisionSegment(seg, (0, -center.distance, 0))
            zoom.collision.add_solid(segment)
        zoom.collision.set_from_collide_mask(zoom.mask)
        zoom.collision.set_into_collide_mask(0x0)
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

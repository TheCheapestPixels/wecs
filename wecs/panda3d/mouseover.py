from dataclasses import field

from panda3d.core import Vec3
from panda3d.core import NodePath
from panda3d.core import CollisionTraverser
from panda3d.core import CollisionHandlerQueue
from panda3d.core import CollisionRay
from panda3d.core import CollisionNode

import wecs

from wecs.core import System, Component
from wecs.core import Proxy
from wecs.core import ProxyType

from wecs.panda3d.prototype import Model
from wecs.panda3d.prototype import Geometry
from wecs.panda3d.camera import Camera
from wecs.panda3d.input import Input

from wecs.panda3d.constants import MOUSEOVER_MASK


@Component()
class MouseOverable:
    solid: object
    mask = MOUSEOVER_MASK
    _node: None = None


@Component()
class MouseOverableGeometry:
    mask = MOUSEOVER_MASK


@Component()
class MouseOveringCamera:
    entity: object = None
    collision_entry: object = None

    
class MouseOverOnEntity(System):
    entity_filters = {
        'mouseoverable': [Proxy('model'), MouseOverable],
        'mouseoverable_geometry': [Proxy('geometry'), MouseOverableGeometry],
        'camera': [Camera, Input, MouseOveringCamera],
    }
    proxies = {
        'model': ProxyType(Model, 'node'),
        'geometry': ProxyType(Geometry, 'node'),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.traverser = CollisionTraverser()
        self.queue = CollisionHandlerQueue()
        
        self.picker_ray = CollisionRay()
        self.picker_node = CollisionNode('mouse ray')
        self.picker_node.add_solid(self.picker_ray)
        self.picker_node.set_from_collide_mask(MOUSEOVER_MASK)
        self.picker_node.set_into_collide_mask(0x0)
        self.picker_node_path = NodePath(self.picker_node)

        self.traverser.add_collider(self.picker_node_path, self.queue)

    def enter_filter_mouseoverable(self, entity):
        model_proxy = self.proxies['model']
        model_node = model_proxy.field(entity)
        mouseoverable = entity[MouseOverable]

        into_node = CollisionNode('wecs_mouseoverable')
        into_node.add_solid(mouseoverable.solid)
        into_node.set_from_collide_mask(0x0)
        into_node.set_into_collide_mask(mouseoverable.mask)
        into_node_path = model_node.attach_new_node(into_node)
        into_node_path.set_python_tag('wecs_mouseoverable', entity._uid)

    def exit_filter_mouseoverable(self, entity):
        # FIXME: Undo all the other stuff that accumulated!
        entity[MouseOverable].solid.detach_node()

    def enter_filter_mouseoverable_geometry(self, entity):
        into_node = self.proxies['geometry'].field(entity)

        old_mask = into_node.get_collide_mask()
        new_mask = old_mask | entity[MouseOverableGeometry].mask
        into_node.set_collide_mask(new_mask)
        into_node.find('**/+GeomNode').set_python_tag('wecs_mouseoverable', entity._uid)

    def update(self, entities_by_filter):
        for entity in entities_by_filter['camera']:
            mouse_overing = entity[MouseOveringCamera]
            camera = entity[Camera]
            input = entity[Input]

            # Reset overed entity to None
            mouse_overing.entity = None
            mouse_overing.collision_entry = None

            requested = 'mouse_over' in input.contexts
            has_mouse = base.mouseWatcherNode.has_mouse()
            if requested and has_mouse:
                # Attach and align testing ray, and run collisions
                self.picker_node_path.reparent_to(camera.camera)
                mpos = base.mouseWatcherNode.get_mouse()
                self.picker_ray.set_from_lens(
                    base.camNode,
                    mpos.getX(),
                    mpos.getY(),
                )
                self.traverser.traverse(camera.camera.get_top())

                # Remember reference to mouseovered entity, if any
                if self.queue.get_num_entries() > 0:
                    self.queue.sort_entries()
                    entry = self.queue.get_entry(0)
                    picked_node = entry.get_into_node_path()
                    picked_uid = picked_node.get_python_tag('wecs_mouseoverable')
                    mouse_overing.entity = picked_uid
                    mouse_overing.collision_entry = entry


class PrintMouseOveredEntity(System):
    entity_filters = {
        'camera': [Camera, Input, MouseOveringCamera],
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['camera']:
            mouse_overing = entity[MouseOveringCamera]
            if mouse_overing.entity is not None:
                print(self.world.get_entity(mouse_overing.entity))


@Component()
class Selectable:
    pass


def select_indicator():
    model = base.loader.load_model('models/smiley')
    model.set_sz(0.1)
    return model


@Component()
class Targetable:
    pass


def target_indicator():
    model = base.loader.load_model('models/frowney')
    model.set_scale(0.1, 0.1, 0.25)
    model.set_z(2.1)
    return model


@Component()
class Pointable:
    pass


def point_indicator():
    model = base.loader.load_model('models/jack')
    model.set_scale(0.1)
    return model


@Component()
class UserInterface:
    selected_entity: wecs.core.UID = None
    targeted_entity: wecs.core.UID = None
    point_coordinates: Vec3 = None
    select_indicator: NodePath = field(default_factory=select_indicator)
    target_indicator: NodePath = field(default_factory=target_indicator)
    point_indicator: NodePath = field(default_factory=point_indicator)


class UpdateMouseOverUI(System):
    entity_filters = {
        'cursor': [Input, MouseOveringCamera, UserInterface],
    }
    input_context = 'select_entity'
    proxies = {
        'model': ProxyType(Model, 'node'),
    }

    def exit_filter_cursor(self, entity):
        ui = entity[UserInterface]
        ui.select_indicator.detach_node()
        ui.target_indicator.detach_node()
        ui.point_indicator.detach_node()

    def update(self, entities_by_filter):
        for entity in entities_by_filter['cursor']:
            ui = entity[UserInterface]
            mouseover = entity[MouseOveringCamera]
            mouseovered_entity_uid = mouseover.entity
            mouseovered_entity = None
            selected_entity = None
            target_entity = None
            point_coordinates = None
            
            # Does the currently selected entity still exist, and which
            # is it?
            if ui.selected_entity is not None:
                try:
                    selected_entity = self.world.get_entity(ui.selected_entity)
                except NoSuchUID:
                    ui.selected_entity = None
            # Update the selection indicator
            if selected_entity is not None:
                selected_node = self.proxies['model'].field(selected_entity)
                ui.select_indicator.reparent_to(selected_node)
            else:
                ui.select_indicator.detach_node()
    
            # Update target and point indicators.
            if mouseovered_entity_uid is not None:
                # If we are pointing at an entity, then target, point,
                # or do neither, depending on the entity.
                mouseovered_entity = self.world.get_entity(mouseovered_entity_uid)
                mouseovered_entity_node = self.proxies['model'].field(mouseovered_entity)
                if Targetable in mouseovered_entity:
                    target_entity = mouseovered_entity
                    ui.target_indicator.reparent_to(mouseovered_entity_node)
                    ui.point_indicator.detach_node()
                elif Pointable in mouseovered_entity:
                    target_entity = mouseovered_entity
                    ui.target_indicator.detach_node()
                    ui.point_indicator.reparent_to(mouseovered_entity_node)
                    # FIXME: Adjust position
                    point_coordinates = mouseover.collision_entry.get_surface_point(mouseovered_entity_node)
                    ui.point_indicator.set_pos(point_coordinates)
                else:
                    ui.target_indicator.detach_node()
                    ui.point_indicator.detach_node()
            else:
                # If we're not pointing at an entity, don't indicate a
                # target.
                ui.target_indicator.detach_node()
                ui.point_indicator.detach_node()

            # Write results into the component for consumption by other
            # systems.
            if selected_entity is None:
                ui.selected_entity = None
            else:
                ui.selected_entity = selected_entity._uid
            if target_entity is None:
                ui.targeted_entity = None
            else:
                ui.targeted_entity = target_entity._uid
            ui.point_coordinates = point_coordinates

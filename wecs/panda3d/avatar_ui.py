import wecs

from wecs.core import System
from wecs.core import Component
from wecs.core import Proxy
from wecs.core import ProxyType

from wecs.panda3d.prototype import Model
from wecs.panda3d.input import Input
from wecs.panda3d.mouseover import MouseOveringCamera
from wecs.panda3d.mouseover import UserInterface
from wecs.panda3d.mouseover import Selectable
from wecs.panda3d.ai import BehaviorAI


@Component()
class Embodiable:
    pass


class AvatarUI(System):
    """
    Command rules:
    if not embodied and not targeting_selection:
        selection(goto target)
    if not embodied and targeting_selection:
        selection(idle)
    if embodied and selecting and not targeting_selection:
        selection(goto target)
    if embodied and selecting and targeting_selection:
        selection(idle)
    if embodied and not selecting and targeting_selection:
        self(idle)
    if embodied and not selecting and not targeting_selection:
        self(goto target)
    """
    entity_filters = {
        'cursor': [Input, MouseOveringCamera, UserInterface],
    }
    proxies = {
        'parent': ProxyType(Model, 'parent'),
    }
    input_context = 'select_entity'
    
    def update(self, entities_by_filter):
        for entity in entities_by_filter['cursor']:
            input = entity[Input]
            if self.input_context in input.contexts:
                context = base.device_listener.read_context(self.input_context)
                self.process_input(entity, context)

    def process_input(self, entity, context):
        ui = entity[UserInterface]
        mouseover = entity[MouseOveringCamera]

        mouseovered_entity = None
        if mouseover.entity is not None:
            mouseovered_entity = self.world.get_entity(mouseover.entity)
        targeting_self = mouseover.entity == entity._uid

        selected_entity = None
        if ui.selected_entity is not None:
            selected_entity = self.world.get_entity(ui.selected_entity)
        target_entity = None
        if ui.targeted_entity is not None:
            target_entity = self.world.get_entity(ui.targeted_entity)
        point_coordinates = ui.point_coordinates
        targeting_selection = False
        if selected_entity is not None and ui.selected_entity == ui.targeted_entity:
            targeting_selection = True
        
        embodied = Embodiable in entity
        targeting_embodiable = None
        if mouseovered_entity is not None:
            targeting_embodiable = Embodiable in mouseovered_entity
        
        # Now we can evaluate the player's input. First, he clicked to
        # select.
        if context.get('select', False):
            if target_entity is None or Selectable not in target_entity:
                # Selecting while not pointing at a valid target
                # unselects.
                ui.selected_entity = None
                ui.select_indicator.detach_node()
            else:
                # But selecting a selectable entity... selects it.
                if not embodied or mouseover.entity != entity._uid:
                    ui.selected_entity = target_entity._uid
        # The player instead clicked to give a command, and there is a
        # valid target, ...
        elif context.get('command', False):
            # 3rd person mode, giving command with to selected entity
            if not embodied and selected_entity and target_entity and not targeting_selection:
                action = ['walk_to_entity', mouseover.entity]
                if point_coordinates:
                    action.append(point_coordinates)
                self.command(selected_entity, *action)
            if not embodied and targeting_selection:
                self.command(selected_entity, 'idle')
            if embodied and selected_entity and target_entity and not targeting_selection:
                action = ['walk_to_entity', mouseover.entity]
                if point_coordinates:
                    action.append(point_coordinates)
                self.command(selected_entity, *action)
            if embodied and ui.selected_entity and target_entity and not targeting_selection:
                self.command(entity, 'idle')
            if embodied and targeting_selection:
                self.command(selected_entity, 'idle')
            if embodied and not ui.selected_entity and targeting_selection:
                self.command(entity, 'idle')
            if embodied and not ui.selected_entity and target_entity and not targeting_self:
                action = ['walk_to_entity', mouseover.entity]
                if point_coordinates:
                    action.append(point_coordinates)
                self.command(entity, *action)
            if embodied and targeting_self and not ui.selected_entity:
                self.command(entity, 'idle')
        # Now the player clicked to dis-/embody...
        elif context.get('embody', False):
            if not embodied and not targeting_embodiable and selected_entity:
                self.embody(entity, selected_entity)
            if not embodied and targeting_embodiable:
                self.embody(entity, target_entity)
            if embodied and targeting_embodiable and not targeting_self:
                self.jump_body(entity, target_entity)
            if embodied and not targeting_embodiable:
                self.disembody(entity)

    def command(self, entity, *action):
        ai = entity[BehaviorAI]
        ai.behavior = action

    def embody(self, entity, target):
        raise NotImplementedError

    def jump_body(self, entity, target):
        raise NotImplementedError

    def disembody(self, entity):
        raise NotImplementedError
        

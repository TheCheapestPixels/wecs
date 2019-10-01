from panda3d.core import KeyboardButton

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter

from .character import CharacterController
from .character import FallingMovement
from .character import JumpingMovement


@Component()
class Input:
    pass


class AcceptInput(System):
    entity_filters = {
        'character': and_filter([
            CharacterController,
            Input,
        ]),
    }

    def init_entity(self, filter_name, entity):
        base.win.movePointer(
            0,
            int(base.win.getXSize() / 2),
            int(base.win.getYSize() / 2),
        )
        #entity[Input].last_mouse_pos = None

    def update(self, entities_by_filter):
        for entity in entities_by_filter['character']:
            character = entity[CharacterController]
            character.move.x = 0.0
            character.move.y = 0.0
            character.heading = 0.0
            character.pitch = 0.0

            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("w")):
                character.move.y += 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("s")):
                character.move.y -= 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("a")):
                character.move.x -= 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("d")):
                character.move.x += 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.up()):
                character.pitch += 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.down()):
                character.pitch -= 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.left()):
                character.heading += 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.right()):
                character.heading -= 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.space()):
                if FallingMovement in entity and JumpingMovement in entity:
                    if entity[FallingMovement].ground_contact:
                        character.jumps = True
            else:
                character.jumps = False


            # if base.mouseWatcherNode.has_mouse():
            #     mouse_pos = base.mouseWatcherNode.get_mouse()
            #     character.heading = mouse_pos.get_x() * -character.max_heading
            #     character.pitch = mouse_pos.get_y() * character.max_pitch
            # else:
            #     mouse_pos = None
            # base.win.movePointer(
            #     0,
            #     int(base.win.getXSize() / 2),
            #     int(base.win.getYSize() / 2),
            # )
            # entity[Input].last_mouse_pos = mouse_pos

from panda3d.core import KeyboardButton

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter

from .camera import TurntableCamera

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
            character.jumps = False
            character.sprints = False
            character.crouches = False
            character.move.x = 0.0
            character.move.y = 0.0
            character.heading = 0.0
            character.pitch = 0.0
            # For debug purposes, emulate analog stick on keyboard
            # input, being half-way pressed, by holding shift
            analog = 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.shift()):
                analog = 0.5
            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("w")):
                character.move.y += analog
            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("s")):
                character.move.y -= analog
            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("a")):
                character.move.x -= analog
            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("d")):
                character.move.x += analog

            # Rotation
            if base.mouseWatcherNode.is_button_down(KeyboardButton.up()):
                character.pitch += 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.down()):
                character.pitch -= 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.left()):
                character.heading += 1
            if base.mouseWatcherNode.is_button_down(KeyboardButton.right()):
                character.heading -= 1

            if TurntableCamera in entity:
                camera = entity[TurntableCamera]
                camera.heading = camera.pitch = 0
                if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("j")):
                    camera.heading = 1
                if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("l")):
                    camera.heading = -1
                if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("i")):
                    camera.pitch = -1
                if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("k")):
                    camera.pitch = 1


            # Special movement modes.
            # By default, you run ("sprint"), unless you press e, in
            # which case you walk. You can crouch by pressing q; this
            # overrides walking and running. Jump by pressing space.
            # This logic is implemented by the Walking system. Here,
            # only intention is signalled.
            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("e")):
                character.sprints = True
            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("c")):
                character.crouches = True
            if base.mouseWatcherNode.is_button_down(KeyboardButton.space()):
                character.jumps = True

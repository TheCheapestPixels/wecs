from panda3d.core import KeyboardButton

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter

from .camera import FirstPersonCamera, ThirdPersonCamera

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
<<<<<<< HEAD

            if ThirdPersonCamera in entity:
                camera = entity[ThirdPersonCamera]
            elif FirstPersonCamera in entity:
                camera = entity[FirstPersonCamera]

            character.sprints = False
            character.crouching = False
=======
            character.sprints = True
            character.crouches = False
            character.jumps = False
>>>>>>> 678c21429403db00c686b8154238e11d3c2879f0

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

<<<<<<< HEAD
=======
            # Rotation
>>>>>>> 678c21429403db00c686b8154238e11d3c2879f0
            if base.mouseWatcherNode.is_button_down(KeyboardButton.up()):
                camera.pivot.set_p(camera.pivot.get_p()+1)
            if base.mouseWatcherNode.is_button_down(KeyboardButton.down()):
                camera.pivot.set_p(camera.pivot.get_p()-1)
            if base.mouseWatcherNode.is_button_down(KeyboardButton.left()):
                camera.pivot.set_h(camera.pivot.get_h()+2)
            if base.mouseWatcherNode.is_button_down(KeyboardButton.right()):
<<<<<<< HEAD
                camera.pivot.set_h(camera.pivot.get_h()-2)
            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("e")):
                character.sprints = True

            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("c")):
                character.crouching = True
=======
                character.heading -= 1

            # Special movement modes.
            # By default, you run ("sprint"), unless you press e, in
            # which case you walk. You can crouch by pressing q; this
            # overrides walking and running. Jump by pressing space.
            # This logic is implemented by the Walking system. Here,
            # only intention is signalled.
            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("e")):
                character.sprints = False
            if base.mouseWatcherNode.is_button_down(KeyboardButton.ascii_key("q")):
                character.crouches = True
>>>>>>> 678c21429403db00c686b8154238e11d3c2879f0
            if base.mouseWatcherNode.is_button_down(KeyboardButton.space()):
                character.jumps = True

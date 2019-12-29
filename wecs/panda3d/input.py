from panda3d.core import KeyboardButton

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter

from wecs.mechanics.clock import Clock

from .camera import TurntableCamera
from .character import CharacterController
from .character import FallingMovement
from .character import JumpingMovement


@Component()
class Input:
    context: str = "character_movement"


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
            input = entity[Input]
            context = base.device_listener.read_context(input.context)

            character.move.x = context['direction'].x
            character.move.y = context['direction'].y
            character.heading = context['rotation'].x
            character.pitch = context['rotation'].y

            if TurntableCamera in entity:
                camera = entity[TurntableCamera]
                camera.heading = context['camera'].x
                camera.pitch = context['camera'].y

            # Special movement modes.
            # By default, you run ("sprint"), unless you press e, in
            # which case you walk. You can crouch by pressing q; this
            # overrides walking and running. Jump by pressing space.
            # This logic is implemented by the Walking system. Here,
            # only intention is signalled.
            character.jumps = context['jump']
            character.sprints = context['sprint']
            character.crouches = context['crouch']

            # Time control
            if Clock in entity:
                clock = entity[Clock]
                clock.scaling_factor *= 1 + context['clock_control']

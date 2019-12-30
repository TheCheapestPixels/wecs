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
    contexts = ['character_movement', 'camera_movement', 'clock_control']


class AcceptInput(System):
    entity_filters = {
        'input': and_filter([Input]),
    }

    def init_entity(self, filter_name, entity):
        base.win.movePointer(
            0,
            int(base.win.getXSize() / 2),
            int(base.win.getYSize() / 2),
        )

    def update(self, entities_by_filter):
        for entity in entities_by_filter['input']:
            input = entity[Input]
            if CharacterController in entity and 'character_movement' in input.contexts:
                context = base.device_listener.read_context('character_movement')
                character = entity[CharacterController]

                character.move.x = context['direction'].x
                character.move.y = context['direction'].y
                character.heading = -context['rotation'].x
                character.pitch = context['rotation'].y

                # Special movement modes.
                # By default, you run ("sprint"), unless you press e, in
                # which case you walk. You can crouch by pressing q; this
                # overrides walking and running. Jump by pressing space.
                # This logic is implemented by the Walking system. Here,
                # only intention is signalled.
                character.jumps = context['jump']
                character.sprints = context['sprint']
                character.crouches = context['crouch']

            if TurntableCamera in entity and 'camera_movement' in input.contexts:
                context = base.device_listener.read_context('camera_movement')
                turntable = entity[TurntableCamera]
                turntable.heading = -context['rotation'].x
                turntable.pitch = context['rotation'].y


            # Time control
            if Clock in entity and 'clock_control' in input.contexts:
                context = base.device_listener.read_context('clock_control')
                clock = entity[Clock]
                clock.scaling_factor *= 1 + context['time_zoom']

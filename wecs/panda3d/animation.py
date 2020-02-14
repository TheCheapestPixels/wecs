from dataclasses import field

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.core import or_filter

from .input import Input
from .character import CharacterController, FallingMovement
from .model import Geometry
from .model import Actor
from .model import Scene
from .model import Clock


@Component()
class Animation:
    to_play: list = field(default_factory=list)
    playing: list = field(default_factory=list)
    blends: list = field(default_factory=list)
    framerate: int = 1


class AnimateCharacter(System):
    entity_filters = {
        'animated_character': and_filter([
            Actor,
            Animation,
            CharacterController
        ])
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['animated_character']:
            controller = entity[CharacterController]
            animation = entity[Animation]
            actor = entity[Actor].node

            if FallingMovement in entity:
                grounded = entity[FallingMovement].ground_contact
            else:
                grounded = False

            initial = "idle"
            if not grounded:
                if controller.jumps:
                    initial = "jumping"
                elif controller.translation.z < -0.2:
                    initial = "falling"
            elif controller.crouches:
                initial = "crouch"
            animation.to_play = [initial, "walk_forward", "run_forward"]
            #TODO: bad constant, 1.4? Should be fixed in animation
            # when the right value is found in lab.
            forward_speed = abs(controller.translation.y*1.4)
            idle = max(0, (1 - forward_speed))
            walk = 1 - abs(forward_speed - 0.5) * 2
            run = max(0, forward_speed * 2 - 1)
            blends = [idle, walk, run]
            # sideways movement
            #TODO: same here, another constant. Fix in animation after lab.
            strafe_speed = (controller.translation.x*1.4)
            if not strafe_speed == 0:
                blends.append(abs(strafe_speed))
                if strafe_speed > 0:
                    animation.to_play.append("walk_right")
                elif strafe_speed < 0:
                    animation.to_play.append("walk_left")

            animation.framerate = (0.5+(forward_speed + abs(strafe_speed)))
            # If walking backwards simply play the animation in reverse
            # TODO: Only do this when there's no animations for walking backwards.
            if controller.translation.y < 0:
                animation.framerate = -animation.framerate
            if controller.translation.z < -0.2:
                animation.framerate *= 0.2

            animation.blends = blends

            # # vertical animation
            # vertical_speed = controller.last_translation_speed.z
            # blends = [1]
            # if vertical_speed > 0.1:
            #     animation.to_play = ["jumping"]
            # elif vertical_speed < -0.1:
            #     animation.to_play = ["falling"]
            # else:
            #     # forward animation
            #     if controller.crouches:
            #         # TODO: Don't crouch instantly but ease in (bounce?).
            #         initial = "crouch"
            #     else:
            #         initial = "idle"
            #     animation.to_play = [initial, "walk_forward", "run_forward"]
            #     forward_speed = abs(controller.last_translation_speed.y)
            #     idle = max(0, (1 - forward_speed * 2))
            #     walk = 1 - abs(forward_speed - 0.5) * 2
            #     run = max(0, forward_speed * 2 - 1)
            #     blends = [idle, walk, run]
            #     # strafe animation
            #     strafe_speed = controller.last_translation_speed.x
            #     if not strafe_speed == 0:
            #         blends.append(abs(strafe_speed))
            #         if strafe_speed > 0:
            #             animation.to_play.append("walk_right")
            #         elif strafe_speed < 0:
            #             animation.to_play.append("walk_left")
            #
            #     animation.framerate = (0.5+(forward_speed + abs(strafe_speed)))
            #     # If walking backwards simply play the animation in reverse
            #     # Only do this when there's no animations for walking backwards?
            #     if controller.last_translation_speed.y < 0:
            #         animation.framerate = -animation.framerate
            #
            # animation.blends = blends


class Animate(System):
    entity_filters = {
        'animation': and_filter([
            Actor,
            Animation,
        ])
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['animation']:
            animation = entity[Animation]
            actor = entity[Actor].node
            if not animation.playing == animation.to_play:
                if len(animation.to_play) > 0:
                    actor.enableBlend()
                else:
                    actor.disableBlend()

                # TODO: Don't stop and swap different animations instantly
                # but ease in (and bounce?) between them.

                #Stop animations not in to_play.
                for name in animation.playing:
                    if not name in animation.to_play:
                        actor.stop(name)
                        actor.setControlEffect(name, 0)

                #Play newly added animations.
                for n, name in enumerate(animation.to_play):
                    if name not in animation.playing:
                        actor.loop(name)
                animation.playing = animation.to_play

            # Set blends each frame
            for b, blend in enumerate(animation.blends):
                if b < len(animation.playing):
                    name = animation.playing[b]
                    actor.setControlEffect(name, blend/len(animation.playing))

            # Set framerate each frame
            for name in animation.playing:
                actor.setPlayRate(animation.framerate, name)

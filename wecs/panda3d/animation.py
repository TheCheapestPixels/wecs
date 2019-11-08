from dataclasses import field

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.core import or_filter

from .character import CharacterController
from .model import Model
from .model import Scene
from .model import Clock


# Animations:
# Idle
# Crouch/Walk/Run/Sprint/ forward/backward/left/right
# Flying/Jumping/Falling/Landing


@Component()
class Animation:
    to_play: list = field(default_factory=list)
    playing: list = field(default_factory=list)
    blends: list = field(default_factory=list)
    framerate: int = 30


class AnimateCharacter(System):
    entity_filters = {
        'animated_character': and_filter([
            Animation,
            Model,
            CharacterController
        ])
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['animated_character']:
            controller = entity[CharacterController]
            animation = entity[Animation]
            actor = entity[Model].node
            combined_speed = controller.translation.x+controller.translation.y
            if combined_speed == 0:
                animation.to_play = ["idle"]
            else:
                animation.to_play = ["walk_forward", "run_forward"]
                speed = controller.translation.y
                animation.blends = [1-speed,speed]

                if speed > 0:
                    animation.framerate = 0.7+speed
                else:
                    animation.framerate = -0.5+speed


class Animate(System):
    entity_filters = {
        'animation': and_filter([
            Animation,
            Model,
        ])
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['animation']:
            animation = entity[Animation]
            actor = entity[Model].node
            if not animation.playing == animation.to_play:
                if len(animation.to_play) > 0:
                    actor.enableBlend()
                else:
                    actor.disableBlend()

                #Stop animations not in list.
                for name in animation.playing:
                    if not name in animation.to_play:
                        actor.stop(name)
                        actor.setControlEffect(name, 0)

                #Play new animations and add to list.
                for n, name in enumerate(animation.to_play):
                    if name not in animation.playing:
                        actor.loop(name)
                animation.playing = animation.to_play

            # Set blends each frame
            for b, blend in enumerate(animation.blends):
                if b < len(animation.playing):
                    name = animation.playing[b]
                    actor.setControlEffect(name, blend)

            # Set framerate each frame
            for name in animation.playing:
                actor.setPlayRate(animation.framerate, name)

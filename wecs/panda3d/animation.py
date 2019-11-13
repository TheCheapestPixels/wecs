from dataclasses import field

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.core import or_filter

from .input import Input
from .character import CharacterController
from .model import Model
from .model import Scene
from .model import Clock


def clamp_list(to_clamp, floor, ceiling):
    clamped = []
    for i in to_clamp:
        clamped.append(min(max(i, floor), ceiling))
    return clamped

# Animations:
# Idle
# Crouch/Walk/Run/Sprint/ forward/backward/left/right
# Flying/Jumping/Falling/Landing


@Component()
class Animation:
    to_play: list = field(default_factory=list)
    playing: list = field(default_factory=list)
    blends: list = field(default_factory=list)
    framerate: int = 1


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
            animation.to_play = ["idle", "walk_forward", "run_forward"]
            blends = [0, 0, 0]
            s_speed = (controller.translation.x*2)
            if s_speed > 0:
                animation.to_play.append("walk_right")
                blends.append(s_speed*2)
            if s_speed < 0:
                animation.to_play.append("walk_left")
                blends.append(-(s_speed*2))

            # set forward animations
            f_speed = (controller.translation.y*2)
            if f_speed == 0:
                blends[1] = 0
                blends[0] = 1
            else:
                blends[2] = -0.35+(f_speed)
                blends[1] = (f_speed - (blends[1]/2)) - 0.1
                blends[0] = (1-(f_speed*4))/2

            animation.blends = clamp_list(blends, 0, 1)
            animation.framerate = 1


class Animate(System):
    entity_filters = {
        'animation': and_filter([
            Animation,
            Model,
        ])
    }
    def init_entity(self, filter_name, entity):
        print(entity[Model].node.getAnimNames())

    def update(self, entities_by_filter):
        for entity in entities_by_filter['animation']:
            animation = entity[Animation]
            actor = entity[Model].node
            if not animation.playing == animation.to_play:
                if len(animation.to_play) > 0:
                    actor.enableBlend()
                else:
                    actor.disableBlend()

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

            if Input in entity:
                print(animation.blends)
                print(animation.playing)

            # Set blends each frame
            for b, blend in enumerate(animation.blends):
                if b < len(animation.playing):
                    name = animation.playing[b]
                    actor.setControlEffect(name, blend/len(animation.playing))

            # Set framerate each frame
            for name in animation.playing:
                actor.setPlayRate(animation.framerate, name)

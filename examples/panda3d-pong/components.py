from panda3d.core import NodePath
from panda3d.core import Vec3

from wecs.core import Component


@Component()
class Paddle:
    player: int
    size: float
    speed: float


@Component()
class Ball:
    pass


@Component()
class Resting:
    pass


@Component()
class Position:
    value: Vec3


@Component()
class Movement:
    value: Vec3


@Component()
class Model:
    model_name: str


@Component()
class Scene:
    root: NodePath

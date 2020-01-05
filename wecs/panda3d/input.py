from dataclasses import field

from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter


@Component()
class Input:
    contexts: list = field(default_factory=list)

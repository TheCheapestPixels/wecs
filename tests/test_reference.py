import pytest

from fixtures import world

from wecs.core import UID
from wecs.core import NoSuchUID
#from wecs.core import Entity
from wecs.core import Component


@Component()
class Reference:
    uid: UID


# This test feels silly... More on it when serialization comes knocking.
def test_uid():
    uid_1 = UID()
    uid_2 = UID()
    assert uid_1 is not uid_2
    assert uid_1 != uid_2


def test_reference():
    c = Reference(uid=UID())


def test_resolving_reference(world):
    to_entity = world.create_entity()
    from_entity = world.create_entity()
    from_entity.add_component(Reference(uid=to_entity._uid))
    reference = world.get_entity(from_entity.get_component(Reference).uid)
    assert reference is to_entity


def test_resolving_dangling_reference(world):
    to_entity = world.create_entity()
    from_entity = world.create_entity()
    from_entity.add_component(Reference(uid=to_entity._uid))
    to_entity.destroy()
    with pytest.raises(NoSuchUID):
        world.get_entity(from_entity.get_component(Reference).uid)

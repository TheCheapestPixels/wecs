import pytest

from fixtures import world

from wecs.core import UID
from wecs.core import NoSuchUID
from wecs.core import Component


@Component()
class Reference:
    uid: UID


def test_user_defined_names(world):
    entity = world.create_entity(name="foo")
    assert entity._uid.name == "foo"


def test_automatic_names(world):
    entity = world.create_entity()
    assert entity._uid.name


def test_automatic_unique_names(world):
    entity_1 = world.create_entity()
    entity_2 = world.create_entity()
    assert entity_1._uid.name != entity_2._uid.name


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
    world.flush_component_updates()
    reference = world.get_entity(from_entity.get_component(Reference).uid)
    assert reference is to_entity


def test_resolving_dangling_reference(world):
    to_entity = world.create_entity()
    from_entity = world.create_entity()
    from_entity.add_component(Reference(uid=to_entity._uid))
    to_entity.destroy()
    world.flush_component_updates()
    with pytest.raises(NoSuchUID):
        world.get_entity(from_entity.get_component(Reference).uid)

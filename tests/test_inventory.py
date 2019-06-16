import pytest

from fixtures import world

from wecs.core import UID
from wecs.core import NoSuchUID
from wecs.rooms import Room
from wecs.rooms import RoomPresence
from wecs.rooms import PerceiveRoom
from wecs.inventory import Inventory
from wecs.inventory import Takeable
from wecs.inventory import TakeAction
from wecs.inventory import DropAction
from wecs.inventory import ItemNotInRoom
from wecs.inventory import ItemNotInInventory
from wecs.inventory import ActorHasNoInventory
from wecs.inventory import ActorNotInRoom
from wecs.inventory import is_in_inventory
from wecs.inventory import can_take
from wecs.inventory import can_drop
from wecs.inventory import take
from wecs.inventory import drop
from wecs.inventory import TakeOrDrop


@pytest.fixture
def room(world):
    return world.create_entity(
        Room(
            adjacent=[],
            presences=[],
            arrived=[],
            continued=[],
            gone=[],
        ),
    )


@pytest.fixture
def item(world, room):
    return world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
        Takeable(),
    )


def test_is_in_inventory(world, room):
    item = world.create_entity(
        Takeable(),
    )
    actor = world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
        Inventory(contents=[item._uid]),
    )
    world.flush_component_updates()

    assert is_in_inventory(item, actor)


def test_is_not_in_inventory(world, room, item):
    actor = world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
        Inventory(contents=[]),
    )
    world.flush_component_updates()

    assert not is_in_inventory(item, actor)


def test_take_item(world, room, item):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(), 1)
    world.add_system(PerceiveRoom(), 2, add_duplicates=True)
    actor = world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
        Inventory(contents=[]),
        TakeAction(item=item._uid),
    )
    world.update()

    assert actor.get_component(Inventory).contents == [item._uid]
    assert not actor.has_component(TakeAction)
    assert not item.has_component(RoomPresence)


def test_drop_item(world, room):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(), 1)
    world.add_system(PerceiveRoom(), 2, add_duplicates=True)
    item = world.create_entity(
        Takeable(),
    )
    actor = world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
        Inventory(contents=[item._uid]),
        DropAction(item=item._uid),
    )
    world.update()

    assert actor.get_component(Inventory).contents == []
    assert not actor.has_component(DropAction)
    assert item.has_component(RoomPresence)
    assert item.get_component(RoomPresence).room == actor.get_component(RoomPresence).room


def test_can_not_take_item_from_other_room(world, room, item):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(), 1)
    world.add_system(PerceiveRoom(), 2, add_duplicates=True)
    other_room = world.create_entity(
        Room(
            adjacent=[],
            presences=[],
            arrived=[],
            continued=[],
            gone=[],
        ),
    )
    actor = world.create_entity(
        RoomPresence(room=other_room._uid, presences=[]),
        Inventory(contents=[]),
        TakeAction(item=item._uid),
    )
    world.update()

    assert actor.get_component(Inventory).contents == []
    assert not actor.has_component(TakeAction)
    assert item.has_component(RoomPresence)


def test_can_not_take_item_from_other_room_exception(world, room, item):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(throw_exc=True), 1)
    world.add_system(PerceiveRoom(), 2, add_duplicates=True)
    other_room = world.create_entity(
        Room(
            adjacent=[],
            presences=[],
            arrived=[],
            continued=[],
            gone=[],
        ),
    )
    actor = world.create_entity(
        RoomPresence(room=other_room._uid, presences=[]),
        Inventory(contents=[]),
        TakeAction(item=item._uid),
    )
    with pytest.raises(ItemNotInRoom):
        world.update()


def test_can_not_take_without_an_inventory(world, room, item):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(), 1)
    world.add_system(PerceiveRoom(), 2, add_duplicates=True)
    actor = world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
        TakeAction(item=item._uid),
    )
    world.update()

    assert not actor.has_component(TakeAction)
    assert item.has_component(RoomPresence)


def test_can_not_take_without_an_inventory_exception(world, room, item):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(throw_exc=True), 1)
    world.add_system(PerceiveRoom(), 2, add_duplicates=True)
    actor = world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
        TakeAction(item=item._uid),
    )
    with pytest.raises(ActorHasNoInventory):
        world.update()


def test_can_not_take_nonexistant_item(world, room):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(), 1)
    world.add_system(PerceiveRoom(), 2, add_duplicates=True)
    actor = world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
        Inventory(contents=[]),
        TakeAction(item=UID()),
    )
    world.update()

    assert actor.get_component(Inventory).contents == []
    assert not actor.has_component(TakeAction)


def test_can_not_take_nonexistant_item_exception(world, room):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(throw_exc=True), 1)
    actor = world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
        Inventory(contents=[]),
        TakeAction(item=UID()),
    )
    with pytest.raises(NoSuchUID):
        world.update()


def test_can_not_drop_item_that_actor_does_not_have(world, room, item):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(), 1)
    world.add_system(PerceiveRoom(), 2, add_duplicates=True)
    actor = world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
        Inventory(contents=[]),
        DropAction(item=item._uid),
    )
    world.update()

    assert actor.get_component(Inventory).contents == []
    assert not actor.has_component(DropAction)
    assert item.has_component(RoomPresence)


def test_can_not_drop_item_that_actor_does_not_have_exception(world, room, item):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(throw_exc=True), 1)
    actor = world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
        Inventory(contents=[]),
        DropAction(item=item._uid),
    )
    with pytest.raises(ItemNotInInventory):
        world.update()


def can_not_take_untakeable_item(world, room):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(), 1)
    world.add_system(PerceiveRoom(), 2, add_duplicates=True)

    item =  world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
    )
    actor = world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
        Inventory(contents=[]),
        TakeAction(item=item._uid),
    )
    world.update()

    assert actor.get_component(Inventory).contents == []
    assert not actor.has_component(TakeAction)
    assert item.has_component(RoomPresence)


def can_not_take_untakeable_item_exception(world, room):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(throw_exc=True), 1)

    item =  world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
    )
    actor = world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
        Inventory(contents=[]),
        TakeAction(item=item._uid),
    )
    with pytest.raises(NotTakeable):
        world.update()


def can_not_drop_untakeable_item(world, room):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(), 1)
    world.add_system(PerceiveRoom(), 2, add_duplicates=True)

    item =  world.create_entity()
    actor = world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
        Inventory(contents=[item._uid]),
        DropAction(item=item._uid),
    )
    world.update()

    assert actor.get_component(Inventory).contents == [item._uid]
    assert not actor.has_component(DropAction)
    assert not item.has_component(RoomPresence)


def can_not_drop_untakeable_item_exception(world, room):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(throw_exc=True), 1)

    item =  world.create_entity()
    actor = world.create_entity(
        RoomPresence(room=room._uid, presences=[]),
        Inventory(contents=[item._uid]),
        DropAction(item=item._uid),
    )
    with pytest.raises(NotTakeable):
        world.update()


def test_can_not_take_from_the_void(world):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(), 1)
    world.add_system(PerceiveRoom(), 2, add_duplicates=True)

    item =  world.create_entity(
        Takeable(),
    )
    actor = world.create_entity(
        Inventory(contents=[]),
        TakeAction(item=item._uid),
    )
    world.update()

    assert actor.get_component(Inventory).contents == []
    assert not actor.has_component(TakeAction)


def test_can_not_take_from_the_void_exception(world):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(throw_exc=True), 1)

    item =  world.create_entity(
        Takeable(),
    )
    actor = world.create_entity(
        Inventory(contents=[]),
        TakeAction(item=item._uid),
    )
    with pytest.raises(ActorNotInRoom):
        world.update()


def test_can_not_drop_into_the_void(world):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(), 1)
    world.add_system(PerceiveRoom(), 2, add_duplicates=True)

    item = world.create_entity(
        Takeable(),
    )
    actor = world.create_entity(
        Inventory(contents=[item._uid]),
        DropAction(item=item._uid),
    )
    world.update()

    assert actor.get_component(Inventory).contents == [item._uid]
    assert not actor.has_component(DropAction)
    assert not item.has_component(RoomPresence)


def test_can_not_take_from_the_void_exception(world):
    world.add_system(PerceiveRoom(), 0)
    world.add_system(TakeOrDrop(throw_exc=True), 1)

    item = world.create_entity(
        Takeable(),
    )
    actor = world.create_entity(
        Inventory(contents=[item._uid]),
        DropAction(item=item._uid),
    )
    with pytest.raises(ActorNotInRoom):
        world.update()

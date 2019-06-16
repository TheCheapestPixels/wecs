import pytest

from fixtures import world

from wecs.rooms import Room
from wecs.rooms import RoomPresence
from wecs.rooms import ChangeRoomAction
from wecs.rooms import PerceiveRoom
from wecs.rooms import ChangeRoom
from wecs.rooms import is_in_room
from wecs.rooms import EntityNotInARoom
from wecs.rooms import ItemNotInARoom
from wecs.rooms import RoomsNotAdjacent


def test_creation(world):
    world.add_system(PerceiveRoom(), 0)

    room = world.create_entity(
        Room(
            adjacent=[],
            presences=[],
            arrived=[],
            continued=[],
            gone=[],
        ),
    )
    actor = world.create_entity(
        RoomPresence(
            room=room._uid,
            presences=[],
        ),
    )
    world.update()
    room_cmpt = room.get_component(Room)
    assert len(room_cmpt.presences) == 1
    assert room_cmpt.presences[0] == actor._uid
    assert len(room_cmpt.arrived) == 1
    assert room_cmpt.arrived[0] == actor._uid
    assert len(room_cmpt.continued) == 0
    assert len(room_cmpt.gone) == 0
    presence_cmpt = actor.get_component(RoomPresence)
    assert len(presence_cmpt.presences) == 1
    assert presence_cmpt.presences[0] == actor._uid

    world.update()
    room_cmpt = room.get_component(Room)
    assert len(room_cmpt.presences) == 1
    assert room_cmpt.presences[0] == actor._uid
    assert len(room_cmpt.arrived) == 0
    assert len(room_cmpt.continued) == 1
    assert room_cmpt.continued[0] == actor._uid
    assert len(room_cmpt.gone) == 0
    presence_cmpt = actor.get_component(RoomPresence)
    assert len(presence_cmpt.presences) == 1
    assert presence_cmpt.presences[0] == actor._uid


def test_change_room(world):
    world.add_system(ChangeRoom(), 0)
    world.add_system(PerceiveRoom(), 1)
    room = world.create_entity()
    other_room = world.create_entity()

    room.add_component(
        Room(
            adjacent=[other_room._uid],
            presences=[],
            arrived=[],
            continued=[],
            gone=[],
        ),
    )
    other_room.add_component(
        Room(
            adjacent=[room._uid],
            presences=[],
            arrived=[],
            continued=[],
            gone=[],
        ),
    )
    actor = world.create_entity(
        RoomPresence(
            room=room._uid,
            presences=[],
        ),
    )
    world.update()
    actor.add_component(
        ChangeRoomAction(
            room=other_room._uid,
        ),
    )
    world.update()

    room_cmpt = room.get_component(Room)
    assert len(room_cmpt.presences) == 0
    assert len(room_cmpt.arrived) == 0
    assert len(room_cmpt.continued) == 0
    assert len(room_cmpt.gone) == 1
    assert room_cmpt.gone[0] == actor._uid

    other_room_cmpt = other_room.get_component(Room)
    assert len(other_room_cmpt.presences) == 1
    assert other_room_cmpt.presences[0] == actor._uid
    assert len(other_room_cmpt.arrived) == 1
    assert other_room_cmpt.arrived[0] == actor._uid
    assert len(other_room_cmpt.continued) == 0
    assert len(other_room_cmpt.gone) == 0

    presence_cmpt = actor.get_component(RoomPresence)
    assert presence_cmpt.room == other_room._uid
    assert len(presence_cmpt.presences) == 1
    assert presence_cmpt.presences[0] == actor._uid


def test_mutual_perception(world):
    world.add_system(ChangeRoom(), 0)
    world.add_system(PerceiveRoom(), 1)

    # Two connected rooms, an actor in each
    room = world.create_entity()
    other_room = world.create_entity()
    room.add_component(
        Room(
            adjacent=[other_room._uid],
            presences=[],
            arrived=[],
            continued=[],
            gone=[],
        ),
    )
    other_room.add_component(
        Room(
            adjacent=[room._uid],
            presences=[],
            arrived=[],
            continued=[],
            gone=[],
        ),
    )
    actor = world.create_entity(
        RoomPresence(
            room=room._uid,
            presences=[],
        ),
    )
    other_actor = world.create_entity(
        RoomPresence(
            room=other_room._uid,
            presences=[],
        ),
    )

    world.update()

    # They only see themselves
    presence_cmpt = actor.get_component(RoomPresence)
    assert len(presence_cmpt.presences) == 1
    assert presence_cmpt.presences[0] == actor._uid
    other_presence_cmpt = actor.get_component(RoomPresence)
    assert len(other_presence_cmpt.presences) == 1
    assert other_presence_cmpt.presences[0] == actor._uid

    # Now let one actor change rooms
    actor.add_component(
        ChangeRoomAction(
            room=other_room._uid,
        ),
    )
    world.update()

    # Now they see each other.
    presence_cmpt = actor.get_component(RoomPresence)
    assert len(presence_cmpt.presences) == 2
    assert actor._uid in presence_cmpt.presences
    assert other_actor._uid in presence_cmpt.presences
    other_presence_cmpt = actor.get_component(RoomPresence)
    assert len(other_presence_cmpt.presences) == 2
    assert actor._uid in other_presence_cmpt.presences
    assert other_actor._uid in other_presence_cmpt.presences


def test_is_in_room(world):
    world.add_system(PerceiveRoom(), 0)

    # A room, and an actor and an item in the roomless void.
    room = world.create_entity(
        Room(
            adjacent=[],
            presences=[],
            arrived=[],
            continued=[],
            gone=[],
        ),
    )
    actor = world.create_entity()
    item = world.create_entity()

    assert not is_in_room(item, actor)
    with pytest.raises(EntityNotInARoom):
        is_in_room(item, actor, throw_exc=True)

    # Now the actor is in the room.
    actor.add_component(
        RoomPresence(
            room=room._uid,
            presences=[],
        ),
    )
    world.update()

    assert not is_in_room(item, actor)
    with pytest.raises(ItemNotInARoom):
        is_in_room(item, actor, throw_exc=True)

    # And now the item is there, too.
    item.add_component(
        RoomPresence(
            room=room._uid,
            presences=[],
        ),
    )
    world.update()

    assert is_in_room(item, actor)


def test_cant_change_to_non_adjacent_room(world):
    world.add_system(ChangeRoom(throw_exc=True), 0)
    world.add_system(PerceiveRoom(), 1)

    # Two connected rooms, an actor in each
    room = world.create_entity(
        Room(
            adjacent=[],
            presences=[],
            arrived=[],
            continued=[],
            gone=[],
        ),
    )
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
        RoomPresence(
            room=room._uid,
            presences=[],
        ),
        ChangeRoomAction(
            room=other_room._uid,
        ),
    )

    with pytest.raises(RoomsNotAdjacent):
        world.update()


def test_cant_change_to_current_room(world):
    # This test and the next are more of an informative nature. Since
    # a room is usually not adjacent to itself, you can't change from
    # it to it.
    world.add_system(ChangeRoom(throw_exc=True), 0)
    world.add_system(PerceiveRoom(), 1)
    room = world.create_entity(
        Room(
            adjacent=[],
            presences=[],
            arrived=[],
            continued=[],
            gone=[],
        ),
    )
    actor = world.create_entity(
        RoomPresence(
            room=room._uid,
            presences=[],
        ),
        ChangeRoomAction(
            room=room._uid,
        ),
    )

    with pytest.raises(RoomsNotAdjacent):
        world.update()


def test_can_change_to_current_room(world):
    # But we *can* make rooms circular in nature.
    # I don't know what the point of this is supposed to be. Maybe
    # someone in the future will have a use case for this.
    world.add_system(ChangeRoom(throw_exc=True), 0)
    world.add_system(PerceiveRoom(), 1)
    room = world.create_entity()
    room.add_component(
        Room(
            adjacent=[room._uid],
            presences=[],
            arrived=[],
            continued=[],
            gone=[],
        ),
    )
    actor = world.create_entity(
        RoomPresence(
            room=room._uid,
            presences=[],
        ),
    )
    # Let's update to have a clean room state.
    world.update()

    actor.add_component(
        ChangeRoomAction(
            room=room._uid,
        ),
    )
    world.update()
    room_cmpt = room.get_component(Room)
    assert len(room_cmpt.presences) == 1
    assert actor._uid in room_cmpt.presences
    assert len(room_cmpt.arrived) == 0
    assert len(room_cmpt.continued) == 1
    assert actor._uid in room_cmpt.continued
    assert len(room_cmpt.gone) == 0

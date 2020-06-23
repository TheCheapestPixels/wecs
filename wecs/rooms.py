from dataclasses import field

from wecs.core import Component, System, UID, and_filter


# Rooms, and being in a room
@Component()
class Room:
    # Neighboring room entities
    adjacent: list = field(default_factory=list)
    # Entities (thought to be) in the room
    presences: list = field(default_factory=list)
    # Presence entered the room
    arrived: list = field(default_factory=list)
    # Presence continues to be present
    continued: list = field(default_factory=list)
    # Presences that left the room
    gone: list = field(default_factory=list)


@Component()
class RoomPresence:
    room: UID
    # Entities perceived
    presences: list = field(default_factory=list)


@Component()
class ChangeRoomAction:
    room: UID  # Room to change to


class EntityNotInARoom(Exception): pass


class ItemNotInARoom(Exception): pass


class RoomsNotAdjacent(Exception): pass


def is_in_room(item, entity, throw_exc=False):
    if not entity.has_component(RoomPresence):
        if throw_exc:
            raise EntityNotInARoom
        else:
            return False
    presence = entity.get_component(RoomPresence)

    if item._uid not in presence.presences:
        if throw_exc:
            raise ItemNotInARoom
        else:
            return False

    return True


class PerceiveRoom(System):
    entity_filters = {
        'room': and_filter([Room]),
        'presences': and_filter([RoomPresence]),
    }

    def update(self, filtered_entities):
        # Clean the bookkeeping lists
        for entity in filtered_entities['room']:
            room = entity.get_component(Room)
            room.arrived = []
            room.continued = []
            room.gone = []
        # New arrivals to rooms, and continued presences
        for entity in filtered_entities['presences']:
            room_uid = entity.get_component(RoomPresence).room
            room_entity = self.world.get_entity(room_uid)
            room = room_entity.get_component(Room)
            if entity._uid not in room.presences:
                room.arrived.append(entity._uid)
            else:
                room.continued.append(entity._uid)
        # Checking who is gone
        for entity in filtered_entities['room']:
            room = entity.get_component(Room)
            for presence in room.presences:
                if presence not in room.continued:
                    room.gone.append(presence)
        # Rebuilding the presence lists
        for entity in filtered_entities['room']:
            room = entity.get_component(Room)
            room.presences = room.arrived + room.continued
        # Let the presences perceive the presences in the room
        for entity in filtered_entities['presences']:
            presence = entity.get_component(RoomPresence)
            room_entity = self.world.get_entity(presence.room)
            room = room_entity.get_component(Room)
            presence.presences = room.presences


class ChangeRoom(System):
    entity_filters = {
        'act': and_filter([ChangeRoomAction, RoomPresence])
    }

    def update(self, filtered_entities):
        for entity in filtered_entities['act']:
            room = self.world.get_entity(
                entity.get_component(RoomPresence).room,
            )
            target = entity.get_component(ChangeRoomAction).room

            if target not in room.get_component(Room).adjacent:
                if self.throw_exc:
                    raise RoomsNotAdjacent
            else:
                entity.get_component(RoomPresence).room = target

            entity.remove_component(ChangeRoomAction)

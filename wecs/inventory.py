from dataclasses import field

from wecs.core import Component, System, UID, NoSuchUID, and_filter
from wecs.rooms import RoomPresence


@Component()
class Inventory:
    contents: list = field(default_factory=list)


@Component()
class Takeable:
    pass


@Component()
class TakeAction:
    item: UID


@Component()
class DropAction:
    item: UID


class ItemNotInRoom(Exception): pass
class ItemNotInInventory(Exception): pass
class ActorHasNoInventory(Exception): pass
class ActorNotInRoom(Exception): pass
class NotTakeable(Exception): pass


def is_in_inventory(item, entity, throw_exc=False):
    # If I have an inventory...
    if not entity.has_component(Inventory):
        if throw_exc:
            raise ActorHasNoInventory
        return False
    inventory = entity.get_component(Inventory).contents

    # ...and the item is in it...
    if item._uid not in inventory:
        if throw_exc:
            raise ItemNotInInventory
        return False

    # ...then it... is in the inventory.
    return True


def can_take(item, entity, throw_exc=False):
    # If I have an inventory...
    if not entity.has_component(Inventory):
        if throw_exc:
            raise ActorHasNoInventory
        return False
    inventory = entity.get_component(Inventory).contents

    # ...and I am somewhere...
    if not entity.has_component(RoomPresence):
        if throw_exc:
            raise ActorNotInRoom
        return False
    presence = entity.get_component(RoomPresence)

    # ...and there is also an item there...
    if not item._uid in presence.presences:
        if throw_exc:
            raise ItemNotInRoom
        return False

    # ...that can be taken...
    if not item.has_component(Takeable):
        if throw_exc:
            raise NotTakeable
        return False

    # ...then the item can be taken.
    return True


def can_drop(item, entity, throw_exc=False):
    # If I have an inventory...
    if not entity.has_component(Inventory):
        if throw_exc:
            raise ActorHasNoInventory
        return False
    inventory = entity.get_component(Inventory).contents

    # ...with an item...
    if item._uid not in inventory:
        if throw_exc:
            raise ItemNotInInventory
        return False

    # ...that can be dropped...
    if not item.has_component(Takeable):
        if throw_exc:
            raise NotTakeable
        return False

    # ...and there is somewhere to drop it into, ...
    if not entity.has_component(RoomPresence):
        if throw_exc:
            raise ActorNotInRoom
        return False

    # ...then drop it like it's hot, drop it like it's hot.
    return True


def take(item, entity):
    item.remove_component(RoomPresence)
    entity.get_component(Inventory).contents.append(item._uid)


def drop(item, entity):
    room_uid = entity.get_component(RoomPresence).room
    inventory = entity.get_component(Inventory).contents
    idx = inventory.index(item._uid)
    del inventory[idx]
    item.add_component(RoomPresence(room=room_uid))


class TakeOrDrop(System):
    entity_filters = {
        'take': and_filter([TakeAction]),
        'drop': and_filter([DropAction]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['take']:
            action = entity.get_component(TakeAction)
            try:
                item = self.world.get_entity(action.item)
                if can_take(item, entity, self.throw_exc):
                    take(item, entity)
            except NoSuchUID:
                if self.throw_exc:
                    raise
            entity.remove_component(TakeAction)
        for entity in entities_by_filter['drop']:
            item = self.world.get_entity(entity.get_component(DropAction).item)
            entity.remove_component(DropAction)
            if can_drop(item, entity, self.throw_exc):
                drop(item, entity)

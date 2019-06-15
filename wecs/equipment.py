from typing import List

from wecs.core import Component
from wecs.core import System
from wecs.core import UID
from wecs.core import and_filter
from wecs.rooms import Room
from wecs.rooms import RoomPresence
from wecs.rooms import is_in_room
from wecs.inventory import Inventory
from wecs.inventory import is_in_inventory


@Component()
class Equipment:
    # Contains entities with Slot component
    slots: List[UID]


@Component()
class Slot:
    # An entity must have a component of this type to be equippable
    # in this slot
    type: type
    content: UID # The actual item


@Component()
class Equippable:
    # Identifies the kind of slot that this item can be equipped in
    type: type


@Component()
class EquipAction:
    item: UID
    slot: UID


@Component()
class UnequipAction:
    slot: UID
    target: UID


def is_equippable_in_slot(item, slot, entity):
    # If the item is equippable...
    if not item.has_component(Equippable):
        return False

    # ...and the item can be picked up...
    if not is_in_inventory(item, entity) and not is_in_room(item, entity):
        return False

    # ...and the avatar has this slot in his equipment...
    # FIXME: Implement
    slot_cmpt = slot.get_component(Slot)

    # ...and the slot is empty...
    if slot_cmpt.content is not None:
        return False

    # ...of corresponding type,...
    slot_type = slot_cmpt.type
    item_type = item.get_component(Equippable).type
    if slot_type is not item_type:
        return False

    # ...then the item is equippable.
    return True


def can_equip(item, slot, entity):
    if not is_equippable_in_slot(item, slot, entity):
        return False

    if not is_in_room(item, entity) and not is_in_inventory(item, entity):
        return False

    return True


def can_unequip(slot, entity):
    has_inventory = entity.has_component(Inventory)
    is_in_room = entity.has_component(RoomPresence)
    if not has_inventory and not is_in_room:
        return False
    return True


def equip(item, slot, entity):
    # FIXME!!! Just run the check once all tests have exc=True
    if not is_equippable_in_slot(item, slot, entity):
        return
    slot_cmpt = slot.get_component(Slot)

    if is_in_room(item, entity):
        item.remove_component(RoomPresence)
        slot_cmpt.content = item._uid
    elif is_in_inventory(item, entity):
        inventory = entity.get_component(Inventory)
        del inventory.contents[inventory.contents.index(item._uid)]
        slot_cmpt.content = item._uid


# FIXME: No world arg once getting UID fields produces entities
def unequip(slot, target, entity, world):
    slot_cmpt = slot.get_component(Slot)
    item_uid = slot_cmpt.content

    if target.has_component(Room):
        slot_cmpt.content = None
        item = world.get_entity(item_uid)
        item.add_component(RoomPresence(room=target._uid, presences=[]))
    elif target.has_component(Inventory):
        inventory = target.get_component(Inventory)
        slot_cmpt.content = None
        inventory.contents.append(item_uid)
    else:
        print("Unequipping failed.")


class EquipOrUnequip(System):
    entity_filters = {
        'equip': and_filter([EquipAction]),
        'unequip': and_filter([UnequipAction]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['unequip']:
            action = entity.get_component(UnequipAction)
            entity.remove_component(UnequipAction)

            slot = self.world.get_entity(action.slot)
            target = self.world.get_entity(action.target)
            unequip(slot, target, entity, self.world)

        for entity in entities_by_filter['equip']:
            action = entity.get_component(EquipAction)
            entity.remove_component(EquipAction)

            item = self.world.get_entity(action.item)
            slot = self.world.get_entity(action.slot)
            equip(item, slot, entity)

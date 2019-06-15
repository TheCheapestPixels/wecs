from typing import List

from wecs.core import Component, System, UID, and_filter


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


@Component()
class UnequipAction:
    item: UID


class EquipOrUnequip(System):
    entities_filter = {
        'equip': and_filter([EquipAction]),
        'unequip': and_filter([UnequipAction]),
    }

    def update(self, entities_by_filter):
        for entity in entities_by_filter['unequip']:
            pass
        for entity in entities_by_filter['equip']:
            pass

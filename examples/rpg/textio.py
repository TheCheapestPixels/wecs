from wecs.core import Component
from wecs.core import System
from wecs.core import and_filter
from wecs.core import or_filter
from wecs.rooms import Room
from wecs.rooms import RoomPresence
from wecs.rooms import ChangeRoomAction
from wecs.inventory import Inventory
from wecs.inventory import Takeable
from wecs.inventory import TakeAction
from wecs.inventory import DropAction
from wecs.inventory import TakeDropMixin

from lifecycle import Alive
from lifecycle import Health
from lifecycle import Dead
from lifecycle import Undead
from magic import Mana
from aging import Age
from character import Name
from dialogue import TalkAction
from components import Action


# This component will try trigger printin data about itself, but it
# needs at least a Name and some component it knows how to print as
# enablers.
@Component()
class Output:
    pass


# This component will make a system ask for command input. Needs two
# enablers, Name (to query for the character to control) and Action
# (to store the given command).
@Component()
class Input:
    pass


class TextOutputMixin():
    def textual_entity_state(self, entity):
        o = "" # Output accumulator

        # Name
        if entity.has_component(Name):
            name = entity.get_component(Name).name
        else:
            name = "Avatar"

        # Lifecycle status
        if entity.has_component(Alive):
            o += "{} is alive.\n".format(name)
        if entity.has_component(Dead):
            o += "{} is dead.\n".format(name)
        if entity.has_component(Undead):
            o += "{} is undead.\n".format(name)

        # Age
        if entity.has_component(Age):
            age = entity.get_component(Age).age
            frailty = entity.get_component(Age).age_of_frailty
            o += "{}'s age: ".format(name)
            o += "{}/{}".format(age, frailty)
            if age >= frailty:
                o += " (frail)"
            o += "\n"

        # Health
        if entity.has_component(Health):
            o += "{}'s health: {}/{}.\n".format(
                entity.get_component(Name).name,
                entity.get_component(Health).health,
                entity.get_component(Health).max_health,
            )

        # Mana
        if entity.has_component(Mana):
            o += "{}'s mana: {}/{}.\n".format(
                entity.get_component(Name).name,
                entity.get_component(Mana).mana,
                entity.get_component(Mana).max_mana,
            )

        # Castable spells
        if entity.has_component(Mana):
            o += "{} can cast: {}\n".format(
                entity.get_component(Name).name,
                ', '.join(entity.get_component(Mana).spells_ready),
            )
        return o

    def textual_room_state(self, entity):
        o = "" # Output accumulator

        # Name
        if entity.has_component(Name):
            name = entity.get_component(Name).name
        else:
            name = "Avatar"

        # Presence in a room
        if not entity.has_component(RoomPresence):
            o += "{} is not anywhere.\n".format(name)
            return o

        # The room itself
        room_ref = entity.get_component(RoomPresence).room
        room = self.world.get_entity(room_ref)
        if not room.has_component(Name):
            o += "{} is in a nameless room\n".format(name)
        else:
            room_name = room.get_component(Name).name
            o += "{} is the room '{}'\n".format(name, room_name)

        # Other presences in the room
        presences = entity.get_component(RoomPresence).presences
        if presences:
            names = []
            for idx, presence in enumerate(presences):
                present_entity = self.world.get_entity(presence)
                if present_entity.has_component(Name):
                    names.append("({}) {}".format(
                        str(idx),
                        present_entity.get_component(Name).name,
                    ))
            o += "In the room are: {}\n".format(', '.join(names))

        # Adjacent rooms
        nearby_rooms = room.get_component(Room).adjacent
        nearby_room_names = []
        for idx, nearby_room in enumerate(nearby_rooms):
            nearby_room_entity = self.world.get_entity(nearby_room)
            if nearby_room_entity.has_component(Name):
                nearby_room_names.append("({}) {}".format(
                    str(idx),
                    nearby_room_entity.get_component(Name).name,
                ))
            else:
                nearby_room_names.append("({}) (unnamed)".format(str(idx)))
        o += "Nearby rooms: {}\n".format(', '.join(nearby_room_names))

        return o

    def print_entity_state(self, entity):
        o = self.textual_entity_state(entity)
        print(o)
        # If we have written any text yet, let's add a readability
        # newline.
        if o != "":
            o += "\n"

        o = self.textual_room_state(entity)
        print(o)
        # If we have written any text yet, let's add a readability
        # newline.
        if o != "":
            o += "\n"


class ShellMixin(TakeDropMixin):
    def shell(self, entity):
        if entity.has_component(Name):
            name = entity.get_component(Name).name
        else:
            name = "Avatar"
        query = "Command for {}: ".format(
            name,
        )
        while not self.run_command(input(query), entity):
            pass

    def run_command(self, command, entity):
        if entity.has_component(Dead):
            print("You are dead. You do nothing.")
            return True
        if command in ("i", "inventory"):
            self.show_inventory(entity)
            return False # Instant action
        if command == "l" or command.startswith("look "):
            self.look_at(entity, int(command[5:]))
            return False # Instant action
        elif command.startswith("take "):
            return self.take_command(entity, int(command[5:]))
        elif command.startswith("drop "):
            return self.drop_command(entity, int(command[5:]))
        elif command.startswith("go "):
            return self.change_room_command(entity, int(command[3:]))
        elif command.startswith("talk "):
            return self.talk_command(entity, int(command[5:]))
        else:
            # FIXME: Replace this by individual FooAction components.
            # Currently pending:
            # * SpellcastingMixin
            # * Individual spells
            # Then systems.py and components.py can be retired.
            entity.get_component(Action).plan = command
            return True
        print("Unknown command \"{}\"".format(command))
        return False

    def take_command(self, entity, object_id):
        if not entity.has_component(RoomPresence):
            print("Can't take objects from the roomless void.")
            return False
        presences = entity.get_component(RoomPresence).presences

        item = self.world.get_entity(presences[object_id])
        if self.can_take(item, entity):
            entity.add_component(TakeAction(item=item._uid))
            return True

        return False

    def drop_command(self, entity, object_id):
        # If I have an inventory...
        if not entity.has_component(Inventory):
            print("{} has no inventory.".format(name))
            return False

        inventory = entity.get_component(Inventory).contents
        item = self.world.get_entity(inventory[object_id])

        if self.can_drop(item, entity):
            entity.add_component(DropAction(item=item._uid))
            return True

        return False

    def change_room_command(self, entity, target_idx):
        if not entity.has_component(RoomPresence):
            print("You have no presence that could be somewhere.")
            return False

        room_e = self.world.get_entity(entity.get_component(RoomPresence).room)
        room = room_e.get_component(Room)
        if target_idx < 0 or target_idx > len(room.adjacent):
            print("No such room.")
            return False

        target = room.adjacent[target_idx]
        entity.add_component(ChangeRoomAction(room=target))
        return True

    def talk_command(self, entity, target_idx):
        # FIXME: Sooo many assumptions in this line...
        talker = entity.get_component(RoomPresence).presences[target_idx]
        entity.add_component(TalkAction(talker=talker))
        return True

    def show_inventory(self, entity):
        if entity.has_component(Name):
            name = entity.get_component(Name).name
        else:
            name = "Avatar"

        if not entity.has_component(Inventory):
            print("{} has no inventory.".format(name))
            return False

        # FIXME: try/except NoSuchUID:
        contents = [self.world.get_entity(e)
                    for e in entity.get_component(Inventory).contents]
        if len(contents) == 0:
            print("{}'s inventory is empty".format(name))
            return False

        content_names = []
        for idx, content in enumerate(contents):
            if content.has_component(Name):
                content_names.append(
                    "({}) {}".format(
                        str(idx),
                        content.get_component(Name).name,
                    )
                )
            else:
                content_names.append("({}) (unnamed)".format(str(idx)))

        for entry in content_names:
            print(entry)
        return True

    def look_at(self, entity, lookee_idx):
        if not entity.has_component(RoomPresence):
            print("You are nowhere, so there's nothing to look at.")
            return False
        presences = entity.get_component(RoomPresence).presences

        if lookee_idx < 0 or lookee_idx > len(presences):
            print("Invalid room presence id.")
            return False
        lookee = self.world.get_entity(presences[lookee_idx])

        o = self.textual_entity_state(lookee)
        if o == "":
            print("There's nothing there to look at.")
            return False

        print(o)
        return True


class Shell(TextOutputMixin, ShellMixin, System):
    entity_filters = {
        'outputs': and_filter([Output]),
        'act': and_filter([Input])
    }

    def update(self, filtered_entities):
        outputters = filtered_entities['outputs']
        actors = filtered_entities['act']
        for entity in outputters:
            self.print_entity_state(entity)
            if entity in filtered_entities['act']:
                self.shell(entity)
        # Also give the actors without output a shell
        for entity in [e for e in actors if e not in outputters]:
            self.shell(entity)

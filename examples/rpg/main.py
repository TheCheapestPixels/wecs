import crayons

from wecs.core import World, Component, System
from wecs import rooms, inventory

# Game mechanics
import components
import lifecycle
import magic
import dialogue
import aging
import textio


world = World()
system_queue = [
    rooms.PerceiveRoom,
    aging.Aging,
    lifecycle.DieFromHealthLoss,
    magic.BecomeLich,
    lifecycle.Die,
    magic.RegenerateMana,
    magic.ReadySpells,
    textio.Shell,
    dialogue.HaveDialogue,
    inventory.TakeOrDrop,
    magic.CastRejuvenationSpell,
    magic.CastRestoreHealthSpell,
    magic.CastLichdomSpell,
    rooms.ChangeRoom,
]
for sort, system in enumerate(system_queue):
    world.add_system(system(), sort)


def make_basic_character_components():
    character_components = [
        lifecycle.Alive(),
        aging.Age(age=0, age_of_frailty=8),
        lifecycle.Health(health=10, max_health=10),
        components.Action(plan=''),
    ]
    return character_components


def make_standard_wizard_components():
    wizard_components = [
        magic.Mana(mana=5, max_mana=10, spells_ready=[]),
        magic.RejuvenationSpell(mana_cost=4, time_restored=5),
        magic.RestoreHealthSpell(mana_cost=2, health_restored=4),
        magic.LichdomSpell(mana_cost=10),
    ]
    return wizard_components


def make_player_character_components():
    player_character_components = [
        textio.Output(),
        textio.Input(),
    ]
    return player_character_components


# The room
room = world.create_entity()
other_room = world.create_entity()
room.add_component(rooms.Room(
    adjacent=[other_room._uid],
    presences=[],
    arrived=[],
    continued=[],
    gone=[],
))
room.add_component(textio.Name(name="Hall"))
other_room.add_component(rooms.Room(
    adjacent=[room._uid],
    presences=[],
    arrived=[],
    continued=[],
    gone=[],
))
other_room.add_component(textio.Name(name="Balcony"))

# Bob the wizard
entity = world.create_entity()
for c in make_basic_character_components():
    entity.add_component(c)
for c in make_standard_wizard_components():
    entity.add_component(c)
for c in make_player_character_components():
    entity.add_component(c)
entity.add_component(rooms.RoomPresence(room=room._uid, presences=[]))
entity.add_component(textio.Name(name="Bob the Wizard"))
entity.add_component(inventory.Inventory(contents=[]))


# Obo the Barbarian
entity = world.create_entity()
for c in make_basic_character_components():
    entity.add_component(c)
entity.add_component(rooms.RoomPresence(room=room._uid, presences=[]))
entity.add_component(textio.Name(name="Obo the Barbarian"))


# Ugu the Barbarian (not in the room)
entity = world.create_entity()
for c in make_basic_character_components():
    entity.add_component(c)
entity.add_component(textio.Name(name="Ugu the Barbarian"))


# Sasa the Innocent Bystander
entity = world.create_entity()
for c in make_basic_character_components():
    entity.add_component(c)
entity.add_component(rooms.RoomPresence(
    room=other_room._uid,
    presences=[],
))
entity.add_component(textio.Name(name="Sasa the Innocent Bystander"))
entity.add_component(dialogue.Dialogue(phrase="What a beautiful sight."))


# A flask
entity = world.create_entity()
entity.add_component(textio.Name(name="a potion flask"))
entity.add_component(inventory.Takeable())
entity.add_component(rooms.RoomPresence(room=room._uid, presences=[]))


# A necklace
entity = world.create_entity()
entity.add_component(textio.Name(name="a necklace"))
entity.add_component(inventory.Takeable())
entity.add_component(rooms.RoomPresence(room=other_room._uid, presences=[]))


def generate_dependency_graphs():
    from wecs.graphviz import system_component_dependency

    # Systems grouped by... well, grouped.
    systems_groups={
        'Magic': [
            magic.BecomeLich,
            magic.RegenerateMana,
            magic.ReadySpells,
        ],
        'Casting_spells': [
            magic.CastRejuvenationSpell,
            magic.CastRestoreHealthSpell,
            magic.CastLichdomSpell,
        ],
        'IO': [
            textio.PrintOutput,
            textio.ReadInput,
        ],
        'Lifecycle': [
            aging.Aging,
            lifecycle.DieFromHealthLoss,
            lifecycle.Die,
        ],
    }

    # Make sure that the list above covers all the systems
    all_systems = set()
    for l in systems_groups.values():
        all_systems.update(l)
    assert all([type(s) in all_systems for s in world.systems.values()])

    # ...and render!
    system_component_dependency(world, systems_groups=systems_groups)


# generate_dependency_graphs()

commands = """
Actions that take time:
  spell name: cast spell.
  go <id>: go into a room.
  talk <id>: talk to someone.
  take <id>: take object and put it in the inventory
  drop <id>: take object out of the inventory and drop it
Instant actions:
  i, inventory: show inventory contents
"""
print(commands)
i = 0
while True:
    i += 1
    print(crayons.cyan("\n--- Timestep {}".format(i)))
    world.update()

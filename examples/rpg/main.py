from wecs.core import World, Component, System

import systems
import components


world = World()
system_queue = [
    systems.PerceiveRoom,
    systems.Aging,
    systems.DieFromHealthLoss,
    systems.BecomeLich,
    systems.Die,
    systems.RegenerateMana,
    systems.ReadySpells,
    systems.PrintOutput,
    systems.ReadInput,
    systems.ChangeRoom,
    systems.CastRejuvenationSpell,
    systems.CastRestoreHealthSpell,
    systems.CastLichdomSpell,
]
for sort, system in enumerate(system_queue):
    world.add_system(system(), sort)


def make_basic_character_components():
    character_components = [
        components.Alive(),
        components.Age(age=0, age_of_frailty=8),
        components.Health(health=10, max_health=10),
        components.Action(plan=''),
    ]
    return character_components


def make_standard_wizard_components():
    wizard_components = [
        components.Mana(mana=5, max_mana=10, spells_ready=[]),
        components.RejuvenationSpell(mana_cost=4, time_restored=5),
        components.RestoreHealthSpell(mana_cost=2, health_restored=4),
        components.LichdomSpell(mana_cost=10),
    ]
    return wizard_components


def make_player_character_components():
    player_character_components = [
        components.Output(),
        components.Input(),
    ]
    return player_character_components


# The room
room = world.create_entity()
other_room = world.create_entity()
room.add_component(components.Room(
    adjacent=[other_room._uid],
    presences=[],
    arrived=[],
    continued=[],
    gone=[],
))
room.add_component(components.Name(name="Hall"))
other_room.add_component(components.Room(
    adjacent=[room._uid],
    presences=[],
    arrived=[],
    continued=[],
    gone=[],
))
other_room.add_component(components.Name(name="Balcony"))

# Bob the wizard
entity = world.create_entity()
for c in make_basic_character_components():
    entity.add_component(c)
for c in make_standard_wizard_components():
    entity.add_component(c)
for c in make_player_character_components():
    entity.add_component(c)
entity.add_component(components.RoomPresence(room=room._uid, presences=[]))
entity.add_component(components.Name(name="Bob the Wizard"))


# Obo the Barbarian
entity = world.create_entity()
for c in make_basic_character_components():
    entity.add_component(c)
entity.add_component(components.RoomPresence(room=room._uid, presences=[]))
entity.add_component(components.Name(name="Obo the Barbarian"))


# Ugu the Barbarian (not in the room)
entity = world.create_entity()
for c in make_basic_character_components():
    entity.add_component(c)
entity.add_component(components.Name(name="Ugu the Barbarian"))


# Sasa the Innocent Bystander
entity = world.create_entity()
for c in make_basic_character_components():
    entity.add_component(c)
entity.add_component(components.RoomPresence(
    room=other_room._uid,
    presences=[],
))
entity.add_component(components.Name(name="Sasa the Innocent Bystander"))


def generate_dependency_graphs():
    from wecs.graphviz import system_component_dependency

    # Systems grouped by... well, grouped.
    systems_groups={
        'Magic': [
            systems.BecomeLich,
            systems.RegenerateMana,
            systems.ReadySpells,
        ],
        'Casting_spells': [
            systems.CastRejuvenationSpell,
            systems.CastRestoreHealthSpell,
            systems.CastLichdomSpell,
        ],
        'IO': [
            systems.PrintOutput,
            systems.ReadInput,
        ],
        'Lifecycle': [
            systems.Aging,
            systems.DieFromHealthLoss,
            systems.Die,
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
Commands:
  spell name to cast spell.
  go <room id> to go into a room.
"""
print(commands)
i = 0
while True:
    i += 1
    print("\n--- Timestep {}".format(i))
    world.update()

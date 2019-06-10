from wecs.core import World, Component, System

import systems
import components


world = World()
system_queue = [
    systems.Aging,
    systems.DieFromHealthLoss,
    systems.BecomeLich,
    systems.Die,
    systems.RegenerateMana,
    systems.ReadySpells,
    systems.PrintOutput,
    systems.ReadInput,
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


def make_non_player_character_components():
    player_character_components = [
        components.Output(),
    ]
    return player_character_components


entity = world.add_entity()
for c in make_basic_character_components():
    entity.add_component(c)
for c in make_standard_wizard_components():
    entity.add_component(c)
for c in make_player_character_components():
    entity.add_component(c)
entity.add_component(components.Name(name="Bob the Wizard"))


entity = world.add_entity()
for c in make_basic_character_components():
    entity.add_component(c)
for c in make_non_player_character_components():
    entity.add_component(c)
#entity.add_component(components.Name(name="Obo the Barbarian"))


entity = world.add_entity()
for c in make_basic_character_components():
    entity.add_component(c)
for c in make_non_player_character_components():
    entity.add_component(c)
#entity.add_component(components.Name(name="Ugu the Barbarian"))


def generate_dependency_graphs():
    from wecs.graphviz import system_component_dependency

    # Systems grouped by... well, grouped.
    systems_groups={
        'Magic': [
            systems.BecomeLich,
            systems.RegenerateMana,
            systems.ReadySpells,
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


generate_dependency_graphs()


i = 0
while True:
    i += 1
    print("\n--- Timestep {}".format(i))
    world.update()

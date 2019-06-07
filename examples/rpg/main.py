from wecs.core import World, Component, System

import systems
import components

world = World()
systems = [
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
for sort, system in enumerate(systems):
    world.add_system(system(), sort)


def make_basic_character_components():
    character_components = [
        components.Alive(),
        components.Age(age=0),
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
entity.add_component(components.Name(name="Obo the Barbarian"))


entity = world.add_entity()
for c in make_basic_character_components():
    entity.add_component(c)
for c in make_non_player_character_components():
    entity.add_component(c)
entity.add_component(components.Name(name="Ugu the Barbarian"))


i = 0
while True:
    i += 1
    print("\n--- Timestep {}".format(i))
    world.update()

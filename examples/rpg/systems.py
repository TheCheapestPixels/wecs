from wecs.core import System, and_filter, or_filter

from components import Name
from components import Age
from components import Alive
from components import Dying
from components import Dead
from components import Undead
from components import Health
from components import Mana
from components import RejuvenationSpell
from components import RestoreHealthSpell
from components import LichdomSpell
from components import LichdomSpellEffect
from components import Output
from components import Input
from components import Action


spells = [RejuvenationSpell, RestoreHealthSpell, LichdomSpell]


class Aging(System):
    entity_filters = {
        'has_age': and_filter([Age]),
        'grows_frail': and_filter([Age, Alive, Health]),
    }

    def update(self, filtered_entities):
        for entity in filtered_entities['has_age']:
            entity.get_component(Age).age += 1
        for entity in filtered_entities['grows_frail']:
            if entity.get_component(Age).age > 8:
                entity.get_component(Health).health -= 1


class RegenerateMana(System):
    entity_filters = {
        'has_mana': and_filter([Mana]),
    }

    def update(self, filtered_entities):
        for entity in filtered_entities['has_mana']:
            c = entity.get_component(Mana)
            if c.mana < c.max_mana:
                c.mana += 1


class ReadySpells(System):
    entity_filters = {
        'all_casters': and_filter([Mana]),
        'rejuvenation': and_filter([Mana, Age, Alive, RejuvenationSpell]),
        'restore_health': and_filter([
            and_filter([Mana, Health, RestoreHealthSpell]),
            or_filter([Alive, Undead]),
        ]),
        'lichdom': and_filter([Mana, Health, Alive, LichdomSpell]),
    }

    def update(self, filtered_entities):
        for entity in filtered_entities['all_casters']:
            entity.get_component(Mana).spells_ready = []

        for spell in spells:
            entities = filtered_entities[spell.name]
            for entity in entities:
                mana_cost = entity.get_component(spell).mana_cost
                if entity.get_component(Mana).mana >= mana_cost:
                    entity.get_component(Mana).spells_ready.append(spell.name)


class DieFromHealthLoss(System):
    entity_filters = {
        'is_living': and_filter([Health, Alive]),
    }

    def update(self, filtered_entities):
        for entity in set(filtered_entities['is_living']):
            if entity.get_component(Health).health <= 0:
                entity.remove_component(Alive)
                entity.add_component(Dying())


class BecomeLich(System):
    entity_filters = {
        'is_transforming': and_filter([Dying, LichdomSpellEffect]),
        'has_health': and_filter([Dying, LichdomSpellEffect, Health]),
    }

    def update(self, filtered_entities):
        transforming = set(filtered_entities['is_transforming'])
        has_health = set(filtered_entities['has_health'])
        for entity in transforming:
            print("LICHDOM SPELL TAKES EFFECT!")
            entity.remove_component(Dying)
            entity.remove_component(LichdomSpellEffect)
            entity.add_component(Undead())
        for entity in has_health:
            health = entity.get_component(Health)
            health.health = int(health.max_health / 2)


class Die(System):
    entity_filters = {
        'is_dying': and_filter([Dying]),
    }

    def update(self, filtered_entities):
        for entity in set(filtered_entities['is_dying']):
            entity.remove_component(Dying)
            entity.add_component(Dead())


class PrintOutput(System):
    entity_filters = {
        'all_outputters': and_filter([Name, Output]),
        'print_alive': and_filter([Alive, Name, Output]),
        'print_dead': and_filter([Dead, Name, Output]),
        'print_undead': and_filter([Undead, Name, Output]),
        'print_age': and_filter([Age, Name, Output]),
        'print_mana': and_filter([Mana, Name, Output]),
        'print_health': and_filter([Health, Name, Output]),
        'print_can_cast': and_filter([Mana, Name, Output]),
    }

    def update(self, filtered_entities):
        for entity in filtered_entities['all_outputters']:
            if entity in filtered_entities['print_age']:
                print("{} is {} time old.".format(
                    entity.get_component(Name).name,
                    entity.get_component(Age).age,
                ))
            if entity in filtered_entities['print_alive']:
                print("{} is alive.".format(
                    entity.get_component(Name).name,
                ))
            if entity in filtered_entities['print_dead']:
                print("{} is dead.".format(
                    entity.get_component(Name).name,
                ))
            if entity in filtered_entities['print_undead']:
                print("{} is undead.".format(
                    entity.get_component(Name).name,
                ))
            if entity in filtered_entities['print_health']:
                print("{} is {} healthy.".format(
                    entity.get_component(Name).name,
                    entity.get_component(Health).health,
                ))
            if entity in filtered_entities['print_mana']:
                print("{} has {} mana.".format(
                    entity.get_component(Name).name,
                    entity.get_component(Mana).mana,
                ))
            if entity in filtered_entities['print_can_cast']:
                print("{} can cast: {}".format(
                    entity.get_component(Name).name,
                    ', '.join(entity.get_component(Mana).spells_ready),
                ))


class ReadInput(System):
    entity_filters = {
        'act': and_filter([Input, Action, Name])
    }

    def update(self, filtered_entities):
        for entity in filtered_entities['act']:
            name = entity.get_component(Name).name
            query = "Command for {} (enter spell name or nothing): ".format(
                name,
            )
            command = input(query)
            entity.get_component(Action).plan = command


class CastRejuvenationSpell(System):
    entity_filters = {
        'cast_spell': and_filter([Action, Mana, RejuvenationSpell, Age, Alive]),
    }

    def update(self, filtered_entities):
        for entity in filtered_entities['cast_spell']:
            if entity.get_component(Action).plan == 'rejuvenation':
                mana = entity.get_component(Mana)
                if 'rejuvenation' in mana.spells_ready:
                    spell = entity.get_component(RejuvenationSpell)
                    age = entity.get_component(Age)
                    mana.mana -= spell.mana_cost
                    age.age -= spell.time_restored
                    print("REJUVENATION SPELL CAST!")
                else:
                    print("Not enough mana for rejuvenation spell.")
                entity.get_component(Action).plan = None


class CastRestoreHealthSpell(System):
    entity_filters = {
        'cast_spell': and_filter(
            [
                and_filter([Action, Mana, Health, RestoreHealthSpell]),
                or_filter([Alive, Undead]),
            ],
        ),
    }

    def update(self, filtered_entities):
        for entity in filtered_entities['cast_spell']:
            if entity.get_component(Action).plan == 'restore_health':
                spell = entity.get_component(RestoreHealthSpell)
                mana = entity.get_component(Mana)
                if 'restore_health' in mana.spells_ready:
                    mana.mana -= spell.mana_cost
                    print("RESTORE HEALTH CAST!")
                    health = entity.get_component(Health)
                    health.health += spell.health_restored
                    if health.health > health.max_health:
                        health.health = health.max_health
                else:
                    print("Not enough mana to restore health.")
                entity.get_component(Action).plan = None


class CastLichdomSpell(System):
    entity_filters = {
        'cast_spell': and_filter(
            [
                and_filter([Action, Mana, LichdomSpell, Alive]),
                # not_filter([LichdomSpellEffect])
            ],
        ),
    }

    def update(self, filtered_entities):
        for entity in filtered_entities['cast_spell']:
            if entity.get_component(Action).plan == 'lichdom':
                spell = entity.get_component(LichdomSpell)
                mana = entity.get_component(Mana)
                if mana.mana >= spell.mana_cost:
                    mana.mana -= spell.mana_cost
                    if entity.has_component(LichdomSpellEffect):
                        print("SPELL FAILS, already under its effect.")
                    else:
                        entity.add_component(LichdomSpellEffect())
                        print("LICHDOM SPELL CAST!")
                else:
                    print("Not enough mana for lichdom spell.")
                entity.get_component(Action).plan = None

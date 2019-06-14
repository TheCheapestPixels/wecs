from wecs.core import Component, System, and_filter, or_filter

from aging import Age
from components import Action
from lifecycle import Health, Alive, Dying, Undead


@Component()
class Mana:
    max_mana: int
    mana: int
    spells_ready: list # Currently castable spells


# Spells
# FooSpell is a character's knowledge of a spell.
# FooSpellCasting is the action that a character does to cast a spell.
# FooSpellEffect is the effect of a spell that's lingering on an
#   entity.
# FooSpell.name is used to indicate the Action.plan symbol that causes casting
#   this spell, and the Mana.spells_ready entry indicating that it can be cast.
# CastFooSpell is the system for casting FooSpell.
# Before any CastFooSpell can be run, the system ReadySpells must have added
#   FooSpell.name to Mana.spells_ready this frame.

@Component()
class RejuvenationSpell:
    name = 'rejuvenation'
    mana_cost: int
    time_restored: int


@Component()
class RestoreHealthSpell:
    name = 'restore_health'
    mana_cost: int
    health_restored: int


@Component()
class LichdomSpell:
    name = 'lichdom'
    mana_cost: int


spells = [RejuvenationSpell, RestoreHealthSpell, LichdomSpell]


# Spell effects

@Component()
class LichdomSpellEffect:
    pass


# Caster systems

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


# Spell effects

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


# Casting

class SpellcastingMixin:
    def update(self, filtered_entities):
        for entity in filtered_entities['cast_spell']:
            if entity.get_component(Action).plan == self.spell_class.name:
                mana = entity.get_component(Mana)
                if self.spell_class.name in mana.spells_ready:
                    self.cast_spell(entity)
                else:
                    self.spell_not_ready(entity)


class CastRejuvenationSpell(System, SpellcastingMixin):
    entity_filters = {
        'cast_spell': and_filter([Action, Mana, RejuvenationSpell, Age, Alive]),
    }
    spell_class = RejuvenationSpell

    def update(self, filtered_entities):
        SpellcastingMixin.update(self, filtered_entities)

    def cast_spell(self, entity):
        mana = entity.get_component(Mana)
        spell = entity.get_component(self.spell_class)
        age = entity.get_component(Age)
        mana.mana -= spell.mana_cost
        age.age -= spell.time_restored
        if age.age < 0:
            age.age = 0
        print("REJUVENATION SPELL CAST!")
        entity.get_component(Action).plan = None

    def spell_not_ready(self, entity):
        entity.get_component(Action).plan = None


class CastRestoreHealthSpell(System, SpellcastingMixin):
    entity_filters = {
        'cast_spell': and_filter(
            [
                and_filter([Action, Mana, Health, RestoreHealthSpell]),
                or_filter([Alive, Undead]),
            ],
        ),
    }
    spell_class = RestoreHealthSpell

    def update(self, filtered_entities):
        SpellcastingMixin.update(self, filtered_entities)

    def cast_spell(self, entity):
        mana = entity.get_component(Mana)
        spell = entity.get_component(self.spell_class)
        age = entity.get_component(Age)
        health = entity.get_component(Health)

        mana.mana -= spell.mana_cost
        health.health += spell.health_restored
        if health.health > health.max_health:
            health.health = health.max_health
        print("RESTORE HEALTH CAST!")
        entity.get_component(Action).plan = None

    def spell_not_ready(self, entity):
        print("Not enough mana to restore health.")
        entity.get_component(Action).plan = None


class CastLichdomSpell(System, SpellcastingMixin):
    entity_filters = {
        'cast_spell': and_filter([Action, Mana, LichdomSpell, Alive]),
    }
    spell_class = LichdomSpell

    def update(self, filtered_entities):
        SpellcastingMixin.update(self, filtered_entities)

    def cast_spell(self, entity):
        mana = entity.get_component(Mana)
        spell = entity.get_component(self.spell_class)
        if entity.has_component(LichdomSpellEffect):
            mana.mana -= int(spell.mana_cost / 2)
            print("SPELL FAILS, already under its effect.")
        else:
            mana.mana -= spell.mana_cost
            entity.add_component(LichdomSpellEffect())
            print("LICHDOM SPELL CAST!")
        entity.get_component(Action).plan = None

    def spell_not_ready(self, entity):
        print("Not enough mana for lichdom spell.")
        entity.get_component(Action).plan = None

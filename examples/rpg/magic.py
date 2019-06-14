from wecs.core import Component, System, and_filter, or_filter

from aging import Age
from lifecycle import Health, Alive, Dying, Dead, Undead


@Component()
class Mana:
    max_mana: int
    mana: int
    spells_ready: list # Currently castable spells


# Spells
# FooSpell is a character's knowledge of a spell.
# CastingFooSpell is the action that a character does to cast a spell.
# FooSpellEffect is the effect of a spell that's lingering on an
#   entity.
# FooSpell.name is used to indicate the Action.plan symbol that causes casting
#   this spell, and the Mana.spells_ready entry indicating that it can be cast.
# CanCastFooMixin: Provides `.can_cast()` with special preconditions for the
#   particular spell.
# CastFooSpell is the system for casting FooSpell.
# Before any CastFooSpell can be run, the system ReadySpells must have added
#   FooSpell.name to Mana.spells_ready this frame.

@Component()
class CastingRejuvenationSpell:
    pass


@Component()
class RejuvenationSpell:
    name = 'rejuvenation'
    casting_action = CastingRejuvenationSpell
    mana_cost: int
    time_restored: int


@Component()
class CastingRestoreHealthSpell:
    pass


@Component()
class RestoreHealthSpell:
    name = 'restore_health'
    casting_action = CastingRestoreHealthSpell
    mana_cost: int
    health_restored: int


@Component()
class CastingLichdomSpell:
    pass


@Component()
class LichdomSpell:
    name = 'lichdom'
    casting_action = CastingLichdomSpell
    mana_cost: int


# Spell effects

@Component()
class LichdomSpellEffect:
    pass


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
            if self.can_cast(entity):
                self.cast(entity)
            entity.remove_component(self.spell_class.casting_action)

    def can_cast(self, entity, spell_class=None, readying=False):
        if spell_class is None:
            spell_class = self.spell_class

        # If the character is a caster...
        if not entity.has_component(Mana):
            if not readying:
                print("You're not a caster!")
            return False
        mana = entity.get_component(Mana)

        # ...who happens not to be dead...
        if entity.has_component(Dead):
            if not readying:
                print("Dead people don't cast spells.")
            return False

        # ...and knows the spell...
        if not entity.has_component(spell_class):
            if not readying:
                print("You do not know the spell.")
            return False
        spell = entity.get_component(spell_class)

        # ...and the spell is readied...
        if not readying and spell_class not in mana.spells_ready:
            if not readying:
                print("Spell not ready.")
            return False

        # ...and the caster has sufficient mana,...
        if not mana.mana >= spell.mana_cost:
            if not readying:
                print("Not enough mana.")
            return False

        # ...then it can be cast.
        return True


class CanCastRejuvenationMixin(SpellcastingMixin):
    def can_cast(self, entity, spell_class=None, readying=False):
        if not entity.has_component(Alive):
            if not readying:
                print("Only the living can cast rejuvenation.")
            return False

        if not entity.has_component(Age):
            if not readying:
                print("The spell doesn't affect the ageless.")
            return False

        return SpellcastingMixin.can_cast(
            self,
            entity,
            spell_class=spell_class,
            readying=readying,
        )


class CastRejuvenationSpell(CanCastRejuvenationMixin, System):
    entity_filters = {
        'cast_spell': and_filter([
            Mana,
            CastingRejuvenationSpell,
            Age,
            Alive]),
    }
    spell_class = RejuvenationSpell

    def update(self, filtered_entities):
        super().update(filtered_entities)

    def can_cast(self, entity):
        return super().can_cast(entity)

    def cast(self, entity):
        mana = entity.get_component(Mana)
        spell = entity.get_component(self.spell_class)
        age = entity.get_component(Age)

        mana.mana -= spell.mana_cost
        age.age -= spell.time_restored
        if age.age < 0:
            age.age = 0
        print("REJUVENATION SPELL CAST!")


class CanCastRestoreHealthMixin(SpellcastingMixin):
    def can_cast(self, entity, spell_class=None, readying=False):
        if not entity.has_component(Health):
            if not readying:
                print("You have no health to restore.")
            return False

        return SpellcastingMixin.can_cast(
            self,
            entity,
            spell_class=spell_class,
            readying=readying,
        )


class CastRestoreHealthSpell(CanCastRestoreHealthMixin, System):
    entity_filters = {
        'cast_spell': and_filter(
            [
                and_filter([
                    Mana,
                    Health,
                    CastingRestoreHealthSpell]),
                or_filter([Alive, Undead]),
            ],
        ),
    }
    spell_class = RestoreHealthSpell

    def update(self, filtered_entities):
        super().update(filtered_entities)

    def can_cast(self, entity):
        return CanCastRestoreHealthMixin.can_cast(self, entity)

    def cast(self, entity):
        mana = entity.get_component(Mana)
        spell = entity.get_component(self.spell_class)
        age = entity.get_component(Age)
        health = entity.get_component(Health)

        mana.mana -= spell.mana_cost
        health.health += spell.health_restored
        if health.health > health.max_health:
            health.health = health.max_health
        print("RESTORE HEALTH CAST!")


class CanCastLichdomMixin(SpellcastingMixin):
    def can_cast(self, entity, spell_class=None, readying=False):
        if not entity.has_component(Alive):
            if not readying:
                print("Only the living can cast rejuvenation.")
            return False

        return SpellcastingMixin.can_cast(
            self,
            entity,
            spell_class=spell_class,
            readying=readying,
        )


class CastLichdomSpell(CanCastLichdomMixin, System):
    entity_filters = {
        'cast_spell': and_filter([
            Mana,
            CastingLichdomSpell,
            Alive,
        ]),
    }
    spell_class = LichdomSpell

    def update(self, filtered_entities):
        super().update(filtered_entities)

    def cast(self, entity):
        mana = entity.get_component(Mana)
        spell = entity.get_component(self.spell_class)

        if entity.has_component(LichdomSpellEffect):
            mana.mana -= int(spell.mana_cost / 2)
            print("SPELL FIZZLES, already under its effect.")
        else:
            mana.mana -= spell.mana_cost
            entity.add_component(LichdomSpellEffect())
            print("LICHDOM SPELL CAST!")


# General caster systems

spells = {
    RejuvenationSpell: CanCastRejuvenationMixin,
    RestoreHealthSpell: CanCastRestoreHealthMixin,
    LichdomSpell: CanCastLichdomMixin,
}


class RegenerateMana(System):
    entity_filters = {
        'has_mana': and_filter([Mana]),
    }

    def update(self, filtered_entities):
        for entity in filtered_entities['has_mana']:
            c = entity.get_component(Mana)
            if c.mana < c.max_mana:
                c.mana += 1


class ReadySpells(CanCastRejuvenationMixin,
                  CanCastRestoreHealthMixin,
                  CanCastLichdomMixin,
                  System):
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

        for spell, mixin in spells.items():
            entities = filtered_entities[spell.name]
            if mixin.can_cast(self, entity, spell_class=spell, readying=True):
                entity.get_component(Mana).spells_ready.append(spell)

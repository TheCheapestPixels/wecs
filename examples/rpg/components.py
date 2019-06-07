from wecs.core import Component


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


@Component()
class Action:
    plan: str


@Component()
class Name:
    name: str


# Character life states. A character is one of Alive, Dying, Dead, or
# Undead. If a character has none of them, he... it? Well, that
# character is beyond the mortal coil in terms of that mortal coil
# being defined by the life states. Probably it's just simply a thing.

@Component()
class Alive:
    pass


@Component()
class Dying: # Transitional state between Alive and... others.
    pass


@Component()
class Dead:
    pass


@Component()
class Undead:
    pass


# Character properties

@Component()
class Age:
    age: int


@Component()
class Health:
    max_health: int
    health: int


@Component()
class Mana:
    max_mana: int
    mana: int
    spells_ready: list


# Spells.
# FooSpell is a character's knowledge of a spell.
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


@Component()
class LichdomSpellEffect:
    pass

from wecs.core import System, and_filter, or_filter

from components import Name
from components import Room
from components import RoomPresence
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


# Used by ReadySpells
spells = [RejuvenationSpell, RestoreHealthSpell, LichdomSpell]


class PerceiveRoom(System):
    entity_filters = {
        'room': and_filter([Room]),
        'presences': and_filter([RoomPresence]),
    }

    def update(self, filtered_entities):
        # Clean the bookkeeping lists
        for entity in filtered_entities['room']:
            room = entity.get_component(Room)
            room.arrived = []
            room.continued = []
            room.gone = []
        # New arrivals to rooms, and continued presences
        for entity in filtered_entities['presences']:
            room_uid = entity.get_component(RoomPresence).room
            room_entity = self.world.get_entity(room_uid)
            room = room_entity.get_component(Room)
            if entity._uid not in room.presences:
                room.arrived.append(entity._uid)
            else:
                room.continued.append(entity._uid)
        # Checking who is gone
        for entity in filtered_entities['room']:
            room = entity.get_component(Room)
            for presence in room.presences:
                if presence not in room.continued:
                    room.gone.append(presence)
        # Rebuilding the presencce lists
        for entity in filtered_entities['room']:
            room = entity.get_component(Room)
            room.presences = room.arrived + room.continued
        # Let the presences perceive the presences in the room
        for entity in filtered_entities['presences']:
            presence = entity.get_component(RoomPresence)
            room_entity = self.world.get_entity(presence.room)
            room = room_entity.get_component(Room)
            presence.presences = room.presences


class Aging(System):
    entity_filters = {
        'has_age': and_filter([Age]),
        'grows_frail': and_filter([Age, Alive, Health]),
    }

    def update(self, filtered_entities):
        for entity in filtered_entities['has_age']:
            entity.get_component(Age).age += 1
        for entity in filtered_entities['grows_frail']:
            age = entity.get_component(Age).age
            age_of_frailty = entity.get_component(Age).age_of_frailty
            if age >= age_of_frailty:
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
        'print_room': and_filter([RoomPresence, Name, Output]),
    }

    def update(self, filtered_entities):
        for entity in filtered_entities['all_outputters']:
            if entity in filtered_entities['print_age']:
                print("{}'s age: {} (growing frail at {})".format(
                    entity.get_component(Name).name,
                    entity.get_component(Age).age,
                    entity.get_component(Age).age_of_frailty,
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
                print("{}'s health: {}/{}.".format(
                    entity.get_component(Name).name,
                    entity.get_component(Health).health,
                    entity.get_component(Health).max_health,
                ))
            if entity in filtered_entities['print_mana']:
                print("{}'s mana: {}/{}".format(
                    entity.get_component(Name).name,
                    entity.get_component(Mana).mana,
                    entity.get_component(Mana).max_mana,
                ))
            if entity in filtered_entities['print_can_cast']:
                print("{} can cast: {}".format(
                    entity.get_component(Name).name,
                    ', '.join(entity.get_component(Mana).spells_ready),
                ))
            if entity in filtered_entities['print_room']:
                own_name = entity.get_component(Name).name
                presences = entity.get_component(RoomPresence).presences
                other_names = set()
                for presence in presences:
                    present_entity = self.world.get_entity(presence)
                    if present_entity.has_component(Name):
                        other_names.add(present_entity.get_component(Name).name)
                other_names.remove(own_name)
                print("{} is in a room with: {}.".format(
                    own_name,
                    ', '.join(other_names),
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

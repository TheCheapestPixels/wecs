from wecs.core import Component, System, and_filter


@Component()
class Health:
    max_health: int
    health: int


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


class DieFromHealthLoss(System):
    entity_filters = {
        'is_living': and_filter([Health, Alive]),
    }

    def update(self, filtered_entities):
        for entity in set(filtered_entities['is_living']):
            if entity.get_component(Health).health <= 0:
                entity.remove_component(Alive)
                entity.add_component(Dying())


class Die(System):
    entity_filters = {
        'is_dying': and_filter([Dying]),
    }

    def update(self, filtered_entities):
        for entity in set(filtered_entities['is_dying']):
            entity.remove_component(Dying)
            entity.add_component(Dead())

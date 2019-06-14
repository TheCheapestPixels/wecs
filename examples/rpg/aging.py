from wecs.core import Component, System, and_filter

from lifecycle import Alive
from lifecycle import Health


@Component()
class Age:
    age: int
    age_of_frailty: int


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

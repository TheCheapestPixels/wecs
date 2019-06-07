import dataclasses


class Entity:
    def __init__(self, world):
        self.world = world
        self.components = set()

    def add_component(self, component):
        if any([isinstance(c, type(component)) for c in self.components]):
            raise KeyError("Component type already on entity.")
        self.components.add(component)
        self.world.add_entity_to_filters(self)

    def get_components(self):
        return self.components

    def get_component(self, component_type):
        component = list(
            filter(
                lambda c: isinstance(c, component_type),
                self.components,
            )
        )
        if not component:
            raise KeyError
        assert len(component) == 1
        return component[0]

    def has_component(self, component_type):
        return any([type(c) is component_type for c in self.components])

    def remove_component(self, component_type):
        component = self.get_component(component_type)
        self.components.remove(component)
        self.world.remove_entity_from_filters(self, component)


class Component():
    def __init__(self, unique=True):
        self.unique = unique

    def __call__(self, cls):
        cls = dataclasses.dataclass(cls, eq=False)
        return cls


def and_filter(types):
    def filter(entity):
        if all([entity.has_component(t) for t in types]):
            return True
        else:
            return False
    return filter


def or_filter(types):
    def filter(entity):
        if any([entity.has_component(t) for t in types]):
            return True
        else:
            return False
    return filter


def dnf_filter(type_sets):
    clauses = [and_filter(ts) for ts in type_sets]
    def filter(entity):
        return any([c(entity) for c in clauses])
    return filter


class System:
    def __init__(self):
        self.filter_names = {
            filter_func: filter_name
            for filter_name, filter_func in self.entity_filters.items()
        }

    def init_entity(filter_name, entity):
        pass

    def destroy_entity(filter_name, entity, component):
        pass

    def update(self, filtered_entities):
        pass


class World:
    def __init__(self):
        self.entities = set()
        self.systems = {} # {System: sort}
        self.entity_filters = {}  # {Filter: set([Entities]}
        self.system_of_filter = {}

    def add_entity(self):
        entity = Entity(self)
        self.entities.add(entity)
        return entity

    def add_system(self, system, sort):
        if self.has_system(type(system)):
            raise KeyError("System of that type already on world.")
        if sort in self.systems:
            raise KeyError("sort already in use.")
        self.systems[sort] = system
        system._sort = sort
        # Prefilter for system
        for filter_name, filter_func in system.entity_filters.items():
            self.system_of_filter[filter_func] = system
            self.entity_filters[filter_func] = set()
            # It needs to scan the entities
            for entity in self.entities:
                if filter_func(entity):
                    self.entity_filters[filter_func].add(entity)
                    system.init_entity(filter_name, entity)

    def has_system(self, system_type):
        return any([isinstance(s, system_type) for s in self.systems.values()])

    def get_systems(self):
        return self.systems

    def get_system(self, system_type):
        system = list(
            filter(
                lambda s: isinstance(s, system_type),
                self.systems.values(),
            )
        )
        if not system:
            raise KeyError
        assert len(system) == 1
        return system[0]

    def remove_system(self, system_type):
        system = self.get_system(system_type)
        for filter_name, filter_func in system.entity_filters.items():
            del self.system_of_filter[filter_func]
            entities = self.entity_filters[filter_func]
            for entity in entities:
                system.destroy_entity(filter_name, entity)
            del self.entity_filters[filter_func]
        del self.systems[system._sort]

    def add_entity_to_filters(self, entity):
        for filter_func, entities in self.entity_filters.items():
            if filter_func(entity) and entity not in entities:
                entities.add(entity)
                system = self.system_of_filter[filter_func]
                filter_name = system.filter_names[filter_func]
                system.init_entity(filter_name, entity)

    def remove_entity_from_filters(self, entity, component):
        """
        Removes the entity from prefiltering list if the removal of a
        component has led to it falling out of the pattern.
        """
        for filter_func, entities in self.entity_filters.items():
            if not filter_func(entity) and entity in entities:
                entities.remove(entity)
                system = self.system_of_filter[filter_func]
                filter_name = system.filter_names[filter_func]
                system.destroy_entity(filter_name, entity, component)

    def update(self):
        for sort in sorted(self.systems):
            system = self.systems[sort]
            filtered_entities = {
                filter_name: self.entity_filters[filter_func]
                for filter_name, filter_func in system.entity_filters.items()
            }
            system.update(filtered_entities)

import types
import dataclasses


# FIXME: We rely on the hash of these objects to be unique, which is...
# iffy. If isn't *really* a problem that a UID gets destroyed and a new one is
# created in its place so that a dangling reference is created, because
# thanks to that dangling reference, the now invalid UID is still referenced.
# Still, this smells.
class UID:
    pass


class NoSuchUID(Exception):
    pass


class Entity:
    def __init__(self, world):
        self.world = world
        self.components = set()
        self._uid = UID()
        self._new_components = {} # type: instance
        self._dropped_components = {} # types

    def add_component(self, component):
        exists = any([isinstance(c, type(component))
                      for c in self.components])
        is_being_deleted = type(component) in self._dropped_components
        is_being_added = type(component) in self._new_components
        if exists and (not is_being_added or is_being_added):
            raise KeyError("Component type already on entity.")
        if is_being_added:
            raise KeyError("Component type is already being added to entity.")

        if not self._new_components and not self._dropped_components:
            # First component update in current system run
            self.world.register_entity_for_components_update(self)
        self._new_components[type(component)] = component

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
        if not self._new_components and not self._dropped_components:
            # First component update in current system run
            self.world.register_entity_for_components_update(self)
        self._dropped_components[component_type] = self.get_component(component_type)

    def update_components(self):
        for component_type, component in self._dropped_components.items():
            self.components.remove(component)
        for component_type, component in self._new_components.items():
            self.components.add(component)

    def get_dropped_components_by_type(self):
        return self._dropped_components

    def drop_component_updates(self):
        self._dropped_components = {}
        self._new_components = {}

    def destroy(self):
        self.world.remove_entity(self)
        # FIXME: Needs to be refactored when components are created
        # indirectly, outside update()
        for component in set(self.get_components()):
            self.remove_component()

    def __repr__(self):
        names = [repr(c) for c in self.components]
        return "<Entity ({})>".format(', '.join(names))


class Component():
    def __init__(self, unique=True):
        self.unique = unique

    def __call__(self, cls):
        cls = dataclasses.dataclass(cls, eq=False)
        return cls


class Filter:
    def get_component_dependencies(self):
        dependencies = set()
        for clause in self.types_and_filters:
            if isinstance(clause, Filter):
                dependencies.update(clause.get_component_dependencies())
            else:
                dependencies.add(clause)
        return dependencies


class AndFilter(Filter):
    def __init__(self, types_and_filters):
        self.types_and_filters = types_and_filters

    def __call__(self, entity):
        for clause in self.types_and_filters:
            if isinstance(clause, Filter):
                if not clause(entity):
                    return False
            elif not entity.has_component(clause):
                return False
        return True


def and_filter(types_and_filters):
    return AndFilter(types_and_filters)


class OrFilter(Filter):
    def __init__(self, types_and_filters):
        self.types_and_filters = types_and_filters

    def __call__(self, entity):
        for clause in self.types_and_filters:
            if isinstance(clause, Filter):
                if clause(entity):
                    return True
            elif entity.has_component(clause):
                return True
        return False


def or_filter(types_and_filters):
    return OrFilter(types_and_filters)


class System:
    def __init__(self):
        self.filter_names = {
            filter_func: filter_name
            for filter_name, filter_func in self.entity_filters.items()
        }

    def init_entity(self, filter_name, entity):
        pass

    def destroy_entity(self, filter_name, entity, components_by_type):
        pass

    def update(self, filtered_entities):
        super().update(self, filtered_entities)

    def get_component_dependencies(self):
        dependencies = set()
        for filter_func in self.entity_filters.values():
            dependencies.update(filter_func.get_component_dependencies())
        return dependencies

    def __repr__(self):
        return self.__class__.__name__


class World:
    def __init__(self):
        # TODO: One of these (probably self.entities) is redundant,
        # and should be phased out.
        self.entities = set()
        self.entities_by_uid = {}
        self.systems = {} # {sort: System}
        self.entity_filters = {}  # {Filter: set([Entities]}
        self.system_of_filter = {}
        self.entities_that_update_components= [] # deferred operation

    def create_entity(self, *args):
        entity = Entity(self)
        self.entities.add(entity)
        self.entities_by_uid[entity._uid] = entity
        for arg in args:
            # assert isinstance(arg, Component)
            entity.add_component(arg)
        return entity

    def get_entity(self, uid):
        try:
            entity = self.entities_by_uid[uid]
        except KeyError:
            raise NoSuchUID
        return entity

    def destroy_entity(self, uid_or_entity):
        if isinstance(uid_or_entity, Entity):
            entity = uid_or_entity
        elif isinstance(uid_or_entity, UID):
            entity = entity_by_uid[uid_or_entity]
        else:
            raise ValueError("Entity or UID must be given")
        entity.destroy()

    def remove_entity(self, uid_or_entity):
        if isinstance(uid_or_entity, Entity):
            entity = uid_or_entity
            uid = uid_or_entity._uid
        elif isinstance(uid_or_entity, UID):
            entity = entity_by_uid[uid_or_entity]
            uid = uid_or_entity
        else:
            raise ValueError("Entity or UID must be given")

        del self.entities_by_uid[uid]
        self.entities.remove(entity)

    def add_system(self, system, sort):
        if self.has_system(type(system)):
            raise KeyError("System of that type already on world.")
        if sort in self.systems:
            raise KeyError("sort already in use.")
        self.systems[sort] = system
        system.world = self
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

    def get_system_component_dependencies(self):
        dependencies = {
            system: system.get_component_dependencies()
            for system in self.systems.values()
        }
        return dependencies

    def register_entity_for_components_update(self, entity):
        self.entities_that_update_components.append(entity)

    def flush_component_updates(self):
        for entity in self.entities_that_update_components:
            entity.update_components()
        self.update_entity_filters(self.entities_that_update_components)
        for entity in self.entities_that_update_components:
            entity.drop_component_updates()

        self.entities_that_update_components = []

    def update_entity_filters(self, entities):
        for filter_func, entities_in_filter in self.entity_filters.items():
            for entity in entities:
                is_in_filter = entity in entities_in_filter
                should_be_in_filter = filter_func(entity)
                if should_be_in_filter and not is_in_filter:
                    entities_in_filter.add(entity)
                    system = self.system_of_filter[filter_func]
                    filter_name = system.filter_names[filter_func]
                    system.init_entity(filter_name, entity)
                elif is_in_filter and not should_be_in_filter:
                    entities_in_filter.remove(entity)
                    system = self.system_of_filter[filter_func]
                    filter_name = system.filter_names[filter_func]
                    components = entity.get_dropped_components_by_type()
                    system.destroy_entity(filter_name, entity, components)

    def update(self):
        for sort in sorted(self.systems):
            system = self.systems[sort]
            self.update_system(system)

    def update_system(self, system):
            self.flush_component_updates()
            entities_by_filter = {
                filter_name: self.entity_filters[filter_func]
                for filter_name, filter_func in system.entity_filters.items()
            }
            system.update(entities_by_filter)

import types
import dataclasses


class World:
    '''
    Has a set of
    :class:`wecs.core.Entity`

    and a set of
    :class:`wecs.core.System`
    '''
    def __init__(self):
        self.entities = {} # {UID: Entity}
        self.systems = {} # {sort: System}
        self._addition_pool = set() # Entities
        self._removal_pool = set() # Entities

    # Entity CRUD

    def create_entity(self, *args, name=None):
        '''
        Parameters
        -----------
        *args
            Initial Components.
        name
            Entity name string.
        '''

        entity = Entity(self, name=name)
        self.entities[entity._uid] = entity
        for arg in args:
            entity.add_component(arg)
        return entity

    def get_entity(self, uid):
        '''
        Parameters
        -----------
        uid
            The
            :core:'wecs.core.UID' of entity to return

        :returns: 'wecs.core.Entity'
        '''
        try:
            entity = self.entities[uid]
        except KeyError:
            raise NoSuchUID
        return entity

    def __getitem__(self, uid_or_entity):
        return self.get_entity(uid_or_entity)

    def get_entities(self):
        return self.entities.values()

    def destroy_entity(self, uid_or_entity):
        '''
        Destroys the entity and its components, implicitly
        removing it from all systems.

        Parameters
        -----------
        uid_or_entity
            A 'wecs.core.Entity' or :core:'wecs.core.UID'
        '''
        if isinstance(uid_or_entity, Entity):
            entity = uid_or_entity
        elif isinstance(uid_or_entity, UID):
            entity = entity_by_uid[uid_or_entity]
        else:
            raise ValueError("Entity or UID must be given")
        # Remove all components. This sets it up to be removed from
        # all systems during the next flush.
        entity._destroy()
        # ...and forget it in this world.
        del self.entities[entity._uid]

    def __delitem__(self, uid_or_entity):
        self.destroy_entity(uid_or_entity)

    # System CRUD

    def add_system(self, system, sort, add_duplicates=False):
        '''
        Add a system to the world. During a 'world.update()',
        systems will be processed in order of ascending 'sort'.

        Parameters
        -----------
        system
            System to add.
        sort
            Order the system should run.
        add_duplicates
            If False (default), a KeyError will be raised when
            the world already has a system of that type. If True,
            do not use get_system() to retrieve systems with
            multiple instances.
        '''
        if self.has_system(type(system)) and not add_duplicates:
            raise KeyError("System of that type already on world.")
        if sort in self.systems:
            raise KeyError("sort already in use.")
        self.systems[sort] = system
        system.world = self
        system._sort = sort

        self._flush_component_updates()
        for entity in self.entities.values():
            system._propose_addition(entity)

    def has_system(self, system_type):
        return any([isinstance(s, system_type)
                    for s in self.systems.values()])

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
        system._destroy()
        del self.systems[system._sort]

    # Flush entity component updates
        
    def _register_entity_for_add_flush(self, entity):
        self._addition_pool.add(entity)

    def _register_entity_for_remove_flush(self, entity):
        self._removal_pool.add(entity)

    def _flush_component_updates(self):
        while self._addition_pool or self._removal_pool:
            while self._removal_pool:
                self._removal_flush()
            self._addition_flush()

    def _removal_flush(self):
        removal_pool = self._removal_pool
        self._removal_pool = set()
        for entity in removal_pool:
            for system in self.systems.values():
                system._propose_removal(entity)
            entity._flush_removals()

    def _addition_flush(self):
        addition_pool = self._addition_pool
        self._addition_pool = set()
        for entity in addition_pool:
            entity._flush_additions()
            for system in self.systems.values():
                system._propose_addition(entity)

    def _update_system(self, system):
        '''
        Run a system. First, component updates are flushed,
        then the system's 'update' is run.

        For internal use by 'update'.

        Parameters
        -----------
        system
            System to run
        '''
        self._flush_component_updates()
        system._trigger_update()

    def update(self):
        '''
        Run all systems in ascending order of sort.
        '''
        for sort in sorted(self.systems):
            system = self.systems[sort]
            self._update_system(system)


#
# Entities and components
#


# FIXME: We rely on the hash of these objects to be unique, which is...
# iffy. If isn't *really* a problem that a UID gets destroyed and a new one is
# created in its place so that a dangling reference is created, because
# thanks to that dangling reference, the now invalid UID is still referenced.
# Still, this smells.
class UID:
    '''
    Object for referencing a
    :class:`wecs.core.Entity`

    '''
    def __init__(self, name=None):
        if name is None:
            name = str(id(self))
        self.name = name


class NoSuchUID(Exception):
    pass


class Entity:
    '''
    Everything in a
    :class:`wecs.core.World` is an Entity. They have a set of
    :class:`wecs.core.Component` and are, with regard to how they are processed,
    type- and stateless.

    They are usually created with :func:`wecs.core.World.create_entity`
    '''

    def __init__(self, world, name=None):
        self.world = world
        self._uid = UID(name)
        self.components = {} # type: instance
        self._added_components = {} # type: instance
        self._dropped_components = set() # types

    # Component CRUD

    def add_component(self, component):
        is_present = type(component) in self.components
        is_being_deleted = type(component) in self._dropped_components
        is_being_added = type(component) in self._added_components
        if is_present and not is_being_deleted:
            raise KeyError("Component type already on entity.")
        if is_being_added:
            raise KeyError("Component type is already being added to entity.")

        if not self._added_components:
            # First component update in current system run
            self.world._register_entity_for_add_flush(self)
        self._added_components[type(component)] = component

    def __setitem__(self, component_type, component):
        assert isinstance(component, component_type)
        return self.add_component(component)

    def get_components(self):
        return self.components.values()

    def get_component_types(self):
        return self.components.keys()

    def get_component(self, component_type):
        return self.components[component_type]

    def __getitem__(self, component_type):
        return self.get_component(component_type)

    def has_component(self, component_type):
        return component_type in self.components

    def __contains__(self, component_type):
        return self.has_component(component_type)

    def remove_component(self, component_type):
        if component_type not in self.components:
            raise KeyError("Component type not present on Entity.")
        if not self._dropped_components:
            self.world._register_entity_for_remove_flush(self)
        self._dropped_components.add(component_type)

    def __delitem__(self, component_type):
        return self.remove_component(component_type)

    # Deferred component updates
    
    def _get_post_removal_component_types(self):
        current_types = self.components.keys()
        return set(current_types).difference(self._dropped_components)

    def _get_post_addition_component_types(self):
        current_types = self.components.keys()
        return set(current_types).union(self._added_components) 

    def _flush_removals(self):
        for c_type in self._dropped_components:
            del self.components[c_type]
        self._dropped_components = set()

    def _flush_additions(self):
        self.components.update(self._added_components)
        self._added_components = {}

    # Teardown

    def _destroy(self):
        for component_type in set(self.components.keys()):
            self.remove_component(component_type)

    def __repr__(self):
        return "<Entity {}>".format(self._uid.name)


class Component():
    '''
    New components should inherit from this class like so::

        @Component()
        class SomeNewComponent:
            some_variable: int = 0

    '''
    def __init__(self, unique=True):
        self.unique = unique

    def __call__(self, cls):
        cls = dataclasses.dataclass(cls, eq=False)
        return cls


#
# Systems and Filters
#


class System:
    '''

    Example of a system::

        class Print(System):
            # Filter all entities in the world described as Printer
            entity_filters = {
                'printers' : and_filter([Printer])
            }

            def update(self, entities_by_filter):
                # Iterate over all filtered entities
                for entity in entities_by_filter['printers']:
                    # Print their message
                    print(entity[Printer].message)

    Then add it with :func:`wecs.core.World.add_system`

    '''

    def __init__(self, throw_exc=False):
        self.throw_exc = throw_exc
        self.filters = {
            func: name
            for name, func in self.entity_filters.items()
        }
        self.entities = {
            name: set()
            for name in self.entity_filters.keys()
        }

    def update_entity(self, entity):
        for f_func, f_name in self.filters.items():
            if f_func(entity) and entity not in self.entities[f_name]:
                # TODO: Add entity to filter
                pass
            elif not f_func(entity) and entity in self.entities[f_name]:
                # TODO: Remove entity from filter
                pass
            # TODO: Run enter_filters / exit_filters
            pass

    def enter_filters(self, filters, entity):
        for filter in filters:
            if hasattr(self, 'enter_filter_' + filter):
                getattr(self, 'enter_filter_' + filter)(entity)

    def exit_filters(self, filters, entity):
        for filter in reversed(filters):
            if hasattr(self, 'exit_filter_' + filter):
                getattr(self, 'exit_filter_' + filter)(entity)

    def update(self, entities_by_filter):
        pass

    def _trigger_update(self):
        self.update(self.entities)

    def _propose_removal(self, entity):
        exited_filters = []
        future_components = entity._get_post_removal_component_types()
        for filter_name, filter_func in self.entity_filters.items():
            matches = filter_func(future_components)
            present = entity in self.entities[filter_name]
            if present and not matches:
                self.entities[filter_name].remove(entity)
                exited_filters.append(filter_name)
        self.exit_filters(exited_filters, entity)

    def _propose_addition(self, entity):
        entered_filters = []
        future_components = entity._get_post_addition_component_types()
        for filter_name, filter_func in self.entity_filters.items():
            matches = filter_func(future_components)
            present = entity in self.entities[filter_name]
            if matches and not present:
                self.entities[filter_name].add(entity)
                entered_filters.append(filter_name)
        self.enter_filters(entered_filters, entity)

    def _destroy(self):
        all_entities = set.union(*self.entities.values())
        for entity in all_entities:
            filters = [
                f_name for f_name, f_ent in self.entities.items()
                if entity in f_ent
            ]
            self.exit_filters(filters, entity)
            for filter in filters:
                self.entities[filter].remove(entity)

    def __repr__(self):
        return self.__class__.__name__


class Filter:
    def __init__(self, *types_and_filters):
        old_style = len(types_and_filters) == 1 and isinstance(types_and_filters[0], list)
        if old_style:
            self.types_and_filters = types_and_filters[0]
        else:
            self.types_and_filters

    def get_component_dependencies(self):
        dependencies = set()
        for clause in self.types_and_filters:
            if isinstance(clause, Filter):
                dependencies.update(clause.get_component_dependencies())
            else:
                dependencies.add(clause)
        return dependencies

    def __call__(self, types_or_entity):
        if isinstance(types_or_entity, Entity):
            present_types = types_or_entity.get_component_types()
        else:
            present_types = types_or_entity
        return self.evaluate(present_types)


class AndFilter(Filter):
    def evaluate(self, types):
        for clause in self.types_and_filters:
            if isinstance(clause, Filter):
                if not clause(types):
                    return False
            elif clause not in types:
                return False
        return True


class OrFilter(Filter):
    def evaluate(self, types):
        for clause in self.types_and_filters:
            if isinstance(clause, Filter):
                if clause(types):
                    return True
            elif clause in types:
                return True
        return False


def and_filter(types_and_filters):
    return AndFilter(types_and_filters)


def or_filter(types_and_filters):
    return OrFilter(types_and_filters)

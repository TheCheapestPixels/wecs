import types
import dataclasses


class World:
    """
    A world contains a set of :class:`wecs.core.Entity`, a
    set of :class:`wecs.core.System`, and runs the systems
    when `update()` is called.

    `update` and `add_system` will cause deferred component
    updates to entities to be flushed.
    """
    def __init__(self):
        self.entities = {} # {UID: Entity}
        self.systems = {} # {sort: System}
        self._addition_pool = set() # Entities
        self._removal_pool = set() # Entities

    # Entity CRUD

    def create_entity(self, *components, name=None):
        """
        components
            The entity's initial component instances.
        name
            An optional name for debug purposes.

        :returns: :class:`wecs.core.Entity`
        """

        entity = Entity(self, name=name)
        self.entities[entity._uid] = entity
        for component in components:
            entity.add_component(component)
        return entity

    def get_entity(self, uid):
        """
        uid
            The
            :class:`wecs.core.UID` of entity to return

        :returns: :class:`wecs.core.Entity`
        """
        try:
            entity = self.entities[uid]
        except KeyError:
            raise NoSuchUID
        return entity

    def __getitem__(self, uid_or_entity):
        return self.get_entity(uid_or_entity)

    def get_entities(self):
        """
        :returns:
            An iterable of all :class:`wecs.core.Entity`
            in the world.
        """
        return self.entities.values()

    def destroy_entity(self, uid_or_entity):
        """
        Destroys the entity, removing its components, implicitly
        removing it from all systems during the next flush.

        uid_or_entity
            A :class:`wecs.core.Entity` or :class:`wecs.core.UID`
        """
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
        """
        Add a system to the world. During a 'world.update()',
        systems will be processed in order of ascending 'sort'.

        Adding a system will implicitly cause a flush of
        deferred component updates to instances of
        :class:`wecs.core.Entity`.

        system
            System to add.
        sort
            Order the system should run.
        add_duplicates
            If False (default), a KeyError will be raised when
            the world already has a system of that type. If True,
            do not `use get_system()` to retrieve systems with
            multiple instances.
        """
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
        """
        system_type
            The type of :class:`wecs.core.System` to check for.

        :returns: :bool:
        """
        return any([isinstance(s, system_type)
                    for s in self.systems.values()])

    def get_systems(self):
        """
        :returns:
            A dictionary of `sort`: :class:`wecs.core.System`
        """
        return self.systems

    def get_system(self, system_type):
        """
        system_type
            The type of :class:`wecs.core.System` to return.

        :returns: :class:`wecs.core.System`
        """
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
        """
        system_type
            The type of :class:`wecs.core.System` to remove.
        """
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
        """
        Run a system. First, component updates are flushed,
        then the system's 'update' is run.

        For internal use by 'update'.

        system
            System to run
        """
        self._flush_component_updates()
        system._trigger_update()

    def update(self):
        """
        Run all systems in ascending order of sort.
        """
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
    """
    Object for referencing a :class:`wecs.core.Entity`.
    """
    def __init__(self, name=None):
        if name is None:
            name = str(id(self))
        self.name = name


class NoSuchUID(Exception):
    """
    Raised by :func:`wecs.core.World.get_entity` if the entity
    referenced by the UID has been removed.
    """
    pass


class Entity:
    """
    Everything in a :class:`wecs.core.World` is an Entity. They are a 
    container for a set of :class:`wecs.core.Component`.

    They are created with :func:`wecs.core.World.create_entity`

    When components are added to or removed from entities, these changes
    are deferred until the next flush.
    """

    def __init__(self, world, name=None):
        self.world = world
        self._uid = UID(name)
        self.components = {} # type: instance
        self._added_components = {} # type: instance
        self._dropped_components = set() # types

    # Component CRUD

    def add_component(self, component):
        """
        Add a component to an entity. The addition is deferred until the
        next flush.

        component
            The component instance to add.
        """
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
        """
        :returns:
            An iterable of the current :class:`wecs.core.Component`
            instances in the entity.
        """
        return self.components.values()

    def get_component_types(self):
        """
        :returns:
            An iterable of the types of the current
            :class:`wecs.core.Component` instances in the entity.
        """
        return self.components.keys()

    def get_component(self, component_type):
        """
        component_type
            The type of :class:`wecs.core.Component` to get.

        :returns:
            The :class:`wecs.core.Component` instance.
        """
        return self.components[component_type]

    def __getitem__(self, component_type):
        return self.get_component(component_type)

    def has_component(self, component_type):
        """
        component_type
            The type of :class:`wecs.core.Component` to check for.

        :returns:
            :bool:
        """
        return component_type in self.components

    def __contains__(self, component_type):
        return self.has_component(component_type)

    def remove_component(self, component_type):
        """
        Remove a component to an entity. The removal is deferred until
        the next flush.

        component_type
            The type of component to remove.
        """
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
    """
    New components are declared like dataclasses::

        @Component()
        class MyComponent:
            my_variable: int = 0

    """
    def __init__(self, unique=True):
        self.unique = unique

    def __call__(self, cls):
        cls = dataclasses.dataclass(cls, eq=False)
        return cls


#
# Systems and Filters
#


class System:
    """
    A system implements functionality that is executed during a
    :func:`wecs.core.World.update`. It also implements behavior
    necessary to prepare an entity, or tear it down.

    A system has one or more filters that test whether the system
    should process an entity during an update. It also implements the
    functionality to set up and tear down the entity when it enters or
    leaves filters.
    
    For example::

        @Component()
        class Printer:
            message: str = "I'm being updated!"


        class Print(System):
            entity_filters = {
                'printers' : and_filter([Printer])
            }

            def enter_filter_printers(self, entity):
                print("Entity has entered the filter")

            def update(self, entities_by_filter):
                for entity in entities_by_filter['printers']:
                    print(entity[Printer].message)

            def exit_filter_printers(self, entity):
                print("Entity has exited the filter")

    When a `Printer` component is added to an entity and a flush
    happens, `enter_filter_printers` will be called (with the entity as
    argument). Conversely, when the component is removed, 
    `exit_filter_printers` will be called. As long as it has the
    component during an update, it will be present in the
    `entities_by_filter` dictionary in the set under the key `printers`.
    """

    def __init__(self, throw_exc=False):
        self.throw_exc = throw_exc
        self.filters = {}
        for name, func in self.entity_filters.items():
            if not isinstance(func, Filter):
                # A base component is (hopefully) being used
                func = and_filter(func)
            self.filters[func] = name
        self.entities = {
            name: set()
            for name in self.entity_filters.keys()
        }

    def enter_filters(self, filters, entity):
        """
        This method is called during a flush when an entity newly
        matches one or more filters. It can be overridden in 
        implementations of systems. By default it will look up whether
        the system has an `enter_filter_<name>` method, and will call
        that. The order of those calls is the same in which the filters
        are specified.

        filters
            A list of filter names
        entity
            The entity that has entered the filter(s).
        """
        for filter in filters:
            if hasattr(self, 'enter_filter_' + filter):
                getattr(self, 'enter_filter_' + filter)(entity)

    def exit_filters(self, filters, entity):
        """
        This method is called during a flush when an entity no longer
        satisfies one or more filters. It can be overridden in 
        implementations of systems. By default it will look up whether
        the system has an `enter_filter_<name>` method, and will call
        that. The order of those calls is the *reverse* of that in 
        which the filters are specified.

        filters
            A list of filter names
        entity
            The entity that has exited the filter(s).
        """
        for filter in reversed(filters):
            if hasattr(self, 'exit_filter_' + filter):
                getattr(self, 'exit_filter_' + filter)(entity)

    def update(self, entities_by_filter):
        """
        The system's functionality that is run during an update.

        entity_by_filters
            A dictionary mapping filter names to sets of
            :class:`wecs.core.entity`.
        """
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
    """
    The base class for filters. Please don't use it directly. Instead,
    use :func:`wecs.core.and_filter` and :func:`wecs.core.or_filter`.
    """
    def __init__(self, *types_and_filters):
        old_style = len(types_and_filters) == 1 and isinstance(types_and_filters[0], list)
        if old_style:
            self.types_and_filters = types_and_filters[0]
        else:
            self.types_and_filters = types_and_filters

    def _get_component_dependencies(self):
        """
        Not used anymore; A leftover from an optimization.

        When an entity's component set is changed, it only needs to be
        tested against filters where the changed component's type is
        in the dependency list.

        While not saving any significant time in itself, this could be
        turned inside-out, mapping component types to a complete list of
        filters that relate to the type. This too though would only save
        noticeable time if there's lots and lots of systems, and
        component changes happen many times per update.

        :returns:
            :set: of all component types matched against by this filter
            and its sub-filters
        """
        dependencies = set()
        for clause in self.types_and_filters:
            if isinstance(clause, Filter):
                dependencies.update(clause._get_component_dependencies())
            else:
                dependencies.add(clause)
        return dependencies

    def __call__(self, types_or_entity):
        if isinstance(types_or_entity, Entity):
            present_types = types_or_entity.get_component_types()
        else:
            present_types = types_or_entity
        return self._evaluate(present_types)


class AndFilter(Filter):
    """
    Class for and-filters. Please use :func:`wecs.core.and_filter`
    instead.
    """
    def _evaluate(self, types):
        for clause in self.types_and_filters:
            if isinstance(clause, Filter):
                if not clause(types):
                    return False
            elif clause not in types:
                return False
        return True


class OrFilter(Filter):
    """
    Class for or-filters. Please use :func:`wecs.core.or_filter`
    instead.
    """
    def _evaluate(self, types):
        for clause in self.types_and_filters:
            if isinstance(clause, Filter):
                if clause(types):
                    return True
            elif clause in types:
                return True
        return False


def and_filter(*types_and_filters):
    """
    Creates a filter that matches entities that contains all of
    this filter's :class:`wecs.core.Component` types and sub-filters.
    
    Examples::

        # These filters match entities which have...
        and_filter(Foo)  # ...a Foo component
        and_filter(Foo, Bar)  # ...a Foo and a Bar components
        and_filter(Foo, or_filter(Bar, Qux))  # ...a Foo component, and
            # a Bar and/or Qux component
    
    types_and_filters
        The :class:`wecs.core.Component` types and sub-filters that this
        (sub-)filter matches against.

    :returns:
        The filter object
    """
    return AndFilter(*types_and_filters)


def or_filter(*types_and_filters):
    """
    Creates a filter that matches entities that contains at least one of
    this filter's :class:`wecs.core.Component` types and sub-filters.

    Examples::

        # These filters match entities which have...
        or_filter(Foo)  # ... a Foo component
        or_filter(Foo, Bar)  # ... a Foo and/or a Bar component
        or_filter(Foo, and_filter(Bar, Qux))  # a Foo component, and/or
            # both a Bar and a Qux component.
    
    types_and_filters
        The :class:`wecs.core.Component` types and sub-filters that this
        (sub-)filter matches against.

    :returns:
        The filter object
    """
    return OrFilter(*types_and_filters)

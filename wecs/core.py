import dataclasses


# FIXME: We rely on the hash of these objects to be unique, which is...
# iffy. If isn't *really* a problem that a UID gets destroyed and a new one is
# created in its place so that a dangling reference is created, because
# thanks to that dangling reference, the now invalid UID is still referenced.
# Still, this smells.
import logging


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


class World:
    """
    The World object is the root object of ECS.
    A world contains a set of :class:`wecs.core.Entity`, and
    a set of :class:`wecs.core.System`. The World's update() method
    ensures that all the systems' update() are called.
    When a system's update is called it takes care of all the entities
    that are registered as being part of the system.

    `update` and `add_system` will cause deferred component
    updates to entities to be flushed.
    """

    def __init__(self):
        self.entities = {}  # {UID: Entity}
        self.systems = {}  # {sort: System}
        self._addition_pool = set()  # Entities
        self._removal_pool = set()  # Entities

    # Entity CRUD

    def create_entity(self, *components, name=None):
        """
        Creates an entity with the provided components.

        :param components: The entity's initial component instances
        :param name: An optional name for debug purposes
        :return: :class:`wecs.core.Entity`
        """
        entity = Entity(self, name=name)
        self.entities[entity._uid] = entity
        for component in components:
            entity.add_component(component)
        return entity

    def get_entity(self, uid):
        """
        Returns an entity by uid.

        :param uid: :class:`wecs.core.UID` of entity to return
        :return: :class:`wecs.core.Entity`
        """
        try:
            entity = self.entities[uid]
        except KeyError:
            raise NoSuchUID(f"entity with UID:{uid} was not found")
        return entity

    def __getitem__(self, uid_or_entity):
        return self.get_entity(uid_or_entity)

    def get_entities(self):
        """
        :return: An iterable of all :class:`wecs.core.Entity` in the world.
        """
        return self.entities.values()

    def destroy_entity(self, uid_or_entity):
        """
        Destroys the entity, removing its components, implicitly
        removing it from all systems during the next flush.

        :param uid_or_entity: A :class:`wecs.core.Entity` or :class:`wecs.core.UID`
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
        deferred component updates.

        :param system: System to add
        :param sort: Order the system should run
        :param add_duplicates: If False (default), a KeyError will be raised when the world
            already has a system of that type.
            If True, do not `use get_system()` to retrieve systems with  multiple instances.
        """
        # logging.info(f"in {__name__} got {system, sort, add_duplicates}")
        if self.has_system(type(system)) and not add_duplicates:
            raise KeyError(f"System of type {system} was already added to the  world.")
        if sort in self.systems:
            raise KeyError(f"sort {sort} already in use.")
        self.systems[sort] = system
        system._sort = sort
        system.world = self

        self._flush_component_updates()
        for entity in self.entities.values():
            system._propose_addition(entity)

    def has_system(self, system_type):
        """

        :param system_type: The type of :class:`wecs.core.System` to check for
        :return: :bool:
        """
        return any([isinstance(s, system_type)
                    for s in self.systems.values()])

    def get_systems(self):
        """
        :return: A dictionary of `sort`: :class:`wecs.core.System`
        """
        return self.systems

    def get_system(self, system_type):
        """

        :param system_type: The type of :class:`wecs.core.System` to return.
        :return: :class:`wecs.core.System`
        """
        system = list(
            filter(
                lambda s: isinstance(s, system_type),
                self.systems.values(),
            )
        )
        if not system:
            raise KeyError(f"system {system_type} was not found")
        assert len(system) == 1
        return system[0]

    def remove_system(self, system_type):
        """
        :param system_type: The type of :class:`wecs.core.System` to remove
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
        self.name = name
        self.components = {}  # type: instance
        self._added_components = {}  # type: instance
        self._dropped_components = set()  # types

    # Component CRUD

    def add_component(self, component):
        """
        Add a component to an entity. The addition is deferred until the
        next flush.

        :param component: The component instance to add.
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
        """
         Helper function that lets you write `entity[ComponentType] = ComponentType()`
         instead of `entity.add_component(ComponentType())`.

        :param component_type:
        :param component:
        :return:
        """
        assert isinstance(component, component_type)
        return self.add_component(component)

    def get_components(self):
        """
        Get all component of an Entity.

        :returns: An iterable of the current :class:`wecs.core.Component` instances in the entity.
        """
        return self.components.values()

    def get_component_types(self):
        """
        Get all component types of an Entity.

        :return: An iterable of the types of the current :class:`wecs.core.Component` instances in the entity.
        """
        return self.components.keys()

    def get_component(self, component_type):
        """
        Get an Entity's component based on a component_type.

        :param component_type: The type of :class:`wecs.core.Component` to get.
        :return: The :class:`wecs.core.Component` instance.
        """
        return self.components[component_type]

    def __getitem__(self, component_type):
        """
        Helper function to use instead of :func:`get_component`.
        So instead of
            comp = entity.get_component(some_component_type)
        you can write
        comp = entity[some_component_type]

        :param component_type: The type of :class:`wecs.core.Component` to get.
        :return: :The :class:`wecs.core.Component` instance.
        """
        return self.get_component(component_type)

    def get(self, component_type, default=None):
        """
        Helper function to use instead of :func:`get_component`. Allows adding a default
        value in case :class:`wecs.core.Component` is not part of the entity.

        :param component_type: The type of :class:`wecs.core.Component` to get.
        :param default: the return value if :class:`wecs.core.Component` is not found
        :return: either the :class:`wecs.core.Component` or the default value.
        """
        try:
            return self.get_component(component_type)
        except KeyError:
            return default


    def has_component(self, component_type):
        """
        component_type

        :param component_type: The type of :class:`wecs.core.Component` to check for.
        :return: :bool:
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


class Component:
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


class Proxy:
    """
    When at coding time it is not yet known what component types and
    field names will be used for an aspect of functionality that a
    system will work on (e.g. where to find a `NodePath` to center a
    camera on), a `Proxy` can be used instead to declare a name under
    which the definition can actually be looked up. For example:

        class ProxyingSystem(System):
            entity_filters = {
                'test': Proxy('proxy'),
            }
    
            def update(self, entity_by_filters):
                for entity in entity_by_filters['test']:
                    proxy = self.proxies['proxy']
                    my_component = entity[proxy.component_type]
    
                    field_value = proxy.field(my_component)
    

        @Component()
        class MyComponent:
            foo: str = '123'


        class ActualSystem(ProxyingSystem):
            proxies = {
                'proxy': ProxyType(MyComponent, 'foo'),
            }

    `ActualSystem` thus is an implementation of `ProxyingSystem` where
    `my_component = entity[MyComponent]` and 
    `field_value = my_component.foo`.
    """
    def __init__(self, name):
        self.name = name


class ProxyType:
    def __init__(self, component_type, field_name=None):
        self.component_type = component_type
        self.field_name = field_name

    def field(self, entity):
        component = entity[self.component_type]
        return getattr(component, self.field_name)

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

    When a `Printer` component is added to an entity a flush
    happens, and `enter_filter_printers` will be called (with the entity
    as argument). Conversely, when the component is removed, 
    `exit_filter_printers` will be called. As long as it has the
    component during an update, it will be present in the
    `entities_by_filter` dictionary in the set under the key `printers`.

    FIXME: Document `System.proxy` / `System(proxies=...)`
    """

    def __init__(self, proxies=None, throw_exc=False):
        if proxies is not None:
            if not hasattr(self, 'proxies'):
                self.proxies = {}
            self.proxies.update(proxies)
        self.throw_exc = throw_exc

        self.filters = {}
        for name in self.entity_filters.keys():
            func = self.entity_filters[name]
            # Wrap bare components
            if not isinstance(func, Filter):
                func = and_filter(func)
                self.entity_filters[name] = func
            # Replace proxies with proxied component types
            if hasattr(self, 'proxies'):
                func._resolve_proxies(self.proxies)
            # Build reverse filter dict
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

        :param filters: A list of filter names
        :param entity: The entity that has entered the filter(s).
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

        :param filters: A list of filter names
        :param entity: The entity that has entered the filter(s).
        """
        for filter in reversed(filters):
            if hasattr(self, 'exit_filter_' + filter):
                getattr(self, 'exit_filter_' + filter)(entity)

    def update(self, entities_by_filter):
        """
        The system's functionality that is run during an update.

        :param entities_by_filter:  A dictionary mapping filter names to sets of
            :class:`wecs.core.entity`.

        """
        pass

    def _trigger_update(self):
        self.update(self.entities)

    def _propose_removal(self, entity):
        exited_filters = []
        future_components = entity._get_post_removal_component_types()
        for filter_func, filter_name in self.filters.items():
            matches = filter_func(future_components)
            present = entity in self.entities[filter_name]
            if present and not matches:
                self.entities[filter_name].remove(entity)
                exited_filters.append(filter_name)
        self.exit_filters(exited_filters, entity)

    def _propose_addition(self, entity):
        entered_filters = []
        future_components = entity._get_post_addition_component_types()
        for filter_func, filter_name in self.filters.items():
            matches = filter_func(future_components)
            present = entity in self.entities[filter_name]
            if matches and not present:
                self.entities[filter_name].add(entity)
                entered_filters.append(filter_name)
        self.enter_filters(entered_filters, entity)

    def _destroy(self):
        all_entities = set.union(set(), *self.entities.values())
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
        has_one_element = len(types_and_filters) == 1
        is_a_list = isinstance(types_and_filters[0], list)
        old_style = has_one_element and is_a_list
        if old_style:
            self.types_and_filters = types_and_filters[0]
        else:
            self.types_and_filters = types_and_filters
        self.types_and_filters = list(self.types_and_filters)

    def _resolve_proxies(self, proxies):
        for idx in range(len(self.types_and_filters)):
            t_o_f = self.types_and_filters[idx]
            if isinstance(t_o_f, Proxy):
                proxy = proxies[t_o_f.name]
                if isinstance(proxy, ProxyType):
                    resolved_type = proxy.component_type
                else:
                    # Bare component type
                    resolved_type = proxy
                self.types_and_filters[idx] = resolved_type
                    

    def _get_component_dependencies(self):
        """
        FIXME: Not used anymore; A leftover from an optimization. (delete)

        When an entity's component set is changed, it only needs to be
        tested against filters where the changed component's type is
        in the dependency list.

        While not saving any significant time in itself, this could be
        turned inside-out, mapping component types to a complete list of
        filters that relate to the type. This too though would only save
        noticeable time if there's lots and lots of systems, and
        component changes happen many times per update.

        :return: a set of all component types matched against by this filter
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


class AndFilter(Filter):  # fixme should this be a private or at least protected class?
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


class OrFilter(Filter):  # fixme maybe rename to _OrFilter
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
    
    :param types_and_filters: The :class:`wecs.core.Component` types and sub-filters that this
        (sub-)filter matches against.
    :return: The filter object

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
    
    :param types_and_filters: The :class:`wecs.core.Component` types and sub-filters that this
        (sub-)filter matches against.
    :return: The filter object
    """
    return OrFilter(*types_and_filters)

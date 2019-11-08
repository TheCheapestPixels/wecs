import types


def factory(factory_function):
    def func():
        return factory_function()
    return func


class Aspect:
    def __init__(self, aspects_or_components, overrides=None, name=None):
        self.name = name
        self.components = {}
        for aoc in aspects_or_components:
            if isinstance(aoc, (Aspect)):
                if any(key in aoc.components for key in self.components.keys()):
                    raise ValueError("Aspect {} has clashing components".format(aoc))
                self.components.update(aoc.components)
            else:
                if aoc in self.components:
                    raise ValueError("Component {} is already present in Aspect".format(aoc))
                self.components[aoc] = {}
        if overrides is not None:
            if not all(key in self.components for key in overrides.keys()):
                raise ValueError("Not all override keys in aspect.")
            self.components.update(overrides)

    def in_entity(self, entity):
        return all([component_type in entity for component_type in self.components])

    def add(self, entity, overrides=None):
        if any(component_type in entity for component_type in self.components):
            raise ValueError("Clashing components with entity.")
        for component in self(overrides=overrides):
            entity.add_component(component)

    def remove(self, entity):
        if not self.in_entity(entity):
            raise ValueError("Aspect not in entity.")
        components = []
        if self.in_entity(entity):
            for component_type in self.components:
                components.append(entity[component_type])
                del entity[component_type]
        return components

    def __call__(self, overrides=None):
        components = []
        if overrides is None:
            overrides = {}
        for component_type, defaults in self.components.items():
            # Shallow copy, since we will replace values through
            # overrides and factories
            arguments = self.components[component_type].copy()
            # Overrides
            if component_type in overrides:
                arguments.update(overrides[component_type])
            # Call factories
            for argument in arguments.keys():
                if callable(arguments[argument]):
                    arguments[argument] = arguments[argument]()
            # Create the component
            component = component_type(**arguments)
            components.append(component)
        return components

    def __contains__(self, component_type):
        return component_type in self.components

    def __repr__(self):
        if self.name is not None:
            return self.name
        else:
            return super().__repr__()

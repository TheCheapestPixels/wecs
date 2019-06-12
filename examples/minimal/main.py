from wecs.core import World, Component, System, and_filter, UID, NoSuchUID


# There is a world with an entity in it.
world = World()
entity = world.create_entity()

# Entities can be counters.
@Component()
class Counter:
    value: int

# The entity in the world is a counter.
entity.add_component(Counter(value=0))

# It is possible that in a world, all counters increase their count by
# one each frame.
class Count(System):
    entity_filters = {'counts': and_filter([Counter])}

    def update(self, entities_by_filter):
        for entity in entities_by_filter['counts']:
            entity.get_component(Counter).value += 1

# In this world, that is the case.
world.add_system(Count(), 0)

# Let's make some time pass in the world.
world.update()

# Whoops, no output? Typically we'd add a component to the entity to
# also make it a printer, but I want to show you entity references,
# so we'll do this unnecessarily complicated. There'll be a system
# that does printing for every entity *referenced by* a printing
# entity. 

@Component()
class Printer:
    printee: UID


class Print(System):
    entity_filters = {'prints': and_filter([Printer])}

    def update(self, entities_by_filter):
        for entity in entities_by_filter['prints']:
            reference = entity.get_component(Printer).printee
            # Maybe the reference doesn't point anywhere anymore?
            if reference is None:
                print("Empty reference.")
                return
            # Since those references are UIDs of entitites, not entitites
            # themselves, we'll need to resolve them. It may happen that a
            # referenced entity has been destroyed, so we'll need to handle that
            # case here as well.
            try:
                printed_entity = self.world.get_entity(reference)
            except NoSuchUID:
                print("Dangling reference.")
                return
            # But is it even counter anymore?
            if not printed_entity.has_component(Counter):
                print("Referenced entity is not a counter.")
                return
            # Okay, so the entity's printee is an existing entity that is a
            # Counter. We can actually print its value!
            print(printed_entity.get_component(Counter).value)


# So, let's update our world...
world.add_system(Print(), 1)
other_entity = world.create_entity()
other_entity.add_component(Printer(printee=entity._uid))
# ...and see whether it works.
world.update()
# ...and if we make the entity a non-counter?
entity.remove_component(Counter)
world.update()
# ...and if there is no other entity?
world.remove_entity(entity)
world.update()
# ...and if we unset the printee reference?
other_entity.get_component(Printer).printee = None
world.update()

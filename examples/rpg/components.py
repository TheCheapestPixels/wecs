from wecs.core import Component


# FIXME: This is obsolete and will be replaced by individual component
# types for specific actions.
@Component()
class Action:
    plan: str

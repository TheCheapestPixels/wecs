from wecs.core import Component


# Characters and items can have names, producing prettier output.
@Component()
class Name:
    name: str

from wecs.core import Component, UID, System, and_filter, or_filter

from character import Name
from lifecycle import Dead


# Trivial monologue.
@Component()
class TalkAction:
    talker: UID


@Component()
class Dialogue:
    phrase: str


class HaveDialogue(System):
    entity_filters = {
        'act': and_filter([TalkAction])
    }

    def update(self, filtered_entities):
        for entity in filtered_entities['act']:
            talker = self.world.get_entity(
                entity.get_component(TalkAction).talker,
            )
            entity.remove_component(TalkAction)

            if talker.has_component(Dead):
                print("Dead people don't talk.")
                return False

            # FIXME: Are they in the same room?

            if talker.has_component(Dialogue):
                if talker.has_component(Name):
                    print("> {} says: \"{}\"".format(
                        talker.get_component(Name).name,
                        talker.get_component(Dialogue).phrase,
                    ))
                else:
                    print("> " + talker.get_component(Dialogue).phrase)
            else:
                print("> \"...\"")
            entity.remove_component(TalkAction)

import dataclasses

import cefconsole

from wecs.core import System
from wecs.core import and_filter
from wecs.core import Component


class WECSSubconsole(cefconsole.Subconsole):
    name = "WECS"
    package = 'wecs'
    template_dir = 'templates'
    html = "wecs.html"
    funcs = {
        'refresh_wecs_matrix': 'refresh_wecs_matrix',
        'toggle_live_refresh_wecs_matrix': 'toggle_live_refresh_wecs_matrix',
    }
    refresh = True
    live_refresh = False

    def refresh_wecs_matrix(self):
        self.refresh = True

    def toggle_live_refresh_wecs_matrix(self):
        self.live_refresh = not self.live_refresh

    def update(self):
        if not hasattr(base, 'console'):
            return
        if self.refresh or self.live_refresh:
            entities = base.ecs_world.get_entities()
            uids = {e._uid.name: e for e in entities}
            uid_list = sorted(uids.keys())
            component_types = set()
            for entity in entities:
                for component in entity.components:
                    component_types.add(type(component))
            component_types = sorted(component_types, key=lambda ct: repr(ct))
            def crepr(e, ct):
                if ct in e:
                    return e[ct]
                else:
                    return None
            matrix = [
                (uid, [crepr(uids[uid], ct) for ct in component_types])
                for uid in uid_list
            ]
            template = base.console.env.get_template('{}/wecs_matrix.html'.format(self.name))
            content = template.render(
                component_types=component_types,
                matrix=matrix,
            )
            self.console.exec_js_func('update_wecs_matrix', content)
            self.refresh = False


class UpdateWecsSubconsole(System):
    entity_filters = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(base, 'console'):
            self.has_console = False
            return
        self.has_console = True
        self.subconsole = WECSSubconsole()
        base.console.add_subconsole(self.subconsole)

    def update(self, entities_by_filter):
        if self.has_console:
            self.subconsole.update()


class EntityWatcherSubconsole(cefconsole.Subconsole):
    name = "Entity Watcher"
    package = 'wecs'
    template_dir = 'templates'
    html = "entity.html"
    funcs = {
    }

    def update(self, entities):
        if not hasattr(base, 'console'):
            return
        entities = [
            {'obj': e}
            for e in sorted(
                    list(entities),
                    key=lambda e:repr(e._uid),
            )
        ]

        for entity in entities:
            entity['uid'] = entity['obj']._uid
            entity['components'] = sorted(
                list(entity['obj'].get_components()),
                key=lambda c: repr(c),
            )
            entity['components'] = [
                {'obj': c}
                for c in entity['components']
            ]
            for component in entity['components']:
                component['name'] = type(component['obj'])
                component['fields'] = dataclasses.fields(component['obj'])
                component['fields'] = [
                    {
                        'name': f.name,
                        'type': f.type,
                        'value': getattr(component['obj'], f.name)
                    }
                    for f in component['fields']
                ]


        template = base.console.env.get_template('{}/watcher.html'.format(self.name))
        content = template.render(
            entities=entities,
        )
        self.console.exec_js_func('update_entity_watcher', content)


@Component()
class WatchedEntity:
    pass


class WatchEntitiesInSubconsole(System):
    entity_filters = {
        'watched': and_filter([WatchedEntity]),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(base, 'console'):
            self.has_console = False
            return
        self.has_console = True
        self.subconsole = EntityWatcherSubconsole()
        base.console.add_subconsole(self.subconsole)

    def update(self, entities_by_filter):
        if self.has_console:
            self.subconsole.update(entities_by_filter['watched'])

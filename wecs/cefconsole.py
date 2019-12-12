import cefconsole

from wecs.core import System


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
        if self.refresh or self.live_refresh:
            entities = base.ecs_world.entities
            uids = {repr(e._uid): e for e in entities}
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
        self.subconsole = WECSSubconsole()
        base.console.add_subconsole(self.subconsole)

    def update(self, entities_by_filter):
        self.subconsole.update()

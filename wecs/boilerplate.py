import sys

from panda3d.core import PStatClient
from panda3d.core import loadPrcFileData

from .repl import Interpreter

# We want the time of collision traversal to be added to systems that
# run them.
loadPrcFileData('', 'pstats-active-app-collisions-ctrav false')

from wecs.panda3d import ECSShowBase as ShowBase


def run_game(simplepbr=False, simplepbr_kwargs=None, console=False):
    # Application Basics
    ShowBase()
    base.win.setClearColor((0.5,0.7,0.9,1))
    base.disable_mouse()
    if simplepbr is True:
        import simplepbr
        if simplepbr_kwargs is None:
            simplepbr_kwargs = {}  # i.e. dict(max_lights=1)
        simplepbr.init(**simplepbr_kwargs)

    # Handy Helpers:
    # esc: quit
    # f 9: console
    # f10: frame rate meter
    # f11: pdb, during event loop
    # f12: pstats; connects to a running server
    base.accept('escape', sys.exit)

    if console:
        base.console_open = False
        base.console = make_console()
        base.console.node().hide()
        def toggle_console():
            base.console_open = not base.console_open
            if base.console_open:
                base.console.node().show()
            else:
                base.console.node().hide()
        base.accept('f9', toggle_console)

    base.frame_rame_meter_visible = False
    base.set_frame_rate_meter(base.frame_rame_meter_visible)
    def toggle_frame_rate_meter():
        base.frame_rame_meter_visible = not base.frame_rame_meter_visible
        base.set_frame_rate_meter(base.frame_rame_meter_visible)
    base.accept('f10', toggle_frame_rate_meter)

    def debug():
        import pdb; pdb.set_trace()
    base.accept('f11', debug)

    def pstats():
        base.pstats = True
        PStatClient.connect()
    base.accept('f12', pstats)

    # Set up the world:
    import game
    for sort, system_type in enumerate(game.system_types):
        base.add_system(system_type(), sort)
    if console:
        base.console.render_console()

    # And here we go...
    base.run()


class Subconsole:
    name = ""
    funcs = {}

    def hook_js_funcs(self, console):
        self.console = console
        for js_func, py_func_name in self.funcs.items():
            console.set_js_function(js_func, getattr(self, py_func_name))


class DemoSubconsole(Subconsole):
    name = "Demo"
    html = "demo.html"
    funcs = {'call_python': 'test_hook'}

    def test_hook(self):
        self.console.exec_js_func('color_text', 'red')


class PythonSubconsole(Subconsole):
    name = "Python"
    html = "python.html"
    funcs = {'read_eval': 'read_and_eval'}
    interpreter = Interpreter()

    def read_and_eval(self, input):
        self.interpreter.runline(input)
        out = self.interpreter.output_string
        prompt = self.interpreter.prompt
        self.console.exec_js_func("print_output", out, prompt)


def make_console():
    import cefpanda
    from jinja2 import Environment
    from jinja2 import PackageLoader
    from jinja2 import select_autoescape

    class Console(cefpanda.CEFPanda):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.subconsoles = []
            self.env = Environment(
                loader=PackageLoader('wecs', 'ui'),
                autoescape=select_autoescape(['html', 'xml'])
            )

        def add_subconsole(self, subconsole):
            self.subconsoles.append(subconsole)

        def render_console(self):
            for subconsole in self.subconsoles:
                subconsole.hook_js_funcs(self)
            template = self.env.get_template('console.html')
            content = template.render(subconsoles=self.subconsoles)
            self.load_string(content)

    console = Console() # size=[-1, 1, -0.33, 1])
    # console.add_subconsole(DemoSubconsole())
    console.add_subconsole(PythonSubconsole())
    return console

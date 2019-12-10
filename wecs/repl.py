import sys
import traceback

from panda3d.core import Notify
from panda3d.core import StringStream
from io import StringIO
from contextlib import redirect_stdout
from code import InteractiveConsole


class Interpreter(InteractiveConsole):
    def __init__(self, *args):
        InteractiveConsole.__init__(self, *args)
        self.stream = StringStream()
        self.stringio = StringIO()
        self.input_string = ""
        self.output_string = ""
        self.more = 0
        self.prompt = ">>> "

    def runline(self, line):
        self.output_string = ""
        self.input_string = self.prompt + line + "\n"
        self.write(self.input_string)

        if self.push(line):
            self.prompt = "... "
        else:
            self.prompt = ">>> "

    def showsyntaxerror(self, filename=None):
        type, value, tb = sys.exc_info()
        sys.last_type = type
        sys.last_value = value
        sys.last_traceback = tb
        if filename and type is SyntaxError:
            # Work hard to stuff the correct filename in the exception
            try:
                msg, (dummy_filename, lineno, offset, line) = value.args
            except ValueError:
                # Not the format we expect; leave it alone
                pass
            else:
                # Stuff in the right filename
                value = SyntaxError(msg, (filename, lineno, offset, line))
                sys.last_value = value
        lines = traceback.format_exception_only(type, value)
        self.write(''.join(lines))

    def runcode(self, code):
        # Empty buffers
        self.stringio.truncate(0)
        self.stringio.seek(0)
        self.stream.clearData()
        try:
            # Swap buffers
            notify = Notify.ptr()
            old_notify = notify.get_ostream_ptr()
            notify.set_ostream_ptr(self.stream, False)
            with redirect_stdout(self.stringio):
            # Exec, writing output to buffers
                exec(code, self.locals)
            # Write buffers to output string.
            io_data = self.stringio.getvalue()
            stream_data = self.stream.getData().decode("utf-8")
            self.write(io_data + stream_data)
            # Restore buffers
            notify.set_ostream_ptr(old_notify, False)
        except:
            self.showtraceback()

    def showtraceback(self):
        sys.last_type, sys.last_value, last_tb = ei = sys.exc_info()
        sys.last_traceback = last_tb
        try:
            # Normally, if someone has set sys.excepthook, we let that take
            # precedence over self.write; but cefpython sets sys.excepthook
            # making this behavior undesirable
            lines = traceback.format_exception(ei[0], ei[1], last_tb.tb_next)
            self.write(''.join(lines))
        finally:
            last_tb = ei = None

    def write(self, output_string):
        self.output_string += output_string

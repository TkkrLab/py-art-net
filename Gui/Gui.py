import pygtk
import gtk
import gtk.gdk as gdk
import gobject
import pango
# from gtkcodebuffer import CodeBuffer, SyntaxLoader
import py_compile
import sys
# import traceback
import gtksourceview2 as gtksourceview

from MatrixSim.MatrixScreen import MatrixScreen
from MatrixSim.Interfaces import Interface
from Graphics.Graphics import Graphics, BLACK
from matrix import matrix_width, matrix_height, convertSnakeModes
import artnet
import socket

pygtk.require('2.0')


class PatternDummy(object):
    def __init__(self):
        self.graphics = Graphics(matrix_width, matrix_height)
        self.color = BLACK
        self.graphics.fill(self.color)

    def generate(self):
        return self.graphics.getSurface()


class SendPacketWidget(gtk.ToggleButton):
    def __init__(self, parent, dest_ip='localhost', port=6454):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.port = port
        self.dest_ip = dest_ip
        self.par = parent
        self.pattern = None

    def sendout(self, data):
        try:
            self.socket.sendto(artnet.buildPacket(0, data),
                               (self.dest_ip, self.port))
        except Exception as e:
            print >>self.par, e


class MatrixSimWidget(gtk.DrawingArea, Interface):
    def __init__(self, parent):
        self.args = parent.args
        self.par = parent
        self.pattern = None

        gtk.DrawingArea.__init__(self)
        Interface.__init__(self, matrix_width, matrix_height,
                           self.args.pixelSize)
        self.connect("expose-event", self.expose)

        self.matrixscreen = MatrixScreen(matrix_width, matrix_height,
                                         self.args.pixelSize, self)
        gtk.DrawingArea.set_size_request(self, self.width, self.height)
        # contains data from patterns in the form of a list of tuples of
        # format (r, g, b) colors.
        self.data = None
        # debug printing only once.
        self.hasprinted = False

    def get_pattern(self):
        return self.pattern

    def set_pattern(self, pattern):
        self.pattern = pattern

    def color_convert_f(self, color, depth=8):
        temp = []
        for c in color:
            temp.append(c / 255.)
        return tuple(temp)

    def get_target(self):
        return self.target

    def set_target(self, target):
        return self.target

    def get_data(self):
        return self.data

    def process(self):
        if self.pattern:
            try:
                self.data = self.pattern.generate()
                self.matrixscreen.process_pixels(self.data)
                self.queue_draw()
            except Exception as e:
                if not self.hasprinted:
                    print >>self.par, ("Wrong data Generated >> %s" % e)
                self.hasprinted = True
        return True

    def expose(self, widget, event):
        cr = widget.window.cairo_create()
        if len(self.matrixscreen.pixels):
            for pixel in self.matrixscreen.pixels:
                x, y, width, height = pixel.getRect()
                pixelcolor = pixel.getColor()
                r, g, b = self.color_convert_f(pixelcolor)
                cr.set_source_rgb(0.0, 0.0, 0.0)
                cr.rectangle(x, y, width, height)
                cr.stroke()
                cr.set_source_rgb(r, g, b)
                cr.rectangle(x + 1, y + 1, width - 2, height - 2)
                cr.fill()


class Gui(object):
    def __init__(self, args):
        self.args = args
        # tabwidth in spaces
        self.tabwidth = 4
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)

        self.window.set_title("artnet-editor")
        self.window.connect("destroy", gtk.main_quit)

        self.matrix_widget = MatrixSimWidget(self)
        self.send_packets = SendPacketWidget(self, 'localhost')

        if self.args.fps:
            gobject.timeout_add(int(1000 / self.args.fps), self.run)
        else:
            gobject.timeout_add(0, self.run)

        width, height = self.matrix_widget.width, self.matrix_widget.height
        self.window.resize(width * 2, height * 2)
        self.syntaxfile = "/home/robert/py-artnet/Gui/syntax-highlight/python"
        self.textfilename = "/home/robert/py-artnet/Gui/new_file.py"
        self.intermediatefilename = ("/home/robert/py-artnet/Gui/" +
                                     "IntermediateCode/intermediate.py")

        # menu items
        mb = gtk.MenuBar()

        filemenu = gtk.Menu()
        filem = gtk.MenuItem("_File")
        filem.set_submenu(filemenu)

        agr = gtk.AccelGroup()
        self.window.add_accel_group(agr)

        # shortcut for creating a new file
        newi = gtk.ImageMenuItem(gtk.STOCK_NEW, agr)
        key, mod = gtk.accelerator_parse("<Control>N")
        newi.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)
        newi.connect("activate", self.newfile)
        filemenu.append(newi)

        # shortcut for opening a file.
        openm = gtk.ImageMenuItem(gtk.STOCK_OPEN, agr)
        key, mod = gtk.accelerator_parse("<Control>O")
        openm.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)
        openm.connect("activate", self.openfile)
        filemenu.append(openm)

        # shortcut for saving a file.
        savem = gtk.ImageMenuItem(gtk.STOCK_SAVE, agr)
        key, mod = gtk.accelerator_parse("<Control>S")
        openm.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)
        savem.connect("activate", self.savefile)
        filemenu.append(savem)

        # shortcut for reloading
        reloadm = gtk.ImageMenuItem(gtk.STOCK_REFRESH, agr)
        key, mod = gtk.accelerator_parse("<Control>R")
        reloadm.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)
        reloadm.connect("activate", self.reload_code_on_shortcut)
        filemenu.append(reloadm)

        sep = gtk.SeparatorMenuItem()
        filemenu.append(sep)
        # shortcut for quiting
        exit = gtk.ImageMenuItem(gtk.STOCK_QUIT, agr)
        key, mod = gtk.accelerator_parse("<Control>Q")
        exit.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)
        exit.connect("activate", gtk.main_quit)
        filemenu.append(exit)
        mb.append(filem)

        # the edit menu for all edit related things :)
        editmenu = gtk.Menu()
        editm = gtk.MenuItem("_Edit")
        editm.set_submenu(editmenu)

        # shortcut for undoing your change to the text.
        undom = gtk.ImageMenuItem(gtk.STOCK_UNDO)
        key, mod = gtk.accelerator_parse("<Control>Z")
        undom.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)
        undom.connect("activate", self.undo_text_cb)
        editmenu.append(undom)

        # shortcut for redoing your text change
        redom = gtk.ImageMenuItem(gtk.STOCK_REDO)
        key, mod = gtk.accelerator_parse("<Control>Y")
        redom.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)
        redom.connect("activate", self.redo_text_cb)
        editmenu.append(redom)

        mb.append(editm)

        # syntax highlighting.
        # self.lang = SyntaxLoader(self.syntaxfile)
        # self.buff = CodeBuffer(lang=self.lang)
        lm = gtksourceview.LanguageManager()
        self.language = lm.get_language('python')
        self.buff = gtksourceview.Buffer(language=self.language)
        self.buff.set_text(self.loadfile(self.intermediatefilename))
        self.buff.set_highlight_syntax(True)
        self.buff.set_highlight_matching_brackets(True)

        self.textview = gtksourceview.View(self.buff)
        self.textview.set_show_line_numbers(True)
        self.textview.set_show_line_marks(True)
        self.textview.set_show_right_margin(True)
        self.textview.set_auto_indent(True)
        self.textview.set_draw_spaces(gtksourceview.DRAW_SPACES_SPACE)
        self.textview.set_insert_spaces_instead_of_tabs(True)
        self.textview.set_indent_on_tab(True)
        self.textview.set_tab_width(self.tabwidth)
        fontdesc = pango.FontDescription("monospace 8")
        self.textview.modify_font(fontdesc)
        tabs = pango.TabArray(1, True)
        tabs.set_tab(0, pango.TAB_LEFT, 32)
        self.textview.set_tabs(tabs)
        self.scrolledwindow = gtk.ScrolledWindow()
        self.scrolledwindow.add(self.textview)

        self.hbox = gtk.HBox()
        self.vbox = gtk.VBox()
        self.vbox.pack_start(mb, False, False)
        self.vbox.pack_start(self.scrolledwindow)
        self.hbox.pack_start(self.vbox)
        # this sets it so that the scrolledwindow follows matrix_widget
        self.vbox2 = gtk.VBox()
        self.vbox2.pack_start(self.matrix_widget)
        self.poutputbuff = gtk.TextBuffer()
        self.poutput = gtk.TextView(self.poutputbuff)
        self.pscrolled = gtk.ScrolledWindow()
        self.pscrolled.add(self.poutput)
        self.poutput.set_editable(False)
        self.poutput.set_wrap_mode(gtk.WRAP_WORD)
        self.poutput.connect("size_allocate", self.treeview_changed)
        self.vbox2.pack_start(self.pscrolled)
        self.hbox.pack_start(self.vbox2, False, True)
        self.window.add(self.hbox)

        cb = self.key_released
        self.keyrelease_id = self.textview.connect("key-release-event", cb)
        cb = self.key_pressed
        self.key_pressed_id = self.textview.connect("key-press-event", cb)

        self.window.show_all()

        # do this once and we can import our compiled code.
        self.modpath = '/'.join(self.intermediatefilename.split('/')[:-1])
        sys.path.insert(0, self.modpath)
        # clear intermediate code.
        self.storefile(self.intermediatefilename, "")
        self.storefile(self.intermediatefilename + 'c', "")
        # then load module
        self.intermediate = __import__("intermediate")
        self.colonReleased = False

    def key_pressed(self, widget, event):
        """Check if the key press is 'Return' or 'Backspace' and indent or
        un-indent accordingly.
        """
        buffer = self.buff
        view = widget
        key_name = gdk.keyval_name(event.keyval)
        if key_name not in ('Return', 'Backspace') or \
           len(buffer.get_selection_bounds()) != 0:
            # If some text is selected we want the default behavior of Return
            # and Backspace so we do nothing
            return

        if view.get_insert_spaces_instead_of_tabs():
            self.indent = ' ' * view.props.tab_width
        else:
            self.indent = '\t'

        if key_name == 'Return':
            line = self._get_current_line(buffer)

            if line.endswith(':'):
                old_indent = line[:len(line) - len(line.lstrip())]
                buffer.insert_at_cursor('\n' + old_indent + self.indent)
                return True

            else:
                stripped_line = line.strip()
                n = len(line) - len(line.lstrip())
                starts_with_return = stripped_line.startswith('return')
                starts_with_break = stripped_line.startswith('break')
                starts_with_continue = stripped_line.startswith('continue')
                starts_with_pass = stripped_line.startswith('pass')
                con_check = (starts_with_return or starts_with_break or
                             starts_with_continue or starts_with_pass)
                if (con_check):
                    n -= len(self.indent)

                buffer.insert_at_cursor('\n' + line[:n])
                self._scroll_to_cursor(buffer, view)
                return True

        if key_name == 'BackSpace':
            line = self._get_current_line(buffer)

            if line.strip() == '' and line != '':
                length = len(self.indent)
                nb_to_delete = len(line) % length or length
                self._delete_before_cursor(buffer, nb_to_delete)
                self._scroll_to_cursor(buffer, view)
                return True

    def _delete_before_cursor(self, buffer, nb_to_delete):
        cursor_position = buffer.get_property('cursor-position')
        iter_cursor = buffer.get_iter_at_offset(cursor_position)
        iter_before = buffer.get_iter_at_offset(cursor_position - nb_to_delete)
        buffer.delete(iter_before, iter_cursor)

    def _get_current_line(self, buffer):
        iter_cursor = self._get_iter_cursor(buffer)
        iter_line = buffer.get_iter_at_line(iter_cursor.get_line())
        return buffer.get_text(iter_line, iter_cursor)

    def _get_current_line_nb(self, buffer):
        iter_cursor = self._get_iter_cursor(buffer)
        return iter_cursor.get_line()

    def _get_iter_cursor(self, buffer):
        cursor_position = buffer.get_property('cursor-position')
        return buffer.get_iter_at_offset(cursor_position)

    def _scroll_to_cursor(self, buffer, view):
        # lineno = self._get_current_line_nb(buffer) + 1
        insert = buffer.get_insert()
        view.scroll_mark_onscreen(insert)

    def key_released(self, widget, key):
        # reload except on ctrl-r
        if key.keyval != 114 and key.keyval != 65507:
            try:
                self.reload_code()
            except Exception as e:
                print >>self, e
        return

    def treeview_changed(self, widget, event, data=None):
        # automaticly follow scrolling with the text
        adj = self.scrolledwindow.get_vadjustment()
        adj.set_value(adj.upper - adj.page_size)

        adj = self.pscrolled.get_vadjustment()
        adj.set_value(adj.upper - adj.page_size)

    def run(self):
        self.matrix_widget.process()
        data = self.matrix_widget.get_data()
        if data:
            data = convertSnakeModes(data)
            self.send_packets.sendout(data)
        return True

    def redo_text_cb(self, widget):
        self.buff.redo()

    def undo_text_cb(self, widget):
        self.buff.undo()

    def reload_code_on_shortcut(self, widget):
        try:
            self.reload_code()
        except Exception as e:
            print >>self, e

    def get_pattern_classes(self, module):
        # holds the patterns that are found
        patterns = []
        # look into the modules dictionary for the things in there
        for obj in module.__dict__:
            # if we find objects
            if isinstance(obj, object):
                try:
                    # we try and get that objects dictionary.
                    # if it's a class it will contain methods and more.
                    thedict = module.__dict__[obj].__dict__
                    # and if it contains the 'generate' method
                    if(thedict['generate']):
                        # the class is appended to the list.
                        patterns.append(module.__dict__[obj])
                except:
                    # continue if we try and read something we can't.
                    continue
        # return a list of classes that have a generate function in them
        return patterns

    def write(self, string):
        end_iter = self.poutputbuff.get_end_iter()
        self.poutputbuff.insert(end_iter, string)

    def reload_code(self):
        print >>self, ("Reloading")
        # empty out the .pyc and .py file
        self.storefile(self.intermediatefilename + 'c', "")
        text = self.get_text()
        # save and compile the text in the text widget on change.
        # always get the latest itteration of the compiled code.
        self.storefile(self.intermediatefilename, text)
        py_compile.compile(self.intermediatefilename)
        # check agains all the classes in intermediate code base.
        try:
            self.intermediate = reload(self.intermediate)
        except Exception as e:
            print >>self, "reload()>> " + str(e)
        if len(self.get_pattern_classes(self.intermediate)):
            print >>self, (self.get_pattern_classes(self.intermediate))
        try:
            patterns = self.get_pattern_classes(self.intermediate)
            pattern = patterns[0]()
        except Exception as e:
            pattern = PatternDummy()
            print >>self, "No valid Class with Generate function found!"
        self.matrix_widget.set_pattern(pattern)
        # reset hasprinted in matrix_widget, cause now it might work.
        if self.matrix_widget.hasprinted:
            self.matrix_widget.hasprinted = False

    def get_text(self):
        start_iter = self.buff.get_start_iter()
        end_iter = self.buff.get_end_iter()
        text = self.buff.get_text(start_iter, end_iter, True)
        return text

    def loadfile(self, file):
        text = []
        with open(file, 'r') as thefile:
            text.append(thefile.read())
        return text[0]

    def storefile(self, filename, text):
        with open(filename, 'w') as thefile:
            thefile.write(text)

    def savefile(self, widget):
        fmt = (self.textfilename, )
        fmtstr = "Saving into: %s" % fmt
        print >>self, (fmtstr)
        self.storefile(self.textfilename, self.get_text())

    def newfile(self, widget):
        print >>self, ("supposed to make a new empty file")

    def openfile(self, widget):
        # create a dialog window.
        dialog = gtk.FileChooserDialog("Open..",
                                       None,
                                       gtk.FILE_CHOOSER_ACTION_OPEN,
                                       (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                        gtk.STOCK_OPEN, gtk.RESPONSE_OK)
                                       )
        dialog.set_default_response(gtk.RESPONSE_OK)

        filter = gtk.FileFilter()
        filter.set_name("Python Files.")
        filter.add_mime_type("python")
        filter.add_pattern("*.py")
        dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        dialog.add_filter(filter)

        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            self.textfilename = dialog.get_filename()
            self.buff.set_text(self.loadfile(self.textfilename))
        dialog.destroy()

    def main(self):
        gtk.main()

import time
import sys

from Ledart.Tools.Graphics import BLUE, BLACK
from Ledart.Tools.Graphics import Surface

# setup interface options, if no interface possible
# set to a dummy
from Interfaces.DummyInterface import DummyInterface
interface_opts = {
    "dummy": DummyInterface
}

# set an option for a pygame interface
try:
    from Interfaces.PygameInterface import PygameInterface
    interface_opts["pygame"] = PygameInterface
except Exception as e:
    print("module not installed, %s" % str(e))
    interface_opts["pygame"] = DummyInterface

# set an option for a opengl interface
try:
    from Interfaces.OpenGlInterface import OpenGlInterface
    interface_opts["opengl"] = OpenGlInterface
except Exception as e:
    print("Module not installed, %s" % str(e))
    interface_opts["opengl"] = DummyInterface


class MatrixScreen(object):
    """
    this module/class is a matrix simulator (led)
    it draws blocks in a array the size of the pixels is
    defined in matrix.py
    """
    def __init__(self, width=1, height=1, pixelsize=10, fullscreen=False,
                 interface=DummyInterface):
        self.interface = interface(width, height, pixelsize, fullscreen)
        self.width = width
        self.height = height
        self.pixelSize = pixelsize

        self.window_width = width * pixelsize
        self.window_height = height * pixelsize

        self.interface.setcaption("Matrix Simulator.")
        self.psurface = Surface(width=width, height=height)

    def handleinput(self):
        self.interface.handleinput()

    def draw(self, data):
        # get the indexes of every pixel
        indexes = data.indexes
        # itterate of the colors of every pixel.
        for i, index in enumerate(indexes):
            # take the color
            color = data[index]

            # only draw if pixels differ
            if color != self.psurface[index]:
                # calculate position based on index, pixelsize, and data offset.
                x, y = index
                x, y = x * self.pixelSize, y * self.pixelSize
                xo, yo = data.get_d_offset()
                xo, yo = xo * self.pixelSize, yo * self.pixelSize
                x, y = x + xo, y + yo
                # create a rect based on calculated positions.
                width, height = self.pixelSize, self.pixelSize
                rect = (x, y, width, height)
                # draw the actual block
                self.interface.drawblock(rect, color)
                # store the color we just drew
                self.psurface[index] = color

    def process(self, data):
        self.draw(data)
        # update the screen so our data is shown.
        self.interface.update()

    def close(self):
        self.interface.quit()

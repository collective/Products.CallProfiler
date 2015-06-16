# Copyright (c) ekit.com Inc (http://www.ekit-inc.com/)
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included in
#   all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# This product includes software developed by Digital Creations for use in
# the Z Object Publishing Environment (http://www.zope.org/).
# (specifically, we use the control panel installation code from LeakFinder)

__version__ = '1.4'

from App.ImageFile import ImageFile
from CallProfiler import CallProfiler
import OFS
import os


def initialize(context):
    app = context._ProductContext__app
    no_product_install = app is None
    if no_product_install:
        # must open a secondary ZODB connection to access "Control_Panel"
        # Note: in general, it is dangerous to access the same ZODB from
        # different connections in the same transaction (deadlock may occur)
        # In our special case, our connection should be the only writing one.
        # If necessary, we could abort an existing transaction.
        from transaction import commit  # to be used later
        from Zope2 import app as z_app
        app = z_app()
    try:
        control_panel = app.Control_Panel
        id_ = CallProfiler.id
        CallProfiler.icon = createIcon('www/profiler.gif', globals(), id_)
        panel = getattr(control_panel, id_, None)
        if panel is None:
            panel = CallProfiler()
            control_panel._setObject(id_, panel)
            if no_product_install:
                commit()  # to ensure, `CallProfiler` is installed
    finally:
        if no_product_install:
            app._p_jar.close()


def createIcon(iconspec, _prefix, pid):
    name = os.path.split(iconspec)[1]
    res = 'misc_/%s/%s' % (pid, name)
    icon = ImageFile(iconspec, _prefix)
    icon.__roles__ = None
    if not hasattr(OFS.misc_.misc_, pid):
        setattr(OFS.misc_.misc_, pid, OFS.misc_.Misc_(pid, {}))
    getattr(OFS.misc_.misc_, pid)[name] = icon
    return res

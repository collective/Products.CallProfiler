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

import Globals, OFS, os
from App.ApplicationManager import ApplicationManager
from Acquisition import aq_base
from App.ImageFile import ImageFile

import CallProfiler

def installControlPanel(context, panelClass):
    app = context._ProductContext__app
    cp = app.Control_Panel
    id = panelClass.id
    if 0: # Enable to clean up the control panel.
        try: del cp._objects
        except: pass
    cp.id # Unghostify.
    if cp.__dict__.has_key('_objects'):
        # _objects has been overridden.  We have to persist.
        existing = getattr(aq_base(cp), id, None)
        if existing is None or existing.__class__ != panelClass:
            cp._setObject(id, panelClass())
    else:
        # Don't persist what we don't have to.
        objects = ApplicationManager._objects
        objects = filter(lambda o, id=id: o['id'] != id, objects)
        ApplicationManager._objects = objects + (
            {'id':id, 'meta_type':panelClass.meta_type},)
        try: delattr(cp, id)
        except: pass
        setattr(ApplicationManager, id, panelClass())
    return cp._getOb(id)

_prodname = __name__.split('.')[-1]

def createIcon(iconspec, _prefix, pid=_prodname):
    name = os.path.split(iconspec)[1]
    res = 'misc_/%s/%s' % (pid, name)
    icon = ImageFile(iconspec, _prefix)
    icon.__roles__=None
    if not hasattr(OFS.misc_.misc_, pid):
        setattr(OFS.misc_.misc_, pid, OFS.misc_.Misc_(pid, {}))
    getattr(OFS.misc_.misc_, pid)[name]=icon
    return res

def initialize(context):
    installControlPanel(context, CallProfiler.CallProfiler)
    CallProfiler.CallProfiler.icon = createIcon('www/profiler.gif', globals())


# This is the initialize to use when not auto-installed in the Control Panel
#def initialize(context):
#    context.registerClass(
#	CallProfiler, meta_type = 'Call Profiler',
#	constructors = (CallProfiler.manage_addForm, CallProfiler.manage_add),
#	icon = 'www/profiler.gif'
#    )

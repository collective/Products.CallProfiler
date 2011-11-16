# Copyright (c) 2002 ekit.com Inc (http://www.ekit-inc.com/)
# 
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

# $Id: CallProfiler.py,v 1.12 2002/02/08 04:57:22 rjones Exp $

from App.class_init import InitializeClass
from App.special_dtml import HTMLFile
from OFS.SimpleItem import Item
from Acquisition import Implicit
from Persistence import Persistent
from AccessControl import ClassSecurityInfo
from AccessControl import ModuleSecurityInfo
modulesecurity = ModuleSecurityInfo()

import cStringIO
import time, operator
from thread import get_ident

# get the profiler store
from profiler import profiler

def profiler_call_hook(self, *args, **kw):
    '''A call hook
    '''
    mt = self.meta_type
    sid = self.getId()
    profiler.startCall(mt, sid)
    try:
        return self.profiler_call_original(*args, **kw)
    finally:
        profiler.endCall()

def profiler_publish_hook(request, *args, **kw):
    '''Publisher hook
    '''
    profiler.startRequest(request)
    import ZPublisher.Publish
    try:
        return ZPublisher.Publish.profiler_publish_original(request, *args, **kw)
    finally:
        # if we die here, we want to catch it or the publisher will get
        # confused...
        try:
            profiler.endRequest()
        except:
            # log the error though
            from zLOG import LOG, ERROR
            import sys
            LOG('CallProfiler.publish_hook', ERROR,
                'Error during endmark()', error=sys.exc_info())

class Profileable:
    def __init__(self, module, klass, method):
        self.module = module
        self.method = method

        # get the actual class to patch
        try:
            mod = __import__(module)
        except ImportError:
            self.klass = None
            return
        components = module.split('.')
        for comp in components[1:]:
            mod = getattr(mod, comp)
        self.klass = getattr(mod, klass)
        self.name = self.klass.meta_type
        self.icon = None
        if hasattr(self.klass, 'icon'):
            self.icon = self.klass.icon

    def install(self):
        '''Install the call hook
        '''
        self.klass.profiler_call_original = getattr(self.klass, self.method)
        setattr(self.klass, self.method, profiler_call_hook)

    def uninstall(self):
        '''Uninstall the call hook
        '''
        setattr(self.klass, self.method, self.klass.profiler_call_original)
        del self.klass.profiler_call_original

    def isInstalled(self):
        '''See if the call hook has been installed
        '''
        return hasattr(self.klass, 'profiler_call_original')

    def isAvailable(self):
        '''See if the module is actually available
        '''
        return self.klass is not None

    def checkbox(self):
        '''Display a checkbox to configure this
        '''
        if self.isInstalled():
            s = 'CHECKED'
        else:
            s = ''
        return '<input name="enabled:list" type="checkbox" value="%s"%s>%s'%(
            self.name, s, self.name)

profileable_modules = {
    'Page Template': Profileable('Products.PageTemplates.PageTemplates',
        'PageTemplates', '__call__'),
    'DTML Method': Profileable('OFS.DTMLMethod', 'DTMLMethod', '__call__'),
    'MLDTMLMethod': Profileable('Products.MLDTML.MLDTML',
        'MLDTMLMethod', '__call__'),
    'Z SQL Method': Profileable('Products.ZSQLMethods.SQL', 'SQL', '__call__'),
    'Python Method': Profileable('Products.PythonMethod.PythonMethod',
        'PythonMethod', '__call__'),
    'Script (Python)': Profileable('Products.PythonScripts.PythonScript',
        'PythonScript', '_exec'),
    'Filesystem Script (Python)':
        Profileable('Products.CMFCore.FSPythonScript', 'FSPythonScript',
            '__call__'),
    'Filesystem DTML Method':
        Profileable('Products.CMFCore.FSDTMLMethod', 'FSDTMLMethod',
            '__call__'),
    'Filesystem Page Template':
        Profileable('Products.CMFCore.FSPageTemplate', 'FSPageTemplate',
            '__call__'),
}
        


class CallProfiler(Item, Implicit, Persistent):
    '''An instance of this class provides an interface between Zope and
       roundup for one roundup instance
    '''
    id = 'CallProfiler'
    title = meta_type =  'Call Profiler'
    security = ClassSecurityInfo()

    # define the tabs for the management interface
    manage_options = (
        {'label': 'Configure', 'action':'configureForm'},
        {'label': 'Results', 'action':'results'},
        {'label': 'Results by URL', 'action':'resultsByURL'},
        {'label': 'Aggregates', 'action':'aggregates'},
    ) + Item.manage_options

    #
    # Configuration interface
    #

    # configuration form
    configureForm = HTMLFile('dtml/configure', globals())
    detail = HTMLFile('dtml/detail', globals())
    results = HTMLFile('dtml/results', globals())
    aggregates = HTMLFile('dtml/aggregates', globals())
    aggregateDetail = HTMLFile('dtml/aggregateDetail', globals())
    resultsByURL = HTMLFile('dtml/resultsByURL', globals())
    security.declareProtected('View management screens', 'configureForm',
        'detail', 'results', 'resultsByURL')

    security.declareProtected('View management screens', 'getComponentModules')
    def getComponentModules(self):
        '''List the components available to profile
        '''
        l = []
        names = profileable_modules.keys()
        names.sort()
        for name in names:
            if profileable_modules[name].isAvailable():
                l.append((name, profileable_modules[name]))
        return l

    security.declareProtected('View management screens', 'monitorAll')
    def monitorAll(self):
        '''Set to monitor all that we can
        '''
        enabled = [x[0] for x in self.getComponentModules()]
        return self.configure(enabled=enabled)

    security.declareProtected('View management screens', 'monitorNone')
    def monitorNone(self):
        '''Set to monitor no calls
        '''
        return self.configure()

    security.declareProtected('View management screens', 'configure')
    def configure(self, enabled=[]):
        '''Set the given items to enabled
        '''
        # install or uninstall the publisher hook as required
        if not enabled and self.isPublisherHookInstalled():
            self.uninstallPublisherHook()
        elif enabled and not self.isPublisherHookInstalled():
            self.installPublisherHook()

        # now install the selected modules
        for component, module in self.getComponentModules():
            if component in enabled and not module.isInstalled():
                module.install()
            elif component not in enabled and module.isInstalled():
                module.uninstall()

        if not enabled:
            message = 'all profiling disabled'
        else:
            message = ', '.join(enabled) + ' enabled'

        return self.configureForm(self, self.REQUEST,
            manage_tabs_message=message)

    security.declarePrivate('installPublisherHook')
    def installPublisherHook(self):
        '''Set the ZPublisher hook
        '''
        import ZPublisher.Publish
        ZPublisher.Publish.profiler_publish_original=ZPublisher.Publish.publish
        ZPublisher.Publish.publish = profiler_publish_hook

    security.declarePrivate('uninstallPublisherHook')
    def uninstallPublisherHook(self):
        '''Remove the ZPublisher hook
        '''
        import ZPublisher.Publish
        ZPublisher.Publish.publish=ZPublisher.Publish.profiler_publish_original
        del ZPublisher.Publish.profiler_publish_original

    security.declareProtected('View management screens',
        'isPublisherHookInstalled')
    def isPublisherHookInstalled(self):
        '''Detect the presence of the publisher hook
        '''
        import ZPublisher.Publish
        return hasattr(ZPublisher.Publish, 'profiler_publish_original')

    #
    # Results handling code
    #

    security.declareProtected('View management screens', 'clear')
    def clear(self):
        '''Clear the current results
        '''
        profiler.reset()
        return self.configureForm(self, self.REQUEST,
            manage_tabs_message='cleared')

    security.declareProtected('View management screens', 'resultsOverTime')
    def summary(self):
        '''Calculate summary info
        '''
        #sort = self.REQUEST['sort']
        #if sort:
        #    return profiler.listTransactions(sort=sort)
        #rsort = self.REQUEST['rsort']
        #if rsort:
        #    return profiler.listTransactions(rsort=rsort)
        return profiler.listTransactions(sort='time_start')

    security.declareProtected('View management screens', 'summaryByURL')
    def summaryByURL(self):
        '''Calculate some summary info
        '''
        l = profiler.listTransactions(sort='time_start')

        # print up the summary
        summary = {}
        for transaction in l:
            tt = transaction.time_total
            url = transaction.url
            if summary.has_key(url):
                d = summary[url]
                d['min'] = min(d['min'], tt)
                d['max'] = max(d['max'], tt)
                d['tot'] += tt
                d['num'] += 1
                d['ave'] = d['tot'] / d['num']
                d['transactions'].append((tt, transaction))
            else:
                summary[url] = {'min': tt, 'max': tt, 'tot': tt, 'num': 1,
                        'ave': tt, 'transactions': [(tt, transaction)],
                        'truncated_url': transaction.truncated_url}
        summary = summary.items()
        summary.sort()
        return summary

    security.declareProtected('View management screens', 'validTID')
    def validTID(self, tid):
        '''Determine if the tid is valid
        '''
        return profiler.hasTID(tid)

    security.declareProtected('View management screens', 'detailResults')
    def detailResults(self, tid):
        '''Show a detailed result
        '''
        transaction = profiler.transaction[tid]

        # do the HTML extra bits
        pm = profileable_modules
        for depth, info in transaction.listEvents():
            if info.has_key('events'):
                info['treepart'] = '| '*depth + '+-'
                if info['events'] and info.has_key('time_processing'):
                    percent = info['percentage_processing']
                    time_display = info['time_processing']
                else:
                    percent = info['percentage']
                    time_display = info['time_total']
            else:
                info['treepart'] = '| '*depth
                percent = info['percentage']
                time_display = info['time_total']
            info['time_display'] = time_display
            info['percentage_display'] = percent
            info['percentage_int'] = int(percent/2)
            info['icon'] = ''
            if info.has_key('meta_type'):
                module = pm[info['meta_type']]
                if module.icon:
                    info['icon'] = module.icon
            if percent > 10: info['colour'] = '#ffbbbb'
            elif percent > 5: info['colour'] = '#ffdbb9'
            elif percent > 3: info['colour'] = '#fff9b9'
            else: info['colour'] = ''

        return transaction

    security.declareProtected('View management screens', 'colour_key')
    def colour_key(self):
        '''Draw a table with the highlight colours
        '''
        return '''The colours used in the table highlight the calls that take
a high percentage of the total time for the request:
<table border=0 cellpadding=2 cellspacing=2>
<tr><td bgcolor="white">0-3%</td>
    <td bgcolor="#fff9b9">3-5%</td>
    <td bgcolor="#ffdbb9">5-10%</td>
    <td bgcolor="#ffbbbb">10+%</td>
</tr></table>'''

    security.declareProtected('View management screens', 'aggregateResults')
    def aggregateResults(self):
        '''Generate aggregated results for the calls - where the call patterns
           exactly match by URL
        '''
        return profiler.aggregateResults()

    security.declareProtected('View management screens',
        'aggregateDetailResults')
    def aggregateDetailResults(self, tid, show_all=0):
        '''Generate table row cells for the given transaction
        '''
        agg = profiler.aggregateDetailResults(tid)

        # do the HTML extra bits
        pm = profileable_modules
        for depth, info in agg.listEvents():
            if info.has_key('events'):
                info['treepart'] = '| '*depth + '+-'
                if info['events'] and info.has_key('ave_time_processing'):
                    min_percent = info['min_percentage_processing']
                    percent = info['ave_percentage_processing']
                    max_percent = info['max_percentage_processing']
                    min_time_display = info['min_time_processing']
                    time_display = info['ave_time_processing']
                    max_time_display = info['max_time_processing']
                else:
                    min_percent = info['min_percentage']
                    percent = info['ave_percentage']
                    max_percent = info['max_percentage']
                    min_time_display = info['min_time_total']
                    time_display = info['ave_time_total']
                    max_time_display = info['max_time_total']
            else:
                info['treepart'] = '| '*depth
                min_percent = info['min_percentage']
                percent = info['ave_percentage']
                max_percent = info['max_percentage']
                min_time_display = info['min_time_total']
                time_display = info['ave_time_total']
                max_time_display = info['max_time_total']

            info['min_time_display'] = min_time_display
            info['time_display'] = time_display
            info['max_time_display'] = max_time_display
            info['min_percentage_display'] = min_percent
            info['percentage_display'] = percent
            info['max_percentage_display'] = max_percent

            info['icon'] = ''
            if info.has_key('meta_type'):
                module = pm[info['meta_type']]
                if module.icon:
                    info['icon'] = module.icon

            info['percentage_int'] = int(percent/2)
            if percent > 10: info['colour'] = '#ffbbbb'
            elif percent > 5: info['colour'] = '#ffdbb9'
            elif percent > 3: info['colour'] = '#fff9b9'
            else: info['colour'] = ''

        return agg

InitializeClass(CallProfiler)
modulesecurity.apply(globals())


#
# $Log: CallProfiler.py,v $
# Revision 1.12  2002/02/08 04:57:22  rjones
# typo
#
# Revision 1.11  2002/02/08 03:18:55  rjones
# got meta_type images in there... much nicer
#
# Revision 1.10  2002/02/07 23:12:48  rjones
# Fixes to the data gathering and display
#
# Revision 1.9  2002/02/07 05:09:11  rjones
# Better call stack handling
#
# Revision 1.8  2002/02/06 00:33:55  rjones
# Lots of data handling improvements:
#   . moved the data handling part off into a separate module
#   . that module has some basic unit tests
#
# Revision 1.7  2002/02/05 22:11:02  rjones
# Fixes
#
# Revision 1.6  2002/02/05 04:50:13  rjones
# Fixes, aggregation, oh my! :)
#
# Revision 1.5  2002/02/01 05:42:17  rjones
# fixes
#
# Revision 1.4  2002/01/31 23:11:36  rjones
# copyright and CVS comment cleanups
#
# Revision 1.3  2002/01/31 06:19:17  rjones
# Now adds itself to the Control Panel, and isn't available for adding elsewhere.
#
# Revision 1.2  2002/01/31 05:03:27  rjones
# adding CallProfiler to HEAD
#
# Revision 1.1.2.6  2002/01/31 04:16:33  rjones
# Some more cleanups
#
# Revision 1.1.2.5  2002/01/31 04:09:42  rjones
# More cleanups in the profiler code so we can get at the data more easily
#
# Revision 1.1.2.4  2002/01/31 00:50:08  rjones
# Profiler now patches the Zope modules as required:
#  . ZPublisher/Publish.py publish function
#  . others as defined in the profileable_modules dict in CallProfiler.py
#
# Revision 1.1.2.3  2002/01/30 07:36:00  rjones
# split off the processing code from the display code - should be easy enough
# to do the render in ZPT or *shudder* DTML.
#
# Revision 1.1.2.2  2002/01/30 05:41:33  rjones
# cosmetic changes
#
# Revision 1.1.2.1  2002/01/30 04:48:38  rjones
# CallProfiler initial version
#

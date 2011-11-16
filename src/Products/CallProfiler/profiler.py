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

# $Id: profiler.py,v 1.4 2002/02/08 00:06:33 rjones Exp $

import time, operator
from thread import get_ident

class Profiler:
    def __init__(self):
        self.reset()

    def reset(self):
        '''Reset the dicts
        '''
        # these vars hold the timing values
        self.thread = {}        # maps thread IDs to TID
        self.transaction = {}   # holds the full transaction info by TID

    def hasTID(self, tid):
        return self.transaction.has_key(tid)

    def startRequest(self, request):
        '''Register the start of a request (called by the Publisher)

           The StartDict entry will be transferred to the TimingDict once
           we have a valid timing mark (so it's a request we care about).
        '''
        tid = '%s:%s'%(time.time(), id(request))
        self.thread[get_ident()] = tid
        self.transaction[tid] = Transaction(tid, request.URL+request.PATH_INFO)

    def endRequest(self):
        '''End-of-publishing mark

            Mark the current transaction as finished.
        '''
        if not self.thread.has_key(get_ident()): return
        tid = self.thread[get_ident()]
        if not self.transaction.has_key(tid): return
        transaction = self.transaction[tid]
        if not transaction.events:
            del self.transaction[tid]
        else:
            transaction.finish()

    def startCall(self, type, name):
        '''Register the start of a call
        '''
        tid = self.thread[get_ident()]
        self.transaction[tid].startCall(type, name)

    def endCall(self):
        '''Register the end of a call.
        '''
        tid = self.thread[get_ident()]
        self.transaction[tid].endCall()

    def aggregateResults(self):
        '''Generate aggregated results for the calls - where the call patterns
           exactly match by URL
        '''
        all = {}

        # now, for each session, add to an aggregate
        for tid, transaction in self.transaction.items():
            if not transaction.time_end:
                continue
            aggregates = all.setdefault(transaction.url, [])

            # get the detail results for this run
            transaction = self.transaction[tid]
            for aggregate in aggregates:
                if aggregate.matches(transaction):
                    aggregate.add(tid, transaction)
                    break
            else:
                aggregates.append(Aggregate(tid, transaction))

        # figure min/max/average
        for aggregates in all.values():
            for aggregate in aggregates:
                aggregate.calculate()

        return all.items()

    def aggregateDetailResults(self, tid):
        '''Generate aggregated results for the given session - bringing in all
           identical session timings.
        '''
        transaction = self.transaction[tid]

        # start the aggregate off with the session we're interested in
        aggregate = Aggregate(tid, transaction)

        # now try to add in other entries for the same URL
        for otid, other in self.transaction.items():
            if not other.time_end: continue
            if tid == otid: continue
            if aggregate.matches(other):
                aggregate.add(tid, other)
        aggregate.calculate()

        return aggregate

    def listTransactions(self, sort=None, rsort=None):
        '''List the transactions sorted by "sort" or reverse sorted by "rsort"

           Only include the transactions which are valid
        '''
        l = filter(lambda x: x.time_end, self.transaction.values())
        if sort is None and rsort is None:
            return l
        if rsort is not None:
            sort = rsort
        def sortfun(a, b, sort=sort):
            return cmp(a[sort], b[sort])
        l.sort()
        if rsort is not None:
            l.reverse()
        return l

profiler = Profiler()

class Transaction:
    '''Collect events for a particular transaction.

        There's two types of events:
         call events:
          meta_type
          object
          time_elapsed
          time_start
          time_end
          time_total
          depth
          events

         processing events:
          time_total
    '''
    def __init__(self, tid, url, time_start=None):
        self.tid = tid
        self.url = url
        if time_start is None:
            time_start = time.time()
        self.time_start = time_start
        self.events = []
        self.stack = [self]
        self.time_end = None

    def __getitem__(self, name):
        '''Make this object look like one of the event info dicts
        '''
        if name == 'time_start': return self.time_start
        if name == 'events': return self.events
        raise KeyError, name

    def __setitem__(self, name, value):
        '''Make this object look like one of the event info dicts
        '''
        if name == 'time_processing':
            self.time_processing = value
        elif name == 'percentage_processing':
            self.percentage_processing = value
        else:
            raise KeyError, name

    def startCall(self, meta_type, object, time_start=None):
        '''Register a call
        '''
        if time_start is None:
            time_start = time.time()
        parent = self.stack[-1]

        # insert a processing event
        if parent['events']:
            # get the time of the end of the previous call
            previous = parent['events'][-1]['time_end']
        else:
            # or the start of the current call
            previous = parent['time_start']
        info = {'time_total': time_start - previous}
        parent['events'].append(info)

        # now insert the call
        info = {'meta_type': meta_type, 'object': object,
            'time_start': time_start,
            'time_elapsed': time_start - self.time_start, 'events': []}
        parent['events'].append(info)
        self.stack.append(info)

    def endCall(self, time_end=None):
        '''Register the end of a call
        '''
        if time_end is None:
            time_end = time.time()
        call = self.stack.pop()
        if call['events']:
            # insert a processing event
            previous = call['events'][-1]['time_end']
            info = {'time_total': time_end - previous}
            call['events'].append(info)
        call['time_end'] = time_end
        call['time_total'] = time_end - call['time_start']

    def finish(self, time_end=None):
        '''Register the end of this transaction
        '''
        if time_end is None:
            time_end = time.time()
        self.time_end = time_end
        self.time_total = self.time_end - self.time_start
	self.num_calls = {}
        self.calculate_totals(self)
        if len(self.url) < 100:
            self.truncated_url = self.url
        else:
            self.truncated_url = self.url[:50] + '...' + self.url[-50:]
        self.str_time_start = time.strftime('%Y-%m-%d %H:%M:%S',
            time.localtime(self.time_start))

    def calculate_totals(self, call):
        '''Figure the totals and percentages
        '''
        processing = 0
        for event in call['events']:
            if event.has_key('meta_type'):
		key = (event['meta_type'], event['object'])
		count = self.num_calls.get(key, 0) + 1
		self.num_calls[key] = count
		event['call_count'] = count
		if count == 1:
		    event['str_call_count'] = ''
		elif count%10 == 1:
		    event['str_call_count'] = '(%dst call)'%count
		elif count%10 == 2:
		    event['str_call_count'] = '(%dnd call)'%count
		elif count%10 == 3:
		    event['str_call_count'] = '(%drd call)'%count
		else:
		    event['str_call_count'] = '(%dth call)'%count
                self.calculate_totals(event)
            else:
                processing += event['time_total']
            event['percentage'] = event['time_total']*100 / self.time_total
        call['time_processing'] = processing
        call['percentage_processing'] = processing*100 / self.time_total

    def __str__(self):
        return '''URL: %s
Start time: %s
Total time: %s
'''%(self.url, self.time_start, self.time_total)

    def listEvents(self, call=None, depth=0):
        '''Flatten the events list
        '''
        if call is None: call = self
        l = []
        for event in call['events']:
            if event.has_key('events'):
                l.append((depth, event))
                l = l + self.listEvents(event, depth+1)
            elif event['percentage'] > .5:
                l.append((depth, event))
        return l

    def strEvents(self, call=None, depth=0):
        '''Stringify the list of events
        '''
        l = []
        for depth, event in self.listEvents():
            perc = '%2d%%'%event['percentage']
            if event.has_key('events'):
                if event['events'] and event.has_key('time_processing'):
                    cperc = '%2d%%'%event['percentage_processing']
                    proc = '(%-3s %-5s)'%(event['time_processing'], cperc)
                else:
                    proc = ''
                l.append('%-4s %-2s %-12s %-3s %-5s %s'%(
                    '.'*depth, event['time_elapsed'], event['object'],
                    event['time_total'], perc, proc))
            else:
                l.append('%-4s     %-12s %-3s %-5s'%(
                    '.'*depth, '(processing)', event['time_total'], perc))

        return '\n'.join(l)

class Aggregate:
    def __init__(self, tid, transaction):
        self.url = transaction.url
        self.truncated_url = transaction.truncated_url
        self.tids = [tid]
        self.start_times = [transaction.time_start]
        self.time_totals = [transaction.time_total]
        self.num_runs = 1

        # initialise the run
        self.events = self.copyEvents(transaction.events)

    def copyEvents(self, events):
        '''Copy the events from the given list into a new aggregate event list
        '''
        new = []
        for info in events:
            info = info.copy()
            new.append(info)
            if info.has_key('time_elapsed'):
                info['min_time_elapsed'] = info['time_elapsed']
                info['max_time_elapsed'] = info['time_elapsed']
            if info.has_key('time_total'):
                info['min_time_total'] = info['time_total']
                info['max_time_total'] = info['time_total']
                info['min_percentage'] = info['percentage']
                info['max_percentage'] = info['percentage']
            if info.has_key('time_processing'):
                info['min_time_processing'] = info['time_processing']
                info['max_time_processing'] = info['time_processing']
                info['min_percentage_processing'] =info['percentage_processing']
                info['max_percentage_processing'] =info['percentage_processing']
            if info.has_key('events'):
                info['events'] = self.copyEvents(info['events'])
        return new

    def add(self, tid, transaction):
        '''Add the events from the given transaction to this aggregate
        '''
        self.num_runs += 1
        self.tids.append(tid)
        self.start_times.append(transaction.time_start)
        self.time_totals.append(transaction.time_total)
        self.addEvents(self.events, transaction.events)

    def addEvents(self, a_events, b_events):
        '''Incorporate the events from a_events to b_events
        '''
        for a, b in zip(a_events, b_events):
            if a.has_key('time_elapsed'):
                a['time_elapsed'] += b['time_elapsed']
                a['min_time_elapsed'] = min(a['min_time_elapsed'],
                    b['time_elapsed'])
                a['max_time_elapsed'] = max(a['max_time_elapsed'],
                    b['time_elapsed'])
            if a.has_key('time_total'):
                a['time_total'] += b['time_total']
                a['min_time_total'] = min(a['min_time_total'], b['time_total'])
                a['max_time_total'] = max(a['max_time_total'], b['time_total'])
                a['percentage'] += b['percentage']
                a['min_percentage'] = min(a['min_percentage'], b['percentage'])
                a['max_percentage'] = max(a['max_percentage'], b['percentage'])
            if a.has_key('time_processing'):
                a['time_processing'] += b['time_processing']
                a['min_time_processing'] = min(a['min_time_processing'],
                    b['time_processing'])
                a['max_time_processing'] = max(a['max_time_processing'],
                    b['time_processing'])
                a['percentage_processing'] += b['percentage_processing']
                a['min_percentage_processing'] = min(
                    a['min_percentage_processing'], b['percentage_processing'])
                a['max_percentage_processing'] = max(
                    a['max_percentage_processing'], b['percentage_processing'])
            # recurse
            if a.has_key('events'):
                self.addEvents(a['events'], b['events'])

    def matches(self, transaction):
        '''See if this aggregated events call pattern matches the one passed in
        '''
        if transaction.url != self.url:
            return 0
        return self.matchEvents(self.events, transaction.events)

    def matchEvents(self, a_events, b_events):
        '''Recursively compare the events in a to b
        '''
        if len(a_events) != len(b_events):
            return 0
        for a, b in zip(a_events, b_events):
            if a.has_key('events'):
                if not b.has_key('events'):
                    return 0
                if a['meta_type'] != b['meta_type']:
                    return 0
                if a['object'] != b['object']:
                    return 0
                return self.matchEvents(a['events'], b['events'])
        return 1

    def calculate(self):
        '''Pass through the events and figure the summaries
        '''
        self.min_time_total = min(self.time_totals)
        self.ave_time_total = reduce(operator.add, self.time_totals)/self.num_runs
        self.max_time_total = max(self.time_totals)
        self.calcAverages(self.events)

    def calcAverages(self, events):
        '''Figure the averages
        '''
        n = self.num_runs
        for info in events:
            if info.has_key('time_elapsed'):
                info['ave_time_elapsed'] = info['time_elapsed'] / n
            if info.has_key('time_total'):
                info['ave_time_total'] = info['time_total'] / n
                info['ave_percentage'] = info['percentage'] / n
            if info.has_key('time_processing'):
                info['ave_time_processing'] = info['time_processing'] / n
                info['ave_percentage_processing'] = \
                    info['percentage_processing'] / n
            if info.has_key('events'):
                self.calcAverages(info['events'])

    def listEvents(self, call=None, depth=0):
        '''Flatten the events list
        '''
        if call is None: call = self
        l = []
        for event in call['events']:
            if event.has_key('events'):
                l.append((depth, event))
                l = l + self.listEvents(event, depth+1)
            elif event['ave_percentage'] > .5:
                l.append((depth, event))
        return l

    def strEvents(self):
        '''Stringify the list of events
        '''
        l = []
        for depth, event in self.listEvents():
            perc = '%2.2f%%'%event['ave_percentage']
            if event.has_key('events'):
                if event['events'] and event.has_key('ave_time_processing'):
                    cperc = '%2d%%'%event['ave_percentage_processing']
                    proc = '(%-3s %-5s)'%(event['ave_time_processing'], cperc)
                else:
                    proc = ''
                l.append('%-4s %-2s %-12s %-3s %-5s %s'%(
                    '.'*depth, event['ave_time_elapsed'], event['object'],
                    event['ave_time_total'], perc, proc))
            else:
                l.append('%-4s     %-12s %-3s %-5s'%(
                    '.'*depth, '(processing)', event['ave_time_total'],
                    perc))

        return '\n'.join(l)

    def __getitem__(self, name):
        '''Make this object look like one of the event info dicts
        '''
        if name == 'events': return self.events
        raise KeyError, name
#
# $Log: profiler.py,v $
# Revision 1.4  2002/02/08 00:06:33  rjones
# added call counter
#
# Revision 1.3  2002/02/07 23:12:49  rjones
# Fixes to the data gathering and display
#
# Revision 1.2  2002/02/07 05:09:11  rjones
# Better call stack handling
#
# Revision 1.1  2002/02/06 00:33:55  rjones
# Lots of data handling improvements:
#   . moved the data handling part off into a separate module
#   . that module has some basic unit tests
#
#

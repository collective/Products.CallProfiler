import unittest, time

from profiler import profiler, Transaction, Aggregate

class DummyRequest:
    def __getattr__(self, name):
	if name == 'URL':
	    return 'http://test.com'
	if name == 'PATH_INFO':
	    return '/test/'
	raise AttributeError, name

class ProfilerTest(unittest.TestCase):
    def setUp(self):
	profiler.reset()

    def testMark(self):
	request = DummyRequest()
	profiler.startRequest(request)
	profiler.startCall('foo', 'bar')
	profiler.startCall('foo', 'flebb')
	profiler.endCall()
	profiler.endCall()
	profiler.endRequest()
	self.assertEqual(len(profiler.transaction), 1)
	request, = profiler.transaction.values()

    def do_run(self, t, tid):
	trans = Transaction('http://test.com/test/', t+0.)
	trans.startCall('foo', 'abc', t+1.)
	trans.startCall('foo', 'def', t+3.)
	trans.endCall(t+4.)
	trans.endCall(t+7.)
	trans.finish(t+10.)
	profiler.transaction[tid] = trans
	return trans

    def do_run2(self, t, tid):
	trans = Transaction('http://test.com/test/', t+0.)
	trans.startCall('foo', 'bar', t+1.)
	trans.startCall('foo', 'fle', t+2.)
	trans.endCall(t+3.)
	trans.startCall('foo', 'ble', t+4.)
	trans.startCall('foo', 'fle', t+5.)
	trans.endCall(t+6.)
	trans.endCall(t+7.)
	trans.endCall(t+8.)
	trans.finish(t+10.)
	profiler.transaction[tid] = trans
	return trans

    def testCalc(self):
	result = self.do_run(0, '1')
	profiler.collateTotals()
	print result.strEvents()

    def testAggregate(self):
	self.do_run(0, '1')
	self.do_run2(10, '2')
	self.do_run(20, '3')
	self.do_run2(40, '4')
	self.do_run(60, '5')
	profiler.aggregateResults()

	agg = profiler.aggregateDetailResults('2')
	self.assertEqual(agg.num_runs, 2)
	self.assertEqual(agg.ave_total_time, 10)
	agg = profiler.aggregateDetailResults('4')
	self.assertEqual(agg.events[0]['ave_time_total'], 1)
	self.assertEqual(agg.events[0]['ave_percentage'], 10)
	self.assertEqual(agg.events[1]['ave_time_total'], 7)
	self.assertEqual(agg.events[1]['ave_percentage'], 70)
	self.assertEqual(agg.events[1]['ave_time_processing'], 3)
	self.assertEqual(agg.events[1]['ave_percentage_processing'], 30)

	agg = profiler.aggregateDetailResults('1')
	#print agg.strEvents()
	self.assertEqual(agg.num_runs, 3)
	self.assertEqual(agg.ave_total_time, 10)

def suite():
   return unittest.makeSuite(ProfilerTest)


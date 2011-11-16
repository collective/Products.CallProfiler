.. contents::

Call Profiler Documentation
===========================

Purpose
-------

To monitor the chain of DTML, ZSQL, ZPT, PythonMethod, PythonScript, ...
calls in a Zope request and gather timing information, for the purpose of
identifying hot-spots for potential optimisation.


Usage
-----

Once the product is installed in your Products directory and Zope has
been restarted, visit the Call Profiler link in your Control Panel.

In the configuration tab, check the types of documents you wish to
obtain the timing information for. You may also clear any previously
gathered timing information using the "clear" buttons.

Once you have selected the documents to monitor and have clicked
"Monitor selected calls", load up the pages you wish to profile. Once
they're loaded (or even as they're loading :) you should visit the results
tab. There you will find a list of the requests made by browsers with some
timing information:

* clicking the url will load the page requested
* clicking on the time of the request will bring up a blow-by-blow
  breakdown of the documents called to form the request.

You may also see the requests aggregated by URL on the "Requests By URL"
tab - giving the minimum, average and maximum times for the responses. You
may:

* click the url to load the page requested
* click the session times to see the detailed breakdown of the request

The detailed view is set to highlight calls that broach 3% (yellow), 5%
(orange) and 10% (red) of the total request time.

If a given document call has sub-calls:

* the '...' times indicate the time spent in the call (between sub-calls)
 
* the (end) time gives two timings:
  
  * the first is the time spent in the call not including sub-calls
  * the second time is the total time of the call including sub-calls


Note:

All profiling information is lost when either:

1. Zope is restarted, or
2. the Call Profiler product's code is re-loaded.

Also, don't leave the profiler on for too long - it uses a boundless
memory-based store for the timing values. It will use up all your memory
eventually (though we haven't done any testing to determine how long that
might be).


License
=======
Copyright (c) ekit.com Inc (http://www.ekit-inc.com/)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions::

  The above copyright notice and this permission notice shall be included in
  all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

This product includes software developed by Digital Creations for use in
the Z Object Publishing Environment (http://www.zope.org/).
(specifically, we use the control panel installation code from LeakFinder in
the __init__.py module)


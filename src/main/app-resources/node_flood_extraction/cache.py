# vim: ts=8:expandtab:cpo+=I:fo+=r
"""
    cache
    =====
    
    Library for caching functions and method outputs.
    Two caching methods are provided:
        LRU         store the last N results of the function/method
        Persistent  store results on a file
    This two methods can be used separetaly or chained (first level LRU, on miss try persistent).
    For caching instance methods based on instance state (e.g. attributes value) define its __hash__
    method using hashParameters.
    
    Provides
        cache               decorator for caching using a two-level (in memory and persistent) cache
        quantizeParameters  function for easily quantizing parameters (allows to use results from similar but different parameters)
        hashParameters      function for creating hash of a set of quantized parameter
        registerCache       register a symbolic name for a persistent cache
"""

try:
    from thread import allocate_lock as Lock
except:
    try:
        from _thread import allocate_lock as Lock
    except:
        from _dummy_thread import allocate_lock as Lock
from functools import update_wrapper
from collections import namedtuple
import atexit

################################################################################
### Parameters quantization and hashing for persistent method caching
################################################################################

def quantizeParameters(*args):
    """Smartly quantize parameters in user-defined per-parameter ways
    
    Parameters
    ----------
    args: 3-sequence like (any, None|sequence|slice, None|string)
        The first element represents the actual value.
        The second one indicates the way to quantize the parameter.
        The third one specifies some options.
        See Examples for more details.
    
    Returns
    -------
    outlist: list
        Quantized parameters. Raises a ValueError exception if encounters an invalid option.
    
    See Also
    --------
    hashParameters: create a hash of a list of quantized parameters
    
    Examples
    --------
    >>> print quantizeParameters(
    ...             ('M',      None,           None)     ,  # -> 'M'  (no quantize, no check)
    ...             ('A',      ['A','B'],      'exact')  ,  # -> 'A'  (no quantize, check value)
    ...             (1.5,      [1,3,4],        'floor')  ,  # -> 1
    ...             (-1,       [1,3,4],        'floor')  ,  # -> None
    ...             (1.5,      [1,3,4],        'ceil')   ,  # -> 3
    ...             (5.0,      [1,3,4],        'ceil')   ,  # -> None
    ...             (1.5,      [1,3,4],        'index')  ,  # -> 0
    ...             (-1,       [1,3,4],        'index')  ,  # -> -1
    ...             (5.0,      [1,3,4],        'index')  ,  # -> 2
    ...             (365.3,    [0,90,180,270], 'wfloor') ,  # -> 0    (wrapped)
    ...             (365.3,    [0,90,180,270], 'wceil')  ,  # -> 90   (wrapped)
    ...             (365.3,    [0,90,180,270], 'windex') ,  # -> 0    (wrapped)
    ...             (1.5,      slice(1,4),     'floor')  ,  # -> 1)
    ...             (1.5,      slice(1,4),     'ceil')   ,  # -> 2)
    ...             (1.5,      slice(1,4),     'index')  ,  # -> 0)
    ...             (365.3,    slice(0,360),   'wfloor') ,  # -> 5    (wrapped)
    ...             (365.3,    slice(0,360),   'wceil')  ,  # -> 6    (wrapped)
    ...             (365.3,    slice(0,360),   'windex') ,  # -> 5    (wrapped)
    ['M', 'A', 1, None, 3, None, 0, -1, 2, 0, 90, 0, 1.0, 2.0, 0.0, 5.0, 6.0, 5.0]
    """
    from sys import maxsize
    from math import floor, ceil
    rit = []
    for value,bins,option in args:
        if bins is None:
            rit.append(value)
        elif type(bins) is slice:
            start = float(0         if bins.start is None else bins.start)
            stop  = float(maxsize   if bins.stop  is None else bins.stop)
            step  = float(1         if bins.step  is None else bins.step)
            bin_ = (value-start)/step
            if option[0]=='w':
                #wrap
                bin_ %= (stop - start)
                option = option[1:]
            
            if   option=='floor':   rit.append(floor(bin_)*step + start)
            elif option=='ceil':    rit.append( ceil(bin_)*step + start)
            elif option=='round':   rit.append(floor(bin_+0.5)*step + start)
            elif option=='index':   rit.append(floor(bin_))
            else: raise ValueError("Unknown option: %s" % option)
        else:
            if option=='exact':
                if value in bins: rit.append(value)
                else: raise ValueError("Unadmittable value: %s not in %s" % (value, bins))
            else:
                from numpy import digitize
                if option[0]=='w':
                    #wrap
                    value = ((value-bins[0]) % (bins[1]-bins[0]) ) + bins[0]
                    option = option[1:]
                idx = digitize([value], bins)[0]
                if   option=='floor':   rit.append(bins[idx-1] if idx>0         else None)
                elif option=='ceil':    rit.append(bins[idx]   if idx<len(bins) else None)
                elif option=='index':   rit.append(idx-1)
                else: raise ValueError("Unknown option: %s" % option)
    
    return rit

def hashParameters(*args):
    """Hash arguments using quantization
    
    Parameters
    ----------
    See quantizeParameters
    
    Returns
    -------
    Hash computed from the output of quantizeParameters.
    
    See Also
    --------
    quantizeParameters
    """
    representation = '\x00'.join(map(str, quantizeParameters(*args)))
    return hash(representation)

def quantized(*args):
    """Generate a decorator for quantizing arguments
    
    Parameters
    ----------
    args: 3-sequence like (string, None|sequence|slice, None|string)
        The first element is the argument name
        The second one indicates the way to quantize the parameter.
        The third one specifies some options.
        See quantizeParameters for more details.
    
    Returns
    -------
    A function decorator
    
    See Also
    --------
    quantizeParameters
    
    Examples
    --------
    >>> @quantized(([1,3,4], 'floor'))
    >>> def f(a): return a
    >>> x = range(-1,6) + [100]
    >>> print zip(x, map(f, x))
    [(-1, None), (0, None), (1, 1), (2, 1), (3, 3), (4, 4), (5, 4), (100, 4)]
    """
    bins,option = zip(*args)
    def decorating_function(user_function):
        from inspect import getargspec
        try:
            f = user_function.__wrapped__
        except:
            f = user_function
        nArgs = len(getargspec(f).args)
        defaults = f.__defaults__
        def wrapper(*wargs):
            if len(wargs)-nArgs < len(defaults or ()):
                wargs = wargs + defaults[len(wargs)-nArgs:]
            values = quantizeParameters(*zip(wargs, bins, option))
            return user_function(*values)
        return update_wrapper(wrapper, user_function)
    return decorating_function

################################################################################
### Two-level persistent caching
################################################################################

_cache = {}
def registerCache(ID, filename=None, livesync=False):
    """Associate a symbolic name to a persistent (on-file) cache.
    
    Parameters
    ----------
    ID: string
        Symbolic name to use for the newly created persistent cache.
    filename: string, optional
        Path of the file onto save cached results (defaults to argv[0]).
    livesync: bool, optional
        Whether to update the file each time a new result is generated
        (if True can slow down execution).
    
    Results
    -------
    cache: percache.Cache
        The newly created persistent cache. It is also added to the list of known caches.
    
    See Also
    --------
    cache: decorator for caching function outputs using a LRU cache + a persistent cache
    """
    from sys import argv
    from percache import Cache
    #assert ID not in _cache
    if not ID in _cache: 
        cacheExtension = '.cache'
        if filename is None:
            filename = argv[0]
        if not filename.endswith(cacheExtension):
            filename += cacheExtension
        _cache[ID] = Cache(filename, livesync=livesync, repr=lambda x:repr(hash(x)))
    return _cache[ID]

@atexit.register
def unregisterCache(*args):
    for ID,c in _cache.iteritems():
        if len(args)==0 or ID in args:
            c.close()
    _cache.clear()
        

def cache(lrusize=None, persistent=False, ID='__default__'):
    """Generate a decorator for caching function outputs using a LRU cache + a persistent cache

    Parameters
    ----------
    lrusize: int, optional
        size (in number of elements) of in-memory cached results.
        If 0, no in-memory caching is performed.
        If None, cache in memory forever (no LRU behaviour)
    persistent: bool, optional
        If True, create a second level cache on disk which stores results between sessions.
        If False, cache only in memory (results are not stored between sessions).
        It is advisable to set a finite lrusize if persistent is True.
    ID: string, optional
        Symbolic name of the persistent cache to be used. Unused if persistent is False.
    
    Returns
    -------
    decorator: callable
        A decorator for caching.
    
    See Also
    --------
    registerCache: function for associating a symbolic name to a persistent cache
    """
    if lrusize is not None:
        try:
            lrusize = int(lrusize)
        except TypeError:
            raise TypeError("Wrong lrusize argument, maybe you used @%s instead of @%s()?"  \
                            % (__name__,)*2                                                 \
            )
    
    lru = lru_cache(maxsize=lrusize, typed=False)
    if persistent:
        if ID not in _cache:
            if ID=='__default__':
                registerCache('__default__')
            else:
                raise ValueError("Unknown ID: %s" % ID)
        def wrapper(f):
            rit = lru(_cache[ID](f))
            rit.percache_clear = lambda: _cache[ID].clear() or rit.cache_clear()
            rit.percache_info  = _cache[ID].stats
            return rit
    else:
        def wrapper(f):
            rit = lru(f)
            rit.percache_clear = rit.cache_clear
            rit.percache_info  = rit.cache_info
            return rit
    return wrapper

################################################################################
### LRU Cache function decorator
################################################################################
# The following functions are extracted from functool for Python3.4.0a0 and adapted for Python2.7
# See http://docs.python.org/dev/library/functools.html
_CacheInfo = namedtuple("CacheInfo", ["hits", "misses", "maxsize", "currsize"])

class _HashedSeq(list):
    __slots__ = 'hashvalue'

    def __init__(self, tup, hash=hash):
        self[:] = tup
        self.hashvalue = hash(tup)

    def __hash__(self):
        return self.hashvalue

def _make_key(args, kwds, typed,
             kwd_mark = (object(),),
             fasttypes = {int, str, frozenset, type(None)},
             sorted=sorted, tuple=tuple, type=type, len=len):
    'Make a cache key from optionally typed positional and keyword arguments'
    key = args
    if kwds:
        sorted_items = sorted(kwds.items())
        key += kwd_mark
        for item in sorted_items:
            key += item
    if typed:
        key += tuple(type(v) for v in args)
        if kwds:
            key += tuple(type(v) for k, v in sorted_items)
    elif len(key) == 1 and type(key[0]) in fasttypes:
        return key[0]
    return _HashedSeq(key)

def lru_cache(maxsize=128, typed=False):
    """Least-recently-used cache decorator.

    If *maxsize* is set to None, the LRU features are disabled and the cache
    can grow without bound.

    If *typed* is True, arguments of different types will be cached separately.
    For example, f(3.0) and f(3) will be treated as distinct calls with
    distinct results.

    Arguments to the cached function must be hashable.

    View the cache statistics named tuple (hits, misses, maxsize, currsize)
    with f.cache_info().  Clear the cache and statistics with f.cache_clear().
    Access the underlying function with f.__wrapped__.

    See:  http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    """

    # Users should only access the lru_cache through its public API:
    #       cache_info, cache_clear, and f.__wrapped__
    # The internals of the lru_cache are encapsulated for thread safety and
    # to allow the implementation to change (including a possible C version).

    # Constants shared by all lru cache instances:
    sentinel = object()          # unique object used to signal cache misses
    make_key = _make_key         # build a key from the function arguments
    PREV, NEXT, KEY, RESULT = 0, 1, 2, 3   # names for the link fields

    def decorating_function(user_function):

        cache = {}
        hits = misses = currsize = 0
        full = False
        cache_get = cache.get    # bound method to lookup a key or return None
        lock = Lock()            # because linkedlist updates aren't threadsafe
        root = []                # root of the circular doubly linked list
        root[:] = [root, root, None, None]     # initialize by pointing to self
	
	nonlocals = dict(
	    hits	= hits,
	    misses	= misses,
	    currsize	= currsize,
	    full	= full,
	    root	= root,
	)
	
        if maxsize == 0:

            def wrapper(*args, **kwds):
                # no caching, just a statistics update after a successful call
                result = user_function(*args, **kwds)
                nonlocals['misses'] += 1
                return result

        elif maxsize is None:

            def wrapper(*args, **kwds):
                # simple caching without ordering or size limit
                key = make_key(args, kwds, typed)
                result = cache_get(key, sentinel)
                if result is not sentinel:
                    nonlocals['hits'] += 1
                    return result
                result = user_function(*args, **kwds)
                cache[key] = result
                nonlocals['misses'] += 1
                nonlocals['currsize'] += 1
                return result

        else:

            def wrapper(*args, **kwds):
                # size limited caching that tracks accesses by recency
                key = make_key(args, kwds, typed)
                with lock:
                    link = cache_get(key)
                    if link is not None:
                        # move the link to the front of the circular queue
                        link_prev, link_next, key, result = link
                        link_prev[NEXT] = link_next
                        link_next[PREV] = link_prev
                        last = nonlocals['root'][PREV]
                        last[NEXT] = nonlocals['root'][PREV] = link
                        link[PREV] = last
                        link[NEXT] = nonlocals['root']
                        nonlocals['hits'] += 1
                        return result
                result = user_function(*args, **kwds)
                with lock:
                    if key in cache:
                        # getting here means that this same key was added to the
                        # cache while the lock was released.  since the link
                        # update is already done, we need only return the
                        # computed result and update the count of misses.
                        pass
                    elif nonlocals['full']:
                        # use root to store the new key and result
                        nonlocals['root'][KEY] = key
                        nonlocals['root'][RESULT] = result
                        cache[key] = nonlocals['root']
                        # empty the oldest link and make it the new root
                        nonlocals['root'] = nonlocals['root'][NEXT]
                        del cache[nonlocals['root'][KEY]]
                        nonlocals['root'][KEY] = nonlocals['root'][RESULT] = None
                    else:
                        # put result in a new link at the front of the queue
                        last = nonlocals['root'][PREV]
                        link = [last, nonlocals['root'], key, result]
                        cache[key] = last[NEXT] = nonlocals['root'][PREV] = link
                        nonlocals['currsize'] += 1
                        nonlocals['full'] = (nonlocals['currsize'] == maxsize)
                    nonlocals['misses'] += 1
                return result

        def cache_info():
            """Report cache statistics"""
            with lock:
                return _CacheInfo(nonlocals['hits'], nonlocals['misses'], maxsize, nonlocals['currsize'])

        def cache_clear():
            """Clear the cache and cache statistics"""
            with lock:
                cache.clear()
                nonlocals['root'][:] = [nonlocals['root'], nonlocals['root'], None, None]
                nonlocals['hits'] = nonlocals['misses'] = nonlocals['currsize'] = 0
                nonlocals['full'] = False

        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        wrapper.__wrapped__ = user_function
        return update_wrapper(wrapper, user_function)

    return decorating_function


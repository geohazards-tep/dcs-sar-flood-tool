from abc import ABCMeta, abstractmethod
from itertools import product
from numpy import sinc, empty, arange, dot, floor, nan, isnan, zeros, round
from scipy.interpolate import NearestNDInterpolator, LinearNDInterpolator, CloughTocher2DInterpolator

def createSparseInterpolator(points, values, interpolatorClass=None, **kwargs):
    from numpy import hstack, any, isnan, broadcast_arrays, rollaxis
    if interpolatorClass is None:
        interpolatorClass = LinearNDInterpolator
   
    arr = broadcast_arrays(*(tuple(points) + tuple(values)))
    points, values = arr[:len(points)], arr[len(points):]
    
    points = hstack([c.ravel()[:,None] for c in points])
    values = hstack([z.ravel()[:,None] for z in values])
    idx = ~(any(isnan(points), 1) | any(isnan(values), 1))
    points, values = points[idx, :], values[idx, :]
    
    try:
        interpolator = interpolatorClass(points, values, **kwargs)
    except:
        if interpolatorClass is NearestNDInterpolator:
            raise
        print "Sparse interpolation using %s failed, retrying with %s" % \
              (interpolatorClass, NearestNDInterpolator)
        interpolator = NearestNDInterpolator(points, values)
    return lambda *args: rollaxis(interpolator(*args), -1)

def getInterpolatorClass(name, default=None, check=False):
    mapping = dict(
        nearest  = NearestNDInterpolator,
        linear   = LinearNDInterpolator,
        cubic    = CloughTocher2DInterpolator,
        bspline  = SplineInterpolator,
        bilinear = BilinearInterpolator,
    )
    
    if check:
        rit = mapping.pop(name)
    else:
        rit = mapping.get(name, name)
    if rit is None:
        return default
    else:
        return rit

def griddata(points, values, xi, method='linear', fill_value=nan):
    from numpy import hstack, broadcast_arrays
    interpolatorClass = getInterpolatorClass(method, method)
    
    interpolator = createSparseInterpolator(points, values, interpolatorClass)
    
    xi = broadcast_arrays(*xi)
    points = hstack([c.ravel()[:,None] for c in xi])
    
    values = interpolator(points)
    return values.reshape(((-1,) if len(values)>1 else ()) + xi[0].shape)


def build_kernel(shape, factor, function=sinc):

    kernel = empty((factor[0], factor[1], shape[0], shape[1]))
    step = (1. / factor[0], 1. / factor[1])

    for k0, k1 in product(range(factor[0]), range(factor[1])):

        kernel[k0, k1] = dot(
            function(-k0 * step[0] + arange(-shape[0] // 2 + 1, shape[0] // 2 + 1))[:, None],
            function(-k1 * step[1] + arange(-shape[1] // 2 + 1, shape[1] // 2 + 1))[None, :]
        )

    kernel = kernel / kernel.sum(axis=2).sum(axis=2)[:, :, None, None]

    return kernel


def sinc_interp(x, y, data, factor=[100, 100], shape=[20, 20], function=sinc, fill_value=nan):

    assert (shape[0] % 2 == 0) and (shape[1] % 2 == 0)
    assert x.shape == y.shape
    assert len(data.shape) in set((2, 3))

    datashape = ((1,) * (3 - len(data.shape)) + data.shape)
    nbands = datashape[0]
    out_shape = (nbands,) * (len(data.shape) - 2) + x.shape

    data = data.reshape(datashape)
    x = x.ravel()
    y = y.ravel()

    index_x = floor(x).astype(int)
    index_y = floor(y).astype(int)
    step = (1. / factor[0], 1. / factor[1])

    shift_x = floor((x - index_x) / step[0]).astype(int)
    shift_y = floor((y - index_y) / step[1]).astype(int)

    kernel = build_kernel(shape, factor, function=function)
    z = empty((nbands,) + x.shape)
    z.fill(fill_value)
    
    for k in xrange(x.size):
        if ~isnan(x[k]) and ~isnan(y[k]):

            corner_x = (index_x[k] - (shape[0] // 2) + 1, index_x[k] + shape[0] // 2 + 1)
            corner_y = (index_y[k] - (shape[1] // 2) + 1, index_y[k] + shape[1] // 2 + 1)
            offx, offy = 0, 0
            sizex, sizey = shape[0], shape[1]

            if corner_x[0] < 0:
                offx = - corner_x[0]
                sizex = shape[-2] - offx
            if corner_y[0] < 0:
                offy = - corner_y[0]
                sizey = shape[-1] - offy

            if corner_x[1] > data.shape[-2]:
                sizex = data.shape[-2] - corner_x[0] - offx
            if corner_y[1] > data.shape[-1]:
                sizey = data.shape[-1] - corner_y[0] - offy

            if sizex > 0 and sizey > 0:
                ker = (kernel[shift_x[k], shift_y[k]])
                if sizex < shape[0] or sizey < shape[1]:
                    ker = ker[offx: offx + sizex, offy: offy + sizey]

                z[:,k] = (ker*data[:,
                          corner_x[0] + offx: corner_x[0] + offx + sizex,
                          corner_y[0] + offy: corner_y[0] + offy + sizey]
                         ).sum(-1).sum(-1)

    return z.reshape(out_shape)
 

def isSorted(x, reverse=False):
    from numpy import asarray
    x = asarray(x)
    try:
        from scipy.weave import inline
        n = x.size
        code = """
            return_val = PyInt_FromLong(1);
            for (int i=1; i<n; i++) {
                if (x[i] %s x[i-1]) {
                    return_val = PyInt_FromLong(0);
                    break;
                }
            }
        """ % (">" if reverse else "<")
        return inline(code, ['x', 'n']) != 0
    except:
        if reverse:
            return (x[1:]>x[:-1]).all()
        else:
            return (x[1:]<x[:-1]).all()

class GridInterpolator(object):
    __metaclass__ = ABCMeta
    def __init__(self, values, x, y):
        if any([v.ndim != 2 for v in values]):
            raise ValueError("Values elements must have exactly 2 dimensions")
        if any([v.shape != values[0].shape for v in values]):
            raise ValueError("Values elements must have the same shape")
        
        shape = values[0].shape
        
        def createAxis(ax, size):
            if ax is None:
                ax = slice(None)
            elif not isinstance(ax, slice):
                if ax.squeeze().ndim > 1:
                    raise ValueError("Axes must have exactly 1 dimension (got %d)" % ax.ndim)
                if ax.size != size:
                    raise ValueError("Wrong axis size, got %d but expected %d" % (ax.size, size))
            return ax
        
        self._x = createAxis(x, shape[1])
        self._y = createAxis(y, shape[0])
        self._values = values
        self._shape = shape
    
    @staticmethod
    def parseSlice(slc, size):
        start = 0    if slc.start is None else float(slc.start)
        stop  = size if slc.stop  is None else float(slc.stop)
        step  = 1    if slc.step  is None else float(slc.step)
        if (stop-start)*step < 0:
            raise ValueError(
                "Bad slice, cannot run from %f to %f with step %f" %
                (start, stop, step)
            )
        return start, stop, step
        
    @abstractmethod
    def __call__(self, xi, yi, grid=True):
        pass

class SplineInterpolator(GridInterpolator):
    def __init__(self, values, x=None, y=None, *args, **kwargs):
        from scipy.interpolate import bisplrep
        from numpy import arange, broadcast_arrays
        GridInterpolator.__init__(self, values, x, y)
        if isinstance(self._x, slice): self._x = arange(*self.parseSlice(self._x,self._shape[0]))
        if isinstance(self._y, slice): self._y = arange(*self.parseSlice(self._y,self._shape[1]))
        tmp = broadcast_arrays(self._x, self._y, *self._values)
        x,y,values = tmp[0].ravel(), tmp[1].ravel(), tmp[2:]
        
        self._tck = [bisplrep(x, y, v.ravel(), *args, **kwargs) for v in values]
        self._kx = self._tck[0][3] #should be equal for every interpolation
        self._ky = self._tck[0][4] #should be equal for every interpolation
    
    @property
    def kx(self): return self._kx
    @property
    def ky(self): return self._ky
    
    def __call__(self, x, y, grid=True, dx=0, dy=0):
        from scipy.interpolate import bisplev
        if not grid:
            raise NotImplementedError("Spline interpolation supports only output points forming a grid")
        return [bisplev(x, y, tck, dx, dy) for tck in self._tck]
        
class BilinearInterpolator(GridInterpolator):
    def __init__(self, values, x=None, y=None, check=True, **ignored):
        from numpy import arange
        GridInterpolator.__init__(self, values, x, y)
        def createAxis(ax):
            if isinstance(ax, slice):
                ax = [None, ax]
            else:
                ax = ax.ravel()
                if check:
                    if isSorted(ax):
                        asc = True
                    elif isSorted(ax, reverse=True):
                        asc = False
                    else:
                        raise ValueError("Axes must be sorted in ascending order")
                else:
                    asc = (ax[-1]>ax[0])
                
                if asc: ax = [arange(ax.size), ax]
                else:   ax = [arange(ax.size)[::-1], ax[::-1]]
            return ax
        
        self._x = createAxis(self._x)
        self._y = createAxis(self._y)
    
    def getVirtualIndex(self, values, axis=0):
        from scipy import interp, minimum, maximum
        
        if axis not in range(2):
            raise ValueError("Invalid axis: %d" % axis)
        
        ax = [self._x, self._y][axis]
        
        if isinstance(ax[1], slice):
            start, stop, step = self.parseSlice(ax[1], self._shape[::-1][axis])
            #TODO: it works even if stop<start and step<0, but beaware, the reverse of 
            #      slice(a,a+N*s,s) is slice(a+(N-1)*s,a-s,-s)
            min_, max_ = start, stop-step
            min_, max_ = minimum(min_, max_), maximum(min_, max_)
            return (values.clip(min_, max_) - start) / step
        else:
            return interp(values, ax[1], ax[0])
    
    def __call__(self, xi, yi, grid=False, output=float, order=1):
        from numpy import array, broadcast_arrays, issctype
        from scipy.ndimage import map_coordinates
        
        if issctype(output):
            output = [output]*len(self._values)
            
        if len(output) != len(self._values):
            raise ValueError(
                "Wrong length of output parameter, expected %d but got %d" 
                % (len(self._values), len(output))
            )
        
        xi = self.getVirtualIndex(array(xi, ndmin=1, copy=False), axis=0)
        yi = self.getVirtualIndex(array(yi, ndmin=1, copy=False), axis=1)
        
        if grid:
            xi = xi[:,None]
            yi = yi[None,:]
        xi, yi = broadcast_arrays(xi, yi)

        rit = [
            map_coordinates(z, [yi,xi], output[i], order, mode='nearest')
            for i,z in enumerate(self._values)
        ]
        #map_coordinates returns None when using an user output array
        return [output[i] if t is None else t for i,t in enumerate(rit)]

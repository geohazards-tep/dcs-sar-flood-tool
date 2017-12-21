def temporal_spatial_filter(cube, filter_func, filter_parameters):

    """
        This method filters a stack of images, either spatially and temporally.
        INPUT:
        - cube: stack of data (n images of lxm size)
        - filter_func: function object of the speckle filter to use (string)
        - filter_parameters: dictionary of the parameters to apply to the various filters (keyword expansion, pay attention to the name of the dictionary items: filter_parameters = {"sigma":(0,1), "order":0})

    """
    #import emage.eflood as flood
    import numpy as np
    filtered_cube=[]
    power_cube = cube

    print "Spatial filtering:",
    for i in range(cube.shape[0]):
        print i,
        tmpFiltered = filter_func(cube[i,:,:], **filter_parameters)
        filtered_cube.append(tmpFiltered)

    #return filtered_cube
    spatial_filter = np.vstack(filtered_cube).reshape(power_cube.shape)

    print "rearranging data"

    filtered_cube=[]


    #spatial_gauss_filter = ndimage.gaussian_filter(power_cube, sigma=(0,)+spatial_sigma, order=0)
    temporal_filtered_im = np.zeros(power_cube.shape)
    #saveEnviFile(spatial_gauss_filter, "/var/scratch/GRASSLAND/cohe/filtered_gauss_st.bin")
    ratio = np.sum(power_cube/spatial_filter, axis=0)
    print "ratio.shape", ratio.shape

    print "Temporal filtering:",
    for k in range(cube.shape[0]):
        print k,
        temporal_filtered_im[k,:,:] = 1./power_cube.shape[0] * spatial_filter[k,:,:]*ratio

    return temporal_filtered_im


def multi_temporal_filter(cube, win_size, k, cu, cmax):
    
    """
        This method filters a stack of images, either spatially and temporally. The spatial filter relies on enhannced Lee filter
        INPUT:
        - cube: stack of data (n images of lxm size)
        - win_size: size of the filter box
        - k: dumping factor
        - cu: nominal 

    """
  
    import py_lee_enhanced
    
    lee_parameters = {"win_size":win_size, "k":k, "cu":cu, "cmax":cmax}  # lee enhanced
    lee_pointer = py_lee_enhanced.lee_enhanced_filter
    
    return temporal_spatial_filter(cube, lee_pointer, lee_parameters)

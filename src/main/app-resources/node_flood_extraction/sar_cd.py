# ========================================================================
# Function: execution of change detection on a stack of SAR data
# Massimo Zavagli
# August 2016
# ========================================================================
#
#
#
#
#
#
#
# ========================================================================
#
#
#
#
#
#
# ========================================================================

import os
import numpy as np
import scipy.ndimage as ndimage
import cache


def computePFA_mpmath(Th, n1, n2, enl):
    '''
    Compute the PFA, that is the left tail integral of the pdf.

    Th: threshold. Integral is computed between 0.0 and Th
    n1, n2: number of samples to calculate the ratio of averages
    enl: equivalent number of look of the SAR image

    return: probability of false alarm
    '''

    from mpmath import hyp2f1, gamma, gammaprod, log, exp, nstr
    import numpy as np

    La = n1 * enl
    Lb = n2 * enl

    # calculation factor
    if -(Th * La / Lb) >= -1.0:
        factor1 = gammaprod([La + Lb], [La, Lb])
        factor2_ln = La * (log(La) - log(Lb)) + La * log(Th) - log(La)
        hyp = hyp2f1(La + Lb, La, La + 1.0, -Th * La / Lb)
        pfa = exp(log(factor1) + factor2_ln + log(hyp))
    else:
        factor1 = gammaprod([La + Lb], [La, Lb])
        factor2_ln = Lb * (log(Lb) - log(La)) - Lb * log(Th) - log(Lb)
        hyp = hyp2f1(La + Lb, Lb, Lb + 1.0, -Lb / (Th * La))
        pfa = 1. -  exp(log(factor1) + factor2_ln + log(hyp))

    pfa = np.float(nstr(pfa))

    return pfa

TH_SLICE = slice( 0.0, 100, 0.01)
N1_SLICE = slice( 1, 2500, 1)
N2_SLICE = slice( 1, 2500, 1)
ENL_SLICE = slice( 0.0, 100.0, 0.2)

@cache.quantized(
    (TH_SLICE, 'round'), # AOT-550
    (N1_SLICE, 'round'), # Water Vapour
    (N2_SLICE, 'round'), # Ozone
    (ENL_SLICE, 'round'), # Target_altitude
    (None, None),
    (None, None),
    (None, None),
)
@cache.cache(2048)
def computePFA_scipy(Th, n1, n2, enl):
    '''
    Compute the PFA, that is the left tail integral of the pdf.

    Th: threshold. Integral is computed between 0.0 and Th
    n1, n2: number of samples to calculate the ratio of averages
    enl: equivalent number of look of the SAR image

    return: probability of false alarm
    '''

    from scipy.special import hyp2f1, gamma, gammaln
    import numpy as np

    La = n1 * enl
    Lb = n2 * enl

    # calculation factor
    if -(Th * La / Lb) >= -1.0:
        factor1_ln = gammaln(La + Lb) - gammaln(La) - gammaln(Lb)
        factor2_ln = La * (np.log(La) - np.log(Lb)) + La * np.log(Th) - np.log(La)
        hyp = hyp2f1(La + Lb, La, La + 1.0, -Th * La / Lb)
        pfa = np.exp(factor1_ln + factor2_ln + np.log(hyp))
    else:
        factor1_ln = gammaln(La + Lb) - gammaln(La) - gammaln(Lb)
        factor2_ln = Lb * (np.log(Lb) - np.log(La)) - Lb * np.log(Th) - np.log(Lb)
        hyp = hyp2f1(La + Lb, Lb, Lb + 1.0, -Lb / (Th * La))
        pfa = 1. -  np.exp(factor1_ln + factor2_ln + np.log(hyp))

    return pfa



def spatial_filter(cube, filter_size=(3,3)):

    if (np.array(filter_size, dtype=int)%2).sum() == 0: # if the filter along one dimension has even size
        print "Warning: The box_car filtering has at least one dimension with even size. Along those dimensions the image will be displaced of 1 pixel. Please use odd sizes for the box_car filter."

    print "... uniform filtering"
    
    output = np.empty_like(cube)
    for i in range(cube.shape[0]):
        output[i,:,:] = nan_uniform_filter(cube[i, :, :], win_size=(filter_size[0], filter_size[1]))

    return output





def nan_uniform_filter(img, win_size):
    from scipy.ndimage import uniform_filter

    nan_mask = ~np.isfinite(img)

    filled_img = np.copy(img)
    filled_img[nan_mask] = 0.0

    mean_nan = (1. - uniform_filter(nan_mask.astype(float), win_size))
    filtered_image = uniform_filter(filled_img, win_size)
    filtered_image /= mean_nan

    filtered_image[filtered_image < 0.0] = 0.0
    filtered_image[~np.isfinite(filtered_image)] = np.nan

    return filtered_image


def change_on_neighbor(cube, ml, tol, median=None, lib='scipy', force_change_time=None):
    '''
    change_on_neighbor look for changes in the RCS along the temporal series of SAR data.
    Inputs:
       cube:
       ml:
       pfa:
       median:
    Outputs:
       signed_PFA_map:
       CD_ map:
    '''

    # calculate the ML lambda_a function. It is a 3D array.
    M = cube.shape[0]
    n_rows = cube.shape[1]
    n_cols = cube.shape[2]
    m = (1 + np.arange(M))[:,None,None]
    print "... cumulative sum"
    cumulative_sum = np.cumsum(cube, axis=0)
    if force_change_time is not None:
        print "... force the optimal change time to", force_change_time
        opt_m = force_change_time*np.ones((n_rows, n_cols), dtype=int)
    else:
        print "... lambda_a"
        mlf_lambda_a = np.power(cumulative_sum/m, -m)*np.power((cumulative_sum[-1,:,:] - cumulative_sum)/(M-m), -(M-m))
        # calculate the m values for which the ML lambda_a is maximum
        print "... optimal change time"
        opt_m = 1 + np.argmax(mlf_lambda_a, axis=0)

    # calculate the two means relative to the optimal m values
    ii,jj = np.ogrid[:opt_m.shape[0], :opt_m.shape[1]]
    sum1 = cumulative_sum[opt_m - 1, ii, jj]
    media2 = (cumulative_sum[-1,:,:] - sum1)/(M - opt_m)
    media1 = sum1/opt_m
    eta = media1/media2
    Ma = opt_m.astype("int32")
    Mb = (M-opt_m).astype("int32")
    pfa_map = np.zeros((n_rows, n_cols), dtype="double")
    positive_change = np.zeros((n_rows, n_cols), dtype=bool)
    if lib == 'scipy':
        for i in range(n_rows):
            #print "Line ", i
            for j in range(n_cols):
                x = eta[i,j]
                if x < 1.0:
                    positive_change[i, j] = True
                    pfa_map[i, j] = computePFA_scipy(x, Ma[i,j], Mb[i,j], ml)
                else:
                    positive_change[i, j] = False
                    pfa_map[i, j] = computePFA_scipy(1/x, Mb[i,j], Ma[i,j], ml)
    elif lib == 'mpmath':
        for i in range(n_rows):
            print "Line ", i
            for j in range(n_cols):
                x = eta[i,j]
                if x < 1.0:
                    positive_change[i, j] = True
                    pfa_map[i, j] = computePFA_mpmath(x, Ma[i,j], Mb[i,j], ml)
                else:
                    positive_change[i, j] = False
                    pfa_map[i, j] = computePFA_mpmath(1/x, Mb[i,j], Ma[i,j], ml)
    else:
        print lib, "--> Unknow library. Please consider scipy or mpmath."

    return pfa_map, opt_m, positive_change



def change_detection(cube, power, ml, pfa_th, box_shape, ul_pixel=None, tile_size=None, median=None, sub_sampling=True, lib='scipy', force_change_time=None):
    '''
    change_detection look for changes in the RCS along the temporal series of SAR data.
    Inputs:
       data_list_filename:
       ul_row:
       ul_col:
       tile_size:
       power:
       ml:
       box_shape
       pfa_th:
       median:
       lib:
    Outputs:
       PFA map:
       CD map:
       state:
    '''

    # set the required tollerance
    tol = pfa_th
    tol = pfa_th/10.

    cube_shape0 = cube.shape
    print "Cube shape", cube_shape0

    # spatial box_car filtering
    print "Spatial filtering"
    cube2 = spatial_filter(cube, box_shape)

    if sub_sampling:
        # sub-sampling
        print "... sub-sampling"
        offset_x = box_shape[0]//2
        offset_y = box_shape[1]//2
        cube2 = cube2[:, offset_x::box_shape[0], offset_y::box_shape[1]]
    print "Cube shape after lowpass filter and sub-sampling", cube_shape0

    # start change detection
    print "... probability of false alarm calculation"
    cube_shape = np.array(cube2.shape)
    if box_shape is None:
        # change detection over a segmentation map
        #pfa_map, state = change_on_segmentation(cube2, min_seg, max_seg, seg_map, power, ml, tol, median)
        print "ancora non implementato"
    else:
#        pfa_map, opt_m = change_on_neighbor_C(cube2, ml*np.prod(box_shape), tol, median=median)
        pfa_map, opt_m, positive_change = change_on_neighbor(cube2, ml*np.prod(box_shape), tol, median=median, lib=lib, force_change_time=force_change_time)

    # calculate change detection
    print "... change detection"
    negative_change = np.logical_not(positive_change)
    cd_map = (pfa_map < pfa_th).astype(int)
    cd_map *= opt_m
    cd_map[negative_change] = -cd_map[negative_change]

    pos_pfa = np.ones_like(pfa_map)
    pos_pfa[positive_change] = pfa_map[positive_change]

    neg_pfa = np.ones_like(pfa_map)
    neg_pfa[negative_change] = pfa_map[negative_change]

    if sub_sampling:
        # re-build output to the original sampling
        print "... re-sampling"

        # bilinear
        import interpolation as interp

        n_rows, n_cols = cube_shape0[-2::]
	print "dimensioni immagine in input cd: ", n_rows, n_cols
        in_nrows, in_ncols = pfa_map.shape
        tile_center_row = np.float(box_shape[0])/2.
        tile_center_col = np.float(box_shape[1])/2.

        grid = np.mgrid[0:n_rows, 0:n_cols]

        # ... pfa_map
        bil_pfa = interp.BilinearInterpolator((pfa_map,),
                                              tile_center_col + np.linspace(0, (in_ncols-1)*box_shape[0], in_ncols),
                                              tile_center_row + np.linspace(0, (in_nrows-1)*box_shape[1], in_nrows))
        pfa_map_r = bil_pfa(*grid[::-1])[0]

        # ... pos_pfa
        bil_pos_pfa = interp.BilinearInterpolator((pos_pfa,),
                                              tile_center_col + np.linspace(0, (in_ncols-1)*box_shape[0], in_ncols),
                                              tile_center_row + np.linspace(0, (in_nrows-1)*box_shape[1], in_nrows))
        pos_pfa_r = bil_pos_pfa(*grid[::-1])[0]

        # ... neg_pfa
        bil_neg_pfa = interp.BilinearInterpolator((neg_pfa,),
                                              tile_center_col + np.linspace(0, (in_ncols-1)*box_shape[0], in_ncols),
                                              tile_center_row + np.linspace(0, (in_nrows-1)*box_shape[1], in_nrows))
        neg_pfa_r = bil_neg_pfa(*grid[::-1])[0]

        # ... cd
        bil_cd = interp.BilinearInterpolator((cd_map,),
                                             tile_center_col + np.linspace(0, (in_ncols-1)*box_shape[0], in_ncols),
                                             tile_center_row + np.linspace(0, (in_nrows-1)*box_shape[1], in_nrows))
        cd_map_r = bil_cd(*grid[::-1])[0]

    return pfa_map_r, cd_map_r, pos_pfa_r, neg_pfa_r



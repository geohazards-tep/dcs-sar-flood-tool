#!/opt/pyenv/shims/python
# -*- coding: iso-8859-15 -*-

import os
import numpy as np
import gdal
import sys
import temporal_spatial_filter
import sar_cd
import glob
import scipy.ndimage
import argparse

#stringa di lancio: flood_cd.py --amp_list=lista_immagini_ampiezza --cohe_long_list=lista_coerenze_lunghe --window='xmin ymin xdim ydim' \
#                               --minimum_images=12 --maximum_images=25 --outdir=./

#window è espressa in pixel: xmin=colonna_min, ymin=riga_min, xdim=numero_colonne, y_dim=numero_righe





def coeff_of_variation(image, kernelSize=(3,3)):


    import py_lee_enhanced

    imageMean = py_lee_enhanced.nan_uniform_filter(image, win_size=kernelSize)
    imageMeanQuad = py_lee_enhanced.nan_uniform_filter(image**2, win_size=kernelSize)
    imageStdDev = np.sqrt(imageMeanQuad - imageMean**2)
    return imageStdDev/imageMean






def make_cube_w_gdal(lista_data, AOI_l_c_0=None, AOI_size=None):

    if isinstance(lista_data, basestring):
        with open(lista_data, 'r') as f:
            lines=f.readlines()
        gdal_data = gdal.Open(lines[0][:-1])
        dummy = gdal_data.ReadAsArray()
    else:
        lines=lista_data
        gdal_data = gdal.Open(lines[0])
        dummy = gdal_data.ReadAsArray()

    print "dummy_shape",dummy.shape

    if AOI_l_c_0==None or AOI_size==None:
        AOI_l_c_0=(0,0)
        AOI_size=dummy.shape[-2:]

    if len(dummy.shape) == 3:
        tipo = "complex"
    else:
        tipo = "float"

    cube = np.zeros((len(lines),) + AOI_size, dtype=tipo)

    print "shape cube", cube.shape

    for k, file in enumerate(lines):
        file = file.strip()
        print "file", file
        aux_data =  gdal.Open(file)
        aux = aux_data.ReadAsArray(AOI_l_c_0[1],AOI_l_c_0[0],AOI_size[1],AOI_size[0])
        if tipo == "complex":
            cube[k,:,:] = aux[0,...] + 1j*aux[1,...]
        else:
            cube[k,:,:] = aux
        del aux_data


    return cube, gdal_data.GetGeoTransform(), gdal_data.GetProjection()







def flood_cd(amp_cube, long_cohe_cube):

    # Minimum flood area in pixels
    smallest_flood_pixels = 9
    # De Grandi parameters
    k=0.2; win_size=5; cu=0.523; cmax=1.73

    # Coefficient of variation kernel
    CV_kernel=(3,3)

    # Urban threshold
    urban_th=0.3

    # Dark area thresholds
    water_threshold=0.1

    # Change Detection parameters
    isPower=False
    ml=1.0
    CD_th=0.1
    CD_kernel=(3,3)
    pos_pfa_th=0.1
    neg_pfa_th=0.1

    print "Apply spatial and temporal filtering"
    # power images are filtered with spatial lee filter + temporal filter (= De Grandi)
    k=1.0; win_size=3; cu=0.523; cmax=1.73
    amp_cube_filtered = temporal_spatial_filter.multi_temporal_filter(amp_cube**2., win_size, k, cu, cmax)
    # amplitudes from filtered powers
    amp_cube_filtered = np.sqrt(amp_cube_filtered)
    final_image_filtered = amp_cube_filtered[-1,:,:]

    # texture based on coefficient of variation
    n_im, cols, rows = amp_cube.shape
    mean_CV = np.zeros((cols,rows), dtype=float)
    for i in range(n_im):
        #print i, ":", np.nanmin(amp_cube[i]), np.nanmax(amp_cube[i])
        mean_CV += coeff_of_variation(amp_cube[i]**2, kernelSize=CV_kernel)
    mean_CV /= n_im

    final_image_coeff_var = mean_CV

    # Calculation of the urban mask
    urban_mask = (np.median(amp_cube_filtered, axis=0)*np.mean(long_cohe_cube, axis=0)*final_image_coeff_var) > urban_th


    amp_cube_median = np.median(amp_cube[:-1,:,:], axis=0)
    amp_cube_mean = np.mean(amp_cube[:-1,:,:], axis=0)
    amp_cube_filtered_median = np.median(amp_cube_filtered[:-1,:,:], axis=0)
    amp_cube_filtered_mean = np.mean(amp_cube_filtered[:-1,:,:], axis=0)

    amp_cube_std = np.std(amp_cube[:-1,:,:], axis=0)

    sure_water = amp_cube_median < water_threshold

    th_map = np.ones(sure_water.shape, dtype=float)*np.nan

    th_map[sure_water] = (amp_cube[-1,:,:])[sure_water]
    th_map_val = np.nanmean(th_map)
    th_map_val = np.minimum(th_map_val, water_threshold)


    eps = 0.2*np.mean(amp_cube_std[sure_water])
    print "eps =", eps
    dark_area = amp_cube_filtered[-1,:,:] <= (th_map_val + eps)

    #change detection
    pfa_map_r, cd_map_r, pos_pfa_r, neg_pfa_r = sar_cd.change_detection(amp_cube, isPower, ml, CD_th, CD_kernel,
                                                                    force_change_time=(amp_cube.shape[0]-1))

    ### Final Decision Map

    urban_pot_flood_mask = np.logical_and(urban_mask, pos_pfa_r<pos_pfa_th)
    land_flood_mask = np.logical_and(np.logical_and(np.logical_not(urban_mask), neg_pfa_r<neg_pfa_th), dark_area)
    flood_map = np.logical_or(urban_pot_flood_mask, land_flood_mask)

    return flood_map




def flood_cd_body(amp_list=None, cohe_long_list=None, window=None, minimum_images=10, maximum_images=20, outdir=None, smallest_flood_pixels=9):


    cc=window.split()
    if not cc==[]:
        window=[(int(cc[0]),int(cc[1])),(int(cc[2]),int(cc[3]))]
    else:
        window=cc



    amp_cube, geo_transform, projection = make_cube_w_gdal(amp_list, *window)
    long_cohe_cube, _, _ = make_cube_w_gdal(cohe_long_list, *window)


    if len(window) == 0:
        window = [(0,0),amp_cube.shape[1:]]

    geo_transform = (geo_transform[0] + window[0][1]*geo_transform[1], geo_transform[1], geo_transform[2],
                     geo_transform[3] + window[0][0]*geo_transform[5], geo_transform[4], geo_transform[5])


    ##creare lista con i nomi di output per la flood map outname[] - includere l'outdir
    if isinstance(amp_list, basestring):
	with open(amp_list, 'r') as f:
	    lines=f.readlines()
    else:
        lines = amp_list

    ntot_images=amp_cube.shape[0]
    outname=[]
    for i in range(minimum_images,ntot_images):
        #print outdir+'/'+os.path.basename(lines[i]).rstrip('\n').rstrip('.tif')+'_flood_map.tif'
        outname.append(outdir+'/'+os.path.basename(lines[i]).rstrip('\n').rstrip('_ampl-crop.tif')+'_'+os.path.basename(lines[i-1])[17:77]+'_flood_map.tif')
        print outname


    #ntot_images=amp_cube.shape[0]
    driv = gdal.GetDriverByName('GTIFF')
    for i in range(minimum_images,ntot_images):

        min_i=np.maximum(i-maximum_images, 0)
        tmp_amp_cube=amp_cube[min_i:i+1,:,:]
        #tmp_long_cohe_cube=long_cohe_cube
        print "min_i: ", min_i
        print "i+1: ", i+1
        print long_cohe_cube.shape
        tmp_flood_map=flood_cd(tmp_amp_cube, long_cohe_cube)
        # removal of small flooded areas
        (clumps, numClumps) = scipy.ndimage.label(tmp_flood_map, structure=np.ones((3,3)))
        tmp_flood_area = scipy.ndimage.measurements.sum(tmp_flood_map, clumps, np.arange(0,numClumps+1))
        flood_map = np.where(tmp_flood_area[clumps]>=smallest_flood_pixels, tmp_flood_map, 0)

        new_data = driv.Create(outname[i-1], flood_map.shape[1], flood_map.shape[0], 1, gdal.GDT_Byte)
        new_data.SetGeoTransform(geo_transform)
        new_data.SetProjection(projection)
        new_data.GetRasterBand(1).WriteArray(flood_map.astype('uint8'))
        new_data.FlushCache()
        del new_data
        print "Written file %r (exists: %s, isfile: %s" % (outname[i-1], os.path.exists(outname[i-1]), os.path.isfile(outname[i-1]))
    return outname 

def flood_cd_main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--amp_list", default="", type=str, help="amplitude images list")
    parser.add_argument("-c", "--cohe_long_list", default="", type=str, help="long coherence list")
    parser.add_argument("-w", "--window", default="", type=str, help="AOI for analysis")
    parser.add_argument("-m", "--minimum_images", default="12", type=int, help="minimum number of images necessary for change detection")
    parser.add_argument("-M", "--maximum_images", default="25", type=int, help="maximum number of images usable for change detection")
    parser.add_argument("-o", "--outdir", default="", type=str, help="output directory")
    parser.add_argument("-s", "--smallest_flood_pixels", default="9", type=int, help="minimum size for flood areas")

    kwargs = vars(parser.parse_args())
    flood_cd_body(**kwargs)







if __name__ == '__main__':
    flood_cd_main()



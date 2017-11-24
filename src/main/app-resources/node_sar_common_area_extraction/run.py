#!/opt/anaconda/bin/python
#Classe runSnap legge da una singola cartella i file in essa contenuti
#li ordina in modo decrescente per data e crea
#le coppie per lo start di SNAP
#infine crea il file name da associare all'output di SNAP




import subprocess
import os,sys
import cioppy
import string
import gdal
import ogr
import osr
import numpy as np
ciop = cioppy.Cioppy()




# define the exit codes - need to be better assessed
SUCCESS = 0
ERR_FAILED = 134

# add a trap to exit gracefully
def clean_exit(exit_code):
    log_level = 'INFO'
    if exit_code != SUCCESS:
        log_level = 'ERROR'

    msg = { SUCCESS: 'Download successfully concluded',
           ERR_FAILED: 'Unable to complete the download'}

    ciop.log(log_level, msg[exit_code])

def get_envelope(filepath):
    ds = gdal.Open(filepath, gdal.GA_ReadOnly)
    y,x = np.mgrid[:ds.RasterYSize:2j,:ds.RasterXSize:2j]
    bbox = np.array([gdal.ApplyGeoTransform(ds.GetGeoTransform(), xx, yy)
                     for xx,yy in zip(x.ravel(), y.ravel())])
    srs = osr.SpatialReference(wkt=ds.GetProjection())
    geom = ogr.CreateGeometryFromWkt(
        'POLYGON(({b[0][0]} {b[0][1]}, '
                 '{b[1][0]} {b[1][1]}, '
                 '{b[3][0]} {b[3][1]}, '
                 '{b[2][0]} {b[2][1]}, '
                 '{b[0][0]} {b[0][1]}))'.format(b=bbox),
        srs)
    return geom
    

def main():
    outdir=ciop.tmp_dir
    input = sys.stdin.readlines()
    input_file = input[0][string.find(input[0], "'")+1:string.rfind(input[0],"'")]    
    print input_file
    #print "sys.stdin ", input
    #for input in sys.stdin:
    #print "sys.stdin ", input
    intersection = reduce(lambda x,y: x.Intersection(y) if x else y,
                          [get_envelope(f) for f in input_file)
    res = intersection.ExportToGML()
    print res
    output_file = ciop.publish(res, mode='', metalink=False)
    print "output: ", output_file




try:
    main()
except SystemExit as e:
    if e.args[0]:
        clean_exit(e.args[0])
    raise
#else:
#    atexit.register(clean_exit, 0)




#ciop.publish(outdef, metalink = true)        


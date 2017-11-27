#!/opt/anaconda/bin/python
#Classe runSnap legge da una singola cartella i file in essa contenuti
#li ordina in modo decrescente per data e crea
#le coppie per lo start di SNAP
#infine crea il file name da associare all'output di SNAP




import subprocess
import os,sys
import cioppy
import string
import json
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



def main():
    outdir=ciop.tmp_dir
    input = sys.stdin.readlines()
    input_line = input[0][string.find(input[0], "'")+1:string.rfind(input[0],"'")]    
    print input_line
    #print "sys.stdin ", input
    #for input in sys.stdin:
    #print "sys.stdin ", input
    data = json.loads(input_line)
    filepath = data['file']
    srs = data['srs']
    envelope = data['envelope']
    bounds = [envelope[i] for i in (0,2,1,3)]
    out = os.path.join(outdir, os.path.basename(filepath)[::-1].replace('.', '-crop.'[::-1])[::-1])
    ds = gdal.Warp(outfile, filepath,
                   outputBounds=bounds, outputBoundsSRS=srs,
                   resampleAlg='bilinear', multithread=False)
    del ds
    res = ciop.copy(out, outdir, extract=False)
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


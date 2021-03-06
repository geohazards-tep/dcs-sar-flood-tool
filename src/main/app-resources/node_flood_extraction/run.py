#!/opt/anaconda/bin/python
# -*- coding: utf-8 -*-
#Classe runSnap legge da una singola cartella i file in essa contenuti
#li ordina in modo decrescente per data e crea
#le coppie per lo start di SNAP
#infine crea il file name da associare all'output di SNAP




import subprocess
import os,sys
import cioppy
import string
import datetime
import flood_cd
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
    print "cominciamo!!"
    outdir=ciop.tmp_dir

    cohe_list = []
    image_list = []
    input = sys.stdin.readlines()
    input_files_hdfs = [x.strip().strip("'") for x in input]
    
    #print "input file hdfs: ", input_files_hdfs

    
    for input_file in input_files_hdfs:
    #print "sys.stdin ", input
	#creo una lista di immagini e una di coerenze e i file vanno ad alimentare il processore di flood extraction
       	print "input: ", input_file
	print "vai con la data!"
        #print input_file[-38:-34], input_file[-34:-32], input_file[-32:-30]
        date_img = datetime.date(int(input_file[-48:-44]), int(input_file[-44:-42]),int(input_file[-42:-40]))
	local_infile = ciop.copy(input_file, outdir, extract=False)
        print "date_img: ", date_img
	print "local file : %s" % local_infile
	if (input_file.find('ampl') > -1):
	    image_list.append((date_img, local_infile))
	
	if (input_file.find('cohe') > -1):
            cohe_list.append((date_img, local_infile))

    print image_list
    print cohe_list


    image_list.sort()
    cohe_list.sort()

    print image_list
    print cohe_list
    
    outfile_list=flood_cd.flood_cd_body(amp_list=[x[1] for x in image_list], cohe_long_list=[x[1] for x in cohe_list], window="", minimum_images=1, maximum_images=20, outdir=outdir, smallest_flood_pixels=9)
    print os.path.isfile(outfile_list[0])

    print outfile_list
    
    res = ciop.publish(outfile_list, metalink=True)
    print 'result from publish string: ', res


    ##preview and metadata file generation

    #PREVIEW
    for outfile in outfile_list:
	#outfile_png = outfile.replace("tif","png")
	#cmd = 'gdal_translate  -scale 0 1 -of "PNG" -co WORLDFILE=YES '+outfile+' '+outfile_png
	#print cmd
	#res=subprocess.call(cmd, shell=True)
	#worldfile=outfile.replace("tif","wld")
        #outfile_pngw=worldfile.replace("wld","pngw")
	#os.rename(worldfile, outfile_pngw)
	#res = ciop.publish(outfile_png, metalink=True)
        #res = ciop.publish(outfile_pngw, metalink=True)
        
	#METADATA FILE
	outfile_properties=outfile.replace("tif","properties")
	file_properties=open(outfile_properties, "w")
	file_properties.write("date="+datetime.datetime.now().isoformat()+'\n')
	file_properties.write("output="+os.path.basename(outfile)+'\n')
	file_properties.write("title=Flood map extent of "+os.path.basename(outfile)[17:25]+' relative to the situation of '+os.path.basename(outfile)[68:76]+'\n')
	file_properties.write("copyrigth=e-Geos")
	file_properties.close()
	res = ciop.publish(outfile_properties, metalink=True)
	
    

    #output_file = ciop.publish(res, mode='silent', metalink=True)
    #print "output: ", output_file




try:
    main()
except SystemExit as e:
    if e.args[0]:
        clean_exit(e.args[0])
    raise
#else:
#    atexit.register(clean_exit, 0)




#ciop.publish(outdef, metalink = true)        


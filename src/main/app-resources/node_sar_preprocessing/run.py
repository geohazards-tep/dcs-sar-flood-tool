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
	
    swath = ciop.getparam('swath')
    print 'swath: ', swath
    #input = sys.stdin.readlines()
    #input_file = input[0][string.find(input[0], "'")+1:string.rfind(input[0],"'")]    
    #print input_file
    #print "sys.stdin ", input
	

    for input in sys.stdin:
    	print "input to the specific node: ",input
        tmp_input=input.split("'")
	master=tmp_input[1]
	slave=tmp_input[3]
	mode=tmp_input[5]
	print "master: ", master
	print "slave:  ", slave
	print "mode:  ", mode
        if ( mode == "coregistration" ):
            print "mode:  ", mode
	    #subprocess.call(["unzip",local_file,"-d",extract_dir])
	    #faccio l'estrazione in dirtemp
	    cmd_unzip='unzip '+master+' -d '+extract_dir
	    #mi trovo la directory che è stata estaratta (naming convention basata su S-1)
	    extract_dir=extract_dir+os.sep+os.path.basename(filename)[0:67]+'.SAFE' #da sistemare
	    #creo la variabile con il file manifest.safe
	    
		#lancia la coregistrazione
	    cmd='/opt/snap-5.0/bin/gpt ampl_geo_cal_single_cl.xml -Psub='+swath+' -DAuxDataPath='+outdir+' -Pmaster='+master+os.path.sep+'manifest.safe'+' -Pampl_geo='+master+os.path.sep+os.path.basename(master)[0:-5]+'_ampl'
	    print cmd
	   #subprocess.call('/opt/snap-5.0/bin/gpt ampl_geo_cal_single_cl.xml -Psub='+swath+' -DAuxDataPath='+outdir+' -Pmaster='+master+os.path.sep+'manifest.safe'+' -Pampl_geo='+master+os.path.sep+os.path.basename(master)[0:-5]+'_ampl')
	elif (  mode == "coherence" ):
	    print "mode:  ", mode
	    #lanciala coerenza
	else:
	    print "mode not recognized...terminating"
	    raise ValueError('wrong preprocessing mode, it should be either coregistration or coherence, not '+mode+' mode')
    return 0
	

    #/opt/snap-5.0/bin/gpt ampl_geo_cl_v1.xml  -DAuxDataPath=tmpdir -Pmaster='+input+read1+' \
    #            -Pslave='+input+read2+' -Pampl_geo='+outdef+a+'_'+b+'_ampl.dim -Pcohe_geo='+outdef+a+'_'+b+'_cohe.dim


    #QUI VA INSERITA LA PUBBLICAZIONE DEL RISULTATO VERSO IL NODO SUCCESSIVO (salvataggio su hdfs)
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


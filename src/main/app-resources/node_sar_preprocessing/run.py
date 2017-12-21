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
    extract_dir=ciop.tmp_dir
    outdir = extract_dir	
    swath = ciop.getparam('swath')
    print 'swath: ', swath
    #input = sys.stdin.readlines()
    #input_file = input[0][string.find(input[0], "'")+1:string.rfind(input[0],"'")]    
    #print input_file
    #print "sys.stdin ", input
    xml_path = os.path.dirname(__file__)
    print 'xml_path: %s' % xml_path

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
	    #res=subprocess.call("ls -l "+master)
	    #subprocess.call(["unzip",local_file,"-d",extract_dir])
	    #faccio l'estrazione in dirtemp
	    master_local = ciop.copy(master, outdir, extract=False)
	    cmd_test='ls -l %s' % outdir
	    print "ls command test : %s" % cmd_test
	    res=subprocess.call(cmd_test, shell=True)

            cmd_unzip='unzip '+master_local+' -d '+extract_dir
	    print "cmd_unzip : %s" % cmd_unzip
       	    res=subprocess.call(cmd_unzip, shell=True)
	    
	    #mi trovo la directory che è stata estaratta (naming convention basata su S-1)
	    master_unzip=extract_dir+os.sep+os.path.basename(master)[0:67]+'.SAFE' #da sistemar
	    master_outname=master_unzip+os.path.sep+os.path.basename(master)[0:-4]+'_ampl.tif'
	    cmd_test='ls -l '+master_unzip
	    res=subprocess.call(cmd_test, shell=True)
	    #creo la variabile con il file manifest.safe
	    #lancia la coregistrazione
	    cmd_coreg='/opt/snap-5.0/bin/gpt '+xml_path+os.path.sep+'ampl_geo_cal_single_cl_v1.xml -Psub='+swath+' -DAuxDataPath='+outdir+' -Pmaster='+master_unzip+os.path.sep+'manifest.safe'+' -Pampl_geo='+master_outname
	    print cmd_coreg
	    try:
	    	res=subprocess.call(cmd_coreg, shell=True)
		#outfilename=master_unzip+os.path.sep+os.path.basename(master)[0:-5]+'_ampl'
		#cmd_test='ls -l '+master_outname
		#res=subprocess.call(cmd_test, shell=True)
		print "res: %s" % res
		print master_outname
	        #res = ciop.publish(master_outname, metalink=False)

	    except: 
		print "coregistration of %s failed" % master
		raise
   #subprocess.call('/opt/snap-5.0/bin/gpt ampl_geo_cal_single_cl.xml -Psub='+swath+' -DAuxDataPath='+outdir+' -Pmaster='+master+os.path.sep+'manifest.safe'+' -Pampl_geo='+master+os.path.sep+os.path.basename(master)[0:-5]+'_ampl')
	    #cmd_test='ls -l '+outfilename
            #res=subprocess.call(cmd_test, shell=True)

	elif (  mode == "coherence" ):
	    print "mode:  ", mode
	    #lanciala coerenza
            master_local = ciop.copy(master, outdir, extract=False)
            slave_local = ciop.copy(slave, outdir, extract=False)
            cmd_unzip='unzip '+master_local+' -d '+extract_dir
	    res=subprocess.call(cmd_unzip, shell=True)
            cmd_unzip='unzip '+slave_local+' -d '+extract_dir
            res=subprocess.call(cmd_unzip, shell=True)
	    master_unzip=extract_dir+os.sep+os.path.basename(master)[0:67]+'.SAFE'
	    slave_unzip=extract_dir+os.sep+os.path.basename(slave)[0:67]+'.SAFE'
	
            cohe_outname = outdir+os.path.sep+os.path.basename(master)[0:-4]+'_'+os.path.basename(slave)[0:-4]+'_cohe.tif'
	    
	    cmd_cohe='/opt/snap-5.0/bin/gpt '+xml_path+os.path.sep+'cohe_geo_cl_v3.xml -Psub='+swath+' -DAuxDataPath='+outdir+' -Pmaster='+master_unzip+os.path.sep+'manifest.safe'+' -Pslave='+slave_unzip+os.path.sep+'manifest.safe'+'  -Pcohegeo='+cohe_outname
            print cmd_cohe
	    try:
                res=subprocess.call(cmd_cohe, shell=True)
                #outfilename=master_unzip+os.path.sep+os.path.basename(master)[0:-5]+'_ampl'
                #cmd_test='ls -l '+cohe_outname
                #res=subprocess.call(cmd_test, shell=True)
		print cohe_outname
	        res = ciop.publish(cohe_outname, metalink=False)

            except:
                print "coherence estimation of %s and %s failed" % (master,slave)
                raise
# cohe_geo_cl_v3.xml
#/opt/snap-5.0/bin/gpt cohe_geo_cl_v3.xml  -Psub=IW3 -DAuxDataPath=./ -Pmaster='S1A_IW_SLC__1SDV_20151217T061404_20151217T061434_009078_00D09B_065C.SAFE/manifest.safe' -Pslave='S1A_IW_SLC__1SDV_20151229T061402_20151229T061429_009253_00D59B_32D4.SAFE/manifest.safe'  -Pcohegeo=master_slave_cohe.test




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


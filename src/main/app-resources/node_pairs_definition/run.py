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
    #input = sys.stdin.readlines()
    #input_file = input[0][string.find(input[0], "'")+1:string.rfind(input[0],"'")]    
    #print input_file
    #print "sys.stdin ", input
	

    date_list = []

    image_list = {}
    for input in sys.stdin:
    #print "sys.stdin ", input
       	print "input: ", input
	input_file = input[string.find(input, "'")+1:string.rfind(input,"'")].strip()
	print "input_file: ", input_file
	#image_list.append(input_file)
	#input_file = input[string.find(input, "'")+1:string.rfind(input,"'")]
        #print input_file
	#print 'sto facendo un test'
	#print input_file[-38:-34], input_file[-34:-32], input_file[-32:-30]
	#input_file_basename = os.path.basename(input_file)
	print "vai con la data!"
	print input_file[-38:-34], input_file[-34:-32], input_file[-32:-30]
	date_img = datetime.date(int(input_file[-38:-34]), int(input_file[-34:-32]),int(input_file[-32:-30]))
	print "date_img: ", date_img
	image_list[date_img] = input_file
	date_list.append(date_img)
	print "il file di input e': ",input_file

    date_list.sort()
    
    
    ##Creo le coppie
    gap=datetime.timedelta(days=int(ciop.getparam('long_coherence_interval')))
    print "gap: ", gap
    cohe_list=[]
    for date1 in date_list:
	for date2 in date_list:
	    print date2 - date1
	    if (date2 - date1) > gap:
			cohe_list.append((date1,date2))
		
    print cohe_list
    
    master_coreg_date =  date_list[len(date_list)/2]
    # ADESSO DEVO PUBBLICARE IL RISULTATO 
    # RICOSTRUIRE LA COPPIA DELLE IMMAGINI
    image_pairs=[]
    for i in cohe_list:
        image_pairs.append(str((image_list[i[0]],image_list[i[1]], 'coherence')))

    print "image_pairs: ", image_pairs    
    print "master_coreg_date: ", master_coreg_date
    print "master_coreg: ", image_list[master_coreg_date]
    #adesso devo creare le coppie su cui coregistrare
    for i in date_list:
	#image_pairs.append(str((image_list[master_coreg_date],image_list[i], 'coregistration')))
        image_pairs.append(str((image_list[i], image_list[i], 'coregistration')))	

    print image_pairs
    res = ciop.publish(image_pairs, mode='silent', metalink=True)
    print 'result from publish string: ', res

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


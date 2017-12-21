#!/opt/anaconda/bin/python
#Classe runSnap legge da una singola cartella i file in essa contenuti
#li ordina in modo decrescente per data e crea
#le coppie per lo start di SNAP
#infine crea il file name da associare all'output di SNAP




import subprocess
import os,sys
import cioppy
import string
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
    print "il file di input e': ", input
    try:
	input_file = input[0][string.find(input[0], "'")+1:string.rfind(input[0],"'")]    
        print "input file pulito dall a capo: ",input_file
    #print "sys.stdin ", input
    #for input in sys.stdin:
    #print "sys.stdin ", input
        process=subprocess.Popen(['opensearch-client',input_file,'enclosure'], stdout=subprocess.PIPE)
        out, err=process.communicate()
        output_file=ciop.copy(out,outdir, extract=False)
        print output_file
        res = ciop.publish(output_file, metalink=False)
	print 'result from publish to hdfs: ', res
	#res = ciop.publish(output_file, mode='silent', metalink=True) 
	#print 'result from publish string: ', res
	#subprocess.call(["ls","-l",res])
	subprocess.call(["ls","-l",output_file])
    except:
	print "unexpected error...exiting"




try:
    main()
except SystemExit as e:
    if e.args[0]:
        clean_exit(e.args[0])
    raise
#else:
#    atexit.register(clean_exit, 0)




#ciop.publish(outdef, metalink = true)        


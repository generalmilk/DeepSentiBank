import os,sys,json
import struct,time
import MySQLdb

from array import *
#sys.path.append('libsvm-3.18/python')
#from svmutil import *
from collections import OrderedDict 
import math

if __name__ == '__main__':
	t0 = time.time()
	#currentDir = os.getcwd()
	#os.chdir('deepsentibank')
	if len(sys.argv)<2:
		print  "This program takes one or multiple images as input, and output similar images.\nUsage: python getSimilar.py image_path/image_path_list.txt [similar_image_number] [post_ranking_ratio] [CPU/GPU] [DEVICE_ID=0]"
		exit()
	img_filename = sys.argv[1]
	sim_limit = 100
	if len(sys.argv)>2:
		sim_limit = int(sys.argv[2])
	ratio = '0.001'
	if len(sys.argv)>3:
		ratio = sys.argv[3]
	device = 'CPU'
	if len(sys.argv)>4 and sys.argv[4]=='GPU':
		device = 'GPU'
		if len(sys.argv)>5 and sys.argv[5].find('DEVICE_ID=')>-1:
			device = device + ' ' + sys.argv[5]				
	feature_num = 4096
	classes = json.load(open('classes_memex.json'))
	class_num = len(classes)
	testname = img_filename[:-4] + '-test.txt'
	protoname = img_filename[:-4] + '-test.prototxt'
	featurename = img_filename[:-4] + '-features'
	featurefilename = featurename+'_fc7.dat'
	outputname = img_filename[:-4] + '-sim_'+str(sim_limit)+'_'+ratio+'.json'
		
	if not os.path.exists(outputname):
		simname = featurename + '_fc7-sim_'+ratio+'.txt'

		f = open(testname,'w')
		if img_filename[-4:]=='.txt':
			ins_num = 0
			for line in open(img_filename):
				imgname = line.replace('\n','')
				if len(imgname)>2:
					ins_num = ins_num + 1
					f.write(imgname+' 0\n')
		else:
			f.write(img_filename+' 0')
			ins_num = 1
		f.close()
		if os.name=='nt':
			prefix = ''
		else:
			prefix = './'
		if not os.path.exists(featurefilename):


			batch_size = min(64,ins_num)
			iteration = int(math.ceil(ins_num/float(batch_size)))
			print 'image_number:', ins_num, 'batch_size:', batch_size, 'iteration:', iteration

			f = open('test.prototxt')
			proto = f.read()
			f.close()
			proto = proto.replace('test.txt',testname.replace('\\','/')).replace('batch_size: 1','batch_size: '+str(batch_size))
			f = open(protoname,'w');
			f.write(proto)
			f.close()
			command = prefix+'extract_nfeatures caffe_sentibank_train_iter_250000 '+protoname+ ' fc7,prob '+featurename.replace('\\','/')+'_fc7,'+featurename.replace('\\','/')+'_prob '+str(iteration)+' '+device;
			print command
			os.system(command)
			#os.system(prefix+'getBiconcept caffe_sentibank_train_iter_250000 '+protoname+ ' fc7 '+featurename.replace('\\','/')+'_fc7 1 CPU')
			#os.system(prefix+'getBiconcept caffe_sentibank_train_iter_250000 '+protoname+ ' prob '+featurename.replace('\\','/')+'_prob 1 CPU')

			os.remove(protoname)
		os.remove(testname)
		if not os.path.exists(simname):
			command = prefix+'hashing '+featurefilename + ' 256 '+ratio;
			print command
			os.system(command)
			os.rename(featurename + '_fc7-sim.txt',simname)
		
		#os.remove(probfilename.dat)
		#os.remove(featurefilename)
		#print prob,feature
		#os.system('cd ..')
		#os.chdir(currentDir)
		f = open(simname);
		sim =[]
		db=MySQLdb.connect(host='localhost',user='memex',passwd="darpamemex",db="imageinfo")
		c=db.cursor()
		sql='SELECT url,cached_url, page, cached_page, HT_idx, sha1 FROM urls2 WHERE idx in (%s) ORDER BY FIELD(idx, %s)' 

		count = 0
		for line in f:
			#sim_index.append([])
			nums=line.replace(' \n','').split(' ')
			
			n = min(sim_limit,len(nums))
			query_num = []
			for i in range(0,n):
				query_num.append(int(nums[i])+1)
			in_p=', '.join(map(lambda x: '%s', query_num))
			sqlq = sql % (in_p,in_p)
			
			c.execute(sqlq, query_num*2)
			sim.append(c.fetchall())
			count = count + 1
			if count == ins_num:
				break
		f.close()
		db.close()
		output = []
		for i in range(0,ins_num):	
			output.append(dict())
			output[i]['similar_images']= OrderedDict([['image_urls',[]],['cached_image_urls',[]],['page_urls',[]],['cached_page_urls',[]],['unique_ht_index',[]],['sha1',[]]])
			for simj in sim[i]:
				output[i]['similar_images']['image_urls'].append(simj[0])
				output[i]['similar_images']['cached_image_urls'].append(simj[1])
				output[i]['similar_images']['page_urls'].append(simj[2])
				output[i]['similar_images']['cached_page_urls'].append(simj[3])
				output[i]['similar_images']['unique_ht_index'].append(simj[4])
				output[i]['similar_images']['sha1'].append(simj[5])
		outp = OrderedDict([['number',ins_num],['images',output]])
		json.dump(outp, open(outputname,'w'),indent=4, sort_keys=False)		
 
	print 'query time: ', time.time() - t0
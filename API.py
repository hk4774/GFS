#!/usr/bin/env python


##############################################################################
#                        ################                                    #
#                        # API Version 1#                                    #
#                        ################                                    #
#This is the API version 1. It currently has the create, append, read, delete#
#and undelete functions. Open and close will be added if desired.            #
#file will be imported and called from a client file that the client can just#
#run.                                                                        #
##############################################################################


#import socket for connection, threading to make threads, time in case we want
#a delay, and config to keep the protocol standard.
import socket, threading, time, config, sys, logging
import functionLibrary as fL



###############################################################################

#               Verbose (Debug) Handling                                      #

###############################################################################


# Setup for having a verbose mode for debugging:
# USAGE: When running program, $python API.py , no debug message will show up
# Instead, the program should be run in verbose, $python API.py -v , for debug 
# messages to show up

# Get a list of command line arguments
args = sys.argv
# Check to see if the verbose flag was one of the command line arguments
if "-v" in args:
        # If it was one of the arguments, set the logging level to debug 
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s : %(message)s')
else:
        # If it was not, set the logging level to default (only shows messages with level
        # warning or higher)
        logging.basicConfig(filename='apiLog.log', format='%(asctime)s %(levelname)s : %(message)s')








class API():

	#lets define some variables
	global MASTER_ADDRESS
	global TCP_PORT
	MASTER_ADDRESS = config.masterip
	TCP_PORT = config.port

	#lets make the API able to send and recieve messages
	m = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 	
	m.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	try:
		m.connect((MASTER_ADDRESS, TCP_PORT))
	except:
		print "ERROR: COULD NOT CONNECT TO MASTER"
		exit(0)

	#lets make some methods
	
	#creates a file by first sending a request to the master. Then the 
	#master will send back a chunk handle followed by three locations in
	#which to create this chunk handle. the client then sends the chunk 
	#handle to the three locations (which are chunk servers) along with
	#the data "makeChunk". The chunkservers then make an empty chunk at
	#each of those locations. Takes the filename as an arguement.
	def create(self,filename):
		#send a CREATE request to the master
		try:
			fL.send(self.m, "CREATE|" + filename)
		except: 
			print "ERROR: COULD NOT SEND CREATE REQUEST TO MASTER"
		#receive data back from the master 
		self.data = fL.recv(self.m)
		#error if the file trying to be created already exists 
		if self.data == "FAIL1":
			print "THAT FILE EXISTS ALREADY... EXITING API"
			exit(0)
		elif self.data == "FAIL2":
			print "NO SUCH FILE EXISTS FOR CHUNK CREATION"
			exit(0)
		elif self.data == "FAIL3":
			print "CHUNK IS NOT THE LATEST CHUNK"
			exit(0)
		print self.data
		#parse the received data into locations, and chunk handle
		self.splitdata = self.data.split("|")
		dataLength = len(self.splitdata)
		cH = self.splitdata[-1]
		#close the connection to the master so we can connect to the chunk servers
		self.m.close()
		#iterate through each IP address received from the master
		for n in range(0, dataLength-1):
			#create a socket to be used to connect to chunk server
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			#designate the IP for this iteration
			location = self.splitdata[n]
			print location
			#attempt to connect to the chunk server at the current location
			try:
				s.connect((location,TCP_PORT))
                	except: 
				print "ERROR: COULD NOT CONNECT TO CHUNKSERVER AT ", location
				continue
			#send CREATE request to the chunk server at the current location
			fL.send(s, "CREATE|" + cH)
                	print "CREATE"
			#wait to receive a CONTINUE from chunk server to proceed
                	global ack
			ack = fL.recv(s)
			#close connection to current chunk server.
		s.close()
			#reestablish connection to master
		m = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			m.connect((MASTER_ADDRESS, TCP_PORT))
		except:
			print "COULD NOT RECONNECT TO MASTER"
			exit(0)
		if ack == "FAILED":
                	print "ERROR: FILE CREATION FAILED"
			fL.send(m, "FAILED")
                elif ack == "CREATED":
                	print "File creation successful!"
			fL.send(m, "CREATED")
		
		#oplog stuff for questions contact rohail
	#	try:
	#		opLog = updateOpLog("OPLOG|CREATE|"+cH+"|"+filename)
	#		opLog.start()
	#	except:
	#		print "COULD NOT UPDATE OPLOG"

	
	#appends to an existing file by first prompting the client for what 
	#new data they would like to add to the file (the filename is given 
	#as an arg). The API sends append and the filename to the master which
	#sends back the chunk handle and locations of the existing file. The 
	#client then sends "append" and the new data to the chunk servers which
	#append the new data to the files.
	def append(self, filename, newData):

		self.m.close()
		#send APPEND request to master
		try:
			self.m = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.m.connect((MASTER_ADDRESS, TCP_PORT))

			fL.send(self.m, "APPEND|" + filename)
		except:
			print "COULD NOT SEND APPEND REQUEST TO MASTER"
		#receive data back from master
		self.data = fL.recv(self.m)
		print self.data
		#parse the data into useful parts
		self.splitdata = self.data.split("|")
		dataLength = len(self.splitdata)
                cH = self.splitdata[-1]
		#get length of the requested new data to use for append across chunks
		lenNewData = len(newData)
		#close connection to master 
        	self.m.close()
	        for n in range(0, dataLength-1):
			#create socket to connect to chunk server at location
			self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        location = self.splitdata[n]
	                #attempt to connect to chunk server at location
			try:
				self.s.connect((location,TCP_PORT))
                	except:
				print "ERROR: COULD NOT CONNECT TO CHUNK SERVER AT ", location
			#ask chunk server how much room is left on latest chunk
			fL.send(self.s, "CHUNKSPACE?|" + cH)
			#the response is stored in dat
			remainingSpace = fL.recv(self.s)
			remainingSpace = int(remainingSpace)
			print lenNewData
			print remainingSpace
			#if the length of the new data is greater than the room left in the chunk...
			if (lenNewData > remainingSpace):   
				#...split the data into two parts, the first part being equal to the
				#amount of room left in the current chunk. the second part being the 
				#rest of the data. 
                                newData1 = newData[0:remainingSpace]
				print newData1
                                newData2 = newData[remainingSpace:]
				print newData2
				#tell the chunk server to append the first part of the new data that
				#will fill up the rest of the remaining space on a chunk
				self.s.close()
				s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				try:
					s.connect((location, TCP_PORT))
				except:
					print "ERROR: COULD NOT REOPEN SOCKET"
				fL.send(s, "APPEND|" + cH + "|" + newData1)
				print "first append"
				#close connection to chunk server
				s.close()
				#connect back to the master
				'''m  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				try:
					m.connect((MASTER_ADDRESS, TCP_PORT))
				except:
					print "ERROR: COULD NOT CONNECT TO MASTER DURING APPEND ACROSS CHUNKS"
                			exit(0)'''
			elif (lenNewData <= remainingSpace):
				self.s.close()
				t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				t.connect((location, TCP_PORT))
				try:
					fL.send(t, "APPEND|" + cH + "|" + newData)
				except:
					print "ERROR: COULD NOT SEND APPEND TO CHUNK SERVER"			

		if lenNewData > remainingSpace:
			m  = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        try:
                        	m.connect((MASTER_ADDRESS, TCP_PORT))
				print "connected to master"
                        except:
                                print "ERROR: COULD NOT CONNECT TO MASTER DURING APPEND ACROSS CHUNKS"
                                exit(0)
			#tell the master to create a new chunk for the remaining data
			try:
				fL.send(m, "CREATECHUNK|" + filename + "|" + cH)
			except:
				print "ERROR: COULD NOT CREATE NEW CHUNK TO APPEND TO"
			#receive data back from master
			cData = fL.recv(m)
			#parse this data and handle it very similarly as the in the create function
			
			splitcData = cData.split("|")
			cDataLength = len(splitcData)
                	cH = splitcData[-1]
                	#close the connection to the master so we can connect to the chunk servers
                	m.close()
                	#iterate through each IP address received from the master
                	for n in range(0, cDataLength-1):
                        	#create a socket to be used to connect to chunk server
                        	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        	#designate the IP for this iteration
                        	location = splitcData[n]
                        	print location
                        	#attempt to connect to the chunk server at the current location
                        	try:
                                	s.connect((location,TCP_PORT))
                        	except:
                                	print "ERROR: COULD NOT CONNECT TO CHUNKSERVER AT ", location
                                	continue
                        	#send CREATE request to the chunk server at the current location
                        	fL.send(s, "CREATE|" + cH)
			
			#now that the new chunk has been created on all of the servers...
			#...run append again with the second part of the new data
			self.s.close()
			self.append(filename, newData2)
					


	#reads an existing file by taking the filename, byte offset, and the number of bytes the client
	#wants to read as args. This information is passed on to the master which sends back a list
	#where every element is a list. The outer list is a list of all the chunks that one copy of 
	#the file is on and the inner lists are the locations of each chunk and har far to read on
	#that chunk. I then pass on the necessary data to the chunk servers which send me back the
	#contents of the file. 
	def read(self, filename, byteOffset, bytesToRead):
		#send READ request to the master
		try:
			fL.send(self.m, "READ|" + filename + "|" + str(byteOffset) + "|" + str(bytesToRead))
		except:
			print "ERROR: COULD NOT SEND READ REQUEST TO MASTER"
		#recieve data from the master
		self.data = fL.recv(self.m)
		print self.data
		#split the data into a list
		self.splitdata = self.data.split("|")
		#remove the first element of the list because it is irrelevant
		self.splitdata = self.splitdata[1:]
		print self.splitdata
		#iterate through the list
		for q in self.splitdata:
			#split the list into smaller parts
			secondSplit = q.split("*")
			print secondSplit
			#set the location...
			location = secondSplit[0]
			print "location = ", location
			#...and the chunk handle
			cH = secondSplit[1]
			print "cH = ", cH
			#...and the offset
			offset = secondSplit[2]
			print "offset = ", offset
			#close connection to master
			self.m.close()
			#connect to the chunk server
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			try:
				s.connect((location,TCP_PORT))
			except:
				print "ERROR: COULD NOT CONNECT TO CHUNK SERVER AT ", location
				continue
			#send READ request to chunk server
                	fL.send(s, "READ|" + cH + "|" + offset + "|" + bytesToRead)
                	print "READ|" + cH + "|" + offset + "|" + bytesToRead
			#receive and print the contents of the file
                	dat = fL.recv(s)
                	print dat
		
		#close connection to chunk server		
               	s.close()
		#reestablish connection to master
                m = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
			m.connect((MASTER_ADDRESS, TCP_PORT))
		except:
			print "COULD NOT RECONNECT TO MASTER"
			exit(0)

	#This is the delete function. It takes a filename as a parameter and 
	#deletes the given file from our GFS implementation. When a DELETE 
	#request is sent to the master it marks the file for deletion. The 
	#next time the garbage collector runs it will remove any marked files
	def delete(self, filename):
		#send DELETE request to the master
		try:
			fL.send(self.m, "DELETE|" + filename)
		except:
			print "ERROR: COULD NOT SEND DELETE REQUEST TO MASTER"
		#receive acks from the master
		self.data = fL.recv(self.m)
		#tell the user whether the file was successfully marked or not
		if self.data == "FAILED":
			print "ERROR: COULD NOT MARK FILE FOR DELETION"
		elif self.data == "MARKED":
			print "File successfully marked for deletion."

	
	#This is the undelete function. It takes a filename as a parameter and 
	#if that file is marked for deletion, and the garbage collector has not 
	#removed it yet, the file will be unmarked and safe from deletion.
	def undelete(self, filename):
		#send UNDELETE request to master
		try:
			fL.send(self.m, "UNDELETE|" + filename)
		except:
			print "ERROR COULD NOT SEND UNDELETE REQUEST TO MASTER"
		#receive acks from the master
		self.data = fL.recv(self.m)
		#tell the user whether the file was successfully unmarked or not
		if self.data == "FAILED":
			print "ERROR: COULD NOT UNDELETE FILE"
		elif self.data == "MARKED":
			print "File successfully unmarked for deletion."
		
	

	#I have no idea what this is but I wrote an exception for it
	def fileList(self):
		try:
			fL.send(self.m, "FILELIST|x")
			self.data = fL.recv(s)
			return self.data
		except:
			print "file list error"


#oplog stuff. for questions contact rohail
class updateOpLog(threading.Thread):
        def __init__(self, message):
                threading.Thread.__init__(self)
                self.m = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.message = message

        def run(self):
                self.m.connect((MASTER_ADDRESS,TCP_PORT))
                fL.send(self.m, self.message)
		print "opLog message sent"




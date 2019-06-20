#Created by Pajtim Krasniqi
import os, sys
import json
import time
import socket
import fcntl
import struct


""" Required for RTSP Server """
#from threading import Thread
import threading

from time import sleep
import signal

import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstRtsp", "1.0")
gi.require_version("GstRtspServer", "1.0")
from gi.repository import GLib, GObject, Gst, GstRtsp, GstRtspServer
""" Required for RTSP Server """


# Change the audio node for usb sound card
# eg device=hw:0   or device=hw:2
AUDIO_DEVICE = "device=hw:1"
IFACE_NAME = "wlan0"



class RTSPServerThread ( threading.Thread ):

    def __init__ ( self,loop):
        
        self.loop = loop
        
        self._stopevent = threading.Event( )
        self._sleepperiod = 1.0
        threading.Thread.__init__ ( self )


    """ Run Method keep runnin in Background and pooling for data """
    def run ( self ):
        print ("Starting RTSPServerThread !!!")
        while not self._stopevent.isSet( ):
            
            self.loop.run()
            self._stopevent.wait(self._sleepperiod)
        

        print ("RTSPServerThread %s ends" % self.getName())
        
    def join(self, timeout=None):
        """ Stop the thread and wait for it to end. """
        self._stopevent.set( )
        threading.Thread.join(self, timeout)





class Client:

    def __init__(self):

        # local host IP '127.0.0.1' 
        self.host = ''
      
        # Define the port on which you want to connect 
        self.port = 1234

        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

        self.connection = None
        self.client_address  = None


        """ Variable for rtsp server """
        self.loop = None
        self.PIPELINE = ("( alsasrc "+str(AUDIO_DEVICE)+" ! audioconvert ! audioresample  ! alawenc ! rtppcmapay name=pay0 pt=10 )")

        """ Variable for rtsp client """
        self.player = None

        
    ''' Util fuction to find the IP Address '''
    def getIPAddress(self,ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(),0x8915,struct.pack('256s', ifname[:15]))[20:24])


    def startServer(self):
        """ Open Socket in port 1234 and listen for incoming connection """

        #print('IP %s' % str(self.getIPAddress("wlan0")))
        
        # Bind the socket to the address given on the command line
        self.server_address = ('', self.port)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.server_address)
        
        print('Starting Raspberry Pi Client on %s port 1234' % self.getIPAddress(str(IFACE_NAME)))
        self.sock.listen(1)

        print('waiting for a connection')
        self.connection, self.client_address = self.sock.accept()

        try:
            print('client connected:', self.client_address)
            while True:
                data = self.connection.recv(4096)
                data = data.decode('ascii').replace('\n', '')
                data = data.decode('ascii').replace('\r', '')
                
                if not data:
                    break

                self.handleRequest(data)
        finally:
            self.connection.close()
            
        print("Quitting RPI Client")
        self.sock.close()
        


    '''
    This fuction parse the request received and take the action
    Request-1
    {"MSG_TYPE":"START_RTSP_SERVER","ID":"1"}
    {"MSG_TYPE":"START_RTSP_SERVER", "STATUS":"SUCCESS" , "URL":"rtsp://192.168.1.2/rpi1"}
    {"MSG_TYPE":"START_RTSP_SERVER", "STATUS":"FAILED"} 


    Request-2
    {"MSG_TYPE":"START_RTSP_CLIENT", "URL":"rtsp://192.168.1.2/rpi1"}
    {"MSG_TYPE":"START_RTSP_CLIENT", "STATUS":"SUCCESS" }
    {"MSG_TYPE":"START_RTSP_CLIENT", "STATUS":"FAILED"} 

    Request-3
    {"MSG_TYPE":"STOP_RTSP_CLIENT"}
    {"MSG_TYPE":"STOP_RTSP_CLIENT", "STATUS":"SUCCESS" }
    {"MSG_TYPE":"STOP_RTSP_CLIENT", "STATUS":"FAILED"} 

    Request-4
    {"MSG_TYPE":"STOP_RTSP_SERVER"}
    {"MSG_TYPE":"STOP_RTSP_SERVER", "STATUS":"SUCCESS" }
    {"MSG_TYPE":"STOP_RTSP_SERVER", "STATUS":"FAILED"}
    
    '''
    def handleRequest(self,data):

        recv_data = json.loads(data)
        
        if recv_data["MSG_TYPE"] == "START_RTSP_SERVER":
            ID = recv_data["ID"]
            print("Got START_RTSP_SERVER for ID",ID)

            result = self.startRTSPServer(ID)

            my_json_string = json.dumps({"MSG_TYPE":"START_RTSP_SERVER","STATUS":"SUCCESS","URL":str(result)})            
            my_json_string = my_json_string + "\n"
            print("Sending Msg = %s"%my_json_string)
            self.connection.send(my_json_string.encode('ascii'))

     
            
        elif recv_data["MSG_TYPE"] == "START_RTSP_CLIENT":
            url = recv_data["URL"]
            print("Got START_RTSP_CLIENT for URL",url)

            result = self.startRTSPClient(url)
            
            my_json_string = json.dumps({"MSG_TYPE":"START_RTSP_CLIENT","STATUS":"SUCCESS"})            
            my_json_string = my_json_string + "\n"
            print("Sending Msg = %s"%my_json_string)
            self.connection.send(my_json_string.encode('ascii'))


            
        elif recv_data["MSG_TYPE"] == "STOP_RTSP_CLIENT":
            print("Got STOP_RTSP_CLIENT")

            result = self.stopRTSPClient()
            
            my_json_string = json.dumps({"MSG_TYPE":"STOP_RTSP_CLIENT","STATUS":"SUCCESS"})            
            my_json_string = my_json_string + "\n"
            print("Sending Msg = %s"%my_json_string)
            self.connection.send(my_json_string.encode('ascii'))

        elif recv_data["MSG_TYPE"] == "STOP_RTSP_SERVER":
            print("Got STOP_RTSP_SERVER")
            
            result = self.stopRTSPServer()

            my_json_string = json.dumps({"MSG_TYPE":"STOP_RTSP_SERVER","STATUS":"SUCCESS"})            
            my_json_string = my_json_string + "\n"
            print("Sending Msg = %s"%my_json_string)
            self.connection.send(my_json_string.encode('ascii'))            

    
    '''
    Start the RTPS Server
    Deligate a thread for controlling server.
    '''
    def startRTSPServer(self, ID):


        GObject.threads_init()
        Gst.init(None)

        server = GstRtspServer.RTSPServer.new()
        server.props.service = "3001"

        server.attach(None)
        self.loop = GLib.MainLoop.new(None, False)
            
        self.RTSPServerThreadID = RTSPServerThread(self.loop)
        self.RTSPServerThreadID.start()

        
        media_factory = GstRtspServer.RTSPMediaFactory.new()
        media_factory.set_launch(self.PIPELINE)
        media_factory.set_shared(True)
        
        index = "/rpi"+str(ID)
        server.get_mount_points().add_factory(index, media_factory)

        url = "rtsp://"+self.getIPAddress(str(IFACE_NAME))+":3001"+str(index)
        print("Stream ready at rtsp://"+self.getIPAddress(str(IFACE_NAME))+":3001"+index)
        return url
    

    def stopRTSPServer(self):

        print("In stopRTSPServer")

        if self.loop is not None:
            self.loop.quit()
            self.RTSPServerThreadID.join(0.5)
            self.loop = None
            return 0
        return -1


    def startRTSPClient(self, url):

        result = 0
        self.player = Gst.ElementFactory.make('playbin', 'player')
        try:
            # alsasink pulsesink osssink autoaudiAosink
            alsasink_dev = "alsasink " + str(AUDIO_DEVICE)
            device = Gst.parse_launch(alsasink_dev)
        except GObject.GError:
            print ('Error: could not launch audio sink')
            result = -1
        else:
            self.player.set_property('audio-sink', device)
        
        if result == -1:
            return -1

        self.bus = self.player.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message', self.on_message)

        self.player.set_property('uri', url)
        self.player.set_state(Gst.State.PLAYING)

        return 0


    def stopRTSPClient(self):
        result = -1

        if self.player is not None:
            self.player.set_state(Gst.State.NULL)
            result = 0

        return result;


    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.player.set_state(Gst.State.NULL)
        elif t == Gst.MessageType.ERROR:
            self.player.set_state(Gst.State.NULL)
            err, debug = message.parse_error()
            print ('Error: %s' % err, debug)


''' main fucntion of class '''    
def main():
    mClient = Client()
    mClient.startServer()
    

if __name__=="__main__":
    main()

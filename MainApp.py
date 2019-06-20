#Created by Pajtim Krasniqi
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Import the modules needed to run the script.
import sys, os
import socket
import time
import fcntl
import struct
import json

# Main definition - constants

IFACE_NAME = "wlan0"


class App:

    def __init__(self):

        # local host IP '127.0.0.1' 
        self.mSock1=None
        self.mSock2=None


    # Main menu
    def mainMenu(self):
        #os.system('clear')
        
        print("Usage: stream <option > <argument 1> <argument 2>")
        print("       q - Quit\n")
        print("option: \n\t stop - stop the running stream")
        print("argument: \n\t IP:Port - Remote Machine IP Address Port")
        print("\t local - For local machine\n")
        print("example:")
        print("\tstream 192.168.1.100:1234 192.168.1.101:1234")
        print("\tstream 192.168.1.100:1234 local")
        print("\tstream stop\n")

        choice = ""
        while choice != 'q':
            choice = raw_input(" >>  ")
            #print(choice)
            self.exec_menu(choice)
            
        return


    ''' Util fuction to find the IP Address '''
    def getIPAddress(self):
        iface = str(IFACE_NAME)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(),0x8915,struct.pack('256s', iface[:15]))[20:24])

    # Execute menu
    def exec_menu(self, choice):
        #os.system('clear')
        ch = choice.lower()

        ip_1 = None
        ip_2 = None
        
        port_1 = None
        port_2 = None
        if "stream stop" in ch:
    ##        print("CMD Stop Stream");

            status = 0
            res = self.sendStopRTSPClient(self.mSock1)
            if res < 0:
                status = -1
                print("Failed to Stop RTSP Client#1")

            res = self.sendStopRTSPClient(self.mSock2)
            if res < 0:
                status = -1
                print("Failed to Stop RTSP Client#2")

            res = self.sendStopRTSPServer(self.mSock1)
            if res < 0:
                status = -1
                print("Failed to Stop RTSP Server#1")

            res = self.sendStopRTSPServer(self.mSock2)
            if res < 0:
                status = -1
                print("Failed to Stop RTSP Server#2")
                

            if status ==0:
                print("Communication Closed Successfully !!!")
            else:
                print("Failed to Closed Connection !!!")



        elif "stream" in ch:
    ##        print("CMD Start Stream");
            args=ch.split(" ")

            if len(args) != 3:
                print("Invalid Argument")
                return
            else:

                error = 1

                if args[1] == "local":
                    # resolve the IP/Port for this Server
                    error = error - 1
                    ip_1 = self.getIPAddress()
                    port_1 = "1234"
                    print(" Local #1 IP = "+ip_1+" Port = "+port_1);
                else:
                    remote_param_1 = args[1].split(":")
                    ip_1 = remote_param_1[0]
                    port_1 = remote_param_1[1]
                    print(" Remote #1 IP = "+ip_1+" Port = "+port_1);
                    


                if args[2] == "local":
                    # resolve the IP/Port for this Server
                    error = error - 1
                    ip_2 = self.getIPAddress()
                    port_2 = "1234"
                    print(" Local #2 IP = "+ip_2+" Port = "+port_2);
                else:
                    remote_param_2 = args[2].split(":")
                    ip_2 = remote_param_2[0]
                    port_2 = remote_param_2[1]
                    print(" Remote #2 IP = "+ip_2+" Port = "+port_2);


                if error < 0:
                    print('Invalid local local Argument')
                    return


                self.mSock1 = self.connectToServer(ip_1,port_1)
                if self.mSock1 < 0:
                    print("Failed to connect to Server IP:"+ip_1+" Port:"+port_1)
                    return

                self.mSock2 = self.connectToServer(ip_2,port_2)
                if self.mSock2 < 0:
                    print("Failed to connect to Server IP:"+ip_2+" Port:"+port_2)
                    self.closeConnectionToServer(self.mSock1)
                    return

                url1 = self.sendStartRTSPServer(self.mSock1,1)
                if url1 == None:
                    print("Failed to Start RTSP Server IP:"+ip_1+" Port:"+port_1)
                    self.closeConnectionToServer(self.mSock1)
                    self.closeConnectionToServer(self.mSock2)
                    return

                url2 = self.sendStartRTSPServer(self.mSock2,2)
                if url2 == None:
                    print("Failed to Start RTSP Server IP:"+ip_2+" Port:"+port_2)
                    self.sendStopRTSPServer(self.mSock1)
                    self.closeConnectionToServer(self.mSock1)
                    self.closeConnectionToServer(self.mSock2)
                    return

                ret = self.sendStartRTSPClient(self.mSock2,url1)
                if ret < 0:
                    print("Failed to Start RTSP Client IP:"+ip_2+" Port:"+port_2)
                    self.sendStopRTSPServer(self.mSock1)
                    self.sendStopRTSPServer(self.mSock2)

                    self.closeConnectionToServer(self.mSock1)
                    
                    self.closeConnectionToServer(self.mSock2)

                    return

                ret = self.sendStartRTSPClient(self.mSock1,url2)
                if ret < 0:
                    print("Failed to Start RTSP Client IP:"+ip_1+" Port:"+port_1)
                    self.sendStopRTSPClient(self.mSock2)

                    self.sendStopRTSPServer(self.mSock1)
                    self.sendStopRTSPServer(self.mSock2)

                    self.closeConnectionToServer(self.mSock1)
                    self.closeConnectionToServer(self.mSock2)

                    return

                print("Communication Established Successfully !!!")

        elif ch != 'q':
                print("Invalid Argument. Try Again")

        return



    def connectToServer(self,ip,port):

            sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            #self.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            # connect to remote machine 
            sock.connect((str(ip),int(port)))

            return sock;
        

    def closeConnectionToServer(self,sock):
            if sock:
                sock.close()

        
    def sendStartRTSPServer(self, sock, ID):

        my_json_string = json.dumps({"MSG_TYPE":"START_RTSP_SERVER","ID":str(ID)})            
        my_json_string = my_json_string + "\n"
        print("Sending Msg = %s"%my_json_string)
        sock.send(my_json_string.encode('ascii'))

        data = sock.recv(4096)
        data = data.decode('ascii').replace('\n', '')
        data = data.decode('ascii').replace('\r', '')
        recv_data = json.loads(data)
        
        if recv_data["MSG_TYPE"] == "START_RTSP_SERVER":
            status = recv_data["STATUS"]

            if status == "SUCCESS":
                url = recv_data["URL"]
                print('URl ' , url)
                return url
            else:
                return None
            
        return None 


    def sendStopRTSPServer(self, sock):

        my_json_string = json.dumps({"MSG_TYPE":"STOP_RTSP_SERVER"})            
        my_json_string = my_json_string + "\n"
        print("Sending Msg = %s"%my_json_string)
        sock.send(my_json_string.encode('ascii'))

        data = sock.recv(4096)
        data = data.decode('ascii').replace('\n', '')
        data = data.decode('ascii').replace('\r', '')
        recv_data = json.loads(data)
        
        if recv_data["MSG_TYPE"] == "STOP_RTSP_SERVER":
            status = recv_data["STATUS"]

            if status == "SUCCESS":
                print('Stop Successful ')
                return 0
            else:
                return -1
            
        return -1

            

    def sendStartRTSPClient(self, sock, url):

        my_json_string = json.dumps({"MSG_TYPE":"START_RTSP_CLIENT","URL":str(url)})            
        my_json_string = my_json_string + "\n"
        print("Sending Msg = %s"%my_json_string)
        sock.send(my_json_string.encode('ascii'))

        data = sock.recv(4096)
        data = data.decode('ascii').replace('\n', '')
        data = data.decode('ascii').replace('\r', '')
        recv_data = json.loads(data)
        
        if recv_data["MSG_TYPE"] == "START_RTSP_CLIENT":
            status = recv_data["STATUS"]

            if status == "SUCCESS":
                
                print('Client Started at ' , url)
                return 0
            else:
                return -1
            
        return -1


    def sendStopRTSPClient(self, sock):

        my_json_string = json.dumps({"MSG_TYPE":"STOP_RTSP_CLIENT"})            
        my_json_string = my_json_string + "\n"
        print("Sending Msg = %s"%my_json_string)
        sock.send(my_json_string.encode('ascii'))

        data = sock.recv(4096)
        data = data.decode('ascii').replace('\n', '')
        data = data.decode('ascii').replace('\r', '')
        recv_data = json.loads(data)
        
        if recv_data["MSG_TYPE"] == "STOP_RTSP_CLIENT":
            status = recv_data["STATUS"]

            if status == "SUCCESS":
                print('Stop Successful ')
                return 0
            else:
                return -1
            
        return -1



# Exit program
def exit():
    sys.exit()


# Main Program
if __name__ == "__main__":
    # Launch main menu
    mApp = App()
    mApp.mainMenu()


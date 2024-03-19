"""Small example OSC server

This program listens to several addresses, and prints some information about
received packets.
"""
import argparse
import math
import socketserver, socket
from datetime import datetime
from pythonosc import dispatcher
from pythonosc.osc_message import OscMessage
from pythonosc import osc_server
from firebase import firebase
from threading import Thread

global dispatcher 
global TCP_TIMEOUT

TCP_TIMEOUT = 0.15
# tradeoff here is possibility of dropping data during congestion
# really we should be streaming out commands as they come in. 
#

def fb_callback(result):
    print("fb async return",result)
    
def fwd(addr, *args):
    print("\n-----", datetime.today().strftime('%y-%m-%d %H:%M:%S'))
    print("  ",addr)
    print("    key:  ",args[0])
    if len(args)>1: 
        print("    value:",args[1:])

    result = []
    if (addr).endswith("/kvproperty"): 
        if (len(args) % 2) == 1: 
            print("  setting trailing null value to empty string")
            args=list(args).append("")
        for i in range(0,len(args),2):
            print("     ", args[i],args[i+1])
            firebase.put_async(addr, args[i], args[i+1], params={'print': 'pretty'}, headers={'X_FANCY_HEADER': 'VERY FANCY'},callback=fb_callback)
    else: # if (addr).endswith("/method") or (addr).endswith("/childmethod") or (addr).endswith("/event"):
        result = firebase.post_async(addr, args, params={'print': 'pretty'}, headers={'X_FANCY_HEADER': 'VERY FANCY'},callback=fb_callback)


## Experimental TCP support tested with QLab 5

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def process(self, d): 
        if len(d)==0 or d==b'': return
        #print("handle tcp stream",d)
        try: 
        	msg = OscMessage(d) #strip intro byte?  
        	dispatcher.call_handlers_for_packet(d,self.client_address)              
        except Exception as e:
          print(str(e))
          
    def handle(self):
        data = b''
        log = b'' 
        self.request.settimeout(TCP_TIMEOUT) 
        while True:
          try: 
            _data = self.request.recv(1024)  # accept until connection closed - need to handle streaming?
            if not _data: break 
            data += _data
            log += _data
            msgs = data.split(b'\xc0') 
            if msgs[-1] == b'': 
                for msg in msgs: self.process(msg) 
                data = b''
            else:
                for msg in msgs[:-1]: self.process(msg) 
                data = msg+b'\xc0'  # more efficient way? 
          except socket.timeout:
          	#print("tcp socket timeout") 
            break 
 #       data = data.strip()
 
        for msg in data.split(b'\xc0'): 
        	self.process(msg) 
            
        print("\nfinished tcp {}:".format(self.client_address[0]), log)
  
 
## Forward 

if __name__ == "__main__":

  firebase = firebase.FirebaseApplication('https://oscforwarder-default-rtdb.firebaseio.com/', None)
  
  parser = argparse.ArgumentParser()
  parser.add_argument("--ip",
      default="", help="The ip to listen on")
  parser.add_argument("--port",
      type=int, default=8090, help="The port to listen on")

  args = parser.parse_args()

  dispatcher = dispatcher.Dispatcher()
  dispatcher.map("*", fwd)


  tcpserver = ThreadedTCPServer((args.ip, args.port), ThreadedTCPRequestHandler)
  print("(Experimental) Awaiting tcp connections on {}".format(tcpserver.server_address))
  tcpserver_thread = Thread(target=lambda:tcpserver.serve_forever())
  tcpserver_thread.start() 

    
  udpserver = osc_server.ThreadingOSCUDPServer(
      (args.ip, args.port), dispatcher)
  print("Awaiting udp on {}".format(udpserver.server_address))
  
  try: 
    udpserver.serve_forever()
  except KeyboardInterrupt:
    tcpserver.shutdown()  # simple way
    

  



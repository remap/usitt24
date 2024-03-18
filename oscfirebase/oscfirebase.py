"""Small example OSC server

This program listens to several addresses, and prints some information about
received packets.
"""
import argparse
import math
import socketserver
from datetime import datetime
from pythonosc import dispatcher
from pythonosc.osc_message import OscMessage
from pythonosc import osc_server
from firebase import firebase
from threading import Thread

global dispatcher 
def fwd(addr, *args):
    print("\n-----", datetime.today().strftime('%y-%m-%d %H:%M:%S'))
    print("  addr",addr)
    print("    key  ",args[0])
    if len(args)>1: 
        print("    value",args[1:])

    result = []
    if (addr).endswith("/kvproperty"): 
        if (len(args) % 2) == 1: 
            print("  setting trailing null value to empty string")
            args=list(args).append("")
        for i in range(0,len(args),2):
            print("     ", args[i],args[i+1])
            result.append(firebase.put(addr, args[i], args[i+1], params={'print': 'pretty'}, headers={'X_FANCY_HEADER': 'VERY FANCY'}))
    else: # if (addr).endswith("/method") or (addr).endswith("/childmethod") or (addr).endswith("/event"):
        result = firebase.post(addr, args, params={'print': 'pretty'}, headers={'X_FANCY_HEADER': 'VERY FANCY'})
    print("    returned",result)

## Experimental TCP support tested with QLab 5

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request.recv(2048).strip()
        try: 
          data = data[1:-1]
          print("\ntcp {}:".format(self.client_address[0]),data)
          msg = OscMessage(data) #strip intro byte?  
          dispatcher.call_handlers_for_packet(data,self.client_address)
        except:
          print("\nexception in tcp handling")
 #        response = data  # This could be modified to your needs.
#         self.request.sendall(response)

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
    

  



"""Small example OSC server

This program listens to several addresses, and prints some information about
received packets.
"""
import argparse
import math
from datetime import datetime
from pythonosc import dispatcher
from pythonosc import osc_server

from firebase import firebase


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

  server = osc_server.ThreadingOSCUDPServer(
      (args.ip, args.port), dispatcher)
  print("Serving on {}".format(server.server_address))
  server.serve_forever()
#/usr/bin/env python
#coding=utf-8

'''
Created on 2014年11月28日

@author: liangc
'''
from EmsgClient import Client
import time,uuid

host = "127.0.0.1"
port = 4222

class Conn:
    def __init__(self,i):
        client = Client(host, port)
        client.setHeartBeat(50)
        client.setListener(self.callback)
        jid = "pycli%s@test.com" % i
        print jid
        client.auth(jid, "123")
        self.client = client
    
    def getClient(self):
        return self.client
        
    def callback(self,packet):
        print 'callback' + packet

if __name__ == '__main__':
    cl = []
    for i in range(0,1):
        conn = None
        del conn
        conn = Conn(i)
        cl.append(conn)
    print 'watt .......... %s ' % cl
    time.sleep(2)
    
    while True :
        for c in cl :
            c.getClient().sendMessage(to="%s@test.com" % 'foobar',content="hello world.")
        time.sleep(10000)


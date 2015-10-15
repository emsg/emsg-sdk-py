#/usr/bin/env python
#coding=utf-8
'''
Created on 2014年11月27日
@author: liangc (email: cc14514@icloud.com)
'''
import sys
import socket, json, uuid, Queue,threading,time,traceback



class Client:
    
#     addr = ("127.0.0.1",4222)
#     mySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     callback = None
#     reconnectQueue = Queue.Queue(1)
#     heartBeatQueue = Queue.Queue(3)
#     readerQueue = Queue.Queue(1024)
#     writerQueue = Queue.Queue(1024)
#     isClose = True
#     isAuth = False
#     jid = None
#     pwd = None    
#     heartbeat = 30
    
    def __init__(self,host,port):
        self.addr = (host,port)
        self.mySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.reconnectQueue = Queue.Queue(1)
        self.heartBeatQueue = Queue.Queue(3)
        self.readerQueue = Queue.Queue(1024)
        self.writerQueue = Queue.Queue(1024)
        
    def setHeartBeat(self,beat_time=30):    
        ''' 设置心跳间隔时间，单位秒，默认30秒 '''
        self.heartbeat=beat_time
        
    def setListener(self,callback):
        self.callback = callback
    
    def letReconnect(self,who):
        ''' 发送重连的指令 '''
        try:
            self.reconnectQueue.put(who, timeout=0)
        except:
            pass
    def ioListiner(self):
        ''' 对链接进行初始化，启动收发线程来监听各自的缓冲区队列 '''
        def listener_heartBeat():
            '''
            处理心跳的线程
            '''
            try:
                while True:
                    if self.isAuth :
                        packet = '\02'
                        self.writerQueue.put(packet,timeout=0)
                        self.heartBeatQueue.put(packet,timeout=0)
                        time.sleep(self.heartbeat)
                    else :
                        time.sleep(2)
            except:
                self.letReconnect('heartBeat')
            
        def listener_reader():
            '''
            处理读的线程
            '''
            try:
                part = ''
                while True:
                    data = self.mySocket.recv(1024)
                    if data :
                        arr = data.split('\01'.encode('utf-8'))
                        print 'len=%s ; recv=%s' % (len(arr),data)
                        if len(arr) == 1:
                            pass
                        else :
                            first = arr[0]
                            first = part+first
                            last = part + arr[-1:][0]
                            if not last:
                                part+=last
                                print 'recv part=%s' % part
                            print 'readerQueue.put first=%s' % first
                            self.readerQueue.put(first)
                            for packet in arr[1:-1]:
                                self.readerQueue.put(packet)
                    else :
                        raise "lc : close by remote"
            except:
                traceback.print_exc(file=sys.stdout)
                self.letReconnect('listener_reader')
            
        def listener_writer():
            '''
            处理写的线程
            '''
            try:
                while True:
                    packet = self.writerQueue.get()+"\01"
                    print 'writer take packet == '+packet.encode('utf-8')
                    self.mySocket.sendall(packet.encode('utf8'))
            except:
                self.letReconnect('listener_writer')

        threads = []
        threads.append(threading.Thread(target=listener_heartBeat, name='listener_heartbeat', args=() ))
        threads.append(threading.Thread(target=listener_reader, name='listener_reader', args=() ))
        threads.append(threading.Thread(target=listener_writer, name='listener_writer', args=() ))
        for t in threads:
            t.setDaemon(True)
            t.start()
                                        
    def init(self):
        self.mySocket.connect(self.addr)
        self.isClose = False
        self.ioListiner()
        
        def reader():
            '''
            读取消息并产生回调
            '''
            print "reader_inited ..."
            while True:
                print "reader wait ..."
                packet = self.readerQueue.get()
                packet = packet.decode('utf-8')
                print 'reader <== '+packet
                if packet == '\02':
                    try:
                        self.heartBeatQueue.get(timeout=0)
                    except :
                        pass
                elif packet == '\03':
                    pass
                else :
                    dpacket = json.loads(packet)
                    if dpacket.get('envelope').get('type') == 0 :
                        if dpacket.get('entity').get('result') == 'ok':
                            self.isAuth = True
                        else:
                            self.isAuth = False
                    self.callback(packet)
                    
        t = threading.Thread(target=reader, name='reader', args=() )
        t.setDaemon(True)
        t.start()
    
    def auth(self,jid,pwd):
        self.jid,self.pwd = jid,pwd
        self.init()
        packet = {
            'envelope':{
                'id':uuid.uuid4().hex,
                'type':0,
                'jid':jid,
                'pwd':pwd
            },
            'vsn':'0.0.1'
        }
        packet = json.dumps(packet)
        self.writerQueue.put(packet)
        print 'open_session ==> '+packet        
        
        def reconnect():
            '''
            启动重连线程
            '''
            pass    
        t = threading.Thread(target=reconnect, name='reconnect', args=() )
        t.setDaemon(True)
        t.start()
        
    def shutdown(self):
        pass
    
    def sendMessage(self,to,content,msgtype=1):
        # check packet
        try:
            packet = {
                'envelope':{
                    'id':uuid.uuid4().hex,
                    'type':msgtype,
                    'from':self.jid,
                    'to':to,
                    'ack':1
                },
                'payload':{
                    'attrs':{},
                    'content':content
                },
                'vsn':'0.0.1'
            }
            self.writerQueue.put(json.dumps(packet))
        except Exception,e :
            print e
            return e
                
if __name__ == '__main__':
    client = Client("192.168.2.230", 4222)
    def callback(data):
        print "callback ==> %s" % data
    client.setListener(callback)
    client.setHeartBeat(50)
    if len(sys.argv)>1 and sys.argv[1] :
        jid = sys.argv[1]
    else :
        jid = "lc@test.com"

    if len(sys.argv)>2 and sys.argv[2] :
        to = sys.argv[2]
    else :
        to = "cc@test.com"
        
    client.auth(jid, "123")
    
    msg = ""
    while True :
        m = sys.stdin.read(1)
        msg+=m
        if m=='\n' :
            client.sendMessage(to=to,content=msg,msgtype=1)
            msg = ""
    time.sleep(10000)
        
        

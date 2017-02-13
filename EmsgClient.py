# /usr/bin/env python
# coding=utf-8
'''
Created on 2014年11月27日
@author: liangc (email: cc14514@icloud.com)
'''
import socket, json, uuid, Queue, threading, time, traceback, sys, ssl,logging


_pvs = ''

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

    def __init__(self, host, port, ssl=False):
        self.pvs = ''
        self.addr = (host, port)
        self.mySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.reconnectQueue = Queue.Queue(1)
        self.heartBeatQueue = Queue.Queue(3)
        self.readerQueue = Queue.Queue(1024)
        self.writerQueue = Queue.Queue(1024)
        self.isAuth = False

    def setHeartBeat(self, beat_time=30):
        ''' 设置心跳间隔时间，单位秒，默认30秒 '''
        self.heartbeat = beat_time

    def setListener(self, callback):
        self.callback = callback

    def letReconnect(self, who):
        ''' 发送重连的指令 '''
        try:
            self.reconnectQueue.put(who, timeout=0)
        except:
            pass

    def ioListiner(self):
        ''' 对链接进行初始化，启动收发线程来监听各自的缓冲区队列 '''
        global _pvs
        def listener_heartBeat(pvs):
            '''
            处理心跳的线程
            '''
            logging.debug('HeartBeat thread started. [%s][%s]' % (pvs,_pvs))
            try:
                while True:
                    if _pvs != pvs : return
                    if self.isAuth:
                        packet = '\02'
                        self.writerQueue.put(packet, timeout=0)
                        self.heartBeatQueue.put(packet, timeout=0)
                        time.sleep(self.heartbeat)
                    else:
                        time.sleep(2)
            except:
                self.letReconnect('heartBeat')

        def listener_reader(pvs):
            '''
            处理读的线程
            '''
            try:
                logging.debug('reader thread started. [%s][%s]' % (pvs,_pvs))
                part = ''
                while True:
                    if _pvs != pvs : return
                    data = self.mySocket.recv(1024)
                    if data:
                        arr = data.split('\01'.encode('utf-8'))
                        logging.debug('len=%s ; recv=%s' % (len(arr), data))
                        # 如果 data 中包含 指定分隔符，则 len(arr) 一定大于1，否则 data != nill 时，len = 1
                        if len(arr) == 1:
                            # 如果不包含分隔符，则拼接分片数据
                            part = part + arr[0]
                        else:
                            first = arr[0]
                            first = part + first
                            # last = part + arr[-1]
                            if arr[-1] != '':
                                part = arr[-1]
                                logging.debug('recv part=%s' % part)
                            else :
                                part = ''
                            if first != '\02' and first != '\03' :
                                logging.debug('readerQueue.put first=%s' % first)
                            self.readerQueue.put(first)
                            for packet in arr[1:-1]:
                                self.readerQueue.put(packet)
                    else:
                        raise "lc : close by remote"
            except:
                traceback.print_exc(file=sys.stdout)
                self.letReconnect('listener_reader')

        def listener_writer(pvs):
            '''
            处理写的线程
            '''
            try:
                logging.debug('writer thread started. [%s][%s]' % (pvs,_pvs))
                while True:
                    if _pvs != pvs : return
                    packet = self.writerQueue.get() + "\01"
                    logging.debug('writer take packet == ' + packet.encode('utf-8'))
                    self.mySocket.sendall(packet.encode('utf8'))
            except:
                self.letReconnect('listener_writer')

        threads = []
        threads.append(threading.Thread(target=listener_heartBeat, name='listener_heartbeat', args=(self.pvs,)))
        threads.append(threading.Thread(target=listener_reader, name='listener_reader', args=(self.pvs,)))
        threads.append(threading.Thread(target=listener_writer, name='listener_writer', args=(self.pvs,)))
        for t in threads:
            t.setDaemon(True)
            t.start()

    def init(self):
        # 用 _pvs 作为当前进程序列号，线程如果拿到的不是这个序列号，就要自杀
        global _pvs
        _pvs = uuid.uuid4().hex
        self.pvs = _pvs
        self.mySocket.connect(self.addr)
        self.isClose = False
        self.ioListiner()

        def reader():
            '''
            读取消息并产生回调
            '''
            logging.debug("reader_inited ...")
            while True:
                logging.debug("reader wait ...")
                packet = self.readerQueue.get()
                packet = packet.decode('utf-8')
                logging.debug('reader <== ' + packet)
                if packet == '\02':
                    # Heart beat
                    try:
                        self.heartBeatQueue.get(timeout=0)
                    except:
                        pass
                elif packet == '\03':
                    # KILL
                    pass
                else:
                    dpacket = json.loads(packet)
                    if dpacket.get('envelope').get('type') == 0:
                        if dpacket.get('entity').get('result') == 'ok':
                            self.isAuth = True
                        else:
                            self.mySocket.close()
                    self.callback(packet)

        t = threading.Thread(target=reader, name='reader', args=())
        t.setDaemon(True)
        t.start()

    def auth(self, jid, pwd):
        self.jid, self.pwd = jid, pwd
        self.init()
        packet = {
            'envelope': {
                'id': uuid.uuid4().hex,
                'type': 0,
                'jid': jid,
                'pwd': pwd
            },
            'vsn': '0.0.1'
        }
        packet = json.dumps(packet)
        self.writerQueue.put(packet)
        logging.debug('open_session ==> ' + packet)

        def reconnect():
            '''
            启动重连线程
            '''
            # TODO : 暂未实现
            logging.debug('reconnect thread started.')
            pass

        t = threading.Thread(target=reconnect, name='reconnect', args=())
        t.setDaemon(True)
        t.start()

    def shutdown(self):
        # TODO : 暂未实现
        pass

    def sendMessage(self, to, content, msgtype=1):
        # check packet
        try:
            packet = {
                'envelope': {
                    'id': uuid.uuid4().hex,
                    'type': msgtype,
                    'from': self.jid,
                    'to': to,
                    'ack': 1
                },
                'payload': {
                    'attrs': {},
                    'content': content
                },
                'vsn': '0.0.1'
            }
            self.writerQueue.put(json.dumps(packet))
        except Exception, e:
            logging.error(e)
            return e


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) > 1 and sys.argv[1]:
        host_port = sys.argv[1]
        host, port = host_port.split(':')
    else:
        host = "127.0.0.1"
        port = 4222
    client = Client(host, int(port))


    def callback(data):
        logging.info("callback ==> %s\n\n" % data)


    client.setListener(callback)
    client.setHeartBeat(30)

    if len(sys.argv) > 2 and sys.argv[2]:
        jid = sys.argv[2]
    else:
        jid = "lc@test.com"

    if len(sys.argv) > 3 and sys.argv[3]:
        to = sys.argv[3]
    else:
        to = "cc@test.com"

    client.auth(jid, "123")

    msg = ""
    try :
        while True:
            m = sys.stdin.read(1)
            msg += m
            if m == '\n':
                client.sendMessage(to=to, content=msg, msgtype=1)
                msg = ""
                # client.sendMessage(to=to,content="test",msgtype=1)
                # time.sleep(1)
    except:
        pass

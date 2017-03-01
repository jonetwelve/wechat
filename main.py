#!/usr/bin/python3
# coding=utf-8

from urllib import parse
import time, datetime
import requests
import re
import qrcode
import xml.dom.minidom
import json
import random
import os
import sys
import multiprocessing


def catchKeyboardInterrupt(fn):
    def wrapper(*args):
        try:
            return fn(*args)
        except KeyboardInterrupt:
            print('\n[*] 强制退出程序')

    return wrapper


class Weixin(object):
    def __str__(self):
        description = [
            "=========================",
            "[#] Web Weixin",
            "=========================",
        ]
        return "\n".join(description)

    def __init__(self):
        self.DEBUG = False
        self.uuid = ''
        self.base_uri = 'https://wx.qq.com/cgi-bin/mmwebwx-bin'
        self.redirect_uri = 'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage'
        self.uin = ''
        self.sid = ''
        self.skey = ''
        self.pass_ticket = ''
        self.deviceId = 'e' + repr(random.random())[2:17]
        self.BaseRequest = []
        self.synckey = ''
        self.SyncKey = []
        self.User = []
        self.MemberList = []
        self.ContactList = []  # 好友
        self.GroupList = []  # 群
        self.GroupMemeberList = []  # 群友
        self.PublicUsersList = []  # 公众号／服务号
        self.SpecialUsersList = []  # 特殊账号
        self.autoReplay = False
        self.syncHost = ''
        self.user_agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0'
        self.autoOpen = False
        self.saveFolder = os.path.join(os.getcwd(), 'saved')
        self.saveSubFolders = {'webwxgeticon': 'icons', 'webwxgetheadimg': 'headimgs', 'webwxgetmsgimg': 'msgimgs',
                               'webwxgetvideo': 'videos', 'webwxgetvoice': 'voices'}
        self.appid = 'wx782c26e4c19acffb'
        self.lang = 'zh_CN'
        self.lastCheckTs = time.time()
        self.MemberCount = 0
        self.SpecialUsers = ['newsapp', 'fmessage', 'filehelper', 'weibo', 'qqmail',
                             'fmessage', 'tmessage', 'qmessage', 'qqsync', 'floatbottle', 'lbsapp', 'shakeapp',
                             'medianote', 'qqfriend', 'readerapp', 'blogapp', 'facebookapp', 'masssendapp',
                             'meishiapp', 'feedsapp', 'voip', 'blogappweixin', 'weixin', 'brandsessionholder',
                             'weixinreminder', 'wxid_novlwrv3lqwv11', 'gh_22b87fa7cb3c', 'officialaccounts',
                             'notification_messages', 'wxid_novlwrv3lqwv11', 'gh_22b87fa7cb3c', 'wxitil',
                             'userexperience_alarm', 'notification_messages'
                             ]
        self.TimeOut = 20  # 同步最短时间间隔（单位：秒）
        self.media_count = -1
        self.cookies = None
        self.session = requests.session()
        self.session.headers.update(
            {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0'})
        if not os.path.exists(self.saveFolder):
            os.makedirs(self.saveFolder)

    def loadConf(self, config):
        if config['DEBUG']:
            self.DEBUG = config['DEBUG']
        if config['autoReplay']:
            self.autoReplay = config['autoReplay']

    def getuuid(self):
        url = 'https://login.wx.qq.com/jslogin?appid={0}&redirect_uri={1}&fun=new&lang={2}&_={3}' \
            .format(self.appid, parse.quote_plus(self.redirect_uri), self.lang, int(time.time()))
        req = requests.get(url)
        data = req.text
        if data == '':
            return False
        regx = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
        pm = re.search(regx, data)
        if pm:
            code = pm.group(1)
            self.uuid = pm.group(2)
            return code == '200'
        return False

    def printQr(self):
        url = 'https://login.weixin.qq.com/l/' + self.uuid
        qr = qrcode.QRCode()
        qr.border = 1
        qr.add_data(url)
        qr.make()
        qr.print_ascii(invert=True)

    def _run(self, str, func, *args):
        if func(*args):
            print(str + ' : Success')
        else:
            print(str + ' : False\n[*] exit')
            exit()

    def _loger(self, stri):
        if self.DEBUG:
            with open('log', 'w') as f:
                f.write(str(stri))

    def _dd(self, value):
        self._loger(value)
        exit()

    def _post(self, url, params):
        r = self.session.post(url, data=params)
        r.encoding = 'utf-8'
        return json.loads(r.text)

    @catchKeyboardInterrupt
    def start(self):
        if sys.platform.startswith('win') and input('Not support win. Continue ? (y/n)') == 'n':
            exit()
        print('[*] starting...')
        while True:
            self._run('[*] get UUID', self.getuuid)
            print('[*] uuid : ', self.uuid)
            print('[*] QR code :')
            self.printQr()
            print('Scan the QR code for login')
            waitforlogin = self.waitForLogin()
            if not waitforlogin:
                continue
                print('Please confirm login')

            if not self.waitForLogin(0):
                continue
            break
        self._run('[*] login ing...', self.login)
        self._run('[*] webwxinit init', self.webwxinit)
        self._run('[*] webwxstatusnotify', self.webwxstatusnotify)
        self._run('[*] webwxgetcontact', self.webwxgetcontact)
        self._run('[*] webwxbatchgetcontact', self.webwxbatchgetcontact)
        print('[*] Total contacter count %d, load %d' % (self.MemberCount, len(self.MemberList)))
        print('[*] Total %d groups, %d members, %d special group, %d public group' \
              % (len(self.GroupList), len(self.ContactList), len(self.SpecialUsersList), len(self.PublicUsersList)))
        if input('-> Start auto replay (y/n)') == 'y':
            self.autoReplay = True
            print('[*] auto replay on')
        else:
            print('[*] auto replay off')

        listenProcess = multiprocessing.Process(target=self.listenMsgMode)
        listenProcess.start()

        time.sleep(2)
        self.run()
        return False

    def waitForLogin(self, tip=1):
        time.sleep(tip)
        url = 'https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s' \
              % (tip, self.uuid, int(time.time()))

        data = requests.get(url).text
        if data == '':
            return False
        pm = re.search(r'window.code=(\d+);', data)
        code = pm.group(1)

        if code == '201':
            return True
        elif code == '200':
            pm = re.search(r'window.redirect_uri="(\S+?)";', data)
            r_uri = pm.group(1) + '&fun=new'
            self.redirect_uri = r_uri
            self.base_uri = r_uri[:r_uri.rfind('/')]
            return True
        elif code == '408':
            print('[login timeout] \n')
        else:
            print('[login fail] \n')
        return False

    def login(self):
        data = self.session.get(self.redirect_uri).text
        if data == '':
            return False
        doc = xml.dom.minidom.parseString(data)
        root = doc.documentElement
        for node in root.childNodes:
            if node.nodeName == 'skey':
                self.skey = node.childNodes[0].data
            elif node.nodeName == 'wxsid':
                self.sid = node.childNodes[0].data
            elif node.nodeName == 'wxuin':
                self.uin = node.childNodes[0].data
            elif node.nodeName == 'pass_ticket':
                self.pass_ticket = node.childNodes[0].data

        if '' in (self.skey, self.sid, self.uin, self.pass_ticket):
            return False

        self.BaseRequest = {
            'Uin': int(self.uin),
            'Sid': self.sid,
            'Skey': self.skey,
            'DeviceID': self.deviceId,
        }
        self.cookies = self.session.cookies
        return True

    def webwxinit(self, first=True):
        url = self.base_uri + '/webwxinit?pass_ticket=%s&skey=%s&r=%s' % (self.pass_ticket, self.skey, int(time.time()))
        params = {
            'BaseRequest': self.BaseRequest
        }
        self.session.headers.update({'ContentType': 'application/json; charset=UTF-8'})
        dic = json.loads(self.session.post(url, data=json.dumps(params), cookies=self.cookies).text)
        if dic == '':
            return False
        self.SyncKey = dic['SyncKey']
        self.User = dic['User']
        if type(self.SyncKey['List']) == 'dict':
            self.synckey = '|'.join([val['Key'] + '_' + val['Val'] for val in self.SyncKey['List']])
        elif first:
            return self.webwxinit(False)

        return dic['BaseResponse']['Ret'] == 0

    def webwxstatusnotify(self):
        url = self.base_uri + '/webwxstatusnotify?lang=zh_CN&pass_ticket=%s' % self.pass_ticket
        params = {
            'BaseRequest': self.BaseRequest,
            "Code": 3,
            "FromUserName": self.User['UserName'],
            "ToUserName": self.User['UserName'],
            "ClientMsgId": time.time()
        }
        dic = json.loads(self.session.post(url, data=json.dumps(params), cookies=self.cookies).text)

        return dic['BaseResponse']['Ret'] == 0

    def webwxgetcontact(self):
        SpecialUsers = self.SpecialUsers
        url = self.base_uri + '/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' % (
            self.pass_ticket, self.skey, int(time.time()))
        dic = self._post(url, {})
        self.MemberCount = dic['MemberCount'] - 1
        self.MemberList = dic['MemberList']
        ContactList = self.MemberList[:]
        for i in ContactList:
            if i['UserName'] in SpecialUsers:
                ContactList.remove(i)
                self.SpecialUsersList.append(i)
            elif (i['VerifyFlag'] & 8) != 0:
                ContactList.remove(i)
                self.PublicUsersList.append(i)
            elif i['UserName'].startswith('@@'):
                ContactList.remove(i)
                self.GroupList.append(i)
            elif i['UserName'] == self.User['UserName']:
                ContactList.remove(i)
                # example of i
                # {
                # 'Uin': 0,
                # 'UserName': '@076508dacb11a8942cf6453efc15e0b7',
                # 'NickName': 'username',
                # 'HeadImgUrl': '/cgi-bin/mmwebwx-bin/webwxgeticon?seq=490560&username=@076508dacb11a8942cf6453efc15e0b7&skey=@crypt_d344aab7_49b8b9fcaca5ed1f48d3bf4b6c8c38ea',
                # 'ContactFlag': 1,
                # 'MemberCount': 0,
                # 'MemberList': [],
                # 'RemarkName': '',
                # 'HideInputBarFlag': 0,
                # 'Sex': 1,
                # 'Signature': '茫茫人海觅知音',
                # 'VerifyFlag': 0,
                # 'OwnerUin': 0,
                # 'PYInitial': 'MJW',
                # 'PYQuanPin': 'majunwei',
                # 'RemarkPYInitial': '',
                # 'RemarkPYQuanPin': '',
                # 'StarFriend': 0,
                # 'AppAccountFlag': 0,
                # 'Statues': 0,
                # 'AttrStatus': 4131,
                # 'Province': '甘肃',
                # 'City': '兰州市',
                # 'Alias': '',
                # 'SnsFlag': 0,
                # 'UniFriend': 0,
                # 'DisplayName': '',
                # 'ChatRoomId': 0,
                # 'KeyWord': 'bei',
                # 'EncryChatRoomId': '',
                # 'IsOwner': 0
                # }
        self.ContactList = ContactList
        return True

    def webwxbatchgetcontact(self):
        """批量获取成员信息"""
        url = self.base_uri + '/webwxbatchgetcontact?type=ex&r=%s&pass_ticket=%s' % (int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            'Count': len(self.GroupList),
            'List': [{"UserName": group['UserName'], "EncryChatRoomId": ""} for group in self.GroupList]
        }
        dic = self._post(url, json.dumps(params))
        self.GroupList = dic['ContactList']
        for contact in dic['ContactList']:
            for member in contact['MemberList']:
                self.GroupMemeberList.append(member)
                # example of member
                # {
                # 'Uin': 0,
                # 'UserName': '@8aa415e0e56beabc41599ddab5e957da',
                # 'NickName': 'Pinko',
                # 'AttrStatus': 106549,
                # 'PYInitial': '',
                # 'PYQuanPin': '',
                # 'RemarkPYInitial': '',
                # 'RemarkPYQuanPin': '',
                # 'MemberStatus': 0,
                # 'DisplayName': '',
                # 'KeyWord': 'pin'
                # }

        return True

    def listenMsgMode(self):
        print('[*] sync message')
        self._run('[*] test the sync line', self.testsynccheck)

        redEnvelope = 0

        while True:
            self.lastCheckTs = time.time()
            retcode, selector = self.syncCheck()
            if retcode == '1100':
                print('[*] wechat login on the phone')
                break

            if retcode == '1101':
                print('[*] wechat login on the other device')
                break

            if retcode == '0':
                if selector == '0':
                    time.sleep(1)
                elif selector == '2':
                    r = self.webwxsync()
                    if r is not None:
                        self.handleMsg(r)
                elif selector == '6':
                    redEnvelope += 1
                    print('[*] Get gift %d' % redEnvelope)
                elif selector == '7':
                    print('[*] Handle on the phone')
                    self.webwxsync()
            if (time.time() - self.lastCheckTs) <= 20:
                time.sleep(time.time() - self.lastCheckTs)

    def testsynccheck(self):
        syncHost = ['webpush.wx.qq.com']
        for host in syncHost:
            self.syncHost = host
            retcode, selector = self.syncCheck()
            if retcode == '0':
                return True
        return False

    def syncCheck(self):
        url = 'https://' + self.syncHost + '/cgi-bin/mmwebwx-bin/synccheck?r=%s&sid=%s&uin=%s&skey=%s&deviceid=%s&synckey=%s&_=%s' \
                                           % (int(time.time()), self.sid, self.uin, self.skey, self.deviceId, self.synckey, int(time.time()))
        data = self.session.get(url).text
        if data == '':
            return [-1, -1]
        pm = re.search(r'window.synccheck={retcode:"(\d+)",selector:"(\d+)"}', data)
        retcode = pm.group(1)
        selector = pm.group(2)
        return [retcode, selector]

    def webwxsync(self):
        url = self.base_uri + '/webwxsync?sid=%s&skey=%s&pass_ticket=%s' % (self.sid, self.skey, self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            'SyncKey': self.SyncKey,
            'rr': int(time.time())
        }
        dic = self._post(url, json.dumps(params))
        if dic == '':
            return None
        if dic['BaseResponse']['Ret'] == 0:
            self.SyncKey = dic['SyncKey']
            self.synckey = '|'.join([str(keyVal['Key']) + '_' + str(keyVal['Val']) for keyVal in self.SyncKey['List']])
        return dic

    def handleMsg(self, r):
        for msg in r['AddMsgList']:
            msgType = msg['MsgType']
            name = self.getUserRemarkName(msg['FromUserName'])
            content = msg['Content'].replace('&lt;', '<').replace('&gt;', '>')

            self.recorder({'to': 'jone', 'from': name, 'type': msgType, 'content': content})
            if msgType == 1:
                raw_msg = {'raw_msg': msg}
                if self.autoReplay:
                    # 自己的消息不回复
                    reply = self.robot_answer(content) + '[机器人]'
                    if self.webwxsendmsg(reply, msg['FromUserName']):
                        print('auto reply:', reply)
                        self.recorder({'from': 'jone', 'to': msg['FromUserName'], 'type': '1', 'content': reply})
                    else:
                        print('auto reply fail')
            elif msgType == 3:
                raw_msg = {'raw_msg': msg, 'message': '%s send a image' % name}
            elif msgType == 34:
                raw_msg = {'raw_msg': msg, 'message': '%s send a voice' % name}
            elif msgType == 42:
                raw_msg = {'raw_msg': msg, 'message': '%s send a business card' % name}
            elif msgType == 47:
                raw_msg = {'raw_msg': msg, 'message': '%s send a animation' % name}
            elif msgType == 49:
                raw_msg = {'raw_msg': msg, 'message': '%s send a link' % name}
            # elif msgType == 51:
            #     pass
            #     # 打开联系人对话界面
            #     raw_msg = {'raw_msg': msg, 'message': '[*] Get the contact info success'}
            elif msgType == 62:
                raw_msg = {'raw_msg': msg, 'message': '%s send a video' % name}
            elif msgType == 10002:
                raw_msg = {'raw_msg': msg, 'message': '%s send a business card' % name}
            try:
                self._showMsg(raw_msg)
            except:
                pass

    def recorder(self, msg):
        #from, to, type, content
        msg_dir = os.path.join(self.saveFolder, 'message')
        if not os.path.exists(msg_dir):
            os.makedirs(msg_dir)
        msg_file = os.path.join(msg_dir, datetime.datetime.now().strftime('%Y_%m_%d')) + '.csv'
        now = datetime.datetime.now().strftime('%H:%M:%S')
        with open(msg_file, 'a') as f:
            content = '"%s","%s","%s","%s","%s"\n' % (now, msg['type'], msg['from'], msg['to'], msg['content'])
            f.write(content)

    def robot_answer(self, content):
        url = 'http://www.tuling123.com/openapi/api'
        data = {'key': 'c85e470188434662abd32b238b03e4d4', 'info': content}
        r = json.loads(requests.post(url, data).text)
        return r['text']

    def webwxsendmsg(self, word, to='filehelper'):
        url = self.base_uri + '/webwxsendmsg?pass_ticket=%s' % (self.pass_ticket)
        clientMsgId = str(int(time.time() * 1000)) + str(random.random())[:5].replace('.', '')
        params = {
            'BaseRequest': self.BaseRequest,
            'Msg': {
                "Type": 1,
                "Content": word,
                "FromUserName": self.User['UserName'],
                "ToUserName": to,
                "LocalID": clientMsgId,
                "ClientMsgId": clientMsgId
            }
        }
        headers = {'content-type': 'application/json; charset=UTF-8', 'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0'}
        r = requests.post(url, json.dumps(params, ensure_ascii=False).encode('utf8'), headers=headers)
        dic = r.json()
        return dic['BaseResponse']['Ret'] == 0

    def _showMsg(self, message):
        srcName = None
        dstName = None
        groupName = None
        content = None
        msg = message

        if msg['raw_msg']:
            srcName = self.getUserRemarkName(msg['raw_msg']['FromUserName'])
            dstName = self.getUserRemarkName(msg['raw_msg']['ToUserName'])
            content = msg['raw_msg']['Content'].replace('&lt;', '<').replace('&gt;', '>')
            message_id = msg['raw_msg']['MsgId']

            if content.find('http://weixin.qq.com/cgi-bin/redirectforward?args=') != -1:
                # 位置消息
                content = '%s send a position' % srcName

            if msg['raw_msg']['ToUserName'] == 'filehelper':
                # 文件传输助手
                dstName = 'file helper'

            if msg['raw_msg']['FromUserName'][:2] == '@@':
                # 接收到来自群的消息
                if ":<br/>" in content:
                    [people, content] = content.split(':<br/>', 1)
                    groupName = srcName
                    srcName = self.getUserRemarkName(people)
                    dstName = 'GROUP'
                else:
                    groupName = srcName
                    srcName = 'SYSTEM'
            elif msg['raw_msg']['ToUserName'][:2] == '@@':
                # 自己发给群的消息
                groupName = dstName
                dstName = 'GROUP'
            if content == '收到红包，请在手机上查看':
                msg['message'] = content

            if 'message' in msg.keys():
                content = msg['message']

            if groupName != None:
                print('[%s] %s -> %s: %s' % (
                    groupName.strip(), srcName.strip(), dstName.strip(), content.replace('<br/>', '\n')))
            else:
                print('%s -> %s: %s' % (srcName.strip(), dstName.strip(), content.replace('<br/>', '\n')))

    def getUserRemarkName(self, id):
        name = 'Unknown group' if id[:2] == '@@' else 'Foreigner'
        if id == self.User['UserName']:
            return self.User['NickName']
        if id[:2] == '@@':
            name = self.getGroupName(id)
        else:
            for member in self.SpecialUsersList:
                if member['UserName'] == id:
                    name = member['NickName']
            for member in self.PublicUsersList:
                if member['UserName'] == id:
                    name = member['NickName']
            for member in self.ContactList:
                if member['UserName'] == id:
                    name = member['NickName']
            for member in self.GroupMemeberList:
                if member['UserName'] == id:
                    name = member['NickName']
        return name

    def getGroupName(self, id):
        name = 'Unknown group'
        for member in self.GroupList:
            if member['UserName'] == id:
                name = member['NickName']
        if name == 'Unknown group':
            GroupList = self.getNameById(id)
            for group in GroupList:
                self.GroupList.append(group)
                if group['UserName'] == id:
                    name = group['NickName']
                    MemberList = group['MemberList']
                    for member in MemberList:
                        self.GroupMemeberList.append(member)
        return name

    def getNameById(self, id):
        url = self.base_uri + '/webwxbatchgetcontact?type=ex&r=%s&pass_ticket=%s' % (int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            "Count": 1,
            "List": [{"UserName": id, "EncryChatRoomId": ""}]
        }
        dic = self._post(url, json.dumps(params))

        if dic == '':
            return None
        return dic['ContactList']

    def run(self):
        self.help()
        while True:
            text = input().strip()
            if text == 'q':
                print('[*] quit')
                exit()
            elif text == 'h':
                self.help()
            elif text == 'a':
                self.autoReplay = False if self.autoReplay else True
            elif text == 'f':
                for value in self.ContactList:
                    print("NickName:%s----Alias:%s----UserName:%s" % (
                        value['NickName'], value['Alias'], value['UserName']))
            elif text == 'g':
                for value in self.GroupList:
                    print("NickName:%s----MemberCount:%s----UserName:%s" % (value['NickName'], value['UserName'], value['UserName']))
            elif text == 'gf':
                for value in self.GroupMemeberList:
                    print("NickName:%s----UserName:%s" % (value['NickName'], value['UserName']))
            elif text[:2] == '>>':
                name, word = text[2:].split(' ', 1)
                self.sendMsg(name, word)
                self.recorder({'from': 'jone', 'to': name, 'type': '1', 'content': word})

    def sendMsg(self, name, content):
        id = self.getUserId(name)
        if id:
            if not self.webwxsendmsg(content, id):
                print('[*] send message fail')
        else:
            print('[*] %s not exist' % name)

    def getUserId(self, name):
        for member in self.MemberList:
            if name == member['RemarkName'] or name == member['NickName']:
                return member['UserName']
        return None

    def help(self):
        robot = 'on' if self.autoReplay else 'off'
        print('''
==============================================================
>>[昵称或ID][空格][内容] 给好友发送消息
a 切换机器人 (now %s)
q 退出程序
h 帮助
f 好友列表
g 群列表
gf 群友列表
==============================================================
        ''' % robot)


if __name__ == '__main__':
    wx = Weixin()
    config = {
        'DEBUG': True,
        'autoReplay': False,
    }
    wx.loadConf(config)
    wx.start()

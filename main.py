#!/usr/bin/python3
# -*- coding:utf-8 -*-

from urllib import parse
import time
import requests
import re
import qrcode
import xml.dom.minidom
import json
import random
import os
import sys


def catchKeyboardInterrupt(fn):
    def wrapper(*args):
        try:
            return fn(*args)
        except KeyboardInterrupt:
            print('\n[*] 强制退出程序')

    return wrapper


def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, str):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv


def _decode_dict(data):
    rv = {}
    for (key, value) in data.items():
        if isinstance(key, str):
            key = key.encode('utf-8')
        if isinstance(value, str):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv


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
        self.autoReplyMode = False
        self.syncHost = ''
        self.user_agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0'
        self.interactive = False
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

    def _echo(self, stri):
        if self.DEBUG:
            with open('log', 'w') as f:
                f.write(str(stri)) 

    def _dd(self, value):
        self._echo(value)
        exit()            

    @catchKeyboardInterrupt
    def start(self):
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
            self._echo('---> wait for login 201 success')
            return True
        elif code == '200':
            self._echo('---> wait for login 200 success')
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
        dic = json.loads(self.session.post(url, data={}).text, object_hook=_decode_dict)
        self._dd(type(dic))
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
            elif '@@' in i['UserName']:
                ContactList.remove(i)
                self.GroupList.append(i)
            elif i['UserName'] == self.User['UserName']:
                ContactList.remove(i)
        self.ContactList = ContactList
        self._echo(ContactList)
        return True

    


class UnicodeStreamFilter:
    def __init__(self, target):
        self.target = target
        self.encoding = 'utf-8'
        self.errors = 'replace'
        self.encode_to = self.target.encoding

    def write(self, s):
        if type(s) == str:
            s = s.decode('utf-8')
        s = s.encode(self.encode_to, self.errors).decode(self.encode_to)
        self.target.write(s)

    def flush(self):
        self.target.flush()


if sys.stdout.encoding == 'cp936':
    sys.stdout = UnicodeStreamFilter(sys.stdout)

if __name__ == '__main__':
    wx = Weixin()
    config = {
        'DEBUG': True,
        'autoReplay': False,
    }
    wx.loadConf(config)
    wx.start()

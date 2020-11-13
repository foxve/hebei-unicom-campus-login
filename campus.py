#!/usr/bin/python

import sys
import json
import uuid
import requests, socket
import base64, hmac, hashlib
from pyDes import des, ECB, PAD_PKCS5
from urllib import parse
import time, datetime
import argparse

URL_DOLOGIN                     = "https://icampus.hbwo10010.cn/ncampus/pfdoLogin"
URL_KICK_DEVICE                 = "https://icampus.hbwo10010.cn/ncampus/kickNetAccount"
URL_CONNECT_NET                 = "https://icampus.hbwo10010.cn/controlplatform/netConnect"
URL_PORTAL                      = "http://web1n.com/"

DES_SECRET_KEY_POST             = b'Fly@T2lI'
DES_SECRET_KEY_RESULT           = b'Song$2Mq'
HMAC_SECRET_KEY                 = b'liU%yFt2'


def generate_login_type(url, login_data):
    return hmac.new(HMAC_SECRET_KEY, bytes((login_data).encode('utf-8') + (url[url.rfind("/") + 1:]).encode('utf-8')), hashlib.sha1).hexdigest()

def generate_real_params(url, login_data):
    return {"LOGIN_TYPE": generate_login_type(url, login_data), "inparam": encrypt(login_data, DES_SECRET_KEY_POST)}

def request_data(url, login_data):
    res = requests.get(url = url, params = generate_real_params(url, json.dumps(login_data)), timeout = 5)
    if res.status_code != 200:
        print(res.text)
        exit(1)
    
    return json.loads(str(decrypt(res.text, DES_SECRET_KEY_RESULT)))


def decrypt(content, key):
    return des(key, ECB).decrypt(base64.b64decode(bytes(content.encode('utf-8'))), padmode=PAD_PKCS5).decode('utf8')

def encrypt(content, key):
    return base64.b64encode(des(key, ECB).encrypt(content.encode('utf-8'), padmode=PAD_PKCS5)).decode('utf-8')

def get_ip():
    return socket.gethostbyname(socket.gethostname())


parser = argparse.ArgumentParser(description="Hebei Unicom Campus Login Script")

parser.add_argument("username", help = "wo campus phone number")
parser.add_argument("password", help = "wo campus password")

parser.add_argument("--no-kick-old-device", action = "store_true", help = "do not kick old online device", default=False)

args = parser.parse_args()


# login
print("Getting account info...")

ip = get_ip()
fake_imei = str(uuid.uuid4()).replace("-", "")
random_code = str(uuid.uuid4()).replace("-", "")

result = request_data(URL_DOLOGIN, {"IP_ADDRESS": ip, "IMEI": fake_imei, "AUTH_METH": "0", "APP_VERSION": "2.3.2", "RANDOM_CODE": random_code, "OS_VERSION": "10", "OS": "ANDROID", "PASSWORD": args.password, "PHONE_TYPE": "Android", "PHONE_NAME": "Android Device", "PHONE_NUMBER": args.username})
if int(result["SUCCESS"]) != 0:
    print("Can not login: {}\n".format(result["ERRORINFO"].strip()))
    exit(1)
else:
    print("Account login successfully: {}, account: {}\n".format(result["SCHOOL_NAME"], result["ACCOUNT_ID"]))

net_account = result["ACCOUNT_NET"]
net_passwd  = result["PASSWORD_NET"]
account_id  = result["ACCOUNT_ID"]
token       = result["TOKEN"]


# kick device
if not args.no_kick_old_device:
    print("Kicking old device...")

    result = request_data(URL_KICK_DEVICE, {"DEVICE_TYPE": "01", "ACCOUNT_TYPE": "1", "TOKEN": token, "ACCOUNT_ID": account_id})
    if int(result["SUCCESS"]) == 0:
        print("Old device kicked\n")
    else:
        print("No need to kick any device\n")


# get ip and mac
print("Getting IP and MAC Address...")

res = requests.head(url = URL_PORTAL, allow_redirects = False)
redirect_url = res.headers['Location']
if res.status_code != 302 or len(redirect_url) == 0:
    print("Can not get redirect url")
    exit(1)

redirect_url_parse = parse.parse_qs(parse.urlparse(redirect_url).query)

mac = redirect_url_parse["user-mac"][0]
ip = redirect_url_parse["userip"][0]
nasip = redirect_url_parse["nasip"][0]

print("IP: {}, NASIP: {}, MAC: {}\n".format(ip, nasip, mac))


# post
print("Perform login...")

result = request_data(URL_CONNECT_NET, {"MAC": mac, "IP": ip, "NET_PASSWD": net_passwd, "NET_ACCOUNT": net_account, "REDIRECTURL": redirect_url, "TOKEN": token, "ACCOUNT_ID": account_id})
if int(result["SUCCESS"]) == 0:
    create_time = int(json.loads(result["RESPONSE"])["created_at"]) + 60 * 60 # unicom bug...
    login_time = time.strftime("%Y/%m/%d %H:%M:%S", time.localtime(create_time))

    print("Login Successfully, login time: {}".format(login_time))
else:
    print("Can not login: {}".format(result["ERRORINFO"]))
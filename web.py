import base64
import time
import random
from html.parser import HTMLParser
from io import BytesIO

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from PIL import Image

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.5 Safari/605.1.15',
    'Accept-Language': 'en-gb',
    'Connection': 'keep-alive'
}


class LoginPageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.body = {}
        self.salt = b''

    def handle_starttag(self, tag: str, attrs: list):
        if tag == 'input':
            attrs = dict(attrs)
            html_id = attrs.get('id')
            html_name = attrs.get('name')
            html_value = attrs.get('value')
            if html_name in ['lt', 'dllt', 'execution', '_eventId', 'rmShown']:
                self.body[html_name] = html_value
            elif html_id == 'pwdDefaultEncryptSalt':
                self.salt = html_value.encode('utf-8', 'ignore')

    def error(self, message):
        pass

    @staticmethod
    def create_body(html: str, username: str, password: str) -> dict:
        def random_bytes(length: int):
            result = ''
            chars = 'ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678'
            for i in range(length):
                result += random.choice(chars)
            return result.encode('utf-8', 'ignore')

        # parse html page
        parser = LoginPageParser()
        parser.feed(html)
        parser.body['username'] = username

        # AES password encryption
        if parser.salt != b'':
            iv = random_bytes(16)
            plain_text = pad(random_bytes(
                64) + password.encode('utf-8', 'ignore'), 16, 'pkcs7')
            aes_cipher = AES.new(parser.salt, AES.MODE_CBC, iv)
            cipher_text = aes_cipher.encrypt(plain_text)
            parser.body['password'] = base64.b64encode(
                cipher_text).decode('utf-8', 'ignore')
        else:
            parser.body['password'] = password

        return parser.body


def get_modified_form_data(form_data: list, form_template: list):
    form_data_dict = {}
    for item in form_data:
        value = {}
        name = item['name']
        hide = bool(item['hide'])
        title = item['title']
        if '本人是否承诺所填报的全部内容' in title:
            value['stringValue'] = '是 Yes'
        elif '学生本人是否填写' in title:
            value['stringValue'] = '是'
        elif item['value']['dataType'] == 'STRING':
            value['stringValue'] = item['value']['stringValue']
        elif item['value']['dataType'] == 'ADDRESS_VALUE':
            value['addressValue'] = item['value']['addressValue']
        form_data_dict[name] = {'hide': hide, 'title': title, 'value': value}

    form_data_modified = []
    for item in form_template:
        name = item['name']
        if name in form_data_dict:
            form_data_modified.append({
                'name': name,
                'title': form_data_dict[name]['title'],
                'value': form_data_dict[name]['value'],
                'hide': form_data_dict[name]['hide']
            })
        else:
            form_data_modified.append({
                'name': name,
                'title': item['title'],
                'value': {},
                'hide': 'label' not in name
            })
    return form_data_modified


def checkin(username: str, password: str, vpn_username: str = None, vpn_password: str = None):
    session = requests.Session()

    # get front page
    url = 'https://xmuxg.xmu.edu.cn'
    res = session.get(url, headers=headers, allow_redirects=True)

    # applg (or webvpn) bypass
    if not res.url.startswith('https://xmuxg.xmu.edu.cn/'):
    
        if vpn_username is None:
            vpn_username = username
        if vpn_password is None:
            vpn_password = password

        while True:
            # get chapta
            url = 'https://applg.xmu.edu.cn/wengine-auth/login/image'
            res = session.get(url, headers=headers)
            img = Image.open(BytesIO(base64.b64decode(res.json()['p'][22:])))
            px = img.load()
            time.sleep(2)

            # cacluate captcha answer
            w = img.width
            for i in range(img.width):
                for j in range(img.height):
                    if px[i, j][3] < 255:
                        w = min(w, i)
            w -= 2

            # verify captcha
            url = 'https://applg.xmu.edu.cn/wengine-auth/login/verify'
            body = {'w': str(w),
                    't': '0',
                    'locations[0][x]': '604',
                    'locations[0][y]': '410',
                    'locations[1][x]': str(w + 604),
                    'locations[1][y]': '410'}
            res = session.post(url, body, headers=headers)

            # check if need to retry
            if res.json()['success']:
                break
            time.sleep(3)

        # post applg login form
        url = 'https://applg.xmu.edu.cn/wengine-auth/do-login'
        body = {'auth_type': 'local', 'username': vpn_username,
                'sms_code': '', 'password': vpn_password}
        res = session.post(url, body, headers=headers, allow_redirects=True)

    # get login page
    url = 'https://ids.xmu.edu.cn/authserver/login?service=https://xmuxg.xmu.edu.cn/login/cas/xmu'
    res = session.get(url, headers=headers)
    time.sleep(2)

    # post login form
    body = LoginPageParser.create_body(res.text, username, password)
    res = session.post(url, body, headers=headers, allow_redirects=True)

    # incorrect password
    if '您提供的用户名或者密码有误' in res.text or 'username or password is incorrect' in res.text:
        return False, f'登录失败，用户名 {username} 或密码 {password} 错误'

    # need captcha
    cookie = res.cookies.get('SAAS_U')
    if cookie is None:
        return False, '登录失败，需要验证码'

    # get business id
    url = 'https://xmuxg.xmu.edu.cn/api/app/214/business/now'
    headers['X-Requested-With'] = 'XMLHttpRequest'
    res = session.get(url, headers=headers)
    business_id = str(res.json()['data'][0]['business']['id'])

    # get form template
    url = f'https://xmuxg.xmu.edu.cn/api/formEngine/business/{business_id}/formRenderData?playerId=owner'
    res = session.get(url, headers=headers)
    form_template = res.json()['data']['components']

    # get my form instance
    url = f'https://xmuxg.xmu.edu.cn/api/formEngine/business/{business_id}/myFormInstance'
    res = session.get(url, headers=headers)
    form = res.json()['data']
    form_id = form['id']
    form_data = form['formData']
    time.sleep(2)

    # post changes
    url = f'https://xmuxg.xmu.edu.cn/api/formEngine/formInstance/{form_id}'
    body = {'formData': get_modified_form_data(
        form_data, form_template), 'playerId': 'owner'}
    res = session.post(url, json=body, headers=headers)

    return True, cookie

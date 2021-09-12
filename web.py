import base64
import random
from html.parser import HTMLParser

import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


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
        def random_string(length: int):
            result = ''
            chars = 'ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678'
            for i in range(length):
                result += random.choice(chars)
            return result.encode('utf-8', 'ignore')

        parser = LoginPageParser()
        parser.feed(html)

        parser.body['username'] = username
        if parser.salt != b'':
            # AES password encryption
            iv = random_string(16)
            plain_text = pad(random_string(64) + password.encode('utf-8', 'ignore'), 16, style='pkcs7')
            aes_cipher = AES.new(parser.salt, AES.MODE_CBC, iv)
            cipher_text = aes_cipher.encrypt(plain_text)
            parser.body['password'] = base64.b64encode(cipher_text).decode('utf-8', 'ignore')
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


def checkin(username: str, password: str, old_cookie):
    session = requests.Session()

    # get login page
    url = 'https://ids.xmu.edu.cn/authserver/login?service=https://xmuxg.xmu.edu.cn/login/cas/xmu'
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) '
                        'Version/14.1.2 Safari/605.1.15',
        'Accept-Language': 'en-gb',
        'Referer': 'https://xmuxg.xmu.edu.cn/login',
        'Connection': 'keep-alive'
    }
    try:
        res = session.get(url, headers=headers)
    except:
        return None, False, '错误信息：无法连接统一身份认证服务器，可能开启了 VPN 校内访问，或学工系统维护中'

    # post login form
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) '
                      'Version/14.1.2 Safari/605.1.15',
        'Accept-Language': 'en-gb',
        'Referer': 'https://ids.xmu.edu.cn/authserver/login?service=https://xmuxg.xmu.edu.cn/login/cas/xmu',
        'Connection': 'keep-alive'
    }
    body = LoginPageParser.create_body(res.text, username, password)
    try:
        res = session.post(url, body, headers=headers, allow_redirects=True)
    except:
        return None, False, '错误信息：无法连接统一身份认证服务器，可能开启了 VPN 校内访问，或学工系统维护中'
    if '您提供的用户名或者密码有误' in res.text:
        return None, False, f'错误信息：登录失败，用户名 {username} 或密码 {password} 错误'
    cookie = res.cookies.get('SAAS_U')

    # need captcha to login, use old cookie to try
    if cookie is None:
        if old_cookie is not None:
            requests.utils.add_dict_to_cookiejar(session.cookies, {
                'SAAS_S_ID': 'xmu',
                'SAAS_U': old_cookie
            })
            use_old_cookie = True        
        else:
            return None, False, f'错误信息：登录失败，需要验证码（运气原因，或密码 {password} 强度过低、输入错误次数过多）'

    # get business id
    url = 'https://xmuxg.xmu.edu.cn/api/app/214/business/now'
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-gb',
        'Content-Type': 'application/json',
        'Host': 'xmuxg.xmu.edu.cn',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) '
                        'Version/14.1.2 Safari/605.1.15',
        'Referer': 'https://xmuxg.xmu.edu.cn/app/214',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'X-Requested-With': 'XMLHttpRequest'
    }
    try:
        res = session.get(url, headers=headers)
        business_id = str(res.json()['data'][0]['business']['id'])
    except:
        if use_old_cookie:
            return None, False, f'错误信息：登录失败，需要验证码（运气原因，或密码 {password} 强度过低、输入错误次数过多）'
        else:
            return cookie, False, '错误信息：无法获取今日打卡表单，可能学工系统维护中'
    
    # get form template
    url = f'https://xmuxg.xmu.edu.cn/api/formEngine/business/{business_id}/formRenderData?playerId=owner'
    try:
        res = session.get(url, headers=headers)
        form_template = res.json()['data']['components']
    except:
        return cookie, False, '错误信息：无法获取今日打卡表单模版，可能学工系统维护中'

    # get my form instance
    url = f'https://xmuxg.xmu.edu.cn/api/formEngine/business/{business_id}/myFormInstance'
    try:
        res = session.get(url, headers=headers)
        form = res.json()['data']
        form_id = form['id']
        form_data = form['formData']
    except:
        return cookie, False, '错误信息：无法获取昨日打卡信息，可能学工系统维护中'
    
    # post changes
    url = f'https://xmuxg.xmu.edu.cn/api/formEngine/formInstance/{form_id}'
    body = {'formData': get_modified_form_data(
        form_data, form_template), 'playerId': 'owner'}
    try:
        res = session.post(url, json=body, headers=headers)
    except:
        return cookie, False, '错误信息：无法提交打卡表单，可能学工系统维护中'

    return cookie, True, ''

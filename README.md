# XMU-Check

XMU-Check 自动打卡API。地址：https://f5soft.site/app/xmu-check/

## 使用文档

### 1. 安装环境

需要Python3运行环境。通过`requests`发送HTTP请求，通过`pycryptodome`进行密码的AES加密

```bash
sudo apt install python3
python3 -m pip install requests pycryptodome
```

### 2. API接口

位于`web.py`的`checkin`函数中，调用方法为：

```python
import web
cookie, status, msg = web.checkin('学号', '密码', None)
```

第三个参数为Cookie值，可为空。当用户名+密码登录失败时尝试使用。`checkin`函数返回三元组，其中`cookie`为新的Cookie值，`status`为打卡成功标志`True`或`False`，`msg`为打卡失败时的错误信息。

### 3. 原理说明

待更新

## 免责声明

您点使用本应用，则表明您同意该免责声明。

您在使用本应用前应当了解，本应用的目的在于**简化每日健康信息申报流程，促进同学进行健康申报的积极性，提高学院的打卡率**。本应用的原理为获取前一天的打卡信息，并据此自动更新当日的打卡信息。如果您的所在地址、体温、身体状况、旅居史等其他信息发生改变，需要您自行前往[学工系统](https://xmuxg.xmu.edu.cn/app/214)进行更新。

如果因为没有自行更新信息而导致瞒报等后果，需要您自行承担。本应用的开发者不会承担您的任何恶意使用本应用造成的后果的责任。
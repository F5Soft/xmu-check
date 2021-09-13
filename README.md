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

本应用的原理为获取前一天的打卡信息，并据此自动更新当日的打卡信息。

#### 模拟浏览器操作

首先进行人工打卡操作，在浏览器的开发人员工具的Networks中查看每个请求头，记下关键的请求头字段，如`User-Agent`、`Referrer`等，使用`requests`模块构造相同的HTTP请求。

系统通过Cookie同用户维持会话，因此还需要记下服务器响应头的`Set-Cookie`字段，并在之后的请求中附上这些Cookie。这可以用`requests`模块中的`Session`类实现。

#### 模拟登录和密码加密

登录是通过POST方法提交表单实现，可以在Networks中看到提交的表单数据，包括用户名和密码。值得注意的是，这里的密码是加密后的密码，因此为了能够成功模拟登录，需要手动实现加密算法，或者直接通过JS的运行环境，根据前端的加密代码得到返回值。

因为加密方式较为简单，可以直接手动实现。原理具体可以参考[前端密码AES-CBC加密方式的分析](https://f5soft.site/zh/notes/2021/0913/)

## 免责声明

您点使用本应用，则表明您同意该免责声明。

您在使用本应用前应当了解，本应用的目的在于**简化每日健康信息申报流程，促进同学进行健康申报的积极性，提高学院的打卡率**。本应用的原理为获取前一天的打卡信息，并据此自动更新当日的打卡信息。如果您的所在地址、体温、身体状况、旅居史等其他信息发生改变，需要您自行前往[学工系统](https://xmuxg.xmu.edu.cn/app/214)进行更新。

如果因为没有自行更新信息而导致瞒报等后果，需要您自行承担。本应用的开发者不会承担您的任何恶意使用本应用造成的后果的责任。
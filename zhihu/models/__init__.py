# encoding: utf-8

"""
知乎API
"""
import logging
import re
import time
from http import cookiejar

import requests
import requests.packages.urllib3 as urllib3
from bs4 import BeautifulSoup
from error import ZhihuError
from url import URL

from zhihu.settings import COOKIES
from zhihu.settings import HEADERS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Model(object):
    def __init__(self):
        self._session = requests.Session()
        self._session.verify = False
        self._session.headers = HEADERS
        self._session.cookies = cookiejar.LWPCookieJar(filename=COOKIES)
        try:
            self._session.cookies.load(ignore_discard=True)
        except:
            pass

    @property
    def logger(self):
        logger = logging.getLogger(self.__class__.__name__)
        return logging.LoggerAdapter(logger, {'zhihu': self})

    def log(self, message, level=logging.INFO, **kw):
        self.logger.log(level, message, **kw)

    def _get_captcha(self, **kwargs):
        t = str(int(time.time() * 1000))
        r = self._session.get(URL.captcha(t), **kwargs)
        with open('captcha.jpg', 'wb') as f:
            f.write(r.content)
        captcha = input("验证码：")
        return captcha

    def _get_xsrf(self, **kwargs):
        response = self._session.get(URL.index(), **kwargs)
        soup = BeautifulSoup(response.content, "html.parser")
        xsrf = soup.find('input', attrs={"name": "_xsrf"}).get("value")
        return xsrf

    def _user_id(self, user_slug):
        """
        user_slug 转 user_id
        :param user_slug:
        :return:
        """
        profile = self.user(user_slug=user_slug)
        user_id = profile.get("id")
        return user_id

    def _user_slug(self, profile_url):
        """
        profile_url 转 user_slug
        :param profile_url:
        :return:
        """
        pattern = re.compile("https?://www.zhihu.com/people/([\w-]+)")
        match = pattern.search(profile_url)
        if match:
            user_slug = match.group(1)
            return user_slug
        else:
            raise ZhihuError("invalid profile url")

    def login(self, email, password, **kwargs):
        """
        登录需要的验证码会保存在当前目录,需要用户自己识别,并输入
        """
        # TODO 还有其他登录方式
        request_body = {'email': email,
                        'password': password,
                        '_xsrf': self._get_xsrf(**kwargs),
                        "captcha": self._get_captcha(**kwargs),
                        'remember_me': 'true'}

        response = self._session.post(URL.login(), data=request_body, **kwargs)
        if response.ok:
            data = response.json()
            if data.get("r") == 0:
                # 登录成功'
                self._session.cookies.save()
                self.logger.info("登录成功")
                return True
            else:
                self.logger.info("登录失败, %s" % data.get("msg"))

        else:
            self.logger.error(response.content)
        return False

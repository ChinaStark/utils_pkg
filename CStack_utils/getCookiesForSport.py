# -- coding: utf-8 --
# @Author : ZhiliangLong
# @File : getCookiesForSport.py
# @Time : 2025/5/13 19:34
import argparse
import logging
import types
from logging.handlers import RotatingFileHandler

import time

# 根据系统配置utils和driver

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

formats = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
rHandler = RotatingFileHandler("getCookies.txt",maxBytes = 1024*1024,backupCount = 3)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)  # 设置控制台日志的级别

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

rHandler.setFormatter(formats)
console_handler.setFormatter(formats)

logger.addHandler(rHandler)
logger.addHandler(console_handler)


def init_(args):
    # 创建 ChromeOptions 对象
    chrome_options = Options()
    # 添加无头模式（headless mode），使浏览器在后台运行
    # chrome_options.add_argument("--headless")
    # 忽略 SSL 错误/不安全证书警告
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--allow-insecure-localhost')
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    chrome_options.add_argument('--ignore-ssl-errors=yes')
    chrome_options.add_experimental_option("detach", True)  # 防止浏览器自动关闭
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("window-size=1920,1080")
    # 创建 Service 对象并指定 ChromeDriver 的路径
    service = Service(args.driver_path)
    # 使用指定的 options 和 service 启动 Chrome 浏览器
    driver = webdriver.Chrome(service=service, options=chrome_options)
    logger.info("Driver initialized successfully")
    return driver


def login(args, emit=None):
    logger.info(f"准备获取cookies")
    try:
        driver = init_(args)
        current_time_millis = int(round(time.time() * 1000))
        driver.get(f"https://authserver.szu.edu.cn/authserver/login?service=https://ehall.szu.edu.cn:443/qljfwapp/sys/lwSzuCgyy/index.do?t_s={current_time_millis}#/sportVenue")
        # 等待并点击登录按钮
    except Exception as e:
        logger.error("bug in driver", e)
        return False, "bug in driver"
    try:
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="login_submit"]'))
        )
        username_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="username"]'))
        )
        username_input.send_keys(args.id)

        password_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="password"]'))
        )
        time.sleep(2)
        password_input.send_keys(args.pwd)

        login_button.click()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="sportVenue"]/div[1]/div'))
        )
        click_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '/html/body/main/article/div/div[1]/div/div[1]'))
        )
        click_btn.click()

        logger.info(f"clicked")
        cookies = driver.get_cookies()
        logger.info("获取Succeed")
        if emit:
            emit('appointment_update', {'message': '获取cookies Succeed'})
    except Exception as e:
        logger.error(f"获取失败...", e)
        if emit: emit('appointment_response', {'success': False, 'error': "cookies Filed"})
        driver.quit()
        return False, "bug in login"
    cookie_string = ""
    for cookie in cookies:
        cookie_string += f"{cookie['name']}={cookie['value']}; "

    # 移除末尾多余的分号和空格
    if cookie_string.endswith("; "):
        cookie_string = cookie_string[:-2]
    return True, cookie_string
def get_cookies(pwd, id, driver_path, cookies_path, emit=None):
    """
    获取Cookies
    :param pwd: 密码
    :param id: 学号
    :param driver_path: 驱动路径
    :param cookies_path: 你的cookies 文件
    :return: 是否获取成
    """
    args = types.SimpleNamespace(
        pwd=pwd,
        id=id,
        driver_path=driver_path
    )
    flag, data_or_msg = login(args,emit=emit)
    if flag:
        with open(cookies_path, "w") as f:
            f.write(data_or_msg)
        return True, "success get cookies"
    else:
        return False, data_or_msg


# if __name__ == '__main__':
    # parser = argparse.ArgumentParser(description='处理命令行参数')
    # parser.add_argument('--pwd', default=None, help='密码')
    # parser.add_argument('--id', default=None, help='用户ID')
    # parser.add_argument('--driver_path', default=None, help='驱动路径，path/to/chromedriver.exe')
    # args = parser.parse_args()
    # r = login(args)
    # logger.info(r)
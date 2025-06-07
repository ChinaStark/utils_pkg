# -- coding: utf-8 --
# @Author : ZhiliangLong
# @File : sportGet.py
# @Time : 2025/3/22 20:19

import time
from datetime import datetime, timedelta
import requests
import json

from CStack_utils import getCookiesForSport

debug = True


getTimeList = "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/sportVenue/getTimeList.do"
getRoomList = "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/modules/sportVenue/getOpeningRoom.do"
insertUrl="https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/sportVenue/insertVenueBookingInfo.do"

# ----------config-------------- #
import types
def init(**args):
    """
    001: 羽毛球
    003: 排球
    """
    # 提取参数
    you_name = args['you_name']
    you_id = args['you_id']
    YYLX = args['YYLX']  # 默认粤海是 "1.0"
    typeOfSport = args['typeOfSport']  # 预约什么运动 "003"
    appointment_day = args['appointment_day']
    appointment_time_start = args['appointment_time_start']
    cookie_file = args['cookie_file']
    target_time_str = args['target_time_str']
    # 创建参数字典
    params_getRoomList = {
        "XQDM": 1,
        "YYRQ": appointment_day,
        "YYLX": YYLX,
        "XMDM": typeOfSport,
        "KSSJ": "",
        "JSSJ": "",
    }
    params_getTimeList = {
        "XQ": 1,
        "YYRQ": appointment_day,
        "YYLX": YYLX,
        "XMDM": typeOfSport,
    }
    params_insert = {
        "DHID": "",
        "YYRGH": you_id,
        "CYRS": "",
        "YYRXM": you_name,
        "CGDM": "",
        "CDWID": "",
        "XMDM": typeOfSport,
        "XQWID": "",
        "KYYSJD": "",
        "YYRQ": appointment_day,
        "YYLX": YYLX,
        "YYKS": "",
        "YYJS": "",
        "PC_OR_PHONE": "pc",
    }
    headers = {
        'Cookie': ""
    }

    # 创建命名空间对象
    namespace = types.SimpleNamespace(
        target_time_str=target_time_str,
        you_name=you_name,
        you_id=you_id,
        YYLX=YYLX,
        typeOfSport=typeOfSport,
        appointment_day=appointment_day,
        appointment_time_start=appointment_time_start,
        cookie_file=cookie_file,
        params_getRoomList=params_getRoomList,
        params_getTimeList=params_getTimeList,
        params_insert=params_insert,
        headers=headers
    )
    return namespace

def load_cookies(file_path):
    with open(file_path, 'r') as file:
        cookie_str = file.read()
    return cookie_str

def set_cookies(file_path, cookie_str):
    with open(file_path, 'r') as file:
        cookie_str_ = file.read()
    new_content = cookie_str_.replace('{VAR_JACK}', cookie_str)
    with open(file_path, 'w') as file:
        file.write(new_content)






def request_url(cfg, url, params_, headers_):
    try:
        response = requests.post(url, data=params_, headers=headers_)
        set_cookies(cfg.cookie_file, response.headers['Set-Cookie'])
        if debug:
            print(params_)
            print(response.headers['Set-Cookie'])
        response_json = response.json()
        ret = response_json
    except Exception as e:
        return False, "Bug in request_url:"+ str(e)
    return True, ret


def main(cfg, emit = None):
    # 1. 获取当天可用的场次
    try:
        # 防止新用户没有cookies文件
        cookies = load_cookies(cfg.cookie_file)
    except Exception as e:
        if emit : emit('appointment_update', {'message': "检测你为新用户正在尝试登录获取Cookies..."})
        if debug: print("检测你为新用户正在尝试登录获取Cookies...")
        return False, "need cookies"
    cfg.headers["Cookie"] = cookies
    flag_times_list, times_list = request_url(cfg, getTimeList, cfg.params_getTimeList, cfg.headers)
    if flag_times_list:
        if emit:
            emit('appointment_update', {'message': "cookies检查成功"})
        else:
            print("cookies检查成功")
    else:
        if emit:
            emit('appointment_update', {'message': "Cookies 失效，正在重新登陆..."})
        if debug:
            print("Cookies 失效，正在重新登陆...")
            return False, "need cookies"
    if debug:
        print("times_list", times_list)
        print("=" * 30)
    available_times = []
    for item in times_list:
        if not item['disabled']:
            code_start, code_end = item['CODE'].split('-')
            available_times.append({
                'code_start': code_start.strip(),
                'code_end': code_end.strip()
            })
    if debug:
        print("available_times", available_times)
        print("=" * 30)
    # 2. 获取当前可用的Room,这一步需要上一步的可用时间
    if len(available_times) > 0:
        for item in available_times:
            if item['code_start'] < cfg.appointment_time_start:
                continue
            cfg.params_getRoomList['KSSJ'] = item['code_start']
            cfg.params_getRoomList['JSSJ'] = item['code_end']
            cfg.headers['Cookie'] = load_cookies(cfg.cookie_file)
            flags_room_info, room_info = request_url(cfg, getRoomList, cfg.params_getRoomList, cfg.headers)
            if not flags_room_info: return False, room_info
            if debug:
                print("room_info", room_info)
                print("=" * 30)
            available_room = []
    # 3. 获取可用场馆
            for item_room in room_info['datas']['getOpeningRoom']['rows']:
                if not item_room['disabled']:
                    YYRQ = "-".join([item['code_start'],item['code_end']])
                    YYKS = " ".join([cfg.appointment_day,item['code_start']])
                    YYJS = " ".join([cfg.appointment_day,item['code_end']])
                    available_room.append({
                        'CGDM': item_room['CGBM'],
                        'CDWID': item_room['WID'],
                        'XQWID': item_room['XQDM'],
                        'KYYSJD': YYRQ,
                        'YYKS': YYKS,
                        'YYJS': YYJS,
                    })
            if debug:
                print("available_room", available_room)
                print("=" * 30)
    # 4. 构建预约请求体
            if len(available_room) > 0:
                pre_param = []
                for available_item in available_room:
                    params_insert_ = cfg.params_insert
                    params_insert_['CGDM'] = available_item['CGDM']
                    params_insert_['CDWID'] = available_item['CDWID']
                    params_insert_['KYYSJD'] = available_item['KYYSJD']
                    params_insert_['YYKS'] = available_item['YYKS']
                    params_insert_['YYJS'] = available_item['YYJS']
                    params_insert_['XQWID'] = available_item['XQWID']
                    pre_param.append(params_insert_)
            if debug:
                print("pre_param", pre_param)
                print("=" * 30)
            if len(pre_param) > 0:
                for param_item in pre_param:
                    _, ret = request_url(cfg, insertUrl, param_item, cfg.headers)
                    if ret['msg'] == '成功':
                        return True, "success"
                    else:
                        if emit:
                            emit('appointment_update', {'message': "日期:{param_item['YYKS']}\n场馆:{param_item['CGDM']}"
                                                                   "预约失败!!!\n 开始下一场预约..."})
                        print(f"日期:{param_item['YYKS']}\n场馆:{param_item['CGDM']}预约失败!!!\n 开始下一场预约...")
        return False, "可能是你选择的时间段没了"
    else:
        print("网慢了，已经无！要不就是还没开！")
        return False , "网慢了，已经无！要不就是还没开！"
def strat_appointment(day, start_time,stu_name, stu_id, cookie_file_path, sport_type="001", yylx = 1.0,
                      target_time_str="12:30",emit=None, password=None):
    """
    szu 体育场馆预约
    :param cookies_path:
    :param target_time_str:
    :param emit:
    :param password:
    :param day: 预约日期
    :param start_time: 预约时间段的开始时间
    :param sport_type: 运动类型， 默认是羽毛球
    :param stu_name: 你的名字
    :param stu_id: 你的学号
    :param cookie_file_path: cookies的文件位置，也就是你复制一个cookies到一个txt或者什么文件中然后把路径传到这里，注意粘贴cookie的时候
    不要有换行（基本就是在最后有一个换行，你记得删除就行）
    :param yylx: 默认1.0
    :return: None
    """
    if debug : print(emit)
    cfg = init(
        you_name = stu_name,
        cookie_file = cookie_file_path,
        you_id = stu_id,
        YYLX = yylx,
        typeOfSport = sport_type,
        appointment_day = day,
        appointment_time_start = start_time,
        target_time_str = target_time_str
    )
    if cfg.you_id == "":
        print("""请先配置你的信息...
                you_name = ""
                you_id = ""
                YYLX="1.0" 
                typeOfSport = "001" # 001 默认是羽毛球
                appointment_day = "2025-04-13" 预约日期
                appointment_time_start = "16:00" 预约时间
            """)
        return False
    max_retries = 0
    while True:
        current_time_str = datetime.now()
        target_time = datetime.strptime(cfg.target_time_str, "%H:%M")
        target_day = datetime.strptime(str(cfg.appointment_day), "%Y-%m-%d")
        target_time = target_time.replace(year=current_time_str.year, month=current_time_str.month,
                                          day=target_day.day)
        print(target_time)
        target_time_minus_2mins = target_time - timedelta(minutes=2)
        if cfg.appointment_day != datetime.now().strftime("%Y-%m-%d") and target_time > current_time_str:
            if target_time >= current_time_str >= target_time_minus_2mins:
                emit('appointment_update', {'message':
                                                f"没到点，现在是北京时间{current_time_str}"})
                continue
            elif target_time > current_time_str:
                emit('appointment_update', {'message':
                                                f"没到点，现在是北京时间{current_time_str}, 建议12：28再来,所以程序停止"})
                return False
        else:
            if max_retries >= 3:
                if emit:
                    emit('appointment_update', {'message': "超过最大尝试次数，程序已经关闭！"})
                else:
                    print("超过最大尝试次数，程序已经关闭！")
                return False
            max_retries += 1
            _, msg_main = main(cfg, emit=emit)
            if msg_main == "success":
                if emit:
                    emit('appointment_update', {'message': "success appointment!!!  速速付钱!!!"})
                return True
            elif msg_main == "need cookies":
                flag, msg = getCookiesForSport.get_cookies(password, stu_id,
                                               "server/assest/webdriver/chromedriver.exe",
                                               cookie_file_path, emit=emit)
                if not flag:
                    emit('appointment_update', {'message': "获取cookies失败，原因是" + msg})
                #意思是获取cookies 不算次数
                else: max_retries -= 1
            else:
                if emit:
                    emit('appointment_update', {'message': "预约失败，原因是" + msg_main})
                else:
                    print("预约失败，原因是" + msg_main)
                time.sleep(1)
                continue



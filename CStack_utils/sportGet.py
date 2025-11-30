# -- coding: utf-8 --
# @Author : ZhiliangLong
# @File : sportGet.py
# @Time : 2025/3/22 20:19
import re
import time
from datetime import datetime, timedelta, date
import requests
import json
import random

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
        cookie_str = file.read().strip()
    return cookie_str

def set_cookies(file_path, cookie_str):
    new_weu_match = re.search(r"_WEU=([^;]+)", cookie_str)
    if not new_weu_match:
        raise ValueError("当前cookie已失效，请重新获取cookie并更新cookies文件")

    new_weu = new_weu_match.group(1)

    with open(file_path, 'r', encoding="utf-8") as f:
        content = f.read()

    # 替换文件里现有的 _WEU 值
    new_content = re.sub(
        r"_WEU=[^;]+",      # 匹配 _WEU=到分号之间
        f"_WEU={new_weu}",  # 替换为新的值
        content
    )

    with open(file_path, 'w', encoding="utf-8") as f:
        f.write(new_content)



def request_url(cfg, url, params_, headers_):

    response = requests.post(url, data=params_, headers=headers_)
    cookie_header = response.headers.get('Set-Cookie')
    if cookie_header:
        set_cookies(cfg.cookie_file, cookie_header)
    else:
        raise ValueError("request_url: no Set-Cookie header in response, please update your cookie")
    if debug:
        print(params_)
        if cookie_header:
            print(cookie_header)
    try:
        response_json = response.json()
        ret = response_json
    except Exception as e:
        return False, 'Appointment not yet open, please wait...'
    return True, ret

def main(cfg, emit=None, cancel_callback=None, cnt = 1):
    def should_cancel():
        return cancel_callback and cancel_callback()

    if should_cancel():
        return False, '用户取消'

    try:
        cookies = load_cookies(cfg.cookie_file)
    except Exception:
        if emit:
            emit('appointment_update', {'message': '检测你为新用户正在尝试登录获取 cookies...'})
        if debug:
            print('检测你为新用户正在尝试登录获取 cookies...')
        return False, 'need cookies'

    cfg.headers['Cookie'] = cookies
    if should_cancel():
        return False, '用户取消'

    def load_times_list(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = f.read()
        return True, json.loads(data)

    # 这一步是每个场馆都是固定的wid，因此我们记录羽毛球的放在json文件里面，直接加载json数据减少一次请求时间
    if cfg.typeOfSport == "001":
        flag_times_list, times_list = load_times_list("static/time_list.json")
    else:
        flag_times_list, times_list = request_url(cfg, getTimeList, cfg.params_getTimeList, cfg.headers)

    if debug:
        print('times_list', times_list)
        print('=' * 30)
    if should_cancel():
        return False, '用户取消'

    available_times = []
    for item in times_list:
        if should_cancel():
            return False, '用户取消'
        if not item['disabled']:
            code_start, code_end = item['CODE'].split('-')
            available_times.append({
                'code_start': code_start.strip(),
                'code_end': code_end.strip()
            })

    if debug:
        print('available_times', available_times)
        print('=' * 30)
    if should_cancel():
        return False, '用户取消'

    global_CDWID = -1

    def move_dict_to_front(list, target):
        """将特定字典移动到列表首位"""
        if target in list:
            list.remove(target)
            list.insert(0, target)
            return True
        return False

    if len(available_times) > 0:
        for item in available_times:

            if should_cancel():
                return False, '用户取消'
            if item['code_start'] < cfg.appointment_time_start:
                continue
            cfg.params_getRoomList['KSSJ'] = item['code_start']
            cfg.params_getRoomList['JSSJ'] = item['code_end']
            cfg.headers['Cookie'] = load_cookies(cfg.cookie_file)
            if should_cancel():
                return False, '用户取消'
            flags_room_info, room_info = request_url(cfg, getRoomList, cfg.params_getRoomList, cfg.headers)
            if not flags_room_info:
                return False, room_info
            if debug:
                print('room_info', room_info)
                print('=' * 30)
            available_room = []
            for item_room in room_info['datas']['getOpeningRoom']['rows']:
                if should_cancel():
                    return False, '用户取消'
                if item_room['disabled']:
                    continue
                yyrq = '-'.join([item['code_start'], item['code_end']])
                yyks = ' '.join([cfg.appointment_day, item['code_start']])
                yyjs = ' '.join([cfg.appointment_day, item['code_end']])
                available_item = {
                    'CGDM': item_room['CGBM'],
                    'CDWID': item_room['WID'],
                    'XQWID': item_room['XQDM'],
                    'KYYSJD': yyrq,
                    'YYKS': yyks,
                    'YYJS': yyjs,
                }
                available_room.append(available_item)
            if debug:
                print('available_room', available_room)
                print('=' * 30)
            if should_cancel():
                return False, '用户取消'
            pre_param = []
            target_param = None
            if len(available_room) > 0:

                for available_item in available_room:
                    if should_cancel():
                        return False, '用户取消'
                    params_insert_ = cfg.params_insert.copy()
                    params_insert_['CGDM'] = available_item['CGDM']
                    params_insert_['CDWID'] = available_item['CDWID']
                    params_insert_['KYYSJD'] = available_item['KYYSJD']
                    params_insert_['YYKS'] = available_item['YYKS']
                    params_insert_['YYJS'] = available_item['YYJS']
                    params_insert_['XQWID'] = available_item['XQWID']
                    pre_param.append(params_insert_)
                    if available_item['CDWID'] == global_CDWID:
                        target_param = params_insert_

            if len(pre_param) > 0:
                random.shuffle(pre_param)
                if target_param is not None:
                    move_dict_to_front(pre_param, target_param)
                for param_item in pre_param:
                    if should_cancel():
                        return False, '用户取消'
                    flag, ret = request_url(cfg, insertUrl, param_item, cfg.headers)
                    if flag:
                        if cnt == 1:
                            return True, 'success'
                        else:
                            cnt -= 1
                        global_CDWID = param_item['CDWID']
                        if emit:
                            emit('appointment_update', {
                                'message': f"日期:{param_item['YYKS']}\n场馆:{param_item['CGDM']}预约成功!!!\n 开始下一场预约..."
                            })
                        if debug:
                            print(f"日期:{param_item['YYKS']}\n场馆:{param_item['CGDM']}预约成功!!!\n 开始下一场预约...")
                        break
                    else:
                        global_CDWID = -1
                        if emit:
                            emit('appointment_update', {
                                'message': f"日期:{param_item['YYKS']}\n场馆:{param_item['CGDM']}预约失败!!!\n 开始下一场预约..."
                            })
                        if debug:
                            print(f"日期:{param_item['YYKS']}\n场馆:{param_item['CGDM']}预约失败!!!\n 开始下一场预约...")
        return False, '可能是你选择的时间段没了'
    else:
        if debug:
            print('网慢了，已经无！要不就是还没开！')
        return False, '网慢了，已经无！要不就是还没开！'

def strat_appointment(day, start_time, stu_name, stu_id, cookie_file_path, sport_type="001", yylx=1.0,
                      target_time_str="12:30", emit=None, password=None, wait_until_target=False,
                      max_attempts=30, retry_delay=0.5, cancel_callback=None, cnt = 1):
    def notify(msg: str):
        if emit:
            emit('appointment_update', {'message': msg})
        else:
            print(msg)

    def should_cancel():
        return cancel_callback and cancel_callback()

    def cancel_result():
        notify('用户取消，任务已停止')
        return False, '用户取消'

    cfg = init(
        you_name=stu_name,
        cookie_file=cookie_file_path,
        you_id=stu_id,
        YYLX=yylx,
        typeOfSport=sport_type,
        appointment_day=day,
        appointment_time_start=start_time,
        target_time_str=target_time_str
    )

    if not cfg.you_id:
        notify('请先配置个人信息')
        return False, 'missing user information'

    today = datetime.now().date()
    appointment_date = datetime.strptime(cfg.appointment_day, '%Y-%m-%d').date()
    if appointment_date < today:
        notify('预约日期已经过去，程序停止')
        return False, 'appointment day already passed'
    if appointment_date - today >= timedelta(days=2):
        notify('预约日期超出允许范围，请确认系统是否开放')
        return False, 'appointment day out of range'

    if should_cancel():
        return cancel_result()

    target_time = None
    if target_time_str:
        try:
            target_dt = datetime.strptime(cfg.target_time_str, '%H:%M').time()
            target_time = datetime.combine(date.today(), target_dt)
        except ValueError:
            notify(f'目标时间格式错误: {cfg.target_time_str}')
            return False, 'invalid target time'
    def countdown(remaining):
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        countdown_msg = f'距离预约开放时间还剩: {hours:02d}:{minutes:02d}:{seconds:02d}'
        notify(countdown_msg)

    # 检查当前cookie是否有效
    cfg.headers['Cookie'] = load_cookies(cfg.cookie_file)
    _, _ = request_url(cfg, getTimeList, cfg.params_getTimeList, cfg.headers)

    if wait_until_target and target_time:
        while True:
            if should_cancel():
                return cancel_result()
            now = datetime.now()
            if now >= target_time:
                break
            # 计算剩余时间并显示倒计时
            remaining = target_time - now
            if remaining >= timedelta(minutes=20):
                countdown(remaining)
                time.sleep(1000)
                # 刷新cookies
                cfg.headers['Cookie'] = load_cookies(cfg.cookie_file)
                _, _ = request_url(cfg, getTimeList, cfg.params_getTimeList, cfg.headers)
            elif timedelta(minutes=20) >= remaining >= timedelta(minutes=0.5):
                countdown(remaining)
                time.sleep(26)
            else:
                time.sleep(0.2)

    attempts = 0
    last_error = ''
    while attempts < max_attempts:
        if should_cancel():
            return cancel_result()
        attempts += 1
        success, msg_main = main(cfg, emit=emit, cancel_callback=should_cancel, cnt = cnt)
        if success:
            notify('预约成功，速速付款!')
            return True, 'success'
        if msg_main == 'need cookies':
            if not password:
                last_error = 'cookies expired and password missing'
                notify('Cookies 失效且没有提供密码，无法自动刷新')
                break
            if should_cancel():
                return cancel_result()
            flag, msg = getCookiesForSport.get_cookies(
                password, stu_id,
                '../server/assest/webdriver/chromedriver.exe',
                cookie_file_path, emit=emit
            )
            if not flag:
                last_error = msg
                notify('获取 cookies 失败，原因是 ' + msg)
                break
            notify('Cookies 已刷新，继续尝试预约...')
            attempts -= 1
            continue
        last_error = msg_main or 'unknown error'
        notify('预约失败，原因是 ' + last_error)
        if attempts < max_attempts:
            if should_cancel():
                return cancel_result()
            time.sleep(retry_delay)

    if should_cancel():
        return cancel_result()

    if not last_error:
        last_error = '预约失败'
    return False, last_error + f' (尝试 {attempts} 次)'

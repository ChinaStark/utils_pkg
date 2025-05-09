# -- coding: utf-8 --
# @Author : ZhiliangLong
# @File : sportGet.py
# @Time : 2025/3/22 20:19

import time
from datetime import datetime
import requests
import json





# ----------config-------------- #
debug = False
you_name = ""
you_id = ""
YYLX="1.0"
typeOfSport = "001" # 预约什么运动
appointment_day = "2025-04-13"
appointment_time_start = "16:00"
cookie_file=""
#----------config--------------- #



getTimeList = "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/sportVenue/getTimeList.do"
getRoomList = "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/modules/sportVenue/getOpeningRoom.do"
insertUrl="https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/sportVenue/insertVenueBookingInfo.do"
params_getRoomList={
        "XQDM": 1,
        "YYRQ": appointment_day,
        "YYLX": YYLX,
        "XMDM": typeOfSport,
        "KSSJ": "",
        "JSSJ": "",

    }
params_getTimeList = {
    "XQ": 1,
    "YYRQ":appointment_day,
    "YYLX" : YYLX,
    "XMDM" : typeOfSport,

}
params_insert = {
    "DHID":"",
    "YYRGH": you_id,
    "CYRS": "",
    "YYRXM":you_name,
    "CGDM":"",
    "CDWID": "",
    "XMDM": typeOfSport,
    "XQWID":"",
    "KYYSJD": "",
    "YYRQ": appointment_day,
    "YYLX": YYLX,
    "YYKS":"",
    "YYJS": "",
    "PC_OR_PHONE": "pc",

}
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




headers = {
    'Cookie': ""
}

def request_url(url, params_, headers_):
    response = requests.post(url, data=params_, headers=headers_)
    set_cookies("cookie_file", response.headers['Set-Cookie'])
    if debug:
        print(response.headers['Set-Cookie'])
    try:
        response_json = response.json()  # 直接调用 .json() 方法
        ret = response_json
    except json.JSONDecodeError as e:
        print("Error decoding JSON:", e)
        print("Response text:", response.text)
        ret = response.text
    return ret


def main():
    # 1. 获取当天可用的场次
    cookies = load_cookies(cookie_file)
    headers["Cookie"] = cookies
    times_list = request_url(getTimeList, params_getTimeList, headers)
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
    flag = False
    if len(available_times) > 0:
        for item in available_times:
            if flag:
                return True
            else:
                if item['code_start'] < appointment_time_start:
                    continue
                params_getRoomList['KSSJ'] = item['code_start']
                params_getRoomList['JSSJ'] = item['code_end']
                headers['Cookie'] = load_cookies(cookie_file)
                room_info = request_url(getRoomList, params_getRoomList, headers)
                if debug:
                    print("room_info", room_info)
                    print("=" * 30)
                available_room = []
    # 3. 获取可用场馆
                for item_room in room_info['datas']['getOpeningRoom']['rows']:
                    if flag: return True
                    if not item_room['disabled']:
                        YYRQ = "-".join([item['code_start'],item['code_end']])
                        YYKS = " ".join([appointment_day,item['code_start']])
                        YYJS = " ".join([appointment_day,item['code_end']])
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
                        params_insert_ = params_insert
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
                        ret = request_url(insertUrl, param_item, headers)
                        if ret['msg'] == '成功':
                            print("success appointment!!!  速速付钱!!!")
                            flag = True
                            break
                        else:
                            print(f"日期:{param_item['YYKS']}\n场馆:{param_item['CGDM']}预约失败!!!\n 开始下一场预约...")
    else:
        print("网慢了，已经无！要不就是还没开！")
        return False
def strat_appointment(day, start_time,stu_name, stu_id, cookie_file_path, sport_type="1.0", yylx = 1.0):
    """
    szu 体育场馆预约
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

    global  you_name ,you_id, YYLX  ,typeOfSport ,appointment_day , appointment_time_start, cookie_file
    you_name = stu_name
    cookie_file = cookie_file_path
    you_id = stu_id
    YYLX = yylx
    typeOfSport = sport_type
    appointment_day = day
    appointment_time_start = start_time
    target_time_str = "12:30"
    if you_id == "":
        print("""请先配置你的信息...
                you_name = ""
                you_id = ""
                YYLX="1.0" 
                typeOfSport = "001" # 001 默认是羽毛球
                appointment_day = "2025-04-13" 预约日期
                appointment_time_start = "16:00" 预约时间

            """)
        exit(1)

    while True:
        current_time_str = datetime.now().strftime("%H:%M")
        if current_time_str < target_time_str:
            print(f"该没到点，现在是北京时间{current_time_str}")
            time.sleep(0.5)
        else:
            try:
                r = main()
                if r:
                    break
                time.sleep(0.5)
            except:
                print("可能请求过快。。。可以考虑先暂停一下！！！")
                continue

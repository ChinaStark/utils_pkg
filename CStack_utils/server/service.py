# -- coding: utf-8 --
# @Author : ZhiliangLong
# @File : service.py
# @Time : 2025/5/13 12:03
import os

from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS


from CStack_utils import getCookiesForSport, sportGet

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# 示例 API 接口，你需要根据你的 utils_pkg 进行调整
@app.route('/')
def index():
    return render_template('index2.html')


@socketio.on('make_appointment')
def handle_appointment(data):
    cookies_path = "./cookies_file/" + data['you_id'] + "/getCookies.txt"
    if not os.path.exists("./cookies_file/" + data['you_id']):
        os.mkdir("./cookies_file/" + data['you_id'])
    sportGet.strat_appointment(
        data['appointment_day'],
        data['appointment_time_start'],
        data['you_name'],
        data['you_id'],
        cookies_path,
        sport_type=data['typeOfSport'],
        yylx=data['YYLX'],
        emit=emit,
        password=data['password']
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=60006)

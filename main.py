from CStack_utils import *
you_name = "赵梽沣"
you_id = "2410103064"
YYLX="1.0"  # 预约类型，目前羽毛球是1.0，健身房和排球是2.0
typeOfSport = "001" # 预约什么运动 001 羽毛球  003 排球
appointment_day = "2025-11-24"
appointment_time_start = "19:00" # 意愿开始时间
cookie_file="./cookies"
cnt = 2 # 默认是约一场，你可以改，注意一个时间段只能约一场
sportGet.strat_appointment(appointment_day,
                           appointment_time_start,
                           you_name,
                           you_id,
                           cookie_file,
                           sport_type=typeOfSport,
                           wait_until_target=True,
                           yylx=YYLX,
                           cnt = cnt)
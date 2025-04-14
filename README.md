## A Package of some useful utils


> There is only one tool now, you are very welcome to submit new utils 

- [2025.4.12] CStark have provided a util for strong badminton tickets in SZU. 🔥 


### Set up

```python
git clone https://github.com/ChinaStark/utils_pkg.git

cd utils_pkg

# setup
pip install .
```

## Get and write cookies 
### step 1
![](static\cut.png)
### step 2
![](static\QQ20250414-144632.png)
### step 3
Copy the `path/to/cookies` to the variant `cookie_file`
## Run
> [!NOTE]
> Before you run, please write the cookies in you file and the path should give to the variant cookie_file.

```python
# import the pkg you want use, 
# and CStack_utils denote this pkg is provided by CStack
from CStack_utils import *

you_name = "xxx"
you_id = "xxx"
YYLX="1.0"
typeOfSport = "001" # 预约什么运动，默认是羽毛球
appointment_day = "2025-04-15"
appointment_time_start = "16:00"
cookie_file="" 

sportGet.strat_appointment(appointment_day, appointment_time_start,you_name, you_id, cookie_file)

```


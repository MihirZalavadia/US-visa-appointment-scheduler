
#this draft 100% tested in 2025.

import time
import json
import random
import requests
import configparser

from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.common.by import By

from datetime import datetime
from collections import Counter

from embassy import *

config = configparser.ConfigParser()
config.read('config.ini')

# Personal Info:
# Account and current appointment info from https://ais.usvisa-info.com
USERNAME = config['PERSONAL_INFO']['USERNAME']
PASSWORD = config['PERSONAL_INFO']['PASSWORD']
# Find SCHEDULE_ID in re-schedule page link:
# https://ais.usvisa-info.com/en-am/niv/schedule/{SCHEDULE_ID}/appointment
SCHEDULE_ID = config['PERSONAL_INFO']['SCHEDULE_ID']
# Target Period:
PRIOD_START = config['PERSONAL_INFO']['PRIOD_START']
PRIOD_END = config['PERSONAL_INFO']['PRIOD_END']
# Embassy Section:
YOUR_EMBASSY = config['PERSONAL_INFO']['YOUR_EMBASSY']
EMBASSY = Embassies[YOUR_EMBASSY][0]
FACILITY_ID = Embassies[YOUR_EMBASSY][1]
REGEX_CONTINUE = Embassies[YOUR_EMBASSY][2]

# Time Section:
minute = 60
hour = 60 * minute
# Time between steps (interactions with forms)
STEP_TIME = 0.5
# Time between retries/checks for available dates (seconds)
RETRY_TIME_L_BOUND = config['TIME'].getfloat('RETRY_TIME_L_BOUND')
RETRY_TIME_U_BOUND = config['TIME'].getfloat('RETRY_TIME_U_BOUND')
# Cooling down after WORK_LIMIT_TIME hours of work (Avoiding Ban)
WORK_LIMIT_TIME = config['TIME'].getfloat('WORK_LIMIT_TIME')
WORK_COOLDOWN_TIME = config['TIME'].getfloat('WORK_COOLDOWN_TIME')
# Temporary Banned (empty list): wait COOLDOWN_TIME hours
BAN_COOLDOWN_TIME = config['TIME'].getfloat('BAN_COOLDOWN_TIME')


def update_city(do_update):
    """Update global embassy-related variables dynamically."""
    global FACILITY_ID, DATE_URL, TIME_URL
    time.sleep(2)
    # Update FACILITY_ID based on the condition
    if do_update:
        FACILITY_ID = 49
        print("Checking Abu Dhabi")
    else:
        FACILITY_ID = 50
        print("Checking Dubai")

    # Update URLs using the new FACILITY_ID
    DATE_URL = f"https://ais.usvisa-info.com/{EMBASSY}/niv/schedule/{SCHEDULE_ID}/appointment/days/{FACILITY_ID}.json?appointments[expedite]=false"
    TIME_URL = f"https://ais.usvisa-info.com/{EMBASSY}/niv/schedule/{SCHEDULE_ID}/appointment/times/{FACILITY_ID}.json?date=%s&appointments[expedite]=false"


SIGN_IN_LINK = f"https://ais.usvisa-info.com/{EMBASSY}/niv/users/sign_in"
APPOINTMENT_URL = f"https://ais.usvisa-info.com/{EMBASSY}/niv/schedule/{SCHEDULE_ID}/appointment"
DATE_URL = f"https://ais.usvisa-info.com/{EMBASSY}/niv/schedule/{SCHEDULE_ID}/appointment/days/{FACILITY_ID}.json?appointments[expedite]=false"
TIME_URL = f"https://ais.usvisa-info.com/{EMBASSY}/niv/schedule/{SCHEDULE_ID}/appointment/times/{FACILITY_ID}.json?date=%s&appointments[expedite]=false"
SIGN_OUT_LINK = f"https://ais.usvisa-info.com/{EMBASSY}/niv/users/sign_out"

JS_SCRIPT = ("var req = new XMLHttpRequest();"
             f"req.open('GET', '%s', false);"
             "req.setRequestHeader('Accept', 'application/json, text/javascript, */*; q=0.01');"
             "req.setRequestHeader('X-Requested-With', 'XMLHttpRequest');"
             f"req.setRequestHeader('Cookie', '_yatri_session=%s');"
             "req.send(null);"
             "return req.responseText;")


def auto_action(label, find_by, el_type, action, value, sleep_time=0):
    print("\t" + label + ":", end="")

    # Find Element By
    find_by = find_by.lower()
    if find_by == 'id':
        item = driver.find_element(By.ID, el_type)
    elif find_by == 'name':
        item = driver.find_element(By.NAME, el_type)
    elif find_by == 'class':
        item = driver.find_element(By.CLASS_NAME, el_type)
    elif find_by == 'xpath':
        item = driver.find_element(By.XPATH, el_type)
    else:
        return 0

    # Do Action
    action = action.lower()
    if action == 'send':
        item.send_keys(value)
    elif action == 'click':
        item.click()
    else:
        return 0

    print("\t\tCheck!")
    if sleep_time:
        time.sleep(sleep_time)



def start_process():
    # Bypass reCAPTCHA
    driver.get(SIGN_IN_LINK)
    time.sleep(STEP_TIME)
    Wait(driver, 60).until(EC.presence_of_element_located((By.NAME, "commit")))
    auto_action("Click bounce", "xpath", '//a[@class="down-arrow bounce"]', "click", "", STEP_TIME)
    auto_action("Email", "id", "user_email", "send", USERNAME, STEP_TIME)
    auto_action("Password", "id", "user_password", "send", PASSWORD, STEP_TIME)
    auto_action("Privacy", "class", "icheckbox", "click", "", STEP_TIME)
    auto_action("Enter Panel", "name", "commit", "click", "", STEP_TIME)
    Wait(driver, 60).until(EC.presence_of_element_located((By.XPATH, "//a[contains(text(), '" + REGEX_CONTINUE + "')]")))
    print("\n\tlogin successful!\n")

def reschedule(date):
    print("reschedule()")
    time = get_time(date)
    print("date ",date)
    print("time ", time)
    driver.get(APPOINTMENT_URL)
    headers = {
        "User-Agent": driver.execute_script("return navigator.userAgent;"),
        "Referer": APPOINTMENT_URL,
        "Cookie": "_yatri_session=" + driver.get_cookie("_yatri_session")["value"]
    }
    print("headers:")
    print(headers)
    print("create request:")
    data = {
        #"utf8": driver.find_element(by=By.NAME, value='utf8').get_attribute('value'),
        "authenticity_token": driver.find_element(by=By.NAME, value='authenticity_token').get_attribute('value'),
        "confirmed_limit_message": driver.find_element(by=By.NAME, value='confirmed_limit_message').get_attribute('value'),
        "use_consulate_appointment_capacity": driver.find_element(by=By.NAME, value='use_consulate_appointment_capacity').get_attribute('value'),
        "appointments[consulate_appointment][facility_id]": FACILITY_ID,
        "appointments[consulate_appointment][date]": date,
        "appointments[consulate_appointment][time]": time,
    }
    print("request created")
    print(data)
    r = requests.post(APPOINTMENT_URL, headers=headers, data=data)
    if r.status_code == 200:
        flag=1
        title = "SUCCESS"
        msg = f"Successfully Scheduled  {date} {time}"
        success_flag = True
    else:
        title = "FAIL"
        msg = f"Reschedule Failed!!! {date} {time}"
        success_flag = False
    return [success_flag, title, msg]


def get_date():
    print("Debug: get_date()")
    # Requesting to get the whole available dates
    session = driver.get_cookie("_yatri_session")["value"]
    script = JS_SCRIPT % (str(DATE_URL), session)
    content = driver.execute_script(script)
    dates=json.loads(content)
    print("Debug: get_date() done")
    return dates

def get_time(date):
    print("Debug: Get time()")
    time_url = TIME_URL % date
    session = driver.get_cookie("_yatri_session")["value"]
    script = JS_SCRIPT % (str(time_url), session)
    content = driver.execute_script(script)
    data = json.loads(content)
    time = data.get("available_times")[-1]
    print(f"Got time successfully! {date} {time}")
    return time


def is_logged_in():
    content = driver.page_source
    if(content.find("error") != -1):
        return False
    return True


def get_available_date(dates):
    # Evaluation of different available dates
    def is_in_period(date, PSD, PED):
        new_date = datetime.strptime(date, "%Y-%m-%d")
        result = ( PED > new_date and new_date > PSD )
        # print(f'{new_date.date()} : {result}', end=", ")
        return result

    PED = datetime.strptime(PRIOD_END, "%Y-%m-%d")
    PSD = datetime.strptime(PRIOD_START, "%Y-%m-%d")
    for d in dates:
        date = d.get('date')
        if is_in_period(date, PSD, PED):
            return date
    print(f"\n\nNo available dates between ({PSD.date()}) and ({PED.date()})!")


# Global variables to store closest dates and month counts
closest_dates = []
month_counts = {}


def get_closest_dates(dates):
    global closest_dates, month_counts  # Use the global month_counts
    print("Debug: get closest dates()")

    # Convert date strings to datetime objects
    date_objects = [datetime.strptime(d['date'], "%Y-%m-%d") for d in dates]

    # Sort the dates by proximity to the current date, earliest dates first
    current_date = datetime.now()
    sorted_dates = sorted(date_objects, key=lambda date: (abs((date - current_date).days), date))

    # Update the global list with the 10 closest dates
    closest_dates = sorted_dates[:10]

    # Increment the counter only for the year-month of the closest date
    closest_year_month = closest_dates[0].strftime("%Y-%m")
    if closest_year_month not in month_counts:
        month_counts[closest_year_month] = 0
    month_counts[closest_year_month] += 1

    # Get the 5 most common year-month combinations sorted by proximity to the current date
    # Sort the year-months by the count, then by the closest date within each year-month
    sorted_months = sorted(
        month_counts.items(),
        key=lambda x: abs((datetime.strptime(x[0], "%Y-%m") - current_date).days)
    )[:5]

    # Prepare display strings
    dates_string = "10 Closest Dates to Current Date: " + ", ".join(
        [date.strftime("%Y-%m-%d") for date in closest_dates])
    months_string = "5 Most closest monthes: " + ", ".join(
        [f" {year_month}: {count} tms" for year_month, count in sorted_months])

    # Display results
    print(dates_string)
    print(months_string)


def info_logger(file_path, log):
    # file_path: e.g. "log.txt"
    with open(file_path, "a") as file:
        file.write(str(datetime.now().time()) + ":\n" + log + "\n")



chrome_driver_path = "chromedriver.exe"
driver = webdriver.Chrome()




if __name__ == "__main__":
    Req_count = 0
    first_loop = True
    change_city = True
    while 1:
        change_city=not change_city
        update_city(change_city)

        if first_loop:
            t0 = time.time()
            total_time = 0
            Req_count = 0
            start_process()
            first_loop = False
        Req_count += 1
        try:
            msg = "-" * 60 + f"\nRequest count: {Req_count}, Log time: {datetime.today()}"
            print(msg)
            dates = get_date()

            if not dates:
                # Ban Situation
                msg = f"List is empty, Probabely banned!\n\tSleep for {BAN_COOLDOWN_TIME} hours!\n"
                msg = "List is empty"
                print(msg)

                sleep_time=random.randint(RETRY_TIME_L_BOUND, RETRY_TIME_U_BOUND)
                msg2 = "Retry Wait Time: " + str(sleep_time) + " seconds"
                print(msg2)
                time.sleep(sleep_time)

                #first_loop = True
            else:
                print("Avaliable dates:")
                # Print Available dates:
                try:
                    datesss=dates
                    get_closest_dates(datesss)

                except:
                     print("get_closest_dates(dates) exception")
                msg = ""
                for d in dates:
                    msg = msg + "%s" % (d.get('date')) + ", "
                msg = msg
                print(msg)
                #info_logger(LOG_FILE_NAME, msg)
                date = get_available_date(dates)
                if date:
                    print("A good date to schedule for")
                    # A good date to schedule for
                    success_flag, END_MSG_TITLE, msg = reschedule(date)
                    print(END_MSG_TITLE)
                    print(msg)
                    if success_flag == True:
                        break

                RETRY_WAIT_TIME = random.randint(RETRY_TIME_L_BOUND, RETRY_TIME_U_BOUND)
                t1 = time.time()
                total_time = t1 - t0
                msg = "\nWorking Time:  ~ {:.2f} minutes".format(total_time/minute)
                print(msg)
                #info_logger(LOG_FILE_NAME, msg)
                if total_time > WORK_LIMIT_TIME * hour:
                    # Let program rest a little
                    driver.get(SIGN_OUT_LINK)
                    time.sleep(WORK_COOLDOWN_TIME * hour)
                    first_loop = True
                else:
                    msg = "Retry Wait Time: "+ str(RETRY_WAIT_TIME)+ " seconds"
                    print(msg)
                    #info_logger(LOG_FILE_NAME, msg)
                    time.sleep(RETRY_WAIT_TIME)
        except:
            # Exception Occured
            msg = f"Break the loop after exception!\n"
            END_MSG_TITLE = "EXCEPTION"
            #break


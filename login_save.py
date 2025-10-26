#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from datetime import datetime, timedelta
import pytz
import jdatetime

# Login storage - ساختار جدید
login_data = {
    "current_week": {},  # { "1405/10/10": ["12:30:45", "14:20:15"], ... }
    "current_saturday": None,  # تاریخ شنبه هفته جاری
    "last_login_time": None    # آخرین زمان ثبت لاگین
}

def get_current_saturday():
    tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tz)
    j_now = jdatetime.datetime.fromgregorian(datetime=now)
    days_since_saturday = j_now.weekday()
    current_saturday = j_now - timedelta(days=days_since_saturday)
    return current_saturday.strftime("%Y/%m/%d")

def should_record_login():
    tz = pytz.timezone("Asia/Tehran")
    current_time = datetime.now(tz)
    if login_data["last_login_time"] is None:
        return True
    time_diff = current_time - login_data["last_login_time"]
    return time_diff.total_seconds() >= 300

def update_login_data():
    if not should_record_login():
        return
    tz = pytz.timezone("Asia/Tehran")
    current_time = datetime.now(tz)
    j_current = jdatetime.datetime.fromgregorian(datetime=current_time)
    current_date = j_current.strftime("%Y/%m/%d")
    current_time_str = j_current.strftime("%H:%M:%S")
    current_saturday = get_current_saturday()
    if login_data["current_saturday"] != current_saturday:
        login_data["current_week"] = {}
        login_data["current_saturday"] = current_saturday
    if current_date not in login_data["current_week"]:
        login_data["current_week"][current_date] = []
    if current_time_str not in login_data["current_week"][current_date]:
        login_data["current_week"][current_date].append(current_time_str)
        login_data["current_week"][current_date].sort()
    login_data["last_login_time"] = current_time

def get_week_report():
    week_days_persian = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]
    tree_report = {
        "saturday": login_data["current_saturday"] or get_current_saturday(),
        "days": []
    }
    current_saturday = jdatetime.datetime.strptime(tree_report["saturday"], "%Y/%m/%d")
    for i in range(7):
        current_date = current_saturday + timedelta(days=i)
        date_str = current_date.strftime("%Y/%m/%d")
        day_name = week_days_persian[i]
        day_data = {
            "date": date_str,
            "day_name": day_name,
            "logins": login_data["current_week"].get(date_str, []),
            "count": len(login_data["current_week"].get(date_str, []))
        }
        tree_report["days"].append(day_data)
    return tree_report
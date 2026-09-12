# -*- coding: utf-8 -*-
"""
长沙市 2022 年全年历史天气数据爬取、清洗与可视化
数据来源：天气后报历史天气网 https://lishi.tianqi.com/changsha/202201.html
流程：requests+lxml 爬取 -> csv 存原始数据 -> pandas 清洗统计 -> matplotlib/pyecharts 可视化
"""
import base64
import calendar
import csv
import datetime
import time

import requests
from lxml import etree
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from pyecharts import options as opts
from pyecharts.charts import Bar, Timeline

# matplotlib 中文显示设置（Windows 用黑体）
matplotlib.rcParams["font.sans-serif"] = ["SimHei"]
matplotlib.rcParams["axes.unicode_minus"] = False

CITY = "changsha"
YEAR = 2022
BASE = f"https://lishi.tianqi.com/{CITY}"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
}

# ---------------- 1. 爬取 ----------------

# 网页"查看更多"按钮的加密参数（还原自页面混淆 JS）：
# AES-CBC/Pkcs7 加密 "城市名_当前时间YYYYMMDDHHMMSS"，再 base64
AES_KEY = b"5ha5Z7cZ3WNbD3rA"
AES_IV = b"AYk98XaiBwCi0Dst"


def make_crypte():
    """生成 monthdata 接口所需的 crypte 参数"""
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    data = f"{CITY}_{ts}".encode()
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return base64.b64encode(cipher.encrypt(pad(data, 16))).decode()


def clean_text(s):
    """去掉网页文本中的空白字符和℃符号"""
    return s.replace("\r", "").replace("\n", "").replace("\t", "").replace("℃", "").strip()


def crawl_month(month):
    """爬取某月全部天气数据，返回 [日期, 最高气温, 最低气温, 天气] 列表的列表"""
    ym = f"{YEAR}{month:02d}"
    # 1) HTML 页面：默认渲染每月前 10 天，用 XPath 解析 ul.thrui 下的 li
    r = requests.get(f"{BASE}/{ym}.html", headers=HEADERS, timeout=15)
    r.encoding = "utf-8"
    html = etree.HTML(r.text)
    rows = []
    for li in html.xpath('//ul[@class="thrui"]/li'):
        divs = li.xpath("./div/text()")
        if len(divs) >= 4:
            rows.append([clean_text(divs[0]).split(" ")[0],   # 日期（去掉星期）
                         clean_text(divs[1]),                 # 最高气温
                         clean_text(divs[2]),                 # 最低气温
                         clean_text(divs[3])])                # 天气
    got = {x[0] for x in rows}
    # 2) AJAX 接口：POST /monthdata/ 补齐当月剩余天数
    r2 = requests.post(f"https://lishi.tianqi.com/monthdata/{CITY}/{ym}",
                       data={"crypte": make_crypte()},
                       headers={**HEADERS, "Referer": f"{BASE}/{ym}.html",
                                "X-Requested-With": "XMLHttpRequest"},
                       timeout=15)
    for item in r2.json():
        if item["date_str"] not in got:
            rows.append([item["date_str"], item["htemp"], item["ltemp"], item["weather"]])
    rows.sort(key=lambda x: x[0])
    return rows


def crawl_year():
    """爬取 12 个月，每月间隔 1 秒防止请求过快"""
    all_rows = []
    for m in range(1, 13):
        try:
            rows = crawl_month(m)
            print(f"{YEAR}-{m:02d} 爬取 {len(rows)} 天")
            all_rows.extend(rows)
        except Exception as e:
            print(f"{YEAR}-{m:02d} 爬取失败: {e}")
        time.sleep(1)
    return all_rows


# ---------------- 2. 原始数据保存 ----------------

def save_raw(rows, path="weather.csv"):
    """用 csv 模块把爬到的原始数据写入本地文件"""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["日期", "最高气温", "最低气温", "天气"])
        writer.writerows(rows)
    print(f"原始数据已保存: {path}（{len(rows)} 行）")


# ---------------- 3. pandas 清洗与统计 ----------------

def clean_and_analyze(raw_path="weather.csv", clean_path="weather_clean.csv"):
    df = pd.read_csv(raw_path)
    n0 = len(df)
    # 去掉重复日期、缺失行
    df = df.drop_duplicates(subset="日期").dropna()
    # 日期字符串转标准时间格式，并新增月份列
    df["日期"] = pd.to_datetime(df["日期"], format="%Y-%m-%d", errors="coerce")
    df = df.dropna(subset=["日期"])
    # 气温转数值类型，非法值转 NaN 后删除
    df["最高气温"] = pd.to_numeric(df["最高气温"], errors="coerce")
    df["最低气温"] = pd.to_numeric(df["最低气温"], errors="coerce")
    df = df.dropna().reset_index(drop=True)
    df["月份"] = df["日期"].dt.month
    df.to_csv(clean_path, index=False, encoding="utf-8-sig")
    print(f"清洗后已保存: {clean_path}（{n0} 行 -> {len(df)} 行）")

    # 简化天气类型：如"阴到小雨"归并为"雨"，便于统计分布规律
    def simple_weather(w):
        if "雨" in w:
            return "雨"
        if "雪" in w:
            return "雪"
        return w

    df["天气分类"] = df["天气"].apply(simple_weather)
    # 按月份+天气类型分组统计天数
    month_weather = df.groupby(["月份", "天气分类"]).size().unstack(fill_value=0)
    year_weather = df["天气分类"].value_counts()
    return df, month_weather, year_weather


# ---------------- 4. matplotlib 可视化 ----------------

def plot_line(df, path="line_temp.png"):
    """折线图：全年每日最高/最低气温变化趋势"""
    plt.figure(figsize=(14, 6))
    plt.plot(df["日期"], df["最高气温"], color="orangered", label="最高气温", linewidth=1)
    plt.plot(df["日期"], df["最低气温"], color="steelblue", label="最低气温", linewidth=1)
    plt.title(f"长沙市 {YEAR} 年气温变化趋势图")
    plt.xlabel("日期")
    plt.ylabel("气温 (℃)")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"折线图已保存: {path}")


def plot_pie(year_weather, path="pie_weather.png"):
    """饼状图：全年天气类型占比"""
    plt.figure(figsize=(8, 8))
    plt.pie(year_weather, labels=year_weather.index, autopct="%.1f%%",
            startangle=90, counterclock=False)
    plt.title(f"长沙市 {YEAR} 年全年天气类型占比")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"饼状图已保存: {path}")


def plot_bar(month_weather, path="bar_weather.png"):
    """柱状图：每月各天气类型天数（堆叠）"""
    plt.figure(figsize=(12, 6))
    bottom = None
    for w in month_weather.columns:
        plt.bar(month_weather.index, month_weather[w], bottom=bottom, label=w)
        bottom = month_weather[w] if bottom is None else bottom + month_weather[w]
    plt.title(f"长沙市 {YEAR} 年每月天气类型天数分布")
    plt.xlabel("月份")
    plt.ylabel("天数")
    plt.xticks(month_weather.index)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"柱状图已保存: {path}")


# ---------------- 5. pyecharts 轮播柱状图 ----------------

def plot_timeline(month_weather, path="weathers1.html"):
    """时间轮播柱状图：逐月展示各类天气天数"""
    timeline = Timeline()
    for month, row in month_weather.iterrows():
        bar = (
            Bar()
            .add_xaxis(list(row.index))
            .add_yaxis("天数", [int(v) for v in row.values])
            .set_global_opts(title_opts=opts.TitleOpts(
                title=f"长沙市 {YEAR} 年 {month} 月天气分布"),
                xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30)),
                yaxis_opts=opts.AxisOpts(max_=31))
        )
        timeline.add(bar, f"{month}月")
    timeline.render(path)
    print(f"pyecharts 轮播柱状图已保存: {path}")


if __name__ == "__main__":
    rows = crawl_year()
    save_raw(rows)
    df, month_weather, year_weather = clean_and_analyze()
    print("\n全年天气类型统计：")
    print(year_weather.to_string())
    plot_line(df)
    plot_pie(year_weather)
    plot_bar(month_weather)
    plot_timeline(month_weather)

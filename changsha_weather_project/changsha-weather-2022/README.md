# 长沙市 2022 年历史天气数据爬取与可视化分析

## 项目简介
基于 Python 的网络爬虫与数据分析小项目：从天气后报历史天气网（lishi.tianqi.com）爬取长沙市 2022 年全年 365 天的每日天气数据（日期、最高气温、最低气温、天气现象），完成数据清洗、分组统计，并生成多种可视化图表，总结长沙全年天气分布规律。

## 技术栈
- **爬虫**：requests + lxml（XPath 解析）
- **反爬破解**：还原网页混淆 JS，用 pycryptodome 复现 AES-CBC 加密参数，调通"查看更多"数据接口
- **数据存储**：csv 模块持久化
- **数据清洗**：pandas（去重、类型转换、缺失处理、groupby 分组统计）
- **可视化**：matplotlib（折线图/饼图/柱状图）、pyecharts（Timeline+Bar 月度轮播图）

## 文件说明
| 文件 | 说明 |
|---|---|
| changsha_weather_2022.py | 完整源代码（爬取→存储→清洗→可视化全流程） |
| weather.csv | 爬取的原始数据（365 行） |
| weather_clean.csv | pandas 清洗后的数据（含月份列） |
| line_temp.png | 全年每日最高/最低气温折线图 |
| pie_weather.png | 全年天气类型占比饼图 |
| bar_weather.png | 每月天气类型天数堆叠柱状图 |
| weathers1.html | pyecharts 月度天气轮播柱状图（浏览器打开） |

## 运行方法
```
pip install requests lxml pandas matplotlib pyecharts pycryptodome
python changsha_weather_2022.py
```

## 分析结论
- 长沙 2022 年以多云为主（209 天，57.3%），其次晴 71 天、雨 58 天、阴 22 天
- 气温呈"冬冷夏热"单峰曲线：极端最低 -3℃（1 月），极端最高 40℃（7-8 月）
- 降雨集中在 5-6 月（夏汛），冬季干燥少雨，冬季出现 4 天降雪

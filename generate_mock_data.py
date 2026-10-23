#!/usr/bin/env python3
"""
生成 L2-01-02 集团合并利润汇总表 模拟虚拟数据
参考真实数据结构：长表，每个结构 × 12个月 × 加载年月
"""
import random
from openpyxl import Workbook

# ========== 配置 ==========
OUTPUT_FILE = r"C:\Users\Zhujh\OneDrive - IPowerBI\CMOC Group - 文档\05.345项目\05.模拟数据\L2-01-02 集团合并利润汇总表_模拟数据.xlsx"

# 利润项目列表（结构排序: 结构名称）
STRUCTURES = [
    (2, "铜钴板块"),
    (3, "铜钴未实现毛利"),
    (4, "铌磷板块"),
    (5, "钼钨板块"),
    (6, "巴西金矿"),
    (7, "华越"),
    (8, "销售平台"),
    (9, "集采业务"),
    (10, "贸易板块"),
    (11, "金融投资"),
    (12, "金融衍生品"),
    (13, "总部费用"),
    (14, "电力事业部"),
    (15, "其他业务"),
]

# 加载年月列表（2026年1月~10月）
LOAD_YEARS = ["202601", "202602", "202603", "202604", "202605", "202606", "202607", "202608", "202609", "202610"]

# 月份列表
MONTHS = [
    (1, "1月", "Q1"), (2, "2月", "Q1"), (3, "3月", "Q1"),
    (4, "4月", "Q2"), (5, "5月", "Q2"), (6, "6月", "Q2"),
    (7, "7月", "Q3"), (8, "8月", "Q3"), (9, "9月", "Q3"),
    (10, "10月", "Q4"), (11, "11月", "Q4"), (12, "12月", "Q4"),
]

# 每个板块的基准营收（万元）
BASE_REVENUE = {
    "铜钴板块": 50000,
    "铜钴未实现毛利": 8000,
    "铌磷板块": 15000,
    "钼钨板块": 12000,
    "巴西金矿": 20000,
    "华越": 8000,
    "销售平台": 30000,
    "集采业务": 25000,
    "贸易板块": 40000,
    "金融投资": 5000,
    "金融衍生品": -2000,
    "总部费用": -10000,
    "电力事业部": 8000,
    "其他业务": 3000,
}

# ========== 生成数据 ==========
wb = Workbook()
ws = wb.active
ws.title = "L2-01-02 集团合并利润汇总表"

# 表头
headers = [
    "加载年月", "结构唯一ID", "季度", "当月YTD", "同比YTD", "去年同期YTD",
    "预算YTD", "预算达成率", "环比MTD", "当月MTD", "上月MTD",
    "月份", "实际值", "月份排序", "结构", "结构排序"
]
ws.append(headers)

random.seed(42)  # 固定随机种子，保证每次生成一样

for load_year in LOAD_YEARS:
    load_month_num = int(load_year[4:6])  # 1~4月
    
    for struct_sort, struct_name in STRUCTURES:
        # 基准值
        base = BASE_REVENUE.get(struct_name, 1000)
        
        # 结构唯一ID（模拟BW的格式）
        struct_id = f"[4VGQHR12MHZ3FU4L96KDFQ9OO].[MOCK_{struct_sort:02d}XXX]"
        
        for month_sort, month_name, quarter in MONTHS:
            # 分月实际值：只有<=当前加载月的月份才有数据
            if month_sort <= load_month_num:
                # 生成合理的月度数据
                monthly_factor = 0.8 + random.random() * 0.4  # 0.8~1.2 波动
                actual_value = int(base * monthly_factor / 12 * month_sort)  # 累计YTD
                monthly_value = int(base * monthly_factor / 12)  # 当月值
                
                # YTD值 = 截止当月的累计
                ytd_value = actual_value
                
                # 去年同期 = YTD * (0.9~1.1)
                last_year_ytd = int(ytd_value * (0.9 + random.random() * 0.2))
                
                # 同比变化率 = (今年-去年)/去年
                yoy_ytd = round((ytd_value - last_year_ytd) / last_year_ytd, 4) if last_year_ytd != 0 else 0
                
                # 预算 = YTD * (0.95~1.05)
                budget_ytd = int(ytd_value * (0.95 + random.random() * 0.1))
                
                # 预算达成率 = 实际/预算
                budget_rate = round(ytd_value / budget_ytd, 4) if budget_ytd != 0 else 0
                
                # 上月MTD
                if month_sort > 1:
                    last_month_value = int(base * (0.8 + random.random() * 0.4) / 12 * (month_sort - 1))
                else:
                    last_month_value = 0
                
                # 环比变化率
                if last_month_value != 0 and monthly_value != 0:
                    mom_mtd = round((monthly_value - last_month_value) / last_month_value, 4)
                else:
                    mom_mtd = 0
                
                # 当月MTD = 当月值
                current_mtd = monthly_value
                
            else:
                # 未来月份没有数据
                actual_value = 0
                ytd_value = 0
                last_year_ytd = 0
                yoy_ytd = 0
                budget_ytd = 0
                budget_rate = 0
                current_mtd = 0
                last_month_value = 0
                mom_mtd = 0
            
            row = [
                load_year,           # 加载年月
                struct_id,           # 结构唯一ID
                quarter,             # 季度
                ytd_value,           # 当月YTD
                yoy_ytd,             # 同比YTD
                last_year_ytd,       # 去年同期YTD
                budget_ytd,          # 预算YTD
                budget_rate,         # 预算达成率
                mom_mtd,             # 环比MTD
                current_mtd,         # 当月MTD
                last_month_value,    # 上月MTD
                month_name,          # 月份
                actual_value,        # 实际值
                month_sort,          # 月份排序
                struct_name,         # 结构
                struct_sort,         # 结构排序
            ]
            ws.append(row)

# 保存
wb.save(OUTPUT_FILE)
print(f"模拟数据已生成：{OUTPUT_FILE}")
print(f"共 {ws.max_row - 1} 行数据")
print(f"列：{headers}")

# -*- coding: utf-8 -*-
"""财务自由年限计算器 v1.1
覆盖：4%法则(FIRE数字) / 储蓄率→退休年限 / Coast FIRE 临界点

依赖：仅 Python 标准库（json / argparse），无需 pip 安装任何第三方包
用法：
    python3 fire_calc.py                       # 用内置示例数据演示
    python3 fire_calc.py --config fire.json    # 用自己的数据
"""
import json, argparse

# 内置示例（不带 --config 时使用）
DEMO = {
  "name": "示例：30岁 / 年收入24万 / 年支出14.4万",
  "annual_income": 240000,
  "annual_expense": 144000,
  "swr": 0.04,
  "real_return": 0.05,
  "current_assets": 180000,
  "coast_years": 20,
}

def fire_number(annual_expense, swr=0.04):
    return annual_expense / swr

def years_to_fi(save_rate, real_return=0.05, start=0.0):
    """储蓄率→财务自由年限（从零储蓄起）
    模型：每月余额按实际收益率复利 + 每月储蓄；终点=年支出×25"""
    if save_rate <= 0: return float('inf')
    if save_rate >= 1: return 0.0
    monthly_r = (1 + real_return) ** (1/12) - 1
    # 以"年支出=1"为单位：月储蓄 = save_rate/(1-save_rate) /12 × 年支出
    annual_income = 1.0 / (1 - save_rate)          # 令年支出=1
    monthly_save = annual_income * save_rate / 12
    target = 25.0                                   # 年支出(1) × 25
    bal, months = start, 0
    while bal < target and months < 1200:           # 上限100年
        bal = bal * (1 + monthly_r) + monthly_save
        months += 1
    return months / 12

def coast_fire(current_assets, annual_expense, years, real_return=0.05):
    """Coast FIRE：当前资产按复利增长，years年后能否达到FIRE数字"""
    target = fire_number(annual_expense)
    future = current_assets * ((1 + real_return) ** years)
    return target, future, future >= target

def run(c):
    e = c["annual_expense"]; inc = c["annual_income"]
    sr = (inc - e) / inc
    swr = c.get("swr", 0.04); rr = c.get("real_return", 0.05)
    print("="*68); print(f"财务自由测算 · {c['name']}".center(56)); print("="*68)
    fn = fire_number(e, swr)
    print(f"\n【4%法则】FIRE 目标本金 = 年支出 ÷ 安全提取率")
    print(f"  年支出 {e:,.0f} 元  ÷  {swr*100:.1f}%  =  {fn:,.0f} 元  （即年支出 × {1/swr:.0f} 倍）")
    print(f"  达到后每年可提取 {fn*swr:,.0f} 元，且组合有较大概率支撑 30 年以上")
    print(f"\n【储蓄率】月收入 {inc/12:,.0f} 元 | 年支出 {e:,.0f} 元")
    print(f"  储蓄率 = (收入 − 支出) ÷ 收入 = {sr*100:.1f}%")
    y = years_to_fi(sr, rr)
    print(f"  按实际年化 {rr*100:.1f}% 测算 → 还需工作约 {y:.1f} 年")
    print("\n【储蓄率 → 年限对照表】(7%名义 − 2.5%通胀 ≈ 4.4%实际口径，本表按模型一贯口径)")
    print(f"  {'储蓄率':<8}{'年限':>8}   {'':<22}")
    for s in [0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80]:
        yy = years_to_fi(s, rr)
        bar = "█" * max(1, int((60-yy)/2))
        mark = "  ⬅ 你的位置" if abs(s-sr)<0.025 else ""
        print(f"  {s*100:>5.0f}%  {yy:>7.1f} 年  {bar}{mark}")
    if c.get("current_assets"):
        t, f, ok = coast_fire(c["current_assets"], e, c.get("coast_years",20), rr)
        print(f"\n【Coast FIRE 检查】当前可投资资产 {c['current_assets']:,.0f} 元")
        print(f"  若从此不再新增投入，{c.get('coast_years',20)} 年后按 {rr*100:.1f}% 复利 → {f:,.0f} 元")
        print(f"  FIRE 目标 {t:,.0f} 元 → {'✅ 已达成 Coast FIRE，之后只需赚够日常开销' if ok else '❌ 尚未达成，仍需继续储蓄'}")
    print("\n" + "-"*68)
    print("⚠ 4%法则的局限：第1步 源于美国历史数据，其他市场需下调至 3%–3.5%")
    print("  第2步 未计入大额医疗/长期护理支出 第3步 退休前 5 年遇股灾（序列风险）杀伤极大")
    print("  → 保守做法：把提取率降到 3.25%，或为退休初期预留 2–3 年现金桶")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", help="JSON 配置文件路径；省略则使用内置示例")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8")) if a.config else DEMO
    run(cfg)

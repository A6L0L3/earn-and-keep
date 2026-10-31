# -*- coding: utf-8 -*-
"""个人财务体检 v1.1 —— 守库/截流/开流/增值 四维打分

依赖：仅 Python 标准库（json / argparse），无需 pip 安装任何第三方包
用法：
    python3 finance_check.py                      # 用内置示例数据演示
    python3 finance_check.py --config my.json     # 用自己的数据

配置字段说明见同目录 my_finance.json。
"""
import json, argparse

# 内置示例（不带 --config 时使用）；改成自己的数字即可直接跑
DEMO = {
  "name": "示例：28岁 / 月入1.5万 / 一线城市",
  "monthly_income": 15000,
  "monthly_expense": {"居住": 4200, "餐饮": 2600, "交通": 700,
                      "购物": 1800, "人情": 900, "娱乐": 1100, "通信": 300},
  "micro_habits": {"每天一杯咖啡": 9000, "每周3次打车": 6240, "自动续费会员": 1400},
  "emergency_fund": 20000,
  "liquid_assets": 120000,
  "insurance": {"医疗险": True, "重疾险": False, "意外险": True, "定期寿险": False},
  "high_interest_debt": 30000,
  "debt_apr": 0.18,
  "income_sources": {"主动收入": 180000, "技能收入": 6000, "资产收入": 0},
  "invested_assets": 40000,
  "idle_cash": 80000,
}

def band(v, good, ok, name, unit="", reverse=False):
    if not reverse:
        lv = "达标" if v >= good else ("警戒" if v >= ok else "危险")
    else:
        lv = "达标" if v <= good else ("警戒" if v <= ok else "危险")
    return lv

def run(c: dict):
    print("="*68); print(f"财务体检报告 · {c['name']}".center(58)); print("="*68)
    inc, exp = c["monthly_income"], sum(c["monthly_expense"].values())
    save = inc - exp
    sr = save/inc
    print(f"\n【截流】月收入 {inc:,.0f} 元 | 月支出 {exp:,.0f} 元 | 月结余 {save:,.0f} 元")
    print(f"  储蓄率 = {sr*100:.1f}%   标准: <10%危险 / 10-20%警戒 / ≥20%达标")
    print(f"  判定: {band(sr, .20, .10, 'sr')}")
    print("  支出结构（按占比降序）:")
    for k, v in sorted(c["monthly_expense"].items(), key=lambda x: -x[1]):
        bar = "█" * int(v/inc*40)
        print(f"    {k:<8} {v:>8,.0f} ({v/inc*100:>5.1f}%) {bar}")
    # 年度化：把小额高频支出放大，暴露"隐形黑洞"
    print("\n  ⚠ 年度化换算（小额高频 → 年支出）:")
    for k, v in c.get("micro_habits", {}).items():
        print(f"    {k:<14} {v:>6,.0f} 元/年   10年复利(按5%)≈ {v*((1.05**10-1)/0.05)*1.05:>10,.0f} 元")

    em, asset = c["emergency_fund"], c["liquid_assets"]
    months = em/exp if exp else 0
    print(f"\n【守库】应急金 {em:,.0f} 元 / 月支出 {exp:,.0f} 元 = 可支撑 {months:.1f} 个月")
    print(f"  判定: {band(months, 6, 3, 'em')}   (≥6个月达标 / 3-6警戒 / <3危险)")
    ins = c.get("insurance", {})
    miss = [k for k, v in {"医疗险":1,"重疾险":1,"意外险":1,"定期寿险":1}.items() if not ins.get(k)]
    print(f"  保障配齐度: {'✅ 四类齐全' if not miss else '❌ 缺: ' + '、'.join(miss)}")
    debt = c.get("high_interest_debt", 0); rate = c.get("debt_apr", 0.18)
    print(f"  高息负债: {debt:,.0f} 元 @ {rate*100:.1f}%  "
          f"→ 年利息 {debt*rate:,.0f} 元（{'优先清偿，优于任何投资' if debt>0 else '无'}）")
    dti = debt/inc if inc else 0
    print(f"  负债/月收入 = {dti:.1f} 倍  {'⚠ 超过6倍属高危' if dti>6 else ''}")

    src = c.get("income_sources", {})
    tot = sum(src.values()) or 1
    active = src.get("主动收入", 0)/tot
    print(f"\n【开流】收入结构（主动收入占比 {active*100:.1f}%）:")
    for k, v in sorted(src.items(), key=lambda x: -x[1]):
        print(f"    {k:<10} {v:>8,.0f} ({v/tot*100:>5.1f}%) {'█'*int(v/tot*30)}")
    print(f"  判定: {'危险·单柱风险' if active>.9 else ('警戒·建议启动第二收入线' if active>.7 else '达标·结构健康')}")

    inv, idle = c.get("invested_assets", 0), c.get("idle_cash", 0)
    print(f"\n【增值】投资资产 {inv:,.0f} 元 | 闲置活期 {idle:,.0f} 元")
    if asset:
        idle_r = idle/asset
        print(f"  闲置现金占总资产 {idle_r*100:.1f}%  "
              f"{'⚠ 死水型：收益被通胀侵蚀' if idle_r>.4 else ('合理' if idle_r>.1 else '⚠ 缓冲不足')}")
    print(f"  投资/总资产 = {inv/asset*100:.1f}% (若资产={asset:,.0f})" if asset else "")

    # 四维总分
    scores = {"守库": 0, "截流": 0, "开流": 0, "增值": 0}
    scores["守库"] = 2 if months>=6 else (1 if months>=3 else 0)
    scores["守库"] = max(0, scores["守库"] - (1 if miss else 0) - (1 if debt/ (inc or 1) > 6 else 0))
    scores["截流"] = 2 if sr>=.2 else (1 if sr>=.1 else 0)
    scores["开流"] = 2 if active<=.7 else (1 if active<=.9 else 0)
    scores["增值"] = 2 if (asset and .1 <= idle/asset <= .4) else 1 if asset else 0
    print("\n" + "-"*68)
    print("四维评分（每项 0–2 分）:")
    for k, v in scores.items():
        print(f"    {k}  {'●'*v}{'○'*(2-v)}  {v}/2")
    weak = min(scores, key=scores.get)
    order = ["守库", "截流", "开流", "增值"]
    print(f"\n>>> 总分 {sum(scores.values())}/8　最弱环节：{weak}")
    print(f">>> 建议修复顺序：{' → '.join(sorted(order, key=lambda x: scores[x]))}")
    print(">>> 铁律：先守库，再截流，后开流，最后增值。底板漏了，前面全白干。")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", help="JSON 配置文件路径；省略则使用内置示例")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8")) if a.config else DEMO
    run(cfg)

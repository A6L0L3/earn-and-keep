# -*- coding: utf-8 -*-
"""组合再平衡计算器 v1.1
支持：目标比例 / 当前市值 -> 调仓指令；阈值触发判定；定投加钱的最优分配

依赖：仅 Python 标准库（json / argparse），无需 pip 安装任何第三方包
用法：
    python3 rebalance.py                          # 用内置示例数据演示
    python3 rebalance.py --config portfolio.json  # 用自己的数据
"""
import json, argparse

# 内置示例（不带 --config 时使用）
DEMO = {
  "name": "示例：35岁稳健型组合",
  "target": {"A股宽基ETF": 0.30, "海外宽基ETF": 0.20,
             "债券/固收": 0.35, "黄金ETF": 0.05, "现金/货币": 0.10},
  "current": {"A股宽基ETF": 128000, "海外宽基ETF": 62000,
              "债券/固收": 70000, "黄金ETF": 15000, "现金/货币": 25000},
  "new_cash": 20000,
  "abs_band": 0.05,
  "rel_band": 0.25,
  "dca_monthly": 5000,
}

def plan(target, current, cash=0.0, abs_band=0.05, rel_band=0.25):
    total = sum(current.values()) + cash
    rows, actions = [], []
    for k in target:
        cur = current.get(k, 0.0)
        tgt_val = total * target[k]
        diff = tgt_val - cur
        cur_pct = cur/sum(current.values()) if sum(current.values()) else 0
        dev = cur_pct - target[k]
        # 触发规则：绝对偏离 > abs_band 且 相对偏离 > rel_band
        rel = abs(dev)/target[k] if target[k] else 0
        trig = abs(dev) > abs_band and rel > rel_band
        rows.append((k, cur, cur_pct, target[k], tgt_val, diff, dev, rel, trig))
        actions.append((k, diff))
    return total, rows, actions

def run(c):
    tgt, cur, cash = c["target"], c["current"], c.get("new_cash", 0)
    ab, rb = c.get("abs_band", .05), c.get("rel_band", .25)
    print("="*74); print(f"组合再平衡方案 · {c['name']}".center(64)); print("="*74)
    total, rows, actions = plan(tgt, cur, cash, ab, rb)
    print(f"当前市值 {sum(cur.values()):,.0f} 元 + 新增资金 {cash:,.0f} 元 = 总盘子 {total:,.0f} 元\n")
    print(f"{'资产':<12}{'当前市值':>10}{'当前%':>8}{'目标%':>8}{'目标市值':>11}{'调仓额':>11}{'触发':>7}")
    print("-"*74)
    for k, cur_v, cp, tp, tv, diff, dev, rel, trig in rows:
        act = "买入" if diff > 0 else "卖出"
        print(f"{k:<12}{cur_v:>10,.0f}{cp*100:>7.1f}%{tp*100:>7.1f}%{tv:>11,.0f}"
              f"{act}{abs(diff):>9,.0f}{'  ⚑' if trig else '   ':>7}")
    print("-"*74)
    trig = [r for r in rows if r[8]]
    cash_needed = sum(d for _, d in actions if d > 0)
    print(f"\n触发再平衡的资产：{('、'.join(r[0] for r in trig)) if trig else '无（全部在容忍带内）'}")
    print(f"需要买入总额 {cash_needed:,.0f} 元 / 卖出释放 {sum(-d for _,d in actions if d<0):,.0f} 元")
    if cash >= cash_needed:
        print(f"✅ 新增资金 {cash:,.0f} 元 已可覆盖全部买入需求，无需卖出（最省税费的路径）")
        print(f"   剩余 {cash-cash_needed:,.0f} 元 按目标比例补入最大缺口项")
    else:
        print(f"⚠ 新增资金不足，需卖出 {cash_needed-cash:,.0f} 元 资产腾挪")
    # 阈值说明
    print(f"\n触发规则：绝对偏离 > {ab*100:.0f}% 且 相对偏离 > {rb*100:.0f}%（双条件，避免频繁调仓）")
    # 定投补入演示
    if c.get("dca_monthly"):
        m = c["dca_monthly"]
        print(f"\n【定投分配演示】每月 {m:,.0f} 元，按“缺口优先”分配：")
        gaps = sorted([(k, d) for k, d in actions if d > 0], key=lambda x: -x[1])
        for k, d in gaps:
            share = min(m, d) if gaps else 0
            print(f"   {k:<12} 补入 {share:>8,.0f} 元 (缺口 {d:,.0f})")
            m -= share
            if m <= 0: break
        if m > 0: print(f"   其余 {m:,.0f} 元 按目标比例分配")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", help="JSON 配置文件路径；省略则使用内置示例")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8")) if a.config else DEMO
    run(cfg)

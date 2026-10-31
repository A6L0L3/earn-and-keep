# -*- coding: utf-8 -*-
"""仓位管理器 v1.0 —— 凯利公式 / 半凯利 / 2%法则 / 止损反推仓位
依赖：仅 Python 标准库（argparse），无需 pip 安装任何第三方包
用法: python3 position.py            （内置演示：敏感度矩阵 + 三个算例 + 2%法则表）
      python3 position.py --p 0.6 --b 2.5                  （指定胜率与盈亏比）
      python3 position.py --total 1000000 --stop 0.10      （2%法则反推仓位）
"""
import argparse

def kelly(p, b):
    """f* = (b*p - q)/b = p - q/b
    p=胜率  b=盈亏比(平均盈利/平均亏损)  q=1-p"""
    return p - (1 - p) / b

def two_pct_rule(total, stop_pct, risk_pct=0.02):
    """2%法则：最大仓位 = 单笔最大亏损额 ÷ 止损幅度"""
    return total * risk_pct / stop_pct

def verdict(f, cap_single=0.25, cap_total=0.80):
    half = f / 2
    quarter = f / 4
    return {
        "满凯利": f, "半凯利(推荐)": min(half, cap_single),
        "1/4凯利(保守)": min(quarter, cap_single),
    }

def run_demo(p=None, b=None, total=None, stop=None):
    print("="*70); print("仓位管理器 · 凯利公式与实战降级方案".center(52)); print("="*70)
    if p is None:
        print("\n【一】敏感度矩阵：不同胜率 p 与盈亏比 b 下的满凯利仓位 f*")
        hdr = "p\\b"
        print("\n  " + hdr.ljust(7) + "".join(f"{bb:>9.1f}" for bb in [1.0,1.5,2.0,2.5,3.0,4.0,5.0]))
        print("  " + "-"*68)
        for pp in [0.35,0.40,0.45,0.50,0.55,0.60,0.65,0.70,0.80]:
            row = f"  {pp*100:>4.0f}%  "
            for bb in [1.0,1.5,2.0,2.5,3.0,4.0,5.0]:
                f = kelly(pp, bb)
                cell = f"{f*100:>7.0f}%" if f > 0 else f"{'空仓':>8}"
                row += cell
            print(row)
        print("\n  读法：f* ≤ 0 → 负期望值，应当空仓。")
        print("        低胜率必须靠高盈亏比弥补（右侧两列），反之亦然。")
        print("        例：胜率仅 40% 时，盈亏比必须 ≥ 1.5 才有正期望。")

        print("\n【二】实战降级：为什么不能直接用满凯利")
        print(f"  {'维度':<14}{'满凯利':<14}{'半凯利':<14}{'1/4凯利'}")
        print("  " + "-"*56)
        rows = [("长期增长率","最大","约为满凯利75%","约为满凯利40%"),
                ("最大回撤","可能超50%","约25%","约12%"),
                ("心理压力","极大","可承受","很小"),
                ("参数误差容忍","极低","较高","很高"),
                ("破产风险","有","极低","几乎无")]
        for r in rows:
            print(f"  {r[0]:<14}{r[1]:<14}{r[2]:<14}{r[3]}")

        print("\n【三】两个算例")
        for name, pp, bb in [("趋势股：胜率60%、盈亏比2.5", 0.60, 2.5),
                             ("价值股：胜率70%、盈亏比1.5", 0.70, 1.5),
                             ("低胜率高赔率：胜率35%、盈亏比4", 0.35, 4.0)]:
            f = kelly(pp, bb)
            print(f"\n  {name}")
            if f <= 0:
                print(f"    f* = {f*100:.1f}%  → 负期望，空仓")
                continue
            v = verdict(f)
            for k, val in v.items():
                print(f"    {k:<16} {val*100:>6.1f}%")
            print(f"    ⚠ 单票硬上限 25%，总仓硬上限 80%（留现金防黑天鹅）")
    else:
        f = kelly(p, b)
        print(f"\n输入：胜率 p={p*100:.0f}%　盈亏比 b={b}")
        print(f"满凯利 f* = p − (1−p)/b = {f*100:.2f}%")
        if f <= 0:
            print("→ 负期望值，应当空仓。不要交易。")
            return
        for k, val in verdict(f).items():
            print(f"  {k:<16} {val*100:>6.2f}%")

    print("\n【四】2%法则：不想算凯利时的最简方案")
    print("  最大仓位 = (总资金 × 单笔最大亏损比例) ÷ 止损幅度")
    if total and stop:
        pos = two_pct_rule(total, stop)
        print(f"\n  总资金 {total:,.0f} 元，止损幅度 {stop*100:.0f}%")
        print(f"  最大仓位 = {total:,.0f} × 2% ÷ {stop*100:.0f}% = {pos:,.0f} 元 "
              f"（占总资金 {pos/total*100:.1f}%）")
    else:
        print(f"\n  {'止损幅度':<10}{'最大仓位(占总资金)':>22}{'100万本金对应金额':>20}")
        print("  " + "-"*54)
        for s in [0.05, 0.08, 0.10, 0.15, 0.20]:
            frac = two_pct_rule(1.0, s)
            print(f"  {s*100:>5.0f}%    {frac*100:>18.0f}%    {frac*1000000:>17,.0f} 元")
        print("\n  读法：止损放得越宽，单笔仓位就必须越小——这是数学约束，不是建议。")
    print("\n  核心：亏损 50% 需涨 100% 才回本，仓位失控 = 自杀。")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--p", type=float); ap.add_argument("--b", type=float)
    ap.add_argument("--total", type=float); ap.add_argument("--stop", type=float)
    a = ap.parse_args()
    run_demo(a.p, a.b, a.total, a.stop)

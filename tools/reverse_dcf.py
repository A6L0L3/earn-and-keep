# -*- coding: utf-8 -*-
"""逆向DCF v1.0 —— 从市价反推"市场在假设什么"
正向DCF：预测现金流 → 折现 → 得内在价值 → 与市价比较
逆向DCF：市价已知 → 反解出使DCF等于市价的那个隐含增长率 → 判断该假设是否合理
依赖：仅 Python 标准库（argparse / sys），无需 pip 安装任何第三方包
用法: python3 reverse_dcf.py            （内置演示三种典型场景）
      python3 reverse_dcf.py --price 100 --fcf 5 --r 0.10 --years 10 --tg 0.025
"""
import argparse, sys

def dcf_value(fcf0, g, r, years=10, tg=0.025):
    pv, fcf = 0.0, fcf0
    for t in range(1, years+1):
        fcf *= (1+g)
        pv += fcf / ((1+r)**t)
    tv = fcf*(1+tg)/(r-tg)
    return pv + tv/((1+r)**years)

def solve_g(price, fcf0, r, years=10, tg=0.025, lo=-0.20, hi=0.60):
    """二分法求解隐含增长率"""
    if dcf_value(fcf0, lo, r, years, tg) > price: return lo, "低于下界"
    if dcf_value(fcf0, hi, r, years, tg) < price: return hi, "高于上界"
    for _ in range(200):
        mid = (lo+hi)/2
        if dcf_value(fcf0, mid, r, years, tg) < price: lo = mid
        else: hi = mid
    return (lo+hi)/2, "已求解"

def rdict(price, fcf0, r, years, tg, name, bench):
    g, note = solve_g(price, fcf0, r, years, tg)
    print("="*74)
    print(f"逆向DCF · {name}".center(60))
    print("="*74)
    print(f"  当前市价 {price:.2f} 元 | 起点自由现金流 {fcf0:.2f} 元/股")
    print(f"  折现率 r={r*100:.1f}% | 显式期 {years} 年 | 永续增长 tg={tg*100:.1f}%")
    print(f"\n  >>> 市场隐含的【显式期年化增长率】= {g*100:.2f}%   ({note})")
    print(f"  >>> 参照基准：{bench}")
    if g > 0.15:
        print("  >>> 判读：⚠ 隐含增长 > 15%，市场已在为极高的成长预期定价。")
        print("      除非你能举出该增速的硬证据（产能、订单、渗透率斜率），否则偏贵。")
    elif g > 0.08:
        print("  >>> 判读：⚠ 隐含增长 8%–15%，属于乐观区间。能长期做到 7%–8% 已是顶尖。")
    elif g > 0.02:
        print("  >>> 判读：✅ 隐含增长 2%–8%，处于合理区间，估值未透支。")
    elif g >= 0:
        print("  >>> 判读：✅ 隐含增长 0%–2%，市场假设接近零增长——悲观定价。")
    else:
        print("  >>> 判读：✅ 隐含增长为负，市场在假设这家公司会持续萎缩。")
        print("      若你判断它只是周期性低谷而非永久衰退，这里可能是机会。")
    # 敏感性：若按你自己假设的增长率，价值是多少
    print(f"\n  反向验证——若按不同增长率，对应的内在价值：")
    print(f"    {'假设增长率':<12}{'内在价值':>12}{'相对市价':>12}")
    for gg in [0.0, 0.03, 0.05, 0.08, 0.12, 0.15]:
        v = dcf_value(fcf0, gg, r, years, tg)
        d = (v-price)/price*100
        print(f"    {gg*100:>8.0f}%   {v:>11.2f}   {d:>+10.1f}%")
    return g

def demo():
    print("\n" + "#"*74)
    print("# 逆向DCF：不问「它值多少」，而问「市场在假设什么」")
    print("#"*74)
    print("""
正向DCF 的最大问题：所有输入都是你的主观假设，你很容易把乐观藏进 g 里。
逆向DCF 把这个顺序反过来——承认市价是对的，倒推出市场 consensus 隐含的
增长率，再判断"这个假设我信不信"。

这一步的价值在于：它把"贵不贵"的争论，转化成"你信不信这个增速"的具体问题。
""")
    # 场景1 高估值成长股
    rdict(price=100, fcf0=2.0, r=0.10, years=10, tg=0.025,
          name="场景一：高估值成长股（起点自由现金流仅 2 元）",
          bench="行业长期增速 3%，该公司过去 5 年实际增速 6%")
    print()
    # 场景2 合理估值蓝筹
    rdict(price=40, fcf0=3.0, r=0.10, years=10, tg=0.025,
          name="场景二：稳定蓝筹（起点自由现金流 3 元）",
          bench="行业长期增速 3%，公司历史增速 4%")
    print()
    # 场景3 深度低估
    rdict(price=20, fcf0=4.0, r=0.10, years=10, tg=0.025,
          name="场景三：被冷落的低估股（起点自由现金流 4 元）",
          bench="行业长期增速 2%，公司历史增速 3%")
    print("\n" + "="*74)
    print("使用要点：")
    print("  1. 起点自由现金流必须用【所有者盈余】而非净利润（见板块4_3）")
    print("  2. 若求出的 g > 15% 或 < 0%，先怀疑自己的起点现金流，再怀疑市场")
    print("  3. 逆向DCF 是【合理性检验】，不是买入信号——")
    print("     即使隐含增长为负，也要先排除「这是价值陷阱」的可能")
    print("  4. 配合板块5的三重交叉估值使用，作为第四个视角")
    print("="*74)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--price", type=float); ap.add_argument("--fcf", type=float)
    ap.add_argument("--r", type=float, default=0.10)
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--tg", type=float, default=0.025)
    a = ap.parse_args()
    if a.price and a.fcf:
        rdict(a.price, a.fcf, a.r, a.years, a.tg, "自定义场景", "（请自行设定参照基准）")
    else:
        demo()

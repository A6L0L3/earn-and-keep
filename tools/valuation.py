# -*- coding: utf-8 -*-
"""
价值估值计算器 v1.1  —— 修复 v1.0 "机械取最小值" 缺陷
v1.0 BUG：对持续经营企业直接取 min()，会被清算价值(NCAV)压垮，
          得出 -700% 安全边际这类无意义结论。
v1.1 修复：引入"有意义性闸门"——清算价值只有在标的确实落入烟蒂区间时才作为主锚；
           否则以持续经营类估值(DCF / 格雷厄姆数 / 成长公式)取低者。
新增：--mode {auto,liquidation,going_concern}  --test 回归测试

依赖：仅 Python 标准库（json / math / argparse），无需 pip 安装任何第三方包
用法：
    python3 valuation.py                        # 用内置示例数据演示
    python3 valuation.py --config demo.json     # 用自己的数据
    python3 valuation.py --config demo.json --mode liquidation
    python3 valuation.py --test                 # 跑 5 项回归测试（内置数据，无需外部文件）
"""
import json, math, argparse

# 内置示例（不带 --config 时使用）。
# 注意：v1.0 曾把测试数据写死在外部绝对路径，换到别的目录就跑不起来。
# v1.2 改为内置，脚本完全自包含——复制到任何地方都能直接运行。
DEMO = {
  "name": "示例：某制造业公司（单位：万元 / 万股）",
  "price": 32.0,
  "shares": 10000,
  "balance": {"current_assets": 100000, "total_liab": 60000, "preferred": 0,
              "cash": 30000, "ar": 25000, "inventory": 40000, "prepaid": 5000},
  "income": {"eps": 3.20, "bvps": 28.50, "g": 5.0, "aaa_yield": 4.4,
             "net_income": 32000, "da": 6000, "maint_capex": 5000, "dwc": 2000},
  "dcf": {"g": 0.03, "r": 0.10, "years": 10, "tg": 0.025},
}

# ---------- 基础公式 ----------
def ncav(ca, tl, pref, shares):          return (ca - tl - pref) / shares
def nnwc(cash, ar, inv, pre, tl, shares, ar_d=.75, inv_d=.50, pre_d=.25):
    return (cash + ar*ar_d + inv*inv_d + pre*pre_d - tl) / shares
def graham_number(eps, bvps):
    if eps <= 0 or bvps <= 0: return None
    return math.sqrt(22.5 * eps * bvps)
def graham_growth(eps, g, y=None, base=4.4):
    v = eps * (8.5 + 2*g);  return v if y is None else v * base / y
def owner_earnings(ni, da, mc, dwc):     return ni + da - mc - dwc
def dcf(fcf0, g, r, years=10, tg=0.025):
    pv = 0.0; fcf = fcf0
    for t in range(1, years+1):
        fcf *= (1+g); pv += fcf / ((1+r)**t)
    tv = fcf*(1+tg)/(r-tg)
    return pv + tv/((1+r)**years)

EPS_TOL = 1e-9
def mos_band(iv, price):
    """安全边际分档。
    边界语义（重要）：折扣率恰好落在分界点(30%/40%/50%)时，归入【仓位更小、
    更严格】的一档。理由——估值本身有误差，边界值应从严处理。
    故：>50% -> 深度； [40%,50%] -> 便宜； [30%,40%) -> 勉强； <30% -> 不买。"""
    m = (iv - price)/iv
    if   m >  .50 + EPS_TOL: return m, "深度低估(>50%)",   "≤15%"
    elif m >= .40 - EPS_TOL: return m, "便宜低估(40–50%)", "≤10%"
    elif m >= .30 - EPS_TOL: return m, "勉强便宜(30–40%)", "≤5%"
    return m, "不够便宜(<30%)", "0%（不买入）"

# ---------- 核心：有意义性闸门 ----------
def pick_conservative(values, price, mode="auto"):
    """values: dict{方法名: 每股价值}
    返回 (保守内在价值, 采用的方法, 决策说明)"""
    liq = values.get("清算(NCAV)") or 0
    gc  = {k:v for k,v in values.items() if k != "清算(NCAV)" and v and v > 0}
    gc_min = min(gc.values()) if gc else None
    # 烟蒂判定：股价已跌破或逼近清算价值的 2/3 → 清算视角才有意义
    is_netnet = price <= liq * 2/3 and liq > 0
    if mode == "liquidation":
        return (liq if liq > 0 else gc_min), "清算(NCAV)", "强制清算口径"
    if mode == "going_concern":
        return gc_min, min(gc, key=gc.get), "强制持续经营口径"
    if is_netnet:
        return liq, "清算(NCAV)", f"股价{price} ≤ NCAV的2/3({liq*2/3:.2f})，落入烟蒂区间，清算值成为主锚"
    note = (f"股价{price} 远高于 NCAV({liq:.2f})，企业按持续经营定价；"
            f"清算值仅作压力测试下限，不参与取最小值")
    return gc_min, min(gc, key=gc.get), note

def run(cfg, mode="auto", verbose=True):
    p, sh = cfg["price"], cfg["shares"]; b, i, d = cfg["balance"], cfg["income"], cfg["dcf"]
    if verbose:
        print("="*66)
        print(f"标的：{cfg['name']}　现价 {p} 元　股本 {sh} 万股".center(56))
        print("="*66)
    v_ncav = ncav(b["current_assets"], b["total_liab"], b.get("preferred",0), sh)
    v_nnwc = nnwc(b["cash"], b["ar"], b["inventory"], b.get("prepaid",0), b["total_liab"], sh)
    gn  = graham_number(i["eps"], i["bvps"])
    g   = i.get("g", 0.0); y = i.get("aaa_yield")
    v62 = graham_growth(i["eps"], g)
    v74 = graham_growth(i["eps"], g, y) if y else v62
    oe  = owner_earnings(i["net_income"], i["da"], i["maint_capex"], i["dwc"])
    v_dcf = dcf(oe/sh, d["g"], d["r"], d.get("years",10), d.get("tg",.025))
    if verbose:
        print(f"[1] NCAV/股       = {v_ncav:>8.2f} 元   烟蒂买点(≤2/3) = {v_ncav*2/3:>7.2f} 元")
        print(f"[2] NNWC/股(打折) = {v_nnwc:>8.2f} 元   烟蒂买点(≤2/3) = {v_nnwc*2/3:>7.2f} 元")
        print(f"[3] 格雷厄姆数字   = {gn:>8.2f} 元   (EPS={i['eps']}, BVPS={i['bvps']})")
        print(f"[4] 成长公式1962  = {v62:>8.2f} 元   (g={g}%)")
        print(f"[5] 成长公式1974  = {v74:>8.2f} 元   (AAA债Y={y}%) ← 利率修正")
        print(f"[6] 所有者盈余     = {oe:>8.2f} 万元 (净利{i['net_income']}+折旧{i['da']}"
              f"-维持性资本开支{i['maint_capex']}-营运资本变动{i['dwc']})")
        print(f"[7] 简化DCF/股    = {v_dcf:>8.2f} 元   (g={d['g']*100:.1f}%, r={d['r']*100:.1f}%, 永续{d.get('tg',.025)*100:.1f}%)")
        print("-"*66); print("三重交叉估值：")
    values = {"清算(NCAV)": v_ncav, "格雷厄姆数": gn, "成长公式74": v74, "DCF": v_dcf}
    iv, method, note = pick_conservative(values, p, mode)
    if verbose:
        for k, v in values.items():
            if v is None: continue
            tag = "  ★采用" if k == method else ""
            print(f"    {k:<12} {v:>8.2f} 元{tag}")
        print(f"\n  决策说明：{note}")
        print(f">>> 保守内在价值 = {iv:.2f} 元（{method}）")
        m, band, cap = mos_band(iv, p)
        print(f">>> 安全边际 = ({iv:.2f} − {p}) / {iv:.2f} = {m*100:.1f}%")
        print(f">>> 评级：{band}　建议单股上限：{cap}")
        print(f">>> 卖出区间(内在价值90%–100%)：{iv*0.9:.2f} – {iv:.2f} 元")
        print(f">>> 清算下限压力测试：NCAV {v_ncav:.2f} 元 → 现价较清算值溢价 {(p/v_ncav-1)*100:.0f}%"
              if v_ncav > 0 else "")
    else:
        m, band, cap = mos_band(iv, p)
    return iv, m, band, cap

# ---------- 回归测试 ----------
def self_test():
    print("\n" + "#"*66); print("# 回归测试（v1.1）"); print("#"*66)
    base = json.loads(json.dumps(DEMO))          # 深拷贝内置示例，避免被后续用例污染
    # T1 持续经营企业：不得输出负的安全边际
    iv, m, band, cap = run(base, mode="auto", verbose=False)
    ok1 = -1.0 < m < 1.0
    print(f"[T1] 持续经营口径安全边际有界      -> {m*100:6.1f}%  {'PASS' if ok1 else 'FAIL'}")
    # T2 强制清算口径仍可用
    iv2, m2, *_ = run(base, mode="liquidation", verbose=False)
    ok2 = abs(iv2 - 4.0) < 1e-6
    print(f"[T2] 强制清算口径 IV==NCAV(4.00)   -> {iv2:6.2f}  {'PASS' if ok2 else 'FAIL'}")
    # T3 烟蒂场景：股价 2.0 <= NCAV*2/3(2.67) -> 主锚应切到清算值
    netnet = json.loads(json.dumps(base)); netnet["price"] = 2.0
    iv3, m3, b3, c3 = run(netnet, mode="auto", verbose=False)
    ok3 = abs(iv3 - 4.0) < 1e-6 and abs(m3 - 0.5) < 1e-6 and c3 == "≤10%"
    print(f"[T3] 烟蒂价2.0元 -> 主锚切清算且边界保守 -> IV={iv3:.2f}, MOS={m3*100:.1f}%, 仓位{c3}  {'PASS' if ok3 else 'FAIL'}")
    # T4 折价充分 -> 触发仓位上限
    deep = json.loads(json.dumps(base)); deep["price"] = 20.0
    iv4, m4, b4, c4 = run(deep, mode="auto", verbose=False)
    ok4 = c4 in ("≤10%", "≤15%")
    print(f"[T4] 现价20元 -> {b4}, 仓位上限{c4}        {'PASS' if ok4 else 'FAIL'}")
    # T5 边界：恰好 30% / 40% / 50%
    r70, r60, r50, r49, r75 = (mos_band(100,70), mos_band(100,60),
                               mos_band(100,50), mos_band(100,49), mos_band(100,75))
    ok5 = (r70[1].startswith("勉强") and r60[1].startswith("便宜")
           and r50[1].startswith("便宜") and r49[1].startswith("深度")
           and r75[2].startswith("0%"))
    print(f"[T5] 边界保守化: MOS30%->{r70[1][:4]} 40%->{r60[1][:4]} "
          f"50%->{r50[1][:4]}(从严) 51%->{r49[1][:4]} 25%->{r75[1][:4]}  {'PASS' if ok5 else 'FAIL'}")
    print(f"\n>>> 全部通过：{all([ok1,ok2,ok3,ok4,ok5])}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", help="JSON 配置文件路径；省略则使用内置示例")
    ap.add_argument("--mode", default="auto",
                    choices=["auto","liquidation","going_concern"])
    ap.add_argument("--test", action="store_true", help="运行内置回归测试")
    a = ap.parse_args()
    if a.test:
        self_test()
    else:
        cfg = json.load(open(a.config, encoding="utf-8")) if a.config else DEMO
        run(cfg, a.mode)

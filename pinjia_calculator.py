#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pinjia_calculator - 2026 年拼假计算器。

紧贴 2026 年热梗「请3休13」「请6休17」（中秋国庆拼假攻略）：
输入年假余额，算出全年每种拼法，按性价比排序，标出年度王炸。
纯 Python 标准库，无第三方依赖。
"""
import argparse
import calendar
import datetime as dt
import sys

YEAR = 2026

# ---------------------------------------------------------------------------
# 2026 年法定节假日安排（起止日期均已用 `date -d` 逐项核验星期，见 README）
# ---------------------------------------------------------------------------
HOLIDAYS = [
    ("元旦",   dt.date(2026, 1, 1),  dt.date(2026, 1, 3)),    # 周四~周六
    ("春节",   dt.date(2026, 2, 15), dt.date(2026, 2, 23)),   # 周日~周一，9天
    ("清明",   dt.date(2026, 4, 4),  dt.date(2026, 4, 6)),    # 周六~周一
    ("劳动节", dt.date(2026, 5, 1),  dt.date(2026, 5, 5)),    # 周五~周二
    ("端午",   dt.date(2026, 6, 19), dt.date(2026, 6, 21)),   # 周五~周日
    ("中秋",   dt.date(2026, 9, 25), dt.date(2026, 9, 27)),   # 周五~周日
    ("国庆",   dt.date(2026, 10, 1), dt.date(2026, 10, 7)),   # 周四~周三
]

# 调休上班日（落在周末但要上班的日子，请假也要烧年假）
WORK_WEEKENDS = {
    dt.date(2026, 1, 4),    # 周日
    dt.date(2026, 2, 14),   # 周六
    dt.date(2026, 2, 28),   # 周六
    dt.date(2026, 5, 9),    # 周六
    dt.date(2026, 9, 20),   # 周日
    dt.date(2026, 10, 10),  # 周六
}

MAX_SPEND = 10  # 单种拼法最多枚举的请假天数


def day_kind(d):
    """返回某天的类型：holiday(法定假) / weekend(双休) / work(工作日，含调休上班日)。"""
    for _name, s, e in HOLIDAYS:
        if s <= d <= e:
            return "holiday"
    if d in WORK_WEEKENDS:
        return "work"
    if d.weekday() >= 5:
        return "weekend"
    return "work"


def stitch(block_idx, direction, budget):
    """从第 block_idx 个假期块向 direction(1=后拼/-1=前拼)延伸。

    规则：工作日烧 1 天年假，周末/法定假免费；预算花完后继续穿过免费的日子，
    直到撞上下一个工作日为止。返回 (rest_start, rest_end, spent_dates)。
    """
    _name, s, e = HOLIDAYS[block_idx]
    spent = []
    lo, hi = s, e
    step = dt.timedelta(days=1) if direction == 1 else dt.timedelta(days=-1)
    d = (e if direction == 1 else s) + step
    while True:
        if d.year != YEAR:
            break
        if day_kind(d) == "work":
            if len(spent) >= budget:
                break
            spent.append(d)
        if direction == 1:
            hi = d
        else:
            lo = d
        d += step
    return lo, hi, spent


def make_method(origin, direction_name, lo, hi, spent):
    rest = (hi - lo).days + 1
    n = len(spent)
    tag = ""
    ratio = None
    if n == 0:
        tag = "天然假期"
    else:
        ratio = (rest - n) / n
        if origin == "中秋" and direction_name == "后拼":
            if n == 3 and rest == 13:
                tag = "年度王炸·请3休13"
            elif n == 6 and rest == 17:
                tag = "年度王炸·请6休17"
        if not tag:
            if ratio >= 2:
                tag = "血赚"
            elif ratio >= 1:
                tag = "不亏"
            else:
                tag = "硬拼"
    return {
        "origin": origin, "direction": direction_name,
        "start": lo, "end": hi, "rest": rest,
        "spent": n, "spent_dates": spent,
        "ratio": ratio, "tag": tag,
    }


def all_methods(max_spend=MAX_SPEND):
    """枚举全部拼法，按 (start, end) 去重（中秋后拼与国庆前拼可能拼出同一区间）。"""
    methods = []
    seen = set()
    for i, (name, s, e) in enumerate(HOLIDAYS):
        methods.append(make_method(name, "天然", s, e, []))
        seen.add((s, e))
        for direction, dname in ((1, "后拼"), (-1, "前拼")):
            for b in range(1, max_spend + 1):
                lo, hi, spent = stitch(i, direction, b)
                if (lo, hi) in seen:
                    continue
                seen.add((lo, hi))
                methods.append(make_method(name, dname, lo, hi, spent))
    return methods


def sort_methods(methods):
    """天然假期在前（按天数降序），其余按性价比降序、天数降序。"""
    def key(m):
        if m["spent"] == 0:
            return (0, 0, -m["rest"])
        return (1, -m["ratio"], -m["rest"])
    return sorted(methods, key=key)


def fmt_range(m):
    return "%02d-%02d～%02d-%02d" % (
        m["start"].month, m["start"].day, m["end"].month, m["end"].day)


def fmt_method(m):
    if m["spent"] == 0:
        return ("[%s] %s：休 %d 天（%s），不用请假" %
                (m["tag"], m["origin"], m["rest"], fmt_range(m)))
    return ("[%s] %s%s：请 %d 天 → 休 %d 天（%s），性价比 %.2f" %
            (m["tag"], m["origin"], m["direction"], m["spent"],
             m["rest"], fmt_range(m), m["ratio"]))


def render_month(year, month, marks):
    """ASCII 月历。marks: date -> '<'(请年假) 或 '['(白嫖休息)。"""
    cal = calendar.Calendar(firstweekday=0)  # 周一起
    lines = ["      %d年%02d月" % (year, month), "一  二  三  四  五  六  日"]
    for week in cal.monthdayscalendar(year, month):
        cells = []
        for d in week:
            if d == 0:
                cells.append("    ")
                continue
            sym = marks.get(dt.date(year, month, d))
            if sym == "<":
                cells.append("<%2d>" % d)
            elif sym == "[":
                cells.append("[%2d]" % d)
            else:
                cells.append(" %2d " % d)
        lines.append("".join(cells))
    return "\n".join(lines)


def render_method_calendar(m):
    """把一种拼法的休息区间画在月历上。"""
    spent_set = set(m["spent_dates"])
    d = m["start"]
    marks = {}
    while d <= m["end"]:
        marks[d] = "<" if d in spent_set else "["
        d += dt.timedelta(days=1)
    parts = []
    month = m["start"].month
    while month <= m["end"].month:
        parts.append(render_month(YEAR, month, marks))
        month += 1
    parts.append("图例：<> = 烧年假的日子，[] = 白嫖的休息日")
    return "\n".join(parts)


def wangzha(methods):
    return [m for m in methods if m["tag"].startswith("年度王炸")]


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="2026 年拼假计算器：请3休13，请6休17。")
    p.add_argument("--annual", type=int, default=5,
                   help="年假余额（天），默认 5")
    p.add_argument("--list", action="store_true", help="列出全部拼法")
    p.add_argument("--best", action="store_true", help="只看年度王炸")
    args = p.parse_args(argv)
    if args.annual < 0:
        p.error("年假天数不能为负数")
    if args.annual > 365:
        p.error("年假天数不能超过 365 天（你这是要把公司买下来吗）")
    return args


def main(argv=None):
    args = parse_args(argv)
    n = args.annual
    methods = all_methods()
    affordable = [m for m in methods if m["spent"] <= n]
    ranked = sort_methods(affordable)
    wz = wangzha(methods)

    out = []
    out.append("=" * 44)
    out.append("  2026 年拼假计算器：请3休13，请6休17")
    out.append("=" * 44)
    out.append("你的年假余额：%d 天" % n)
    out.append("")

    # ---- 彩蛋 ----
    if n == 0:
        out.append(">>> 你的拼假攻略：好好上班。")
        out.append("（0 天年假还想拼？先把 KPI 拼明白吧）")
        out.append("")
    elif n >= 20:
        out.append(">>> 年假 ≥20 天？你可以直接退休了。")
        out.append("（还算什么拼假，工位都快长草了）")
        out.append("")

    if args.best:
        out.append("--- 年度王炸（中秋×国庆） ---")
        for m in wz:
            need = "✅ 年假够用" if n >= m["spent"] else "❌ 年假不够（需 %d 天）" % m["spent"]
            out.append(fmt_method(m) + "  " + need)
            out.append("")
            out.append(render_method_calendar(m))
            out.append("")
        print("\n".join(out))
        return 0

    if args.list:
        out.append("--- 全部拼法（按性价比排序，共 %d 种） ---" % len(ranked))
        for m in ranked:
            out.append(fmt_method(m))
        print("\n".join(out))
        return 0

    # 默认视图：王炸 spotlight + Top5 + 最佳拼法月历
    out.append("--- 年度王炸 spotlight ---")
    for m in wz:
        need = "✅ 年假够用" if n >= m["spent"] else "❌ 年假不够（需 %d 天）" % m["spent"]
        out.append(fmt_method(m) + "  " + need)
    out.append("")
    out.append("--- 性价比 Top 5（%d 天年假内） ---" % n)
    top = [m for m in ranked if m["spent"] > 0][:5]
    for i, m in enumerate(top, 1):
        out.append("%d. %s" % (i, fmt_method(m)))
    out.append("")
    if top:
        out.append("--- 最佳拼法月历：%s%s ---" % (top[0]["origin"], top[0]["direction"]))
        out.append(render_method_calendar(top[0]))
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

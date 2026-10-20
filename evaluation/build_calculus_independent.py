"""Build a sealed, human-authored retrieval holdout for functions and limits.

Do not use this file or its JSON output to tune retrieval until the evaluation
protocol and candidate configurations have been fixed.
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/calculus/catalog.json"
OUTPUT = ROOT / "evaluation/calculus_independent_80.json"

# id | relevant ids (comma separated) | type | question | public source key
ROWS = """01|calc-tj-01-01|概念对比|把陪域扩大后，同一个对应规则会从满射变成非满射吗？|domain
02|calc-tj-01-02|概念理解|写出同一个解析式，为什么还不足以唯一确定一个函数？|
03|calc-tj-01-03|条件缺失|只看图像的一小段呈对称形状，就能断定整个函数是偶函数吗？|
04|calc-tj-01-04|易混淆概念|为什么原函数的一一性和反函数的定义域是两个需要分别说清的问题？|inverse
05|calc-tj-01-05|概念对比|为什么双曲余弦满足 cosh²x−sinh²x=1，而普通余弦和正弦对应的是和为 1？|
06|calc-tj-02-01|条件理解|数列项总会进入任意小的目标区间，与偶尔进入该区间有什么区别？|
07|calc-tj-02-02|证明思路|若有人说数列同时收敛到 0 和 1，怎样利用足够靠后的同一项发现矛盾？|
08|calc-tj-02-03|反例辨析|一个数列始终落在 [−1,1]，为什么仍可能没有极限？|
09|calc-tj-02-04|易混淆概念|已知数列极限为正，前面有限项可以为负吗？|
10|calc-tj-02-05,calc-an-seq-002|概念对比|“每个子列都收敛”和“存在一个收敛子列”对原数列分别意味着什么？|bw
11|calc-tj-03-01,calc-an-real-003|条件理解|为什么讨论 x→a 的函数极限前，要确认定义域能从别的点逼近 a？|
12|calc-tj-03-02|条件缺失|分段函数在分界点两侧的极限各自存在，还欠哪一步才能写出双侧极限？|
13|calc-tj-03-03|易混淆概念|当 x→+∞ 有极限时，能否直接把结论写成 x→∞ 的极限？|
14|calc-tj-03-04|概念理解|改变函数在趋近点的取值，为什么无法制造第二个不同的极限？|
15|calc-tj-03-05|条件理解|极限附近的“有界”为什么只需要控制足够靠近目标点的函数值？|
16|calc-tj-03-06|条件缺失|函数值最终都为正，能反推出它的极限严格大于零吗？|
17|calc-tj-03-07|应用边界|若分母趋于非零常数，怎样从极限条件推出它在足够近处始终可作除数？|
18|calc-tj-03-08|证明思路|找到一列趋近 a 的点使函数值不趋于 L，能否否定极限为 L？|
19|calc-tj-04-01|概念理解|同一个量在 x→0 时是无穷小，在 x→1 时还一定是无穷小吗？|
20|calc-tj-04-02|概念理解|把 f(x) 写成 A 加上一项趋于 0 的误差，和说 f(x)→A 有什么关系？|
21|calc-tj-04-03|易混淆概念|函数值一会儿很大一会儿很小，为什么不能仅凭无界就说它趋于无穷大？|
22|calc-tj-04-04|条件理解|无穷小的倒数即使绝对值越来越大，为什么还未必趋于正无穷？|
23|calc-tj-05-01|条件缺失|每一项都趋于零的无穷多个函数相加，能直接套用有限和的极限法则吗？|
24|calc-tj-05-02|应用边界|振荡得没有极限的函数，乘上趋零因子后为什么仍可能有极限？|
25|calc-tj-05-03|条件理解|分母在目标点恰好为零，但在附近不为零，商法则究竟看的是哪个条件？|quotient
26|calc-tj-05-04|易混淆概念|两个数列分别收敛时，它们的商在哪一种极限情况下不能直接套公式？|
27|calc-tj-05-05|反例辨析|若 f(x)<g(x) 在目标点附近始终成立，取极限后能否出现两者相等？|inequality
28|calc-tj-05-06,calc-tj-09-03|条件对比|外层函数只有去心极限、并非在该点连续时，内层偶尔等于目标值会带来什么麻烦？|composition_limit
29|calc-tj-06-01|证明思路|夹在同一极限的两个数列之间，只从某一项起才被夹住，结论会变吗？|
30|calc-tj-06-02|条件理解|函数夹逼时，中间函数在目标点的值为什么可以完全不同？|
31|calc-tj-06-03,calc-an-real-001|证明思路|递增数列有上界时，为什么它的极限正好是所有项的上确界？|monotone
32|calc-tj-06-04|易混淆概念|单调函数在端点有单侧极限，为什么不等于说它在端点连续？|
33|calc-tj-06-05|概念对比|只知道相邻两项越靠越近，为什么还不能说数列是柯西列？|cauchy
34|calc-tj-06-06|条件理解|用 sin x/x→1 时，为什么 x 的角度单位会影响这个结论？|
35|calc-tj-07-01|概念对比|若两个无穷小的比值趋于 3，它们是同阶、等价，还是其中一个高阶？|
36|calc-tj-07-02|概念理解|“相差一项比自身更小的误差”和“两项等价”如何互相翻译？|
37|calc-tj-07-03|易混淆概念|为什么 sin x≈x 能用于乘除式，却可能破坏 sin x−x 这种差式的主导项？|equiv
38|calc-tj-08-01,calc-tj-03-01|概念对比|图像在 a 附近逼近一个高度，但 a 处标了另一个高度：有极限和连续分别怎么判断？|limitcontinuity
39|calc-tj-08-02|易混淆概念|左右极限都发散到同一个无穷方向，能靠补一个函数值消除间断吗？|removable
40|calc-tj-09-01|条件缺失|两个函数在某点连续，但分母函数在该点为零，为什么商的连续性不能照搬？|
41|calc-tj-09-02|条件理解|连续的严格单调函数求逆后，为什么反函数的自变量只能取原函数实际取得的值？|inverse
42|calc-tj-09-03|概念对比|外层在 u₀ 连续时，内层恰好反复取到 u₀，为何不妨碍复合极限？|
43|calc-tj-09-04|条件理解|要说 f(g(x)) 在 a 连续，除了各自连续，还需检查哪个定义域条件？|
44|calc-tj-10-01|反例辨析|f(x)=x 在 (0,1) 有界，为什么仍没有最大值？|extreme
45|calc-tj-10-02|条件缺失|只知道连续函数在区间内某两点异号，如何把零点定理用到这两点之间？|ivtopen
46|calc-tj-10-03|概念理解|连续函数在两点之间会取遍两端函数值之间的数，是否需要它单调？|
47|calc-tj-10-04|概念对比|逐点连续时 δ 可以随着考察点变，一致连续为什么不允许这样做？|uniform
48|calc-tj-10-05|条件对比|在开区间 (0,1) 上连续为何不足以自动推出一致连续；额外需要什么思路？|uniformopen
49|calc-an-real-001|易混淆概念|开区间 (0,1) 的上确界和最大值为什么不是同一回事？|sup
50|calc-an-real-002|概念理解|为什么在有理数集合里谈“有上界就有上确界”会遇到缺口？|
51|calc-an-real-003|概念对比|一个点不在集合里，仍可能是这个集合的聚点吗？|
52|calc-an-seq-002|条件理解|有界数列可抽出收敛子列，为什么定理没有说原数列收敛？|bw
53|calc-an-seq-004|概念理解|不断丢掉数列前面的项后，尾部上确界与下确界各会朝什么方向变化？|
54|calc-tj-01-01,calc-tj-01-02|易混淆概念|某规则对每个输入恰有一个输出，却没有覆盖指定陪域，这算函数吗？|domain
55|calc-tj-01-03|反例辨析|常数函数既可能是周期函数，又可能同时是奇函数吗？需要看什么条件？|
56|calc-tj-01-04|应用边界|先算 f(g(x)) 再代入一个 x，为什么只检查 g 自己的定义域还不够？|composition
57|calc-tj-02-01|概念理解|数列无限次接近 L，却也无限次远离 L，这与收敛定义冲突在哪里？|
58|calc-tj-02-03,calc-an-seq-002|概念对比|“有界”“有收敛子列”“自身收敛”三者中，哪些蕴含关系不能反过来？|bw
59|calc-tj-02-05|反例辨析|奇数项趋于 0、偶数项趋于 1，原数列还有机会收敛吗？|
60|calc-tj-03-01,calc-tj-08-01|易混淆概念|为什么可去掉函数在 a 的定义讨论极限，却不能以同样方式断言在 a 连续？|limitcontinuity
61|calc-tj-03-02,calc-tj-08-02|概念对比|左右极限有限却不相等时，间断点属于哪类，修改单点值有用吗？|removable
62|calc-tj-03-08|条件理解|海涅判别里趋近 a 的点列能一直取 xₙ=a 吗？为什么？|
63|calc-tj-04-01,calc-tj-04-03|易混淆概念|“无穷小趋于零”和“无穷大绝对值越过任意界”能否理解为固定小数和固定大数？|
64|calc-tj-05-02|反例辨析|一个因子趋于零，另一个因子无界时，乘积还能保证趋于零吗？|
65|calc-tj-05-03|条件缺失|看到 0/0 型就把分子、分母的极限相除，会在哪一步失去依据？|quotient
66|calc-tj-05-05|条件理解|比较 f 与 g 的极限时，要求 f≤g 对所有 x 成立，还是在目标附近成立就够？|inequality
67|calc-tj-05-06|反例辨析|g(x)→u₀、f(u) 在 u→u₀ 有极限，为什么 f(g(x)) 仍可能不趋于那个值？|composition_limit
68|calc-tj-06-03,calc-tj-06-05|概念对比|单调有界法和柯西准则判断收敛时，各自需要先掌握什么信息？|
69|calc-tj-06-06|易混淆概念|把 (1+1/t)^t 的 t→+∞ 换成 t→−∞，是否仍会接近同一个 e？需检查什么？|
70|calc-tj-07-01,calc-tj-07-03|应用边界|两个表达式同阶但比值不趋于 1，可以在求极限时互作等价替换吗？|
71|calc-tj-08-02|条件理解|函数在 a 没有定义，但两侧共同趋于有限值，怎样区分“未定义”和“不可修复”？|removable
72|calc-tj-09-02|反例辨析|函数连续且有反函数，若定义域不是区间，反函数还一定连续吗？|inverse_disc
73|calc-tj-10-01,calc-an-real-001|概念对比|函数在区间上有上确界，却总达不到它；这为什么不违背最值定理？|extreme
74|calc-tj-10-02,calc-tj-10-03|概念对比|零点定理和介值定理其实如何通过考察 f(x)−y 联系起来？|ivtopen
75|calc-tj-10-04,calc-tj-10-05|条件对比|为什么“闭区间连续必一致连续”不能反推“一致连续的定义域必须闭”？|uniformopen
76|calc-an-real-002,calc-tj-06-03|证明思路|证明有界递增数列收敛时，实数完备性具体用在选取哪个数上？|monotone
77|calc-an-real-003,calc-tj-03-01|条件缺失|若 a 是定义域的孤立点，所谓 x→a 时的去心极限还能按通常定义唯一确定吗？|
78|calc-an-seq-002,calc-tj-06-05|证明思路|柯西列若已有一个收敛子列，怎样把该子列的极限传给整个数列？|bw
79|calc-an-seq-004,calc-tj-02-05|易混淆概念|数列上下极限不同，为什么必然无法让所有子列趋向同一个值？|
80|calc-tj-10-03,calc-tj-10-01|概念对比|连续函数在闭区间上的值域为何是包含端点的整个区间，而不只是某个开区间？|ivtopen"""

SOURCES = {
    "domain": ("https://math.stackexchange.com/questions/59432/domain-co-domain-range-of-a-function", "Domain, Co-Domain & Range of a Function"),
    "inverse": ("https://math.stackexchange.com/questions/1914967/domain-and-range-of-inverse-function-confusion", "Domain and Range of Inverse Function Confusion"),
    "composition": ("https://math.stackexchange.com/questions/5137296/domain-of-g-for-a-composite-function-g-circ-f", "Domain of g for a Composite Function"),
    "bw": ("https://math.stackexchange.com/questions/377081/difference-between-convergent-sequence-and-convergent-subsequence", "Difference between convergent sequence and convergent subsequence"),
    "cauchy": ("https://math.stackexchange.com/questions/2790561/does-a-n-a-n1-to-0-imply-a-n-is-cauchy", "Does |a_n-a_(n+1)|→0 imply (a_n) is Cauchy?"),
    "inverse_disc": ("https://math.stackexchange.com/questions/1665457/a-continuous-injective-function-and-its-inverse", "A continuous injective function and its inverse"),
    "quotient": ("https://math.stackexchange.com/questions/857709/limit-quotient-law", "Limit quotient law"),
    "inequality": ("https://math.stackexchange.com/questions/3974014/do-strict-inequalities-hold-when-taking-limits", "Do strict inequalities hold when taking limits?"),
    "composition_limit": ("https://math.stackexchange.com/questions/285667/how-to-prove-this-limit-composition-theorem", "How to prove this limit composition theorem?"),
    "monotone": ("https://math.stackexchange.com/questions/3861637/monotone-convergence-theorem-proof-by-contradiction", "Monotone convergence theorem proof by contradiction"),
    "equiv": ("https://math.stackexchange.com/questions/2487889/solve-this-limit-using-equivalent-infinitesimals", "Solve this limit using equivalent infinitesimals"),
    "limitcontinuity": ("https://math.stackexchange.com/questions/3228683/difference-between-limits-and-continuity", "Difference between Limits and Continuity"),
    "removable": ("https://math.stackexchange.com/questions/255955/how-to-quickly-tell-if-a-discontinuity-is-removable-or-non-removable", "How to quickly tell if a discontinuity is removable or non-removable?"),
    "extreme": ("https://math.stackexchange.com/questions/2863971/closed-or-open-intervals-in-extreme-value-theorem-rolles-theorem-and-mean-val", "Closed or Open Intervals in Extreme Value Theorem"),
    "ivtopen": ("https://math.stackexchange.com/questions/938121/does-intermediate-value-theorem-apply-to-continuity-on-open-intervals", "Does intermediate value theorem apply to continuity on open intervals?"),
    "uniform": ("https://math.stackexchange.com/questions/653100/difference-between-continuity-and-uniform-continuity", "Difference between continuity and uniform continuity"),
    "uniformopen": ("https://math.stackexchange.com/questions/3028416/uniform-continuity-on-an-open-interval", "Uniform continuity on an open interval?"),
    "sup": ("https://math.stackexchange.com/questions/160451/difference-between-supremum-and-maximum", "Difference between supremum and maximum"),
}


def main() -> None:
    entries = json.loads(CATALOG.read_text(encoding="utf-8"))["entries"]
    valid_ids = {entry["id"] for entry in entries}
    existing = json.loads((ROOT / "evaluation/calculus_questions.json").read_text(encoding="utf-8"))
    existing_questions = {item["question"].strip() for item in existing}
    existing_questions.update(q["text"].strip() for entry in entries for q in entry.get("typical_questions", []))
    result = []
    for raw in ROWS.splitlines():
        number, ids, kind, question, source_key = raw.split("|", 4)
        relevant_ids = ids.split(",")
        assert all(x in valid_ids for x in relevant_ids), (number, ids)
        assert question not in existing_questions, (number, question)
        item = {"id": f"calc-independent-{number}", "question": question, "relevant_ids": relevant_ids, "type": kind}
        if source_key:
            url, title = SOURCES[source_key]
            item["source"] = {"origin": "public_question_inspired", "url": url, "title": title, "platform": "Mathematics Stack Exchange", "note": "依据公开讨论主题独立改写，非原文、非真实中文提问记录"}
        else:
            item["source"] = {"origin": "authored_from_knowledge", "note": "依据知识条目和常见误区独立编写；非真实用户日志"}
        result.append(item)
    assert len(result) == 80
    assert len({item["question"] for item in result}) == 80
    assert set().union(*(set(item["relevant_ids"]) for item in result)) == valid_ids
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(result)} questions to {OUTPUT}")


if __name__ == "__main__":
    main()

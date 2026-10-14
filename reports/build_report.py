# -*- coding: utf-8 -*-
"""解析 pytest JUnit XML（reports/results.xml），生成逐用例 Markdown 报告。

用法（在 blog 目录下）：
    python -m pytest -v --junitxml=reports/results.xml -p no:cacheprovider
    python reports/build_report.py
"""
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

try:
    import pytest

    pytest_ver = pytest.__version__
except Exception:
    pytest_ver = "unknown"

BASE = Path(__file__).resolve().parent.parent
xml_path = BASE / "reports" / "results.xml"
if not xml_path.exists():
    sys.exit(f"未找到 {xml_path}，请先运行 pytest --junitxml=reports/results.xml")

tree = ET.parse(xml_path)
root = tree.getroot()

suites = root.findall("testsuite")
total = failures = errors = skipped = passed = 0
total_time = 0.0
rows_by_file = {}
fail_details = []


def file_from_classname(classname):
    """从 classname（如 tests.test_admin.TestAuth）提取测试文件名。

    新版 pytest 的 JUnit XML 只有一个 name='pytest' 的 testsuite，
    真实归属文件需从每条 testcase 的 classname 推断。
    """
    parts = (classname or "").replace("/", ".").split(".")
    # 形如 tests.test_admin.TestAuth → 取 TestAuth 前一段
    if len(parts) >= 2 and parts[-1][:1].isupper():
        return parts[-2] + ".py"
    if len(parts) >= 2:
        return parts[-1] + ".py"
    return "unknown"


for suite in suites:
    total += int(suite.get("tests", 0))
    failures += int(suite.get("failures", 0))
    errors += int(suite.get("errors", 0))
    skipped += int(suite.get("skipped", 0))
    total_time += float(suite.get("time", 0))
    for tc in suite.findall("testcase"):
        name = tc.get("name", "")
        t = float(tc.get("time", 0))
        fname = file_from_classname(tc.get("classname", ""))
        failure, error = tc.find("failure"), tc.find("error")
        if failure is not None:
            status, icon = "失败", "FAIL"
            fail_details.append((fname, tc.get("classname", ""), name,
                                 failure.get("message", ""), (failure.text or "").strip()))
        elif error is not None:
            status, icon = "错误", "ERROR"
            fail_details.append((fname, tc.get("classname", ""), name,
                                 error.get("message", ""), (error.text or "").strip()))
        elif tc.find("skipped") is not None:
            status, icon = "跳过", "SKIP"
        else:
            status, icon = "通过", "PASS"
            passed += 1
        rows_by_file.setdefault(fname, []).append((name, status, icon, t))

pass_rate = (passed / total * 100) if total else 0
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
ver = sys.version.split()[0]

L = []
L.append("# 个人博客项目 pytest 测试报告\n")
L.append(f"- 生成时间：{now}")
L.append(f"- 运行环境：Windows / Python {ver} / pytest {pytest_ver}")
L.append("- 被测对象：`app.py`、`init_db.py`（Flask + SQLite 个人博客）")
L.append("- 隔离方式：每个用例使用 `tmp_path` 临时数据库，真实 `database.db` 不参与\n")

L.append("## 一、结果总览\n")
L.append("| 指标 | 数值 |")
L.append("| --- | --- |")
L.append(f"| 用例总数 | {total} |")
L.append(f"| 通过 | {passed} |")
L.append(f"| 失败 | {failures} |")
L.append(f"| 错误 | {errors} |")
L.append(f"| 跳过 | {skipped} |")
L.append(f"| 通过率 | {pass_rate:.1f}% |")
L.append(f"| 总耗时 | {total_time:.2f}s |")
conclusion = "全部通过" if failures == 0 and errors == 0 else "存在未通过用例"
L.append(f"| 结论 | **{conclusion}** |\n")

L.append("## 二、各测试文件分布\n")
L.append("| 测试文件 | 通过 | 失败 | 错误 | 跳过 | 耗时(s) |")
L.append("| --- | --- | --- | --- | --- | --- |")
for fname, rows in rows_by_file.items():
    p = sum(1 for r in rows if r[2] == "PASS")
    f = sum(1 for r in rows if r[2] == "FAIL")
    e = sum(1 for r in rows if r[2] == "ERROR")
    s = sum(1 for r in rows if r[2] == "SKIP")
    tm = sum(r[3] for r in rows)
    L.append(f"| {fname} | {p} | {f} | {e} | {s} | {tm:.3f} |")
L.append("")

L.append("## 三、逐用例执行明细\n")
for fname, rows in rows_by_file.items():
    L.append(f"### {fname}（{len(rows)} 条）\n")
    L.append("| # | 用例 | 状态 | 耗时(s) |")
    L.append("| --- | --- | --- | --- |")
    for i, (name, status, icon, t) in enumerate(rows, 1):
        L.append(f"| {i} | `{name}` | {icon} {status} | {t:.3f} |")
    L.append("")

L.append("## 四、失败/错误用例详情\n")
if fail_details:
    for i, (fname, cls, name, msg, text) in enumerate(fail_details, 1):
        L.append(f"### {i}. [{fname}] {name}\n")
        L.append(f"- 所属类：`{cls}`")
        L.append(f"- 失败信息：{msg or '(无)'}")
        if text:
            L.append("\n```text")
            L.append(text[-2000:])
            L.append("```")
        L.append("")
else:
    L.append("本次执行无失败、无错误用例。\n")

all_rows = [(fn, n, st, ic, t) for fn, rs in rows_by_file.items() for (n, st, ic, t) in rs]
slow = sorted(all_rows, key=lambda x: x[4], reverse=True)[:5]
L.append("## 五、耗时最长的 5 条用例\n")
L.append("| 测试文件 | 用例 | 状态 | 耗时(s) |")
L.append("| --- | --- | --- | --- |")
for fn, n, st, ic, t in slow:
    L.append(f"| {fn} | `{n}` | {ic} | {t:.3f} |")
L.append("")

stamp = datetime.now().strftime("%Y%m%d")
out = BASE / "reports" / f"测试报告_{stamp}.md"
out.write_text("\n".join(L), encoding="utf-8")
print(f"报告已生成: {out}")
print(f"总计 {total} 条: PASS={passed} FAIL={failures} ERROR={errors} SKIP={skipped} 耗时={total_time:.2f}s")

# -*- coding: utf-8 -*-
"""直接运行 pytest 捕获真实输出（不经 PowerShell，保证中文不转义），
渲染成终端外观的单列长 HTML，供浏览器全页截图。"""
import html
import subprocess
import sys
from pathlib import Path

proc = subprocess.run(
    [sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider", "--color=no"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
raw = proc.stdout

# 落盘一份纯文本原始证据
Path("reports/pytest_output.txt").write_text(raw, encoding="utf-8")

start = raw.find("============================= test session starts")
if start != -1:
    text = raw[start:].strip("\r\n")
else:
    text = raw.strip("\r\n")

escaped = html.escape(text)
escaped = escaped.replace("PASSED", '<span class="ok">PASSED</span>')
escaped = escaped.replace("FAILED", '<span class="fail">FAILED</span>')
escaped = escaped.replace("ERROR", '<span class="fail">ERROR</span>')
escaped = escaped.replace("SKIPPED", '<span class="skip">SKIPPED</span>')

out_lines = []
for line in escaped.split("\n"):
    if "passed" in line and line.replace("=", "").strip().startswith(("passed", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9")):
        out_lines.append(f'<span class="summary">{line}</span>')
    else:
        out_lines.append(line)
body = "\n".join(out_lines)

page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>pytest 运行结果</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html,body {{ background:#0c0c0c; }}
  body {{ padding:24px; font-family:Consolas,"Courier New",monospace; width:980px; }}
  .terminal {{
    background:#011627; border-radius:10px; overflow:hidden;
    border:1px solid #1f3a4d; box-shadow:0 10px 40px rgba(0,0,0,.6);
  }}
  .titlebar {{ background:#172a3a; padding:10px 16px; display:flex; align-items:center; gap:8px; }}
  .dot {{ width:12px; height:12px; border-radius:50%; }}
  .r {{ background:#ff5f56; }} .y {{ background:#ffbd2e; }} .g {{ background:#27c93f; }}
  .title {{ color:#9fb7c8; font-size:13px; margin-left:10px; }}
  .screen {{
    padding:20px 24px; color:#d6deeb; font-size:13px; line-height:1.6;
    white-space:pre;
  }}
  .ok {{ color:#27c93f; font-weight:bold; }}
  .fail {{ color:#ff5f56; font-weight:bold; }}
  .skip {{ color:#ffbd2e; font-weight:bold; }}
  .summary {{ color:#7fdbca; font-weight:bold; font-size:15px; }}
</style>
</head>
<body>
  <div class="terminal">
    <div class="titlebar">
      <span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
      <span class="title">命令提示符 — python -m pytest -v</span>
    </div>
    <pre class="screen">{body}
</pre>
  </div>
</body>
</html>"""

Path("static/pytest_result.html").write_text(page, encoding="utf-8")
print("rendered, pytest returncode =", proc.returncode)

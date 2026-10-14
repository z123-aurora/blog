# -*- coding: utf-8 -*-
"""把 reports/pytest_output.txt 的真实 pytest 输出绘制成终端风格 PNG。

不依赖浏览器/截图工具：逐字符选择字体（ASCII 用 Consolas 等宽，
中文用微软雅黑回退），PASSED/FAILED/SKIPPED 与总结行着色。
"""
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CONSOLA = "C:/Windows/Fonts/consola.ttf"
CONSOLAB = "C:/Windows/Fonts/consolab.ttf"
YAHEI = "C:/Windows/Fonts/msyh.ttc"

FS = 15                      # 正文字号
LINE_H = 23                  # 行高
PAD_X, PAD_Y = 22, 16
TITLE_H = 42
BG = (1, 22, 39)
BAR = (23, 42, 58)
TEXT = (214, 222, 235)
GREEN = (39, 201, 63)
RED = (255, 95, 86)
YELLOW = (255, 189, 46)
CYAN = (127, 219, 202)
GREY = (159, 183, 200)

f_en = ImageFont.truetype(CONSOLA, FS)
f_en_b = ImageFont.truetype(CONSOLAB, FS)
f_cn = ImageFont.truetype(YAHEI, FS - 1)


def is_cjk(ch):
    return ord(ch) > 0x2E7F


def draw_seg(draw, x, y, seg, color, bold=False):
    """绘制一个文本段，逐字符回退字体，返回结束 x 坐标。"""
    for ch in seg:
        font = f_cn if is_cjk(ch) else (f_en_b if bold else f_en)
        draw.text((x, y), ch, font=font, fill=color)
        x += draw.textlength(ch, font=font)
    return x


def draw_line(draw, x0, y, line):
    """绘制一整行：状态关键字切分着色；总结行整体高亮加粗。"""
    is_summary = bool(re.match(r"=+ .*passed.*=+", line))
    if is_summary:
        draw_seg(draw, x0, y, line, CYAN, bold=True)
        return
    parts = re.split(r"(PASSED|FAILED|ERROR|SKIPPED)", line)
    x = x0
    for part in parts:
        if part == "PASSED":
            x = draw_seg(draw, x, y, part, GREEN, bold=True)
        elif part in ("FAILED", "ERROR"):
            x = draw_seg(draw, x, y, part, RED, bold=True)
        elif part == "SKIPPED":
            x = draw_seg(draw, x, y, part, YELLOW, bold=True)
        else:
            x = draw_seg(draw, x, y, part, TEXT)


def main():
    raw = Path("reports/pytest_output.txt").read_text(encoding="utf-8")
    start = raw.find("============================= test session starts")
    lines = raw[start:].strip("\r\n").split("\n") if start != -1 else raw.splitlines()

    # 先用临时画布量取最宽行
    probe = Image.new("RGB", (10, 10))
    pd = ImageDraw.Draw(probe)

    def line_width(line):
        w = 0.0
        for ch in line:
            f = f_cn if is_cjk(ch) else f_en
            w += pd.textlength(ch, font=f)
        return w

    max_w = max((line_width(ln) for ln in lines), default=800)
    width = int(max_w) + PAD_X * 2
    height = TITLE_H + PAD_Y * 2 + LINE_H * len(lines)

    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    # 标题栏
    draw.rectangle([0, 0, width, TITLE_H], fill=BAR)
    for i, c in enumerate((RED, YELLOW, GREEN)):
        draw.ellipse([16 + i * 20, 15, 28 + i * 20, 27], fill=c)
    draw_seg(draw, 90, 11, "命令提示符  —  python -m pytest -v", GREY)

    # 正文
    y = TITLE_H + PAD_Y
    for ln in lines:
        draw_line(draw, PAD_X, y, ln)
        y += LINE_H

    out = Path("reports/pytest_result.png")
    img.save(out)
    print(f"SAVED {out} ({width}x{height}, {out.stat().st_size} bytes, {len(lines)} lines)")


if __name__ == "__main__":
    main()

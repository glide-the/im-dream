#!/usr/bin/env python3
"""生成导出长图专用的小篆字体子集。

背景：导出长图走 SVG <img> 管线，SVG 图像文档禁止外部子资源，字体必须 base64 内嵌；
完整 Xiaolai-Regular.woff2 有 11.8MB，每个分块都会被 Chrome 重新解析一次（实测约 190ms/块，
占导出 CPU 大头）。本子集只保留 GB2312 汉字 + 常用符号（约 7 千字，2MB 上下），
解析耗时约降为 1/3 ~ 1/4。

产物：
  frontend/public/Xiaolai-ExportSubset.woff2   —— 子集字体（导出时 fetch 一次）
  frontend/src/components/chat/exportFontSubset.ts —— 风险字符表（全量 cmap 有、子集没有的字；
      导出管线逐块扫描文本，命中风险字的分块回退使用全量字体，保证任何字符渲染正确）

依赖：pip install fonttools brotli
用法：python3 frontend/scripts/subset-export-font.py
"""
import json
import os

from fontTools.subset import Subsetter, Options
from fontTools.ttLib import TTFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_FONT = os.path.join(ROOT, 'public', 'Xiaolai-Regular.woff2')
OUT_FONT = os.path.join(ROOT, 'public', 'Xiaolai-ExportSubset.woff2')
OUT_TS = os.path.join(ROOT, 'src', 'components', 'chat', 'exportFontSubset.ts')


def gb2312_chars():
    """GB2312 全部可解码字符（符号区 + 一二级汉字 6763）。"""
    chars = []
    for hi in range(0xA1, 0xF8):
        for lo in range(0xA1, 0xFF):
            try:
                chars.append(bytes([hi, lo]).decode('gb2312'))
            except UnicodeDecodeError:
                continue
    return ''.join(chars)


EXTRA_CHARS = (
    ''.join(chr(c) for c in range(0x20, 0x7F))  # ASCII 可打印
    + '〇0123456789０１２３４５６７８９'
    + '。，、；：？！…—·「」『』《》〈〉【】（）￥～　'
    + '‘’“”‚„‹›«»′″‴‼⁇⁈⁉'
    + '←→↑↓↔↕⇐⇒⇑⇓∀∃∈∉∑∏√∞∠°℃℉‰'
    + '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'
    + 'ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ'
    + 'ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏ'
    + 'ⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ'
)


def main():
    full = TTFont(SRC_FONT)
    full_cmap = set()
    for table in full['cmap'].tables:
        full_cmap.update(table.cmap.keys())

    wanted = gb2312_chars() + EXTRA_CHARS
    wanted_cps = {ord(ch) for ch in wanted}
    subset_cps = wanted_cps & full_cmap
    risky_cps = sorted(full_cmap - subset_cps)

    opts = Options()
    opts.flavor = 'woff2'
    opts.desubroutinize = True
    opts.name_IDs = []
    opts.notdef_outline = True
    opts.recalc_bounds = True
    opts.hinting = False  # woff2 下 hint 意义不大，省体积
    ss = Subsetter(options=opts)
    ss.populate(unicodes=sorted(subset_cps))
    ss.subset(full)
    full.save(OUT_FONT)

    risky_text = ''.join(chr(cp) for cp in risky_cps)
    del risky_text
    # 区间压缩：排序码点合并为 [start, end] 闭区间，TS 侧逐字符二分/线性检查。
    ranges = []
    for cp in risky_cps:
        if ranges and cp == ranges[-1][1] + 1:
            ranges[-1][1] = cp
        else:
            ranges.append([cp, cp])
    ts = (
        '// 由 scripts/subset-export-font.py 生成，请勿手改。\n'
        '// 全量 Xiaolai cmap 中存在、但导出子集字体未覆盖的字符（生僻字等），码点闭区间列表。\n'
        '// 导出管线逐分块扫描文本，命中这些字符的分块回退使用全量内嵌字体渲染。\n'
        f'// 子集覆盖 {len(subset_cps)} 字符；风险字符 {len(risky_cps)} 个，{len(ranges)} 段区间。\n'
        'export const EXPORT_FONT_UNCOVERED_RANGES: ReadonlyArray<readonly [number, number]> = '
        + json.dumps(ranges, separators=(',', ':'))
        + ';\n'
    )
    with open(OUT_TS, 'w', encoding='utf-8') as f:
        f.write(ts)

    print(f'subset font: {os.path.getsize(OUT_FONT)} bytes, {len(subset_cps)} chars')
    print(f'risky chars: {len(risky_cps)} -> {OUT_TS}')


if __name__ == '__main__':
    main()

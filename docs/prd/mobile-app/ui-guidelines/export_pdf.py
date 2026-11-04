#!/usr/bin/env python3
# [Sync] 2026-11-02: v3.1名称修订，完整字标沿原图形与出版入口输出。
# [Input] 同目录Markdown、现行颜色Token、项目手写字体与可配置中文正文字体。
# [Output] 可编辑SVG、嵌入字体的规范PDF及页面边界检查JSON。
# [Pos] 单文档出版工具；应用运行、依赖和构建入口保持。
# [Sync] 2026-11-02: v3.0初版，矢量图与PDF共用图形定义。
# [Sync] 2026-11-02: 默认出版位置改为docs/prd，与可编辑源文件包集中存放。
"""Export this handbook with ReportLab. Requires reportlab and a Chinese TTF."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re

from reportlab.graphics import renderPDF, renderSVG
from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TOKEN_FILE = ROOT / 'frontend/app/_dream/styles/tokens.css'
TEXT = HERE / 'README.md'
PAGE_W, PAGE_H = 595.276, 841.89
MARGIN = 40
WIDTH = PAGE_W - MARGIN * 2
BODY_FONT = 'InkBody'
HAND_FONT = 'InkHand'


def palette(selector: str) -> dict[str, str]:
    css = TOKEN_FILE.read_text()
    block = re.search(selector + r'\s*\{(.*?)\}', css, re.S)
    if not block:
        raise ValueError('Missing palette in current tokens.css')
    return dict(re.findall(r'--color-([\w-]+):\s*(#[\da-fA-F]{6})\s*;', block[1]))


LIGHT = palette(r':root')
DARK = palette(r"\[data-theme='dark'\]")
C = {
    'bg': LIGHT['bg-app'], 'paper': LIGHT['bg-paper'],
    'solid': LIGHT['bg-surface-solid'], 'text': LIGHT['text-primary'],
    'body': LIGHT['text-body'], 'secondary': LIGHT['text-secondary'],
    'border': LIGHT['border-paper'], 'accent': LIGHT['voice-yellow'],
    'blue': LIGHT['action-link'], 'green': LIGHT['state-success'],
    'error': LIGHT['state-error'], 'action': LIGHT['action-primary'],
}


def col(value: str):
    return colors.HexColor(C.get(value, value))


class Figure:
    """Top-origin vector helpers for this document's editable diagrams."""
    def __init__(self, height=260, width=520):
        self.w, self.h = width, height
        self.d = Drawing(width, height)

    def rect(self, x, y, w, h, fill='paper', stroke=None, radius=0, dash=None):
        shape = Rect(x, self.h-y-h, w, h, rx=radius, ry=radius,
                     fillColor=col(fill) if fill else None,
                     strokeColor=col(stroke) if stroke else None,
                     strokeWidth=.85)
        if dash:
            shape.strokeDashArray = dash
        self.d.add(shape)

    def line(self, x1, y1, x2, y2, color='border', width=1, dash=None):
        shape = Line(x1, self.h-y1, x2, self.h-y2,
                     strokeColor=col(color), strokeWidth=width)
        if dash:
            shape.strokeDashArray = dash
        self.d.add(shape)

    def text(self, x, y, text, size=10, color='text', font=BODY_FONT, anchor='start'):
        self.d.add(String(x, self.h-y, text, fontName=font, fontSize=size,
                          fillColor=col(color), textAnchor=anchor))

    def dot(self, x, y, r=3, fill='accent', stroke=None):
        self.d.add(Circle(x, self.h-y, r, fillColor=col(fill) if fill else None,
                          strokeColor=col(stroke) if stroke else None))

    def arrow(self, x1, y1, x2, y2, color='secondary'):
        self.line(x1, y1, x2, y2, color)
        direction = 1 if x2 >= x1 else -1
        self.line(x2-4*direction, y2-3, x2, y2, color)
        self.line(x2-4*direction, y2+3, x2, y2, color)

    def note(self, x, y, title, subtitle='', w=146, h=52, fill='solid'):
        self.rect(x, y, w, h, fill, 'border', 8)
        self.text(x+12, y+21, title, 11)
        if subtitle:
            self.text(x+12, y+39, subtitle, 8, 'secondary')

    def phone(self, x=12, y=10, w=180, h=284, title='Chat', dark=False, tabs=True):
        bg = DARK['bg-app'] if dark else C['paper']
        fg = DARK['text-primary'] if dark else C['text']
        edge = DARK['border-paper'] if dark else C['border']
        self.rect(x, y, w, h, bg, edge, 15)
        self.text(x+12, y+17, '9:41', 7, fg)
        self.line(x+w-30, y+12, x+w-14, y+12, edge, 2)
        self.text(x+12, y+39, '‹', 16, fg)
        self.text(x+w/2, y+38, title, 12, fg, anchor='middle')
        self.line(x+8, y+49, x+w-8, y+49, edge)
        if tabs:
            self.line(x+8, y+h-32, x+w-8, y+h-32, edge)
            self.text(x+22, y+h-17, 'Chat', 8, fg)
            self.text(x+w/2, y+h-17, 'Decks', 8, fg, anchor='middle')
            self.text(x+w-24, y+h-17, 'More', 8, fg, anchor='middle')
        return x+12, y+61, w-24, h-108

    def desktop(self, x=230, y=32, w=277, h=192, title='Chat'):
        self.rect(x, y, w, h, 'paper', 'border', 8)
        self.rect(x, y, 60, h, 'bg', None, 8)
        self.line(x+60, y, x+60, y+h)
        self.text(x+6, y+24, 'Kastention', 8, font=HAND_FONT)
        for i, label in enumerate(['Chat', 'Dream', 'Decks', '更多']):
            self.text(x+10, y+62+i*24, label, 9)
        self.text(x+73, y+22, title, 12)
        self.line(x+69, y+32, x+w-10, y+32)
        return x+73, y+45, w-86, h-59


def figures() -> dict[str, Drawing]:
    result = {}
    f = Figure(310)
    f.rect(0, 0, 520, 310, 'bg', radius=12)
    f.text(28, 35, 'A QUIET PLACE FOR YOUR WORDS', 9, 'secondary', 'Helvetica')
    f.rect(201, 55, 276, 218, 'solid', 'border', 8)
    f.line(229, 64, 229, 262, 'error', .7)
    for y in range(112, 253, 28):
        f.line(216, y, 463, y, 'border', .5)
    f.text(247, 100, '写下今天的一点光。', 19, font=HAND_FONT)
    f.text(247, 139, '把经历留在纸上，', 14, font=HAND_FONT)
    f.text(247, 167, '把自己看得更清楚。', 14, font=HAND_FONT)
    f.rect(40, 100, 184, 130, 'paper', 'border', 10)
    f.text(58, 134, 'Write.', 27, font='Helvetica')
    f.text(58, 170, 'Remember.', 27, font='Helvetica')
    f.line(59, 184, 177, 184, 'accent', 4)
    f.text(58, 208, '内容 · 层级 · 反馈', 10, 'secondary')
    f.line(400, 238, 456, 182, 'text', 7)
    f.dot(449, 190, 3, 'accent')
    f.dot(488, 47, 5, 'accent')
    f.text(30, 284, 'PAPER / INK / MEMORY', 8, 'secondary', 'Helvetica')
    result['cover'] = f.d

    f = Figure(210)
    for x, n, title, desc in [(0,'01','内容层级','标题、正文、说明'),(178,'02','轻纸面','留白建立分组'),(356,'03','局部强调','状态与主操作')]:
        f.rect(x, 6, 164, 194, 'paper', 'border', 8)
        f.text(x+14, 30, n, 11, 'secondary', 'Helvetica')
        f.text(x+14, 57, title, 16)
        f.text(x+14, 77, desc, 8, 'secondary')
        if n == '01':
            f.text(x+14, 110, '今天的一页', 18, font=HAND_FONT)
            for y,w in [(132,128),(146,115),(160,87)]: f.line(x+14,y,x+14+w,y,'border',2)
        elif n == '02':
            for y in (105,138,171):
                f.text(x+14,y,'一条安静的内容',10)
                f.line(x+14,y+12,x+148,y+12)
        else:
            f.dot(x+20,113,4,'green'); f.text(x+34,116,'已保存',10)
            f.rect(x+14,139,114,30,'action',radius=7)
            f.text(x+71,159,'继续写作',10,'#ffffff',anchor='middle')
    result['principles']=f.d

    f = Figure(215)
    for x,p,title in [(0,LIGHT,'LIGHT / 亮色声明块'),(268,DARK,'DARK / 暗色声明块')]:
        f.rect(x,0,252,215,p['bg-app'],p['border-paper'],9)
        f.text(x+15,25,title,10,p['text-primary'])
        f.rect(x+14,41,224,59,p['bg-paper'],radius=7)
        f.text(x+26,64,'纸面承载内容',14,p['text-primary'],HAND_FONT)
        f.text(x+26,84,'画布 / 纸面 / 文本 / 操作',8,p['text-secondary'])
        for i,key in enumerate(['bg-app','bg-paper','text-primary','action-primary']):
            sx=x+15+i*58
            f.rect(sx,115,49,38,p[key],p['border-paper'],5)
            f.text(sx,169,key.split('-')[-1],7,p['text-secondary'])
            f.text(sx,186,p[key].upper(),6.7,p['text-secondary'])
    result['color']=f.d

    f=Figure(222)
    f.rect(0,0,520,222,'paper',radius=8)
    for label,y,size,sample,font in [('标题',36,28,'把记忆留在纸上',HAND_FONT),('正文',89,15,'今天，我留意到一个反复出现的想法。',BODY_FONT),('说明',124,10,'最后更新 · 内容与状态分层表达',BODY_FONT)]:
        f.text(15,y,label,9,'secondary'); f.text(88,y,sample,size,font=font)
    f.line(15,145,505,145)
    f.text(15,169,'写作正文',9,'secondary')
    f.text(88,170,'行距随着实际文字大小一起变化。',18,font=HAND_FONT)
    f.line(88,177,493,177)
    f.text(88,199,'自然换行，保留光标与阅读位置。',18,font=HAND_FONT)
    f.line(88,206,493,206)
    result['typography']=f.d

    f=Figure(267)
    f.phone(14,0,175,260,'页面标题')
    f.rect(27,59,149,113,'bg',radius=4)
    f.text(40,85,'正文 / 列表',12)
    f.text(40,105,'内容区域独立纵滚',8,'secondary')
    f.line(165,71,165,159,'secondary',1.4)
    f.rect(27,180,149,35,'solid','border',7)
    f.text(40,201,'当前主操作',10)
    for y,label in [(15,'系统安全区域'),(39,'页头与返回'),(111,'内容滚动范围'),(198,'输入 / 操作区'),(241,'原底部栏目')]:
        f.arrow(196,y,230,y)
        f.text(242,y+3,label,11)
    for i,v in enumerate([4,8,12,16,24]):
        x=244+i*53
        f.rect(x,218,max(v,4),12,'border')
        f.text(x,246,str(v),9,'secondary')
    f.text(242,185,'常用间距关系 · 整理建议',9,'secondary')
    result['layout']=f.d

    f=Figure(222)
    f.text(0,19,'图标与点击区域分开表达',12)
    for i,label in enumerate(['返回','新建','日历','关闭']):
        x=8+i*64
        f.rect(x,35,44,44,None,'border',8,[3,3])
        if i==0:
            f.line(x+28,47,x+16,57,'text',1.8); f.line(x+16,57,x+28,68,'text',1.8)
        elif i==1:
            f.line(x+22,47,x+22,67,'text',1.8); f.line(x+12,57,x+32,57,'text',1.8)
        elif i==2:
            f.rect(x+12,47,21,21,None,'text',3); f.line(x+12,53,x+33,53,'text',1.2)
        else:
            f.line(x+14,49,x+30,65,'text',1.8); f.line(x+14,65,x+30,49,'text',1.8)
        f.text(x+22,98,label,9,anchor='middle')
    f.text(300,19,'现行容器圆角取样',12)
    for x,r,label in [(300,13,'图标区 13'),(410,18,'更多条目 18')]:
        f.rect(x,37,93,59,'bg','border',r)
        f.text(x+46,117,label,9,anchor='middle')
    f.line(0,139,520,139)
    f.text(8,165,'轻纸面列表',11)
    for y in (181,205):
        f.text(11,y,'名称与说明按同一基线排列',9,'secondary'); f.line(11,y+7,238,y+7)
    f.rect(288,153,225,60,'paper','border',12)
    f.text(303,180,'更多页已有卡片',12)
    f.text(303,200,'容器服务于入口和用途说明',9,'secondary')
    result['geometry']=f.d

    f=Figure(230)
    for x,label,fill,stroke,tc in [(0,'主操作','action',None,'#ffffff'),(138,'次操作','paper','border','text'),(276,'禁用','border',None,'secondary')]:
        f.rect(x,12,122,37,fill,stroke,8);f.text(x+61,36,label,12,tc,anchor='middle')
    f.text(425,34,'按下反馈',9,'secondary')
    f.line(0,69,520,69)
    f.text(0,94,'输入名称',10)
    f.rect(0,106,320,48,'solid','action',7)
    f.text(14,136,'把想说的话写下来',13,'text',HAND_FONT)
    f.line(147,118,147,141,'action',1)
    f.text(340,126,'聚焦边界可辨认',9,'secondary')
    f.text(340,145,'输入内容自然换行',9,'secondary')
    f.rect(0,174,520,44,'paper','border',7)
    f.dot(16,196,4,'blue');f.text(30,200,'任务运行中',10)
    f.rect(350,182,70,28,'solid','border',6);f.text(385,201,'Stop',10,anchor='middle')
    f.text(435,200,'原停止入口',8,'secondary')
    result['controls']=f.d

    f=Figure(227)
    for y,label,selected in [(15,'一项普通资源',False),(57,'一项已选资源',True)]:
        f.text(14,y+20,label,12)
        f.text(275,y+20,'来源与说明',9,'secondary')
        if selected: f.text(486,y+20,'✓',15)
        f.line(14,y+32,506,y+32)
    for y,color,title,action in [(116,'blue','正在读取已有内容…',''),(153,'green','内容已保存',''),(190,'error','读取失败，请重试','重试')]:
        f.dot(19,y+8,4,color);f.text(34,y+12,title,10)
        if action: f.text(464,y+12,action,10)
    result['feedback']=f.d

    f=Figure(250)
    f.phone(8,0,170,244,'原页面')
    f.rect(18,93,150,110,'solid','border',10)
    f.text(30,115,'当前局部任务',12)
    f.text(30,139,'正文与选项独立滚动',8,'secondary')
    f.line(30,151,156,151)
    f.text(30,181,'取消',9);f.text(128,181,'原操作',9)
    for y,label in [(115,'标题说明当前任务'),(140,'正文区域可滚动'),(181,'操作与关闭沿原规则')]:
        f.arrow(184,y,220,y); f.text(234,y+3,label,12)
    f.text(234,222,'关闭 → 返回来源页面',11,'secondary')
    f.text(234,36,'现有弹层的区域关系',14)
    f.text(234,59,'规范示意 · 具体对象沿原合同',9,'secondary')
    result['overlays']=f.d

    for name,title in [('chat','Chat'),('writing','写作'),('reflections','回顾'),('more','更多')]:
        f=Figure(310)
        px,py,pw,ph=f.phone(8,8,178,285,title)
        dx,dy,dw,dh=f.desktop(223,32,289,190,title)
        f.text(8,309,'窄屏 / Native区域骨架',8,'secondary')
        f.text(223,239,'桌面Web参照 / 沿原导航',8,'secondary')
        if name=='chat':
            f.text(px,py+6,'今天想理清一个想法。',10,font=HAND_FONT)
            f.line(px,py+22,px+pw,py+22)
            f.text(px,py+44,'可以从刚发生的事情说起。',9)
            f.text(px,py+65,'正文与工具结果继续纵滚',8,'secondary')
            f.rect(px,py+125,pw,50,'solid','border',9)
            f.text(px+8,py+145,'写下你的问题…',9,'secondary')
            f.text(px+8,py+165,'附件',8); f.text(px+pw-30,py+165,'发送',8)
            f.text(dx,dy+6,'同一对话中的消息',11)
            for yy in [dy+25,dy+42,dy+59]:f.line(dx,yy,dx+dw-6,yy)
            f.rect(dx,dy+88,dw,37,'solid','border',7);f.text(dx+9,dy+111,'原AIInputDock / Send · Stop',8)
            f.text(223,265,'消息纵滚 / 输入区 / 原侧栏与侧会话',9)
        elif name=='writing':
            f.text(141,46,'心情',8)
            f.text(px+64,py,'日历  +  @',9)
            f.text(px,py+25,'11月2日 · 日常',8,'secondary')
            for yy in [py+54,py+79,py+104,py+129]:f.line(px,yy,px+pw,yy)
            f.text(px,py+50,'写下一段今天的经历。',13,font=HAND_FONT)
            f.text(px,py+75,'慢慢看见自己的节奏。',13,font=HAND_FONT)
            f.text(px,py+165,'原保存 / 能量反馈',8,'secondary')
            f.text(dx,dy+2,'日期 / 原心情入口 / 工具',8,'secondary')
            f.line(dx+126,dy+9,dx+126,dy+124)
            for yy in [dy+32,dy+54,dy+76,dy+98]:f.line(dx,yy,dx+113,yy)
            f.text(dx+137,dy+28,'关联Chat',8)
            f.text(dx+137,dy+50,'独立纵滚',8,'secondary')
            f.text(223,265,'正文纵滚；心情在原编辑区域展开',9)
            f.text(223,284,'选择即确认 / 返回更多 / 原偏好重试',9,'secondary')
        elif name=='reflections':
            f.text(px,py+5,'回望自己的经验',16,font=HAND_FONT)
            f.text(px,py+30,'天数    篇数    字数',8,'secondary')
            f.text(px,py+54,'过去的回顾 →',11)
            f.rect(px,py+68,pw,49,'bg','border',7)
            f.text(px+8,py+87,'一份已保存的报告',10)
            f.text(px+8,py+105,'日期 / 原报告信息',8,'secondary')
            f.rect(px+20,py+136,pw-40,29,'solid','border',6)
            f.text(px+pw/2,py+155,'原生成入口',9,anchor='middle')
            f.text(dx,dy+5,'统计 / 历史 / 原分析内容',9)
            f.rect(dx,dy+23,dw,41,'bg','border',5);f.text(dx+10,dy+47,'已有报告 → 阅读页 → 返回',9)
            f.text(dx,dy+86,'原任务反馈 / 保存失败重试',9)
            f.text(223,265,'报告正文独立纵滚，保持原返回来源',9)
            f.text(223,284,'详情手柄只调整原详情区域高度',9,'secondary')
        else:
            f.text(px,py,'记录与回望',8,'secondary')
            f.rect(px,py+10,pw,43,'bg','border',9);f.text(px+10,py+29,'写作',11);f.text(px+10,py+44,'写下今天的经历',7,'secondary')
            for xx,lab in [(px,'时间线'),(px+pw/2+4,'回顾')]:
                f.rect(xx,py+62,pw/2-4,47,'bg','border',9);f.text(xx+8,py+88,lab,10)
            f.text(px,py+129,'偏好',8,'secondary')
            for yy,lab in [(py+139,'主题 · 当前外观'),(py+166,'设置')]:
                f.rect(px,yy,pw,23,'bg','border',7);f.text(px+9,yy+16,lab,8)
            f.text(dx,dy+4,'原侧栏更多入口',11)
            for i,lab in enumerate(['写作 / 时间线 / 回顾','主题 / 账户','设置菜单 → 原子页']):f.text(dx,dy+31+i*28,lab,9,'secondary')
            f.text(223,265,'五项同层入口 / 全页纵滚 / 原返回',9)
            f.text(223,284,'主题动作保持当前页面',9,'secondary')
        result[name]=f.d

    f=Figure(190)
    for x,title,sub in [(0,'用户操作','原入口提交'),(185,'执行反馈','加载 / 运行 / 保存'),(370,'结果核对','原状态与历史')]:
        f.note(x,15,title,sub,w=150,h=58)
    f.arrow(154,44,180,44);f.arrow(339,44,365,44)
    f.note(185,115,'失败与恢复','保留内容 / 原重试',w=150,h=58)
    f.line(445,78,445,143);f.arrow(445,143,342,143)
    f.line(185,143,76,143);f.line(76,143,76,82)
    f.text(0,187,'恢复核对已有结果；重新提交沿原用户动作。',9,'secondary')
    result['states']=f.d

    f=Figure(224)
    samples=[('主文本','text-primary','bg-app','10.61 : 1'),('弱文本','text-muted','bg-app','2.93 : 1'),('暗色主操作白字',None,None,'1.21 : 1')]
    for i,(title,fg,bg,ratio) in enumerate(samples):
        x=i*177
        fill=DARK['action-primary'] if i==2 else LIGHT[bg]
        text='#ffffff' if i==2 else LIGHT[fg]
        f.rect(x,8,166,89,fill,'border',8)
        f.text(x+12,43,'阅读这段文字',14,text)
        f.text(x+12,73,ratio,11,text)
        f.text(x+4,120,title,10)
        f.text(x+4,140,'当前值取样',8,'secondary')
    f.line(0,162,520,162)
    f.text(8,186,'普通文本目标 4.5 : 1',12)
    f.text(8,209,'检测缺口与后续建议分别记录；应用Token保持。',10,'secondary')
    result['accessibility']=f.d
    f=Figure(152)
    f.text(0,18,'同一条规则，从名称走到页面',12)
    for x,title,sub in [(0,'语义变量','bg-paper'),(185,'组件','输入容器'),(370,'页面','Chat输入区')]:
        f.note(x,40,title,sub,w=150,h=59)
    f.arrow(154,70,180,70);f.arrow(339,70,365,70)
    f.text(0,127,'颜色值随主题映射；组件和页面通过用途引用。',10,'secondary')
    result['terms-foundation']=f.d
    f=Figure(138)
    f.text(0,18,'一次保存中的交互术语',12)
    for x,title,sub in [(0,'操作暗示','保存入口可辨认'),(185,'交互状态','请求中 / 保存失败'),(370,'反馈与恢复','保留内容 / 原重试')]:
        f.note(x,37,title,sub,w=150,h=59)
    f.arrow(154,67,180,67);f.arrow(339,67,365,67)
    f.text(0,123,'先理解用户动作，再核对当前状态与下一步。',10,'secondary')
    result['terms-interaction']=f.d
    return result


def markup(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r'!\[([^]]*)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\[([^]]*)\]\((https?://[^)]+)\)', r'<link href="\2" color="#5f4a36">\1</link>', text)
    text = re.sub(r'\[([^]]*)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    return text


def get_font() -> Path:
    configured = os.environ.get('INK_UI_BODY_FONT')
    candidates = ([Path(configured)] if configured else []) + [
        Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf'),
        Path('/usr/share/fonts/truetype/arphic/ukai.ttc'),
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise RuntimeError('Set INK_UI_BODY_FONT to a Chinese TrueType font file.')


def export(output: Path, check_path: Path):
    font_path = get_font()
    pdfmetrics.registerFont(TTFont(BODY_FONT, str(font_path)))
    pdfmetrics.registerFont(TTFont(HAND_FONT, str(ROOT/'frontend/public/Xiaolai-Regular.ttf')))
    drawings=figures()
    assets=HERE/'assets'
    assets.mkdir(exist_ok=True)
    (assets/'.folder.md').write_text('<!-- [Input] export_pdf.py中的规范图形定义。 -->\n<!-- [Output] 可编辑SVG规范示意。 -->\n<!-- [Pos] UI规范正文插图；导出工具统一生成。 -->\n\n# 规范插图\n\n本目录包含封面、视觉原则、色彩、字体、布局、几何、组件、反馈、弹层、四类双端骨架、状态和可访问性取样图。文件名与正文图片引用对应。图形定义归上级export_pdf.py；编辑定义后重新生成SVG与PDF。\n')
    for name,drawing in drawings.items():
        svg=renderSVG.drawToString(drawing)
        svg=svg.replace('font-family: InkBody','font-family: Arial Unicode MS, PingFang SC, sans-serif')
        svg=svg.replace('font-family: InkHand','font-family: Xiaolai, PingFang SC, sans-serif')
        (assets/f'{name}.svg').write_text(svg)
    body=TEXT.read_text()
    chunks=re.split(r'<!-- page: ([\w-]+) -->',body)
    pages=list(zip(chunks[1::2],chunks[2::2]))
    output.parent.mkdir(parents=True,exist_ok=True)
    doc=canvas.Canvas(str(output),pagesize=(PAGE_W,PAGE_H),pageCompression=1)
    doc.setTitle('Kastention 应用界面设计规范 v3.1')
    doc.setAuthor('Kastention')
    doc.setSubject('现行UI规则、规范示意、代表页面和交互反馈；规范文档v3.1')
    style=ParagraphStyle('body',fontName=BODY_FONT,fontSize=10.2,leading=17.2,
                         textColor=col('body'),wordWrap='CJK',alignment=TA_LEFT,
                         splitLongWords=True,spaceAfter=7)
    caption=ParagraphStyle('caption',parent=style,fontSize=7.8,leading=12,textColor=col('secondary'))
    heading=ParagraphStyle('heading',parent=style,fontSize=11.5,leading=18,textColor=col('text'))
    table_style=ParagraphStyle('table',parent=style,fontSize=9,leading=13.5)
    measurements=[]
    errors=[]
    for page_no,(slug,source) in enumerate(pages,1):
        doc.setFillColor(col('solid'));doc.rect(0,0,PAGE_W,PAGE_H,fill=1,stroke=0)
        doc.setFillColor(col('secondary'));doc.setFont('Helvetica',7.5)
        doc.drawString(MARGIN,PAGE_H-28,'KASTENTION / APP UI GUIDELINES')
        doc.drawRightString(PAGE_W-MARGIN,PAGE_H-28,'v3.1 / 2026.11.02')
        doc.setStrokeColor(col('border'));doc.setLineWidth(.5)
        doc.line(MARGIN,41,PAGE_W-MARGIN,41)
        doc.setFont(BODY_FONT,7.5);doc.setFillColor(col('secondary'))
        doc.drawString(MARGIN,27,'规范示意 · v3.1')
        doc.setFont('Helvetica',8);doc.drawRightString(PAGE_W-MARGIN,27,f'{page_no:02d} / {len(pages):02d}')
        doc.bookmarkPage(slug)
        lines=source.strip().splitlines()
        title=next((line.lstrip('# ') for line in lines if line.startswith('#')),slug)
        doc.addOutlineEntry(title,slug,0,False)
        y=PAGE_H-62
        blocks=[]
        i=0
        while i<len(lines):
            line=lines[i].strip()
            if not line or line.startswith('<!--'):
                i+=1;continue
            if line.startswith('# '):
                blocks.append(('cover-title',line[2:]));i+=1
            elif line.startswith('## '):
                blocks.append(('title',line[3:]));i+=1
            elif line.startswith('### '):
                blocks.append(('h3',line[4:]));i+=1
            elif line.startswith('!['):
                match=re.match(r'!\[([^]]*)\]\(assets/([\w-]+)\.svg\)',line)
                if not match:raise ValueError(f'Unsupported figure: {line}')
                blocks.append(('figure',(match[2],match[1])));i+=1
            elif line.startswith('|'):
                rows=[]
                while i<len(lines) and lines[i].strip().startswith('|'):
                    cells=[p.strip() for p in lines[i].strip().strip('|').split('|')]
                    if not all(re.fullmatch(r':?-+:?',p or '-') for p in cells):rows.append(cells)
                    i+=1
                blocks.append(('table',rows))
            else:
                para=[line];i+=1
                while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','![','|','<!--')):
                    para.append(lines[i].strip());i+=1
                blocks.append(('p',' '.join(para)))
        for kind,value in blocks:
            if kind in ('title','cover-title'):
                size=38 if kind=='cover-title' else 22
                font='Helvetica' if kind=='cover-title' else BODY_FONT
                doc.setFont(font,size);doc.setFillColor(col('text'))
                doc.drawString(MARGIN,y-size,value)
                y-=size+20
                if kind=='title':
                    doc.setStrokeColor(col('accent'));doc.setLineWidth(3)
                    doc.line(MARGIN,y+7,MARGIN+34,y+7)
            elif kind=='figure':
                name,label=value;d=drawings[name]
                scale=WIDTH/d.width
                height=d.height*scale
                doc.saveState();doc.translate(MARGIN,y-height);doc.scale(scale,scale)
                renderPDF.draw(d,doc,0,0);doc.restoreState()
                y-=height+7
                p=Paragraph(markup(label),caption);_,h=p.wrap(WIDTH,1000)
                p.drawOn(doc,MARGIN,y-h);y-=h+12
            elif kind=='table':
                count=len(value[0])
                ratios=([.32,.68] if count==2 else [.34,.33,.33] if count==3 else [1/count]*count)
                if slug=='color':ratios=[.48,.26,.26]
                if slug.startswith('glossary'):ratios=[.32,.34,.34]
                cell_style = ParagraphStyle('glossary',parent=table_style,fontSize=10,leading=16) if slug.startswith('glossary') else table_style
                rows=[[Paragraph(markup(cell),cell_style) for cell in row] for row in value]
                table=Table(rows,colWidths=[WIDTH*r for r in ratios],hAlign='LEFT')
                table.setStyle(TableStyle([
                    ('BACKGROUND',(0,0),(-1,0),col('bg')),
                    ('VALIGN',(0,0),(-1,-1),'TOP'),
                    ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
                    ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
                    ('LINEBELOW',(0,0),(-1,0),.8,col('border')),
                    ('LINEBELOW',(0,1),(-1,-1),.35,col('border')),
                ]))
                _,h=table.wrap(WIDTH,2000);table.drawOn(doc,MARGIN,y-h);y-=h+12
            else:
                s=heading if kind=='h3' else style
                p=Paragraph(markup(value),s);_,h=p.wrap(WIDTH,2000)
                p.drawOn(doc,MARGIN,y-h);y-=h+(6 if kind=='h3' else 9)
            if y<56:errors.append({'page':page_no,'slug':slug,'block':kind,'bottom':round(y,2)})
        measurements.append({'page':page_no,'section':slug,'content_bottom_pt':round(y,2),'safe_bottom_pt':56})
        doc.showPage()
    doc.save()
    report={'pages':len(pages),'figures':len(drawings),'font':str(font_path),
            'source_sha256':hashlib.sha256(TEXT.read_bytes()).hexdigest(),
            'pdf_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
            'layout':measurements,'overflow':errors}
    check_path.parent.mkdir(parents=True,exist_ok=True)
    check_path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'pdf':str(output),'pages':len(pages),'figures':len(drawings),'overflow':errors},ensure_ascii=False))
    if errors:raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'docs/prd/Kastention-App-UI-Guidelines-v3.1.pdf')
    parser.add_argument('--validation',type=Path,default=ROOT/'tmp/pdfs/kastention-ui-20261102/layout.json')
    args=parser.parse_args()
    export(args.output.resolve(),args.validation.resolve())

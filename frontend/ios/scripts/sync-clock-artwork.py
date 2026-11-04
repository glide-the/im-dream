#!/usr/bin/env python3
# [Input] User-owned v4.2 prototype, original shared SVG paths and the existing fontTools 4.60.1 build tool.
# [Output] Predeclared vector commands and animation keyframes for the unified native artwork.
# [Pos] Asset generation only; no runtime SVG parser, geometry sampling or application dependency.
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from fontTools.pens.recordingPen import RecordingPen
from fontTools.svgLib.path import parse_path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'docs/prd/Kastention-一体化时间时钟-v4.2-离散跳针与发丝.html'
BASE = ROOT / 'frontend/src/assets/startup-artwork.json'
TARGET = ROOT / 'frontend/src/assets/kastention-clock-v4.2.json'
html = SOURCE.read_text()
ns = {'s': 'http://www.w3.org/2000/svg'}
svg = ET.fromstring(re.search(r'<svg class="dial-svg".*?</svg>', html, re.S).group())

def commands(d):
    pen = RecordingPen()
    parse_path(d, pen)
    names = {'moveTo': 'M', 'lineTo': 'L', 'curveTo': 'C', 'qCurveTo': 'Q', 'closePath': 'Z'}
    result = []
    for op, points in pen.value:
        if op == 'endPath':
            continue
        result.append([names[op], *[round(number, 8) for point in points for number in point]])
    return result

base = json.loads(BASE.read_text())
paths = []
for i, item in enumerate(base['paths']):
    paths.append({**item, 'commands': commands(item['d'])})
hair = svg.findall(".//s:g[@id='hair']/s:path", ns)
for index, element in enumerate(hair, 1):
    assert element.attrib['d'] == paths[index]['d']
    animation = element.find('s:animate', ns)
    paths[index]['keyframes'] = [commands(d) for d in animation.attrib['values'].split(';')]
    assert paths[index]['keyframes'][0] == paths[index]['keyframes'][-1] == paths[index]['commands']
    paths[index]['keyTimes'] = [float(v) for v in animation.attrib['keyTimes'].split(';')]
    paths[index]['splines'] = [[float(v) for v in curve.split()] for curve in animation.attrib['keySplines'].split(';')]

icons = re.search(r'const iconPaths=\{(.*?)\n\};', html, re.S).group(1)
marks = []
for hour, (name, markup) in enumerate(re.findall(r"(\w+):'([^']+)'", icons)):
    parts = []
    for shape in ET.fromstring('<svg>' + markup + '</svg>'):
        parts.append({'commands': commands(shape.attrib['d'])} if shape.tag == 'path' else {'circle': [float(shape.attrib[k]) for k in ['cx','cy','r']]})
        parts[-1]['fill'] = shape.attrib.get('fill', 'none')
        parts[-1]['stroke'] = shape.attrib.get('stroke', 'currentColor')
    angle = (hour * 30 - 90) * math.pi / 180
    radius = 1 / math.sqrt((math.cos(angle)/342)**2 + (math.sin(angle)/291)**2)
    marks.append({'hour': hour, 'name': name, 'center': [round(625 + radius*math.cos(angle),8), round(651 + radius*math.sin(angle),8)], 'parts': parts})
assert len(marks) == 12
result = {
    'source': {'prototype': str(SOURCE.relative_to(ROOT)), 'sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'baseSHA256': hashlib.sha256(BASE.read_bytes()).hexdigest()},
    'size': 1254, 'pivot': [625,650], 'paths': paths,
    'sadMouth': commands('M 495 746 C 528 680 590 684 648 737'),
    'marks': marks, 'markSize': 48,
    'hairDuration': .520, 'mouthDuration': .290, 'tickOffsetMs': 4,
    'handKeyTimes': [0,.30,.51,.69,.81,1], 'handFractions': [0,0,.075,1.065,.985,1],
    'handSplines': [[0,0,1,1],[.7,0,1,1],[.55,0,.8,1],[.2,0,.45,1],[.3,0,.6,1]],
    'hands': [{'key':'hour','duration':.355,'step':30,'fromY':674,'toY':493,'width':19}, {'key':'minute','duration':.300,'step':6,'fromY':685,'toY':401,'width':13}, {'key':'second','duration':.240,'step':6,'fromY':720,'toY':359,'width':6}],
}
content = json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n'
parser = argparse.ArgumentParser(); parser.add_argument('--check', action='store_true'); args = parser.parse_args()
if args.check:
    assert TARGET.read_text() == content, 'Clock asset differs from v4.2 source'
    print('Unified v4.2 artwork verified: 7 original paths, 3 hair curves, 12 original marks, discrete hand policy')
else:
    TARGET.write_text(content)
    print('Generated ' + str(TARGET.relative_to(ROOT)))

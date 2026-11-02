#!/usr/bin/env python3
# [Input] Original public Excalifont WOFF2 and Xiaolai TTF, pinned fontTools/Brotli.
# [Output] Native font files with original glyphs/names and a source/output receipt.
# [Pos] iOS build preparation; no font substitution or application behavior changes.
from pathlib import Path
import hashlib
import json
import shutil
from fontTools.ttLib import TTFont

ios = Path(__file__).resolve().parents[1]
public = ios.parent / 'public'
output = ios / 'RuntimeArtifacts/fonts'
if output.is_symlink():
    raise RuntimeError('Native font output must be an ordinary directory')
output.mkdir(parents=True, exist_ok=True)
receipt = []
for name, extension in [('Excalifont-Regular', 'woff2'), ('Xiaolai-Regular', 'ttf')]:
    source = public / f'{name}.{extension}'
    destination = output / f'{name}.ttf'
    original = TTFont(source, recalcTimestamp=False)
    if extension == 'woff2':
        original.flavor = None
        original.save(destination)
    else:
        shutil.copy2(source, destination)
    native = TTFont(destination, recalcTimestamp=False)
    if original.getBestCmap() != native.getBestCmap():
        raise RuntimeError(f'Glyph mapping changed for {name}')
    if original['hmtx'].metrics != native['hmtx'].metrics:
        raise RuntimeError(f'Glyph metrics changed for {name}')
    if 'glyf' in original:
        for glyph in original.getGlyphOrder():
            if original['glyf'][glyph].getCoordinates(original['glyf']) != native['glyf'][glyph].getCoordinates(native['glyf']):
                raise RuntimeError(f'Glyph outline changed for {name}')
    names = {str(key): original['name'].getDebugName(key) for key in [1, 6, 13, 14]}
    receipt.append({'source': source.name, 'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                    'output': destination.name, 'outputSha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
                    'glyphMappingAndMetrics': 'unchanged', 'names': names})
(output / 'font-receipt.json').write_text(json.dumps({'fontTools':'4.60.1','brotli':'1.2.0','fonts':receipt}, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'fonts':[{'source': item['source'], 'postscriptName':item['names']['6'], 'glyphMappingAndMetrics': item['glyphMappingAndMetrics']} for item in receipt]}))

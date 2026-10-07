# [Input] Current activity documents, new Markdown inventories and installed Mermaid/local Chrome.
# [Output] Read-only structure/path/inventory/README parity and four current Mermaid syntax results.
# [Pos] Explicit technical document-check harness; no page, API, database or functional acceptance.
# [Sync] 2026-10-07: version the existing document harness; resolve repository root from this workflow path.
# [Sync] 2026-10-07: parse/render all current Mermaid graphs inside an owned Chrome DOM; preserve history and only read documents.
from pathlib import Path
import json
import re
import subprocess
import sys
from urllib.parse import unquote

root = Path(__file__).resolve().parents[5]
workflow = root / 'docs/design/claude-agent/priority-activity-workflow-20261007'
documents = sorted(workflow.rglob('*.md')) + [
    root / 'docs/prd/Chat Sidebar.md',
    root / 'docs/prd/Chat Dashboard.md',
    root / 'docs/prd/Chat Sidebar pre-priority-activity-20261007-history.md',
    root / 'docs/prd/chat/priority-activity.md',
    root / 'docs/design/claude-agent/priority-activity-sidebar.md',
    root / 'docs/exec/priority-activity-design-review-20261007.md',
    root / 'docs/exec/priority-activity-implementation-20261007.md',
]
errors = []
links = 0
for path in documents:
    content = path.read_text()
    if sum(line.lstrip().startswith('```') for line in content.splitlines()) % 2:
        errors.append(f'unclosed Markdown fence: {path.relative_to(root)}')
    for line_number, line in enumerate(content.splitlines(), 1):
        if line.rstrip() != line:
            errors.append(f'trailing whitespace: {path.relative_to(root)}:{line_number}')
    for match in re.finditer(r'\[[^\]]*\]\((<[^>]*>|[^)\n]*)\)', content):
        target = match.group(1).strip().strip('<>')
        if not target or target.startswith('#') or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
            continue
        target = unquote(target.split('#', 1)[0])
        if target and not (path.parent / target).exists():
            errors.append(f'missing local link: {path.relative_to(root)} -> {target}')
        links += 1

inventory = {
    'frontend/app/_dream/components/chat/.folder.md': [
        'ChatView.tsx', 'Icons.tsx', 'ActivitySidebar.tsx', 'ActivitySidebar.css',
        'activitySidebarModel.ts', 'useActivitySidebarData.ts',
    ],
    'frontend/app/_dream/components/chat/__tests__/.folder.md': [
        'ActivitySidebarModel.test.ts', 'ActivitySidebar.browser.test.ts',
    ],
    'frontend/app/_dream/api/.folder.md': ['chatHistoryApi.ts', 'scheduledTaskApi.ts'],
    'frontend/app/_dream/.folder.md': ['i18n.ts'],
    'docs/prd/.folder.md': [
        'Chat Sidebar.md', 'Chat Dashboard.md', 'Chat Sidebar pre-priority-activity-20261007-history.md',
    ],
    'docs/prd/chat/.folder.md': ['priority-activity.md'],
    'docs/design/claude-agent/.folder.md': [
        'priority-activity-sidebar.md', 'priority-activity-workflow-20261007/',
    ],
    'docs/exec/.folder.md': [
        'priority-activity-design-review-20261007.md', 'priority-activity-implementation-20261007.md',
    ],
    'docs/design/claude-agent/priority-activity-workflow-20261007/workspace/.folder.md': ['4_ui_design.md'],
}
inventory_entries = 0
for folder, names in inventory.items():
    path = root / folder
    content = path.read_text()
    for name in names:
        if name not in content or not (path.parent / name).exists():
            errors.append(f'missing inventory entry/path: {folder} -> {name}')
        inventory_entries += 1

english = (root / 'README.md').read_text()
chinese = (root / 'README.zh.md').read_text()
headings = lambda text: [len(match.group(1)) for match in re.finditer(r'^(#+)\s', text, re.M)]
if headings(english) != headings(chinese):
    errors.append('README heading structure differs')
english_activity = [line for line in english.splitlines() if line.startswith('- **Chat activity**')]
chinese_activity = [line for line in chinese.splitlines() if line.startswith('- **Chat 活动**')]
if len(english_activity) != 1 or len(chinese_activity) != 1:
    errors.append('README activity feature is missing or duplicated')
elif ('docs/prd/chat/priority-activity.md' not in english_activity[0]
      or 'docs/prd/chat/priority-activity.md' not in chinese_activity[0]
      or 'last five minutes' not in english_activity[0] or '最近五分钟' not in chinese_activity[0]
      or 'deletion' not in english_activity[0] or '删除' not in chinese_activity[0]):
    errors.append('README activity rules/reference parity differs')

formal = root / 'docs/design/claude-agent/priority-activity-sidebar.md'
formal_text = formal.read_text()
graphs = re.findall(r'```mermaid\s*\n(.*?)\n```', formal_text, re.S)
if len(graphs) != 4:
    errors.append(f'expected four formal Mermaid graphs, got {len(graphs)}')
elif ('storyWorkspaceFetchDreamRuns' not in graphs[0] or 'M-->>A' in graphs[0] or 'A->>M' in graphs[0]
      or 'V->>A: props' not in graphs[0]):
    errors.append('normal graph differs from actual read/props ownership')
for relative in ['docs/prd/chat/priority-activity.md', 'docs/design/claude-agent/priority-activity-sidebar.md',
                 'docs/design/claude-agent/priority-activity-workflow-20261007/README.md']:
    content = (root / relative).read_text()
    if '12项focused' not in content or '技术验证待执行' in content:
        errors.append(f'current technical status is stale: {relative}')

node = r'''
import fs from 'node:fs';
import { chromium } from './frontend/node_modules/@playwright/test/index.mjs';
const text = fs.readFileSync('docs/design/claude-agent/priority-activity-sidebar.md', 'utf8');
const graphs = [...text.matchAll(/```mermaid\s*\n([\s\S]*?)\n```/g)].map(match => match[1]);
const browser = await chromium.launch({ channel: 'chrome', headless: true });
try {
  const page = await browser.newPage();
  await page.setContent('<!doctype html><html><body><main id="priority-document-check"></main></body></html>');
  await page.addScriptTag({ path: 'frontend/node_modules/mermaid/dist/mermaid.min.js' });
  const results = await page.evaluate(async (sources) => {
    window.mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' });
    const checked = [];
    for (let index = 0; index < sources.length; index++) {
      const parsed = await window.mermaid.parse(sources[index]);
      const rendered = await window.mermaid.render(`priority_document_graph_${index}`, sources[index]);
      if (!rendered.svg.includes('<svg')) throw new Error(`Graph ${index + 1} returned no SVG`);
      checked.push({ index: index + 1, type: parsed.diagramType });
    }
    return checked;
  }, graphs);
  for (const result of results) console.log(`mermaid_${result.index}=PASS type=${result.type} rendered=SVG`);
} finally {
  await browser.close();
}
'''
parsed = subprocess.run(['node', '--input-type=module', '-e', node], cwd=root, text=True, capture_output=True)
print(parsed.stdout.strip())
if parsed.returncode:
    errors.append(f'Mermaid parse failed: {parsed.stderr.strip()}')
print(json.dumps({'markdown_files': len(documents), 'local_links': links,
                  'inventory_entries': inventory_entries, 'readme_activity_parity': 1 if not any('README' in error for error in errors) else 0,
                  'formal_mermaid_blocks': len(graphs), 'errors': errors}, ensure_ascii=False))
sys.exit(1 if errors else 0)

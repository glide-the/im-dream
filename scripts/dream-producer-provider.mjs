import { createHash } from 'node:crypto';
import { createServer } from 'node:http';

const sha = (value) => `sha256:${createHash('sha256').update(value).digest('hex')}`;

export const PRODUCER_FILES = Object.freeze({
  project: `project_id: e2e-rain-station\nproject_name: E2E Rain Station\nformat:\n  total_episodes: 1\n`,
  character: `# Lin Yu\n\nA restrained night-shift station clerk.\n`,
  characterRefreshed: `# Lin Yu\n\nA restrained night-shift station clerk who protects a sealed letter.\n`,
  scene: `# Rain Station\n\nA closed platform under cold rain.\n`,
  outline: `---\nseries: E2E Rain Station\nepisode: 1\ntitle: The Last Train\n---\n# The Last Train\n\n## Story Goals\n- Establish the sealed letter.\n\n## Core Conflict\nLin Yu must decide whether to board the last train.\n\n## Cliffhanger\nThe train returns without a driver.\n\n## Scene Sequence\n\n### SC-01. Platform [scene-platform]\n\n**Scene Summary**:\nLin Yu opens the sealed letter.\n`,
  script: `---\nseries: E2E Rain Station\nepisode: 1\ntitle: The Last Train\nversion: 1\n---\n# The Last Train\n\nS01. Platform [scene-platform] - Night - Exterior\n\n[Rain crosses the empty platform.]\n\nCAM: CU | PUSH_IN | sealed letter | 3.0\n\nLin Yu (quietly)\nThe last train should have gone.\n`,
  storyboardInitial: `---\nepisode: EP01\ntotal_shots: 1\n---\nshots:\n  - shot_id: S01-E01-001\n    scene_ref: scene-platform\n    script_scene_ref: S01\n    narrative_beat_ref: SC-01\n    shot_type: CU\n    visual: Lin Yu holds the sealed letter in the rain.\n    camera:\n      movement: PUSH_IN\n    timing:\n      duration_sec: 3\n`,
  storyboardFinal: `---\nepisode: EP01\ntotal_shots: 1\ngenerated_from: script@v1\n---\nshots:\n  - shot_id: S01-E01-001\n    scene_ref: scene-platform\n    script_scene_ref: S01\n    narrative_beat_ref: SC-01\n    shot_type: CU\n    visual: Lin Yu opens the sealed letter as the driverless train arrives.\n    camera:\n      movement: PUSH_IN\n    timing:\n      duration_sec: 4\n`,
  prompts: `episode: 1\nproject: e2e-rain-station\nshots:\n  - shot_id: S01-E01-001\n    kling: Cold rain, sealed letter, slow push in.\n    runway: A restrained cinematic push toward Lin Yu.\n    jimeng: Night platform, driverless train, blue-gray palette.\n`,
  render: `# EP01 Render Guide\n\n## Render Queue\n\n\`\`\`yaml\n- shot_id: S01-E01-001\n  status: pending\n  renderer: local-e2e\n\`\`\`\n`,
});

const scriptReview = `---\nscope: script\noverall_verdict: APPROVED\nreviewed_files:\n  - script.md\nsource_revisions:\n  script.md: ${sha(PRODUCER_FILES.script)}\n---\n# Script Review\n\nThe current canonical script is approved.\n`;
export function buildFullReview(storyboardContent) {
  return `---\nscope: full-chain\noverall_verdict: APPROVED\nreviewed_files:\n  - episode-outline.md\n  - script.md\n  - storyboard.yaml\n  - prompts/ep001-prompts.yml\nsource_revisions:\n  episode-outline.md: ${sha(PRODUCER_FILES.outline)}\n  script.md: ${sha(PRODUCER_FILES.script)}\n  storyboard.yaml: ${sha(storyboardContent)}\n  prompts/ep001-prompts.yml: ${sha(PRODUCER_FILES.prompts)}\n---\n# Full Chain Review\n\nThe canonical Episode chain and shot associations are approved.\n`;
}
const fullReview = buildFullReview(PRODUCER_FILES.storyboardInitial);

function write(path, content) {
  return { name: 'Write', input: { file_path: path, content } };
}
function mcp(name, input) {
  return { name: `mcp__story_workspace__${name}`, input };
}

const initialSteps = [
  write('stories/e2e-rain-station/project.yaml', PRODUCER_FILES.project),
  write('stories/e2e-rain-station/characters/lin-yu.md', PRODUCER_FILES.character),
  write('stories/e2e-rain-station/scenes/platform.md', PRODUCER_FILES.scene),
  write('stories/e2e-rain-station/episodes/EP01/storyboard.yaml', PRODUCER_FILES.storyboardInitial),
  mcp('write_dream_run', { workflowRunId: '$RUN_ID', expectedRevision: 0 }),
  mcp('write_dream_stage', {
    workflowRunId: '$RUN_ID', stage: 'characters', expectedRevision: 0,
    sourceFiles: ['stories/e2e-rain-station/characters/lin-yu.md'],
    items: [{ entityId: 'lin-yu', displayName: 'Lin Yu', summary: 'Restrained station clerk', sourceFile: 'stories/e2e-rain-station/characters/lin-yu.md', relations: ['scene-platform'] }],
  }),
  mcp('write_dream_stage', {
    workflowRunId: '$RUN_ID', stage: 'scenes', expectedRevision: 0,
    sourceFiles: ['stories/e2e-rain-station/scenes/platform.md'],
    items: [{ entityId: 'scene-platform', displayName: 'Rain Station', summary: 'Closed platform in cold rain', sourceFile: 'stories/e2e-rain-station/scenes/platform.md', relations: ['lin-yu'] }],
  }),
  mcp('write_dream_stage', {
    workflowRunId: '$RUN_ID', stage: 'storyboards', expectedRevision: 0,
    sourceFiles: ['stories/e2e-rain-station/episodes/EP01/storyboard.yaml'],
    items: [{ entityId: 'ep01-storyboard', displayName: 'EP01 The Last Train', summary: 'One-shot canonical storyboard', sourceFile: 'stories/e2e-rain-station/episodes/EP01/storyboard.yaml', relations: ['EP01', 'scene-platform'] }],
  }),
];

const actionSteps = {
  recover_first_episode_binding: [mcp('bind_first_episode', { workflowRunId: '$RUN_ID', expectedBindingRevision: 0 })],
  plan_episode: [write('stories/e2e-rain-station/episodes/EP01/episode-outline.md', PRODUCER_FILES.outline), mcp('record_episode_workflow_completion', { workflowRunId: '$RUN_ID' })],
  write_script: [write('stories/e2e-rain-station/episodes/EP01/script.md', PRODUCER_FILES.script), mcp('record_episode_workflow_completion', { workflowRunId: '$RUN_ID' })],
  review_script: [write('stories/e2e-rain-station/episodes/EP01/review-report.md', scriptReview), mcp('record_episode_workflow_completion', { workflowRunId: '$RUN_ID' })],
  refresh_assets: [write('stories/e2e-rain-station/characters/lin-yu.md', PRODUCER_FILES.characterRefreshed), mcp('record_episode_workflow_completion', { workflowRunId: '$RUN_ID' })],
  regenerate_storyboard: [write('stories/e2e-rain-station/episodes/EP01/storyboard.yaml', PRODUCER_FILES.storyboardFinal), mcp('record_episode_workflow_completion', { workflowRunId: '$RUN_ID' })],
  generate_prompts: [write('stories/e2e-rain-station/episodes/EP01/prompts/ep001-prompts.yml', PRODUCER_FILES.prompts), mcp('record_episode_workflow_completion', { workflowRunId: '$RUN_ID' })],
  review_full_chain: [write('stories/e2e-rain-station/episodes/EP01/review-report.md', fullReview), mcp('record_episode_workflow_completion', { workflowRunId: '$RUN_ID' })],
  validate_episode: [mcp('record_episode_workflow_completion', { workflowRunId: '$RUN_ID' })],
  prepare_render_guide: [write('stories/e2e-rain-station/episodes/EP01/renders/render-guide.md', PRODUCER_FILES.render), mcp('record_episode_workflow_completion', { workflowRunId: '$RUN_ID' })],
};

function messageText(message) {
  if (!message || !Array.isArray(message.content)) return typeof message?.content === 'string' ? message.content : '';
  return message.content.filter((item) => item?.type === 'text').map((item) => item.text).join('\n');
}

export function currentInstruction(messages) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index]?.role !== 'user') continue;
    const text = messageText(messages[index]);
    if (text && !messages[index].content?.every?.((item) => item?.type === 'tool_result')) return text;
  }
  return '';
}

function systemText(system) {
  if (typeof system === 'string') return system;
  if (!Array.isArray(system)) return '';
  return system.filter((item) => item?.type === 'text').map((item) => item.text).join('\n');
}

function toolResultEvidence(messages) {
  if (!Array.isArray(messages)) return [];
  return messages.flatMap((message) => (
    Array.isArray(message?.content)
      ? message.content.filter((item) => item?.type === 'tool_result').map((item) => ({
          isError: item?.is_error === true,
          codes: [...new Set((JSON.stringify(item).match(/\b[A-Z][A-Z0-9_]{3,}\b/g) ?? []))],
          reasons: [...new Set([...JSON.stringify(item).matchAll(/"reason"\s*:\s*"([a-z_]+)"/g)].map((match) => match[1]))],
        }))
      : []
  ));
}

export function instructionKind(text) {
  if (text.includes('Dream 工作空间生成流程')) return 'initial';
  if (text.includes('请恢复第一集关联')) return 'recover_first_episode_binding';
  for (const action of Object.keys(actionSteps)) {
    if (text.includes(action)) return action;
  }
  return 'generic';
}

export function runIdFromText(text) {
  return text.match(/run_[0-9a-f]{32}/)?.[0] ?? process.env.INK_PRODUCER_RUN_ID ?? '';
}

function frame(event, payload) {
  return `event: ${event}\ndata: ${JSON.stringify(payload)}\n\n`;
}

function toolResponse(tool, requestNumber, runId) {
  const input = JSON.parse(JSON.stringify(tool.input).replaceAll('$RUN_ID', runId));
  const id = `toolu_e2e_${String(requestNumber).padStart(4, '0')}`;
  return [
    frame('message_start', { type: 'message_start', message: { id: `msg_e2e_${requestNumber}`, type: 'message', role: 'assistant', model: 'dream-producer-upstream', content: [], stop_reason: null, stop_sequence: null, usage: { input_tokens: 29, output_tokens: 0 } } }),
    frame('content_block_start', { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id, name: tool.name, input: {} } }),
    frame('content_block_delta', { type: 'content_block_delta', index: 0, delta: { type: 'input_json_delta', partial_json: JSON.stringify(input) } }),
    frame('content_block_stop', { type: 'content_block_stop', index: 0 }),
    frame('message_delta', { type: 'message_delta', delta: { stop_reason: 'tool_use', stop_sequence: null }, usage: { output_tokens: 11 } }),
    frame('message_stop', { type: 'message_stop' }),
  ].join('');
}

function endResponse(requestNumber) {
  return [
    frame('message_start', { type: 'message_start', message: { id: `msg_e2e_${requestNumber}`, type: 'message', role: 'assistant', model: 'dream-producer-upstream', content: [], stop_reason: null, stop_sequence: null, usage: { input_tokens: 17, output_tokens: 0 } } }),
    frame('content_block_start', { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } }),
    frame('content_block_delta', { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: '当前唯一授权步骤已完成，等待服务端重新读取权威状态。' } }),
    frame('content_block_stop', { type: 'content_block_stop', index: 0 }),
    frame('message_delta', { type: 'message_delta', delta: { stop_reason: 'end_turn', stop_sequence: null }, usage: { output_tokens: 13 } }),
    frame('message_stop', { type: 'message_stop' }),
  ].join('');
}

export async function startDreamProducerProvider() {
  const sessions = new Map();
  const observations = [];
  let requestNumber = 0;
  const server = createServer((request, response) => {
    let raw = '';
    request.setEncoding('utf8');
    request.on('data', (chunk) => { raw += chunk; });
    request.on('end', () => {
      if (request.url?.includes('count_tokens')) {
        response.writeHead(200, { 'content-type': 'application/json' });
        response.end(JSON.stringify({ input_tokens: 17 }));
        return;
      }
      requestNumber += 1;
      let body = {};
      try { body = JSON.parse(raw || '{}'); } catch {}
      const instruction = currentInstruction(body.messages ?? []);
      const kind = instructionKind(instruction);
      const runId = runIdFromText(`${systemText(body.system)}\n${instruction}`);
      const signature = `${kind}:${createHash('sha256').update(instruction).digest('hex')}`;
      const index = sessions.get(signature) ?? 0;
      const steps = kind === 'initial' ? initialSteps : (actionSteps[kind] ?? []);
      const tool = steps[index];
      sessions.set(signature, index + 1);
      observations.push({
        requestNumber,
        kind,
        step: index,
        model: body.model ?? null,
        hasRunId: Boolean(runId),
        toolResultEvidence: toolResultEvidence(body.messages).slice(-1),
        instructionPrefix: instruction.slice(0, 500),
        systemPrefix: systemText(body.system).slice(0, 500),
        messageShapes: Array.isArray(body.messages)
          ? body.messages.map((message) => ({
              role: message?.role ?? null,
              contentType: Array.isArray(message?.content) ? 'array' : typeof message?.content,
              contentKinds: Array.isArray(message?.content)
                ? message.content.map((item) => item?.type ?? typeof item)
                : [],
            }))
          : [],
      });
      response.writeHead(200, { 'content-type': 'text/event-stream; charset=utf-8', 'cache-control': 'no-store', 'request-id': `producer-${requestNumber}` });
      response.end(tool && runId ? toolResponse(tool, requestNumber, runId) : endResponse(requestNumber));
    });
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('Producer provider port unavailable');
  return {
    url: `http://127.0.0.1:${address.port}`,
    observations,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

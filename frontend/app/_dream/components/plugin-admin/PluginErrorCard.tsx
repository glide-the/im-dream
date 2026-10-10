// [Input] Structured workflow error code, safe summary, stage, and recovery callback.
// [Output] Sanitized error explanation and actionable recovery control.
// [Pos] Plugin Admin error boundary/card; never renders stack traces or local paths.
// [Sync] 2026-10-10: retain execution error codes but describe the workflow failure and recovery in concrete terms.

const ERROR_COPY: Record<string, { message: string; recovery: string }> = {
  DECK_PLUGIN_MANIFEST_INVALID: { message: '插件定义不合法，请联系发布者。', recovery: '联系发布者发布修复版本' },
  DECK_PLUGIN_SOURCE_DENIED: { message: '插件来源未获允许。', recovery: '申请管理员审批来源' },
  DECK_PLUGIN_INTEGRITY_FAILED: { message: '工作流文件校验失败，当前版本不可使用。', recovery: '选择文件校验通过的版本' },
  RUNTIME_MARKETPLACE_UNAVAILABLE: { message: '工作流依赖的下载来源暂时不可用。', recovery: '来源恢复后重试' },
  RUNTIME_PLUGIN_MATERIALIZATION_FAILED: { message: '工作流已登记，但所需文件准备失败。', recovery: '重试文件准备' },
  DECK_HOST_INCOMPATIBLE: { message: '当前平台版本与该插件不兼容。', recovery: '升级平台或选择兼容版本' },
  CLAUDE_AGENT_INCOMPATIBLE: { message: '当前 Agent 无法执行此工作流版本。', recovery: '选择兼容的工作流版本' },
  STORY_SCHEMA_INCOMPATIBLE: { message: '插件输出无法被当前 Story Workspace 消费。', recovery: '选择兼容版本' },
  WORKFLOW_PERMISSION_DENIED: { message: '当前身份没有执行该管理动作的权限。', recovery: '申请插件管理员授权' },
  DECK_PLUGIN_DISABLED: { message: '该 Deck 工作流插件已禁用。', recovery: '由管理员重新启用' },
  DECK_PLUGIN_UPGRADE_PENDING: { message: '升级新增能力，正在等待管理员审批。', recovery: '审阅能力差异' },
  RUNTIME_PLUGIN_NOT_READY: { message: '工作流所需文件尚未准备完成。', recovery: '等待准备完成或重试准备' },
  RUNTIME_PLUGIN_LOAD_FAILED: { message: '工作流所需文件已准备完成，但加载失败。', recovery: '使用新会话重试' },
};

interface PluginErrorCardProps {
  code?: string;
  summary?: string;
  stage?: string;
  operationId?: string;
  runId?: string;
  canRecover?: boolean;
  onRecover?: () => void;
}

function safeSummary(summary: string | undefined): string | undefined {
  if (!summary) return undefined;
  const firstLine = summary.split(/\r?\n/, 1)[0].trim();
  if (!firstLine || firstLine.includes('/Users/') || firstLine.includes('Traceback')) return undefined;
  return firstLine.slice(0, 240);
}

export default function PluginErrorCard({
  code,
  summary,
  stage,
  operationId,
  runId,
  canRecover = false,
  onRecover,
}: PluginErrorCardProps) {
  if (!code && !summary) return null;
  const copy = code ? ERROR_COPY[code] : undefined;
  const message = copy?.message ?? safeSummary(summary) ?? '插件操作未完成，请查看安全错误码并重试。';

  return (
    <section className="plugin-admin-error" role="alert">
      <div className="plugin-admin-error__icon" aria-hidden="true">!</div>
      <div>
        <strong>{message}</strong>
        {code && <code>{code}</code>}
        <dl className="plugin-admin-inline-facts">
          {stage && <><dt>失败阶段</dt><dd>{stage}</dd></>}
          {operationId && <><dt>operation_id</dt><dd>{operationId}</dd></>}
          {runId && <><dt>run_id</dt><dd>{runId}</dd></>}
        </dl>
        {canRecover && onRecover && (
          <button type="button" className="plugin-admin-link-button" onClick={onRecover}>
            {copy?.recovery ?? '重试'}
          </button>
        )}
      </div>
    </section>
  );
}

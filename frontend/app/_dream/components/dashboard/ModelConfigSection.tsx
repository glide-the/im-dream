// [Sync] 2026-10-29: consume shared model-settings lifecycle; original Web DOM, CSS and business controls remain.
// [Input] Shared Settings model/configuration state and original dashboard design tokens.
// [Output] Original Web model, prompt, workspace, approval and tool environment controls.
// [Pos] Browser renderer for canonical Settings model configuration.
import useModelConfig,{parseSandboxNetworkDomains,parseSandboxFsWritePaths} from '../../hooks/useModelConfig';
import {imageModelAvailabilityMessage,type GatewayModel} from '../../api/gatewayModelsApi';
export type {SandboxNetworkMode} from '../../hooks/useModelConfig';
const SANDBOX_NETWORK_ACCESS_OPTIONS=[{enabled:false,label:'关闭'},{enabled:true,label:'启用'}];

function ModelChoices({ models, selected, kind, disabled, defaultAlias, onChange }: {
  models: GatewayModel[]; selected: string; kind: 'ai' | 'image'; disabled: boolean;
  defaultAlias?: string | null; onChange: (alias: string) => void;
}) {
  return (
    <fieldset disabled={disabled} style={{ width: 'min(100%, 36rem)', margin: 0, padding: 0, border: 0 }}>
      <legend style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0 0 0 0)', whiteSpace: 'nowrap' }}>
        {kind === 'ai' ? '选择 AI 模型' : '选择 Image 模型'}
      </legend>
      <div style={{ display: 'grid', gap: '0.5rem' }}>
        {models.map(option => {
          const callable = kind === 'ai' ? option.callable : option.images?.callable === true;
          const capability = kind === 'ai' ? option.responsesImage : option.images;
          const availabilityLabel = kind === 'image' ? imageModelAvailabilityMessage(option)
            : callable ? (defaultAlias === option.modelAlias ? '推荐' : null)
              : option.availability === 'upgrade_required' ? `需要 ${option.requiredPlanCode ?? '更高'} 套餐`
                : option.availability === 'allowance_exhausted' ? '额度已用完' : '暂不可用';
          const checked = selected === option.modelAlias;
          return (
            <label key={option.modelAlias} style={{ display: 'flex', minHeight: '2.9rem', alignItems: 'center', gap: '0.7rem', padding: '0.7rem 0.8rem', borderRadius: '10px', border: `1px solid ${checked ? 'var(--color-border-focus)' : 'var(--color-border-paper)'}`, background: checked ? 'var(--color-bg-hover)' : 'transparent', opacity: callable ? 1 : 0.6, cursor: callable ? 'pointer' : 'not-allowed' }}>
              <input type="radio" name={kind === 'ai' ? 'platform-model' : 'image-model'} value={option.modelAlias} checked={checked} disabled={!callable || disabled} onChange={() => onChange(option.modelAlias)} />
              <span style={{ minWidth: 0, flex: '1 1 auto', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <strong style={{ color: 'var(--color-text-primary)', fontSize: '0.84rem' }}>{option.displayName}</strong>
                {(capability?.generation || capability?.edit) ? <span style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', color: 'var(--color-text-muted)', fontSize: '0.72rem' }}>
                  {capability.generation ? <span>{kind === 'ai' ? '图片生成' : '生成'}</span> : null}
                  {capability.edit ? <span>{kind === 'ai' ? '图片编辑' : '编辑'}</span> : null}
                  {kind === 'ai' && !capability.callable ? <span>图片操作暂不可用</span> : null}
                </span> : null}
                {availabilityLabel ? <span style={{ color: 'var(--color-text-muted)', fontSize: '0.72rem' }}>{availabilityLabel}</span> : null}
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export default function ModelConfigSection() {
  const {
    systemPrompt,setSystemPrompt,workspaceMode,sandboxNetworkMode,sandboxNetworkDomains,sandboxNetworkSaving,
    sandboxNetworkStatus,sandboxNetworkAddingDomain,setSandboxNetworkAddingDomain,sandboxNetworkNewDomain,setSandboxNetworkNewDomain,sandboxFsPaths,
    sandboxFsSaving,sandboxFsStatus,sandboxFsAddingPath,setSandboxFsAddingPath,sandboxFsNewPath,setSandboxFsNewPath,
    imFullAccessEnabled,selectedModel,selectedImageModel,imageModelOptions,imageModelStatus,configReadError,
    modelSaveUnconfirmed,modelOptions,defaultModelAlias,modelCatalogError,modelStatus,setModelLoadNonce,
    dirty,setDirty,configLoading,setConfigLoading,saving,envVars,
    envVarsDirty,envVarsSaving,handleModelChange,handleImageModelChange,handleWorkspaceToggle,handleSandboxNetworkAccessToggle,
    handleSandboxNetworkPolicySelect,handleAddSandboxNetworkDomain,handleRemoveSandboxNetworkDomain,handleAddSandboxFsPath,handleRemoveSandboxFsPath,handleImFullAccessToggle,
    handleSavePrompt,handleResetPrompt,handleAddEnvVar,handleRemoveEnvVar,handleUpdateEnvVar,handleSaveEnvVars
  }=useModelConfig();
  const fieldStyle: React.CSSProperties = {
    width: '100%',
    padding: '0.75rem 0.85rem',
    borderRadius: '12px',
    border: '1px solid var(--color-border-paper)',
    background: 'var(--color-bg-paper)',
    color: 'var(--color-text-primary)',
    fontFamily: 'inherit',
    fontSize: '0.9rem',
    boxSizing: 'border-box',
  };

  if (configLoading) {
    return <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Loading config…</p>;
  }

  const sandboxNetworkEnabled = sandboxNetworkMode !== 'disabled';
  const sandboxNetworkDomainsList = parseSandboxNetworkDomains(sandboxNetworkDomains);
  const sandboxFsPathsList = parseSandboxFsWritePaths(sandboxFsPaths);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Model */}
      <div>
        <p style={{ margin: '0 0 0.65rem', fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
          AI 模型 / Model
        </p>
        <p style={{ margin: '-0.35rem 0 0.85rem', color: 'var(--color-text-muted)', fontSize: '0.78rem' }}>
          选择新对话使用的模型。
        </p>
        {configReadError ? <div role="alert">
          <p>{configReadError}</p>
          <button type="button" onClick={() => setModelLoadNonce(value => value + 1)}>重新加载设置</button>
        </div> : null}
        {modelSaveUnconfirmed && !configReadError ? <button type="button" disabled={saving}
          onClick={() => setModelLoadNonce(value => value + 1)}>重新加载设置</button> : null}
        {modelCatalogError ? (
          <div role="alert" style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>
            <p>
              {modelCatalogError}
              {modelOptions.length > 0 ? ' 当前展示上次成功加载的模型目录。' : ''}
            </p>
            <button type="button" onClick={() => { setConfigLoading(true); setModelLoadNonce((value) => value + 1); }}>重新加载模型</button>
          </div>
        ) : null}
        {modelOptions.length === 0 ? (
          modelCatalogError ? null : (
            <p role="status" style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>平台尚未启用可展示的模型。</p>
          )
        ) : (
          <>
            {selectedModel && !modelOptions.some((option) => option.modelAlias === selectedModel) ? (
              <div role="alert" style={{ marginBottom: '0.75rem', padding: '0.75rem', border: '1px solid var(--color-border-paper)', borderRadius: '12px', color: 'var(--color-text-muted)', fontSize: '0.78rem' }}>
                已保存的模型 {selectedModel} 已停用或不再存在。请选择新的可调用模型。
              </div>
            ) : null}
            {!modelOptions.some((option) => option.callable) ? (
              <p role="status" style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>
                当前没有可调用模型。<a href="/story-workspace/subscription#subscription-plans">查看 Token 额度与订阅状态</a>
              </p>
            ) : null}
            <ModelChoices models={modelOptions} selected={selectedModel} kind="ai"
              disabled={saving || configLoading || !!configReadError || !!modelCatalogError || modelSaveUnconfirmed}
              defaultAlias={defaultModelAlias} onChange={handleModelChange} />
            {modelStatus ? <p aria-live="polite" style={{ color: 'var(--color-text-muted)', fontSize: '0.76rem' }}>{modelStatus}</p> : null}
          </>
        )}
      </div>

      <section aria-label="Image 模型">
        <p style={{ margin: '0 0 0.65rem', fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>Image 模型</p>
        <p style={{ margin: '0 0 0.85rem', color: 'var(--color-text-muted)', fontSize: '0.78rem' }}>
          仅用于明确要求 image_gen 工具的图片生成和编辑。
        </p>
        {!selectedImageModel && !configReadError && !configLoading ? <p>未选择 Image 模型。请选择后再使用 image_gen。</p> : null}
        {selectedImageModel && !imageModelOptions.some(option => option.modelAlias === selectedImageModel) && !modelCatalogError && !configLoading ?
          <p role="alert">已保存的 Image 模型 {selectedImageModel} 已停用或不再提供图片能力。请选择新的可调用模型。</p> : null}
        {!imageModelOptions.length && !modelCatalogError && !configLoading ? <p role="status">平台尚未发布可展示的 Image 模型。</p> : null}
        <ModelChoices models={imageModelOptions} selected={selectedImageModel} kind="image"
          disabled={saving || configLoading || !!configReadError || !!modelCatalogError || modelSaveUnconfirmed} onChange={handleImageModelChange} />
        {imageModelStatus ? <p aria-live="polite">{imageModelStatus}</p> : null}
      </section>

      {/* System Prompt */}
      <div>
        <p style={{ margin: '0 0 0.65rem', fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
          系统提示词 / System Prompt
        </p>
        <textarea
          value={systemPrompt}
          onChange={(event) => { setSystemPrompt(event.target.value); setDirty(true); }}
          rows={5}
          style={{ ...fieldStyle, resize: 'vertical' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.65rem' }}>
          <button
            type="button"
            onClick={handleResetPrompt}
            style={{ border: 'none', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: '0.82rem' }}
          >
            恢复默认
          </button>
          <button
            type="button"
            onClick={handleSavePrompt}
            disabled={saving || !dirty}
            style={{
              border: 'none',
              borderRadius: '999px',
              padding: '0.55rem 1.1rem',
              background: 'var(--color-action-link)',
              color: 'var(--color-text-on-action)',
              fontWeight: 600,
              fontSize: '0.82rem',
              cursor: saving || !dirty ? 'not-allowed' : 'pointer',
              opacity: saving || !dirty ? 0.55 : 1,
              transition: 'opacity 0.2s ease',
            }}
          >
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      </div>

      {/* Workspace mode */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
        <div>
          <p style={{ margin: 0, fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
            工作区模式 / Workspace Mode
          </p>
          <p style={{ margin: '0.2rem 0 0', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
            对话时启用文件侧边栏上下文，并为当前 thread 开启 Bash 沙箱。
          </p>
        </div>
        <button
          type="button"
          onClick={handleWorkspaceToggle}
          aria-pressed={workspaceMode}
          style={{
            flexShrink: 0,
            position: 'relative',
            width: '2.9rem',
            height: '1.7rem',
            border: 'none',
            borderRadius: '999px',
            background: workspaceMode ? 'var(--color-action-link)' : 'var(--color-disabled-bg)',
            cursor: 'pointer',
            transition: 'background 0.2s ease',
          }}
        >
          <span
            style={{
              position: 'absolute',
              top: '0.15rem',
              left: workspaceMode ? '1.45rem' : '0.15rem',
              width: '1.4rem',
              height: '1.4rem',
              borderRadius: '999px',
              background: 'var(--color-text-on-action)',
              transition: 'left 0.2s ease',
            }}
          />
        </button>
      </div>

      {/* Sandbox network */}
      {workspaceMode ? (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div>
          <p style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            沙箱网络 / Sandbox Network
          </p>
          <p style={{ margin: '0.2rem 0 0', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
            控制 Bash、curl、git、npm 等沙箱子进程的出站网络；WebFetch 仍由工具权限和域名规则控制。
          </p>
        </div>

        <div>
          <p style={{ margin: '0 0 0.55rem', fontSize: '0.88rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            代理网络访问
          </p>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', padding: '0.25rem', borderRadius: '999px', background: 'var(--color-disabled-bg)' }}>
            {SANDBOX_NETWORK_ACCESS_OPTIONS.map((option) => {
              const active = sandboxNetworkEnabled === option.enabled;
              return (
                <button
                  key={option.label}
                  type="button"
                  onClick={() => handleSandboxNetworkAccessToggle(option.enabled)}
                  aria-pressed={active}
                  style={{
                    minWidth: '4.6rem',
                    height: '2.25rem',
                    border: 'none',
                    borderRadius: '999px',
                    background: active ? 'var(--color-bg-paper)' : 'transparent',
                    color: active ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
                    cursor: 'pointer',
                    fontSize: '0.86rem',
                    fontWeight: 700,
                    transition: 'background 0.2s ease, color 0.2s ease',
                  }}
                >
                  {option.label}
                </button>
              );
            })}
          </div>
          {!sandboxNetworkEnabled ? (
            <p style={{ margin: '0.55rem 0 0', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
              设置完成后将禁用网络访问。
            </p>
          ) : null}
        </div>

        {sandboxNetworkEnabled ? (
          <div style={{ borderLeft: '3px solid var(--color-border-paper)', paddingLeft: '1.35rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div>
              <p style={{ margin: '0 0 0.55rem', fontSize: '0.88rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                域允许列表
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                <select
                  value={sandboxNetworkMode === 'open' ? 'open' : 'allowlist'}
                  onChange={(event) => handleSandboxNetworkPolicySelect(event.target.value)}
                  style={{ ...fieldStyle, maxWidth: '24rem', height: '3.15rem', fontWeight: 700 }}
                >
                  <option value="allowlist">自定义域</option>
                  <option value="open">所有域</option>
                </select>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
                  <span aria-hidden="true" style={{ display: 'inline-grid', placeItems: 'center', width: '1rem', height: '1rem', borderRadius: '999px', border: '1px solid var(--color-text-muted)', fontSize: '0.68rem' }}>?</span>
                  域详情
                </span>
              </div>
            </div>

            {sandboxNetworkMode === 'allowlist' ? (
              <div>
                <p style={{ margin: '0 0 0.55rem', fontSize: '0.88rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                  其他允许的域
                </p>
                {sandboxNetworkDomainsList.length ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem', marginBottom: '0.65rem' }}>
                    {sandboxNetworkDomainsList.map((domain) => (
                      <span
                        key={domain}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.4rem',
                          maxWidth: '100%',
                          border: '1px solid var(--color-border-paper)',
                          borderRadius: '999px',
                          padding: '0.35rem 0.5rem 0.35rem 0.75rem',
                          background: 'var(--color-bg-paper)',
                          color: 'var(--color-text-primary)',
                          fontSize: '0.76rem',
                          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                        }}
                      >
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{domain}</span>
                        <button
                          type="button"
                          onClick={() => handleRemoveSandboxNetworkDomain(domain)}
                          aria-label={`Remove ${domain}`}
                          style={{
                            border: 'none',
                            background: 'transparent',
                            color: 'var(--color-text-muted)',
                            cursor: 'pointer',
                            fontSize: '0.85rem',
                            lineHeight: 1,
                            padding: 0,
                          }}
                        >
                          x
                        </button>
                      </span>
                    ))}
                  </div>
                ) : null}

                {sandboxNetworkAddingDomain ? (
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    <input
                      type="text"
                      value={sandboxNetworkNewDomain}
                      onChange={(event) => setSandboxNetworkNewDomain(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') {
                          event.preventDefault();
                          handleAddSandboxNetworkDomain();
                        }
                      }}
                      placeholder="example.com 或 *.example.com"
                      autoFocus
                      style={{ ...fieldStyle, maxWidth: '24rem', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: '0.82rem' }}
                    />
                    <button
                      type="button"
                      onClick={handleAddSandboxNetworkDomain}
                      disabled={sandboxNetworkSaving}
                      style={{
                        border: '1px solid var(--color-border-paper)',
                        borderRadius: '999px',
                        padding: '0.55rem 0.9rem',
                        background: 'var(--color-bg-paper)',
                        color: 'var(--color-text-primary)',
                        cursor: sandboxNetworkSaving ? 'not-allowed' : 'pointer',
                        fontSize: '0.82rem',
                        fontWeight: 700,
                        opacity: sandboxNetworkSaving ? 0.55 : 1,
                      }}
                    >
                      保存
                    </button>
                    <button
                      type="button"
                      onClick={() => { setSandboxNetworkAddingDomain(false); setSandboxNetworkNewDomain(''); }}
                      style={{ border: 'none', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: '0.82rem' }}
                    >
                      取消
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={handleAddSandboxNetworkDomain}
                    style={{
                      border: '1px solid var(--color-border-paper)',
                      borderRadius: '999px',
                      padding: '0.55rem 0.95rem',
                      background: 'transparent',
                      color: 'var(--color-text-primary)',
                      cursor: 'pointer',
                      fontSize: '0.82rem',
                      fontWeight: 700,
                    }}
                  >
                    <span aria-hidden="true" style={{ fontSize: '1.05rem', marginRight: '0.45rem' }}>+</span>
                    添加域
                  </button>
                )}
              </div>
            ) : null}

            {sandboxNetworkMode === 'allowlist' ? (
              <div>
                <p style={{ margin: '0 0 0.55rem', fontSize: '0.88rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                  允许的 HTTP 方法
                </p>
                <select
                  value="all"
                  disabled
                  title="Claude Code sandbox 当前按域名控制网络访问，不提供 HTTP 方法级策略。"
                  style={{ ...fieldStyle, maxWidth: '24rem', height: '3.15rem', fontWeight: 700, opacity: 0.72, cursor: 'not-allowed' }}
                >
                  <option value="all">所有方法</option>
                </select>
              </div>
            ) : null}
          </div>
        ) : null}

        {sandboxNetworkEnabled ? (
          <div style={{
            border: '1px solid color-mix(in srgb, var(--color-action-link) 30%, var(--color-border-paper))',
            borderRadius: '8px',
            background: 'color-mix(in srgb, var(--color-action-link) 12%, var(--color-bg-paper))',
            padding: '1rem',
            color: 'var(--color-text-primary)',
          }}>
            <p style={{ margin: '0 0 0.55rem', fontSize: '0.84rem', fontWeight: 800, color: 'var(--color-text-primary)' }}>
              <span style={{ display: 'inline-block', marginRight: '0.45rem', color: 'var(--color-action-link)' }}>高风险</span>
              启用互联网访问会使你的环境暴露于安全风险之中
            </p>
            <p style={{ margin: 0, fontSize: '0.78rem', lineHeight: 1.65, color: 'var(--color-text-secondary)' }}>
              这些风险包括提示注入、泄露代码或机密、添加恶意软件或漏洞，或者访问受许可证限制的内容。为了降低风险，请仅允许必要的域，并检查 Agent 的输出和工作日志。
            </p>
          </div>
        ) : null}

        {sandboxNetworkStatus ? (
          <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
            {sandboxNetworkStatus}
          </p>
        ) : null}
      </div>
      ) : null}

      {/* Sandbox filesystem extra write paths */}
      {workspaceMode ? (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div>
          <p style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            沙箱文件写入 / Sandbox File Writes
          </p>
          <p style={{ margin: '0.2rem 0 0', fontSize: '0.78rem', color: 'var(--color-text-muted)', lineHeight: 1.65 }}>
            除线程工作区外，额外允许沙箱内 Bash 写入的绝对路径。Claude Code 自身的临时目录（/tmp/claude-$UID 或 $CLAUDE_TMPDIR）已默认放行；工作区内部配置（.claude/settings、.editor 等）仍始终禁止写入。
          </p>
        </div>

        {sandboxFsPathsList.length ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem' }}>
            {sandboxFsPathsList.map((path) => (
              <span
                key={path}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  maxWidth: '100%',
                  border: '1px solid var(--color-border-paper)',
                  borderRadius: '999px',
                  padding: '0.35rem 0.5rem 0.35rem 0.75rem',
                  background: 'var(--color-bg-paper)',
                  color: 'var(--color-text-primary)',
                  fontSize: '0.76rem',
                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                }}
              >
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>{path}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveSandboxFsPath(path)}
                  aria-label={`Remove ${path}`}
                  style={{
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--color-text-muted)',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    lineHeight: 1,
                    padding: 0,
                  }}
                >
                  x
                </button>
              </span>
            ))}
          </div>
        ) : null}

        <div>
          {sandboxFsAddingPath ? (
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <input
                type="text"
                value={sandboxFsNewPath}
                onChange={(event) => setSandboxFsNewPath(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    handleAddSandboxFsPath();
                  }
                }}
                placeholder="/absolute/path"
                autoFocus
                style={{ ...fieldStyle, maxWidth: '24rem', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', fontSize: '0.82rem' }}
              />
              <button
                type="button"
                onClick={handleAddSandboxFsPath}
                disabled={sandboxFsSaving}
                style={{
                  border: '1px solid var(--color-border-paper)',
                  borderRadius: '999px',
                  padding: '0.55rem 0.9rem',
                  background: 'var(--color-bg-paper)',
                  color: 'var(--color-text-primary)',
                  cursor: sandboxFsSaving ? 'not-allowed' : 'pointer',
                  fontSize: '0.82rem',
                  fontWeight: 700,
                  opacity: sandboxFsSaving ? 0.55 : 1,
                }}
              >
                保存
              </button>
              <button
                type="button"
                onClick={() => { setSandboxFsAddingPath(false); setSandboxFsNewPath(''); }}
                style={{ border: 'none', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: '0.82rem' }}
              >
                取消
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={handleAddSandboxFsPath}
              style={{
                border: '1px solid var(--color-border-paper)',
                borderRadius: '999px',
                padding: '0.55rem 0.95rem',
                background: 'transparent',
                color: 'var(--color-text-primary)',
                cursor: 'pointer',
                fontSize: '0.82rem',
                fontWeight: 700,
              }}
            >
              <span aria-hidden="true" style={{ fontSize: '1.05rem', marginRight: '0.45rem' }}>+</span>
              添加可写路径
            </button>
          )}
        </div>

        {sandboxFsStatus ? (
          <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
            {sandboxFsStatus}
          </p>
        ) : null}
      </div>
      ) : null}

      {/* IM approval mode */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
        <div>
          <p style={{ margin: 0, fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
            应如何批准 IM
          </p>
          <p style={{ margin: '0.2rem 0 0', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
            开启后普通工具自动批准，问答表单仍需用户确认。
          </p>
        </div>
        <button
          type="button"
          onClick={handleImFullAccessToggle}
          aria-pressed={imFullAccessEnabled}
          title={imFullAccessEnabled ? '完全访问已开启' : '完全访问已关闭'}
          style={{
            flexShrink: 0,
            minWidth: '6.25rem',
            height: '1.9rem',
            border: 'none',
            borderRadius: '999px',
            padding: '0 0.85rem',
            background: imFullAccessEnabled ? 'var(--color-text-primary)' : 'var(--color-disabled-bg)',
            color: imFullAccessEnabled ? 'var(--color-bg-paper)' : 'var(--color-text-secondary)',
            cursor: 'pointer',
            fontSize: '0.78rem',
            fontWeight: 600,
            transition: 'background 0.2s ease, color 0.2s ease',
            whiteSpace: 'nowrap',
          }}
        >
          完全访问
        </button>
      </div>

      {/* Environment Variables */}
      {workspaceMode ? (
      <div>
        <p style={{ margin: '0 0 0.3rem', fontSize: '0.88rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
          环境变量 / Environment Variables
        </p>
        <p style={{ margin: '0 0 0.75rem', fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
          为 Skills / MCP 工具配置运行时环境变量。
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {envVars.map((ev, i) => (
            <div key={i} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                type="text"
                placeholder="KEY"
                value={ev.key}
                onChange={(e) => handleUpdateEnvVar(i, 'key', e.target.value)}
                style={{ ...fieldStyle, flex: 1, fontFamily: 'monospace', fontSize: '0.82rem' }}
              />
              <input
                type="password"
                placeholder="value"
                value={ev.value}
                onChange={(e) => handleUpdateEnvVar(i, 'value', e.target.value)}
                style={{ ...fieldStyle, flex: 2, fontFamily: 'monospace', fontSize: '0.82rem' }}
              />
              <button
                type="button"
                onClick={() => handleRemoveEnvVar(i)}
                style={{
                  flexShrink: 0,
                  border: 'none',
                  background: 'transparent',
                  color: 'var(--color-text-muted)',
                  cursor: 'pointer',
                  fontSize: '1rem',
                  padding: '0.25rem 0.4rem',
                  borderRadius: '6px',
                }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
          <button
            type="button"
            onClick={handleAddEnvVar}
            style={{
              border: '1px dashed var(--color-border-paper)',
              borderRadius: '8px',
              padding: '0.4rem 0.85rem',
              background: 'transparent',
              color: 'var(--color-text-muted)',
              fontSize: '0.82rem',
              cursor: 'pointer',
            }}
          >
            + 添加变量
          </button>
          <button
            type="button"
            disabled={!envVarsDirty || envVarsSaving}
            onClick={handleSaveEnvVars}
            style={{
              border: 'none',
              borderRadius: '999px',
              padding: '0.4rem 1rem',
              background: 'var(--color-action-link)',
              color: 'var(--color-text-on-action)',
              fontWeight: 600,
              fontSize: '0.82rem',
              cursor: !envVarsDirty || envVarsSaving ? 'not-allowed' : 'pointer',
              opacity: !envVarsDirty || envVarsSaving ? 0.55 : 1,
              transition: 'opacity 0.2s ease',
            }}
          >
            {envVarsSaving ? '保存中…' : '保存'}
          </button>
        </div>
      </div>
      ) : null}
    </div>
  );
}

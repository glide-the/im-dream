> **迁移来源**: Pawkeyland docs/app/design/chat-session-message-er-model.md
> **Ink & Memory 说明**: 以下 ER 模型为 Pawkeyland 的 chat_session + claude_message 持久化设计参考。
> Ink & Memory 目前的最小迁移版本**尚未实现消息持久化**；如需持久化，可参考此 ER 设计，
> 将 `pet_id / persona_id` 字段替换为 Ink & Memory 的 `session_id`（= `user_id`），并在 `database.py` 中建表。

# Chat Session & Claude Message ER Model

> **当前口径**：主链路只保留 `chat_session + claude_message`。`chat_session` 保存 Claude SDK session metadata，`claude_message` 保存 user/assistant 消息明细、顶层 `parts` 和 normalized metadata。

## 1. 设计目标

| 目标 | 说明 |
|------|------|
| 会话 metadata 独立 | `chat_session` 不再保存 transcript 数组，只保存会话状态、宠物快照、`claude_session_id` 和 `agent_contract_version` |
| 消息一行一条 | `claude_message` 以 `message_id` 幂等写入 user/assistant 明细 |
| 用户与角色隔离 | 查询和回放按 `user_id + pet_persona.persona_id` 绑定 |
| 支持 Mem0 flush | Mem0 应用记忆从 `claude_message` 批量读取 user/assistant 明细 |

## 2. ER 图

```text
chat_session
────────────────────────────────────────────────────────────
 PK  chat_id                  TEXT
     user_id                  TEXT
     pet_id                   TEXT
     persona_id               TEXT
     pet_name                 TEXT
     title                    TEXT
     status                   TEXT
     claude_session_id        TEXT NULL
     agent_contract_version   TEXT
     created_at               TIMESTAMPTZ
     updated_at               TIMESTAMPTZ
────────────────────────────────────────────────────────────
 INDEX: (user_id, persona_id, updated_at DESC)

        │ 1
        │
        │ N

claude_message
────────────────────────────────────────────────────────────
 PK  message_id    TEXT
 FK  chat_id       TEXT -> chat_session.chat_id ON DELETE CASCADE
     user_id       TEXT
     pet_id        TEXT
     persona_id    TEXT
     role          TEXT  ('user' | 'assistant')
     content_type  TEXT
     content       TEXT
     parts         JSONB
     media_url     TEXT
     extra         JSONB
     created_at    TIMESTAMPTZ
────────────────────────────────────────────────────────────
 INDEX: (chat_id, created_at DESC)
 INDEX: (user_id, persona_id, created_at DESC)
```

## 3. Schema Bootstrap

启动 schema bootstrap 只声明当前 `chat_session` 与 `claude_message` 结构。

如果 `claude_message` 行缺对应 `chat_session`，bootstrap 会先按 `chat_id` 回填 metadata 占位会话，再添加 `claude_message.chat_id -> chat_session.chat_id` 的外键约束。

## 4. 当前读写规则

- 聊天路由先按 `user_id + pet_id` 定位真实宠物 persona，系统角色则按 `user_id + system_persona_id` 定位。
- 每轮完成后 upsert `chat_session`，保存 `claude_session_id`、`agent_contract_version` 和快照字段。
- 同一轮 user/assistant 明细写入 `claude_message`；assistant 的 `extra.normalized_payload` 保存贴纸、分段和动画 metadata。
- 聊天历史、回放和 Mem0 flush 都读取 `claude_message`，不读取请求中的历史数组。

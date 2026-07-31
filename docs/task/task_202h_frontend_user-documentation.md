# task_202h_frontend_user-documentation.md

> **Task ID**: `task_202h`  
> **关联 Issue**: `SUO-201-DO-001` — `Story Workspace 使用文档`  
> **上游 Issue**: `SUO-201` (Issue 清单)  
> **父 Issue**: `SUO-198`  
> **生成日期**: 2026-08-01  
> **生成 Agent**: `FrontendTaskAgent`

---

## 1. 任务标题

Story Workspace 使用文档编写

---

## 2. 关联 Issue

| Issue ID | 标题 | 类型 | 优先级 |
|---|---|---|---|
| `SUO-201-DO-001` | Story Workspace 使用文档 | docs | P2 |

---

## 3. 任务目标

编写 Story Workspace 的使用文档，包括功能概述、审阅工作流说明、常见问题。面向内部团队和后续维护者。

---

## 4. 实现步骤

1. **编写功能概述**
   - 各模块说明（Dashboard、故事、角色、场景）
   - 核心工作流说明（Agent 产出 → 审阅确认）
   - 页面布局说明（三栏布局）

2. **编写审阅工作流说明**
   - Agent 产出触发方式（Chat 中指令触发）
   - 审阅确认流程（确认/驳回/编辑）
   - 批量审阅操作说明
   - 状态流转图

3. **编写命名规范速查表**
   - 路由命名：`/story-workspace/*`
   - 组件命名：`StoryWorkspace*` 前缀
   - API 命名：`/api/story-workspace/*`
   - 类型命名：`StoryWorkspace*` 前缀

4. **编写 API 端点速查表**
   - 故事 API：GET/POST/PATCH/confirm/reject
   - 角色 API：GET/POST/PATCH/confirm/reject
   - 场景 API：GET/POST/PATCH/confirm/reject
   - 批量操作 API

5. **编写常见问题（FAQ）**
   - 如何触发 Agent 生成剧本？
   - 审阅驳回后如何重新生成？
   - 已确认内容如何进入下游流程？
   - 支持哪些内容类型？

6. **文档格式**
   - Markdown 格式
   - 放在 `docs/` 下合适位置（非 `docs/design/`）
   - 包含目录结构和版本历史

---

## 5. 涉及文件路径

**新增文件**：
- `docs/task/story-workspace-user-guide.md`（或等效路径）

**参考输入**（只读）：
- `docs/design/story-workspace/story-workspace-prd.md`
- `docs/design/story-workspace/story-workspace-layout-design.md`
- `docs/issue/ISSUES_story-workspace.md`

---

## 6. 输入 / 输出说明

**输入**：
- 设计稿 §1-3 背景与方案摘要
- Issue 清单中的验收条件
- 前端任务文档（task_202a ~ task_202g）

**输出**：
- Story Workspace 使用文档（Markdown）

---

## 7. 依赖项

| 依赖 | 状态 | 说明 |
|---|---|---|
| `task_202g` (SH-001 E2E 联调) | ⏳ 需先完成 | 验证工作流正确后方可编写文档 |
| `SUO-201-SH-001` | ⏳ 需先完成 | E2E 验证完成 |

**本任务被依赖**：
- 无（文档是最后阶段产物）

---

## 8. 测试策略

1. **文档完整性检查**：
   - 是否覆盖所有模块
   - 是否包含所有 API 端点
   - FAQ 是否覆盖常见问题

2. **准确性验证**：
   - 与 design 文档一致
   - 与代码实现一致
   - 与 API 契约一致

3. **可读性检查**：
   - 面向内部团队，技术细节充分
   - 包含必要的截图/图示（如有）

---

## 9. 完成标志

- [ ] 文档包含功能概述（各模块说明）
- [ ] 审阅工作流说明（Agent 产出 → 审阅确认流程）
- [ ] 命名规范速查表
- [ ] API 端点速查表
- [ ] 常见问题（FAQ）
- [ ] 文档放在 `docs/` 下合适位置，不写入 `docs/design/`

---

## 10. 风险提示

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| 文档与最终实现不一致 | 中 | E2E 验证完成后再编写，确保准确性 |
| 后端 API 变更 | 低 | 文档标注版本，API 变更时同步更新 |

---

## 附录：文档结构建议

```markdown
# Story Workspace 使用文档

## 1. 功能概述
### 1.1 Dashboard（工作台首页）
### 1.2 故事管理
### 1.3 角色管理
### 1.4 场景管理

## 2. 审阅工作流
### 2.1 Agent 产出触发
### 2.2 审阅确认流程
### 2.3 批量审阅
### 2.4 状态流转图

## 3. 命名规范速查表
### 3.1 路由命名
### 3.2 组件命名
### 3.3 API 命名
### 3.4 类型命名

## 4. API 端点速查表
### 4.1 故事 API
### 4.2 角色 API
### 4.3 场景 API
### 4.4 批量操作 API

## 5. 常见问题（FAQ）

## 6. 版本历史
```

---

## 范围边界

**✅ 范围内**：
- 使用文档编写
- 功能概述
- 工作流说明
- 命名规范
- API 速查
- FAQ

**❌ 范围外**：
- 设计文档修改（禁止修改 docs/design/）
- 技术架构文档（如需要另开 Issue）
- 用户培训材料（面向终端用户的非技术文档）

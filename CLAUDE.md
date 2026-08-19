<!-- [Input] Repository governance contract and current documentation index. -->
<!-- [Output] Root pointer for Claude/Codex workspace rules and product documentation. -->
<!-- [Pos] Repository control-plane entry referenced by AGENTS.md. -->

# Ink & Memory Workspace

执行仓库任务时依次读取：

1. [`AGENTS.md`](AGENTS.md)：工作、数据库、测试和安全契约；
2. 最近的 `**/.folder.md`：目录职责与文件所有权；
3. [`docs/rules/README.md`](docs/rules/README.md)：复用和配置规则；
4. [`docs/README.md`](docs/README.md)：当前业务、架构和部署文档入口。

业务行为以当前生产代码和公开 DTO 为准。修改功能、架构或编码风格时，同步更新所属业务模块
文档、文件头和最近的目录契约；不得在文档中重新建立任务、执行、评审或测试流水。

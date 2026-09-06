<!-- [输入] task_304 与 Phase 2 当前候选证据。 -->
<!-- [输出] G3-01—G3-07 的直接执行要求和最终 QA 证据。 -->
<!-- [定位] Phase 3 requirement；只包含技术依赖、范围、验收和回滚。 -->
<!-- [同步] 2026-09-06：改用技术依赖、可观察验收与回滚。 -->

# TASK-REQUIREMENT：Phase 3 治理与 QA

1. 核对 I2-01—I2-07 的当前候选实现、命令、退出码和 Browser 证据。
2. 完成 G3-01—G3-07，确保 manifest、运行能力、版本和 feature flag 一致。
3. 禁用/升级/销毁必须立即处理已有 Client/View/session 和无引用 connector。
4. 多维并发测试不得串用 catalog、result、notification、identity 或 credential。
5. 诊断按 Chat projection、Browser transport、resource、iframe、权限、Node 和上游 Server 分段，且不泄密。
6. 版本升级先运行官方 demo、inspector、兼容矩阵和当前业务回归。
7. 资源限制来自配置/策略，不硬编码为产品配额；失败不传播到 Agent turn。
8. 记录根 standalone、Backend/Node/Browser、供应链、文档、差异和清理证据。
9. 最终结果明确区分本地技术验收与真实生产发布；`production_apps_effective=false` 保持。

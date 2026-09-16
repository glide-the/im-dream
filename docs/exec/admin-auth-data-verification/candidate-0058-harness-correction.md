<!-- [Input] Actual frozen0057/58 replay and remaining purpose-fixture checks. -->
<!-- [Output] Explicit separation of a scalar psql harness failure from migration outcomes. -->
<!-- [Pos] Read together with candidate-0058-receipt.json and catalog proof. -->
<!-- [Sync] 2026-09-15: retained initial failure and remaining-check rerun scope. -->

# 0057/58 harness 标量输出校正

主任务完整 replay 已产生9条实际子命令回执；升级、重复、并发、全新与两种 partial rollback 断言通过。随后 purpose fixture 的 `INSERT ... RETURNING` 标量输出包含 `INSERT 0 1` command tag，旧 harness `.isdecimal()` 失败，未误报为迁移或业务缺陷。

剩余检查脚本改用 `psql -q` 获取标量，并再次核验名称/用户/端口/data_directory、冻结SHA和现有catalog，只执行尚未完成的fixture/check，不重复已经成功的迁移。实际 `python3 /private/tmp/ink-auth-migration-validation/verify-candidate-0058-purpose.py` 退出0，验证3合法purpose、6 SQL23514拒绝与Session cascade；原迁移命令回执逐字保留，正常数据库没有变更。

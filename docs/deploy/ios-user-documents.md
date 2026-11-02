<!-- [Input] docs/user对外正文、网站静态版本及iOS发布条件。 -->
<!-- [Output] 内部发布人员采用和维护对外说明的文件映射与核定事项。 -->
<!-- [Pos] docs/deploy内部操作资料；使用者正文归docs/user。 -->
<!-- [Sync] 2026-11-02: 按用户确认拆分对外使用说明与内部上架资料。 -->

# ink-dream 对外文件维护与上架采用

## 读者与目录

本文件供内部发布人员使用。`docs/user/`保存面向ink-dream普通使用者的正文，`docs/deploy/`保存部署、安装、填报及上架操作。隐私、费用及人工智能内容按各自主题维护；源码依据、待办、审核操作和验证回执保留在内部资料中。

## 文件与网址

| 主题 | 正文来源 | 网站版本 | 公开路径 |
| --- | --- | --- | --- |
| 隐私政策 | [privacy-policy.md](../user/privacy-policy.md) | [privacy-policy.html](../../frontend/public/privacy-policy.html) | `/privacy-policy.html` |
| 订阅与用量 | [subscription-and-usage.md](../user/subscription-and-usage.md) | [subscription-and-usage.html](../../frontend/public/subscription-and-usage.html) | `/subscription-and-usage.html` |
| 人工智能使用 | [ai-usage.md](../user/ai-usage.md) | [ai-usage.html](../../frontend/public/ai-usage.html) | `/ai-usage.html` |

对外正文以ink-dream为叙述主体；suoxya作为已确认的运营信息在隐私政策的联系部分保留，邮箱沿用`dmeck@suoxya.com`。Markdown为正文来源，HTML与其文字一致；修订后同步网站版本。

现有[隐私与权限填写指南](ios-privacy-and-permissions.md)和[商业与AI材料填写指南](ios-commercial-and-ai-materials.md)继续服务发布人员。使用者阅读入口为[对外说明目录](../user/README.md)。

## 正式公布前的核定事项

当前三份对外说明均为未生效草案。本次只调整文档目录、正文和静态文件，实际服务能力与发布状态按原记录保持。

| 事项 | 正式公布前的完成条件 |
| --- | --- |
| 数据接收方及处理范围 | 核定真实接收主体、可能生效的模型路由范围、用途、隐私政策、训练使用及第三方保护约定；补齐具体告知。 |
| 保存与删除 | 核定各类信息的保存期限、存储地区、跨境安排、删除范围及依法保留规则；将具体规则同步到正式隐私政策。 |
| 用户选择 | 完成共享前明确同意、拒绝与撤回，提供App内账户删除发起及处理反馈，取得对应实际回执。 |
| 商业条件 | 确定首发免费或收费范围、地区、额度、周期、价格及取消/退款条件；付费路径完成正式渠道与权益核验。 |
| 内容处理 | 核对过滤、举报、限制滥用、处置与反馈的实际入口和责任；对外说明与实际行为一致。 |
| 正文和网址 | 核定生效日期，更新草案状态；部署正式HTTPS网址，核对退出登录可读、正文完整及App入口；商店填写实际生效的隐私政策URL。 |

核定完成前保持草案标识。文档编辑完成、公开网址部署、App入口采用和商店提交分别记录。

## 本轮文档验证

验证范围为文档清单、相对路径、外部读者用语、Markdown与HTML正文一致性、HTML结构和空白。实际部署、账户、支付、模型与商店操作均未执行。

| 检查 | 实际命令与结果 |
| --- | --- |
| 文档目录与链接 | `python3 /tmp/ink-public-docs-20261102/validate.py`退出0；16份目标文件、53处本地链接、文件头与目录登记通过。 |
| 对外正文与网站一致性 | 同一命令退出0；三份Markdown与对应HTML正文逐字一致，分别为7、5、4节；公开正文中的内部术语检查通过。 |
| HTML结构及资源 | 同一命令退出0；中文语言、窄屏viewport、标题、标签闭合与ARIA关联通过；脚本及外部资源加载均为0。 |
| 图示及空白 | 同一命令内`git diff --check`退出0；内部上架手册三张Mermaid与本轮采用前快照一致。 |

回执为`/tmp/ink-public-docs-20261102/validation.json`。工作区既有并行修订和历史原文保留；本轮未执行提交、部署或商店写入。

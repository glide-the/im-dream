<!-- [Sync] 2026-11-02: 本稿归内部填报，docs/user维护对外隐私政策正文。 -->
<!-- [Input] ink-dream数据处理、权限、政策正文及Apple隐私填报要求。 -->
<!-- [Output] 发布人员准备政策、填写App Privacy和核对最终包的步骤。 -->
<!-- [Pos] iOS隐私与权限填报指南；用户政策正文独立维护。 -->
<!-- [Sync] 2026-11-02: 聚焦政策采用与商店填报，核查过程和源码依据移存执行历史。 -->

# ink-dream iOS 隐私与权限填写指南（内部）

## 背景与问题

提交应用前，需要让隐私政策、App Privacy问卷、系统权限及最终归档描述同一份实际数据处理范围。

## 目标与边界

发布人员按本指南准备和核对隐私材料。运营主体为 **suoxya**，隐私联系邮箱为 **dmeck@suoxya.com**。面向普通使用者的[隐私政策](../user/privacy-policy.md)维护在`docs/user/`，网站版本为[`privacy-policy.html`](../../frontend/public/privacy-policy.html)，公开路径为`/privacy-policy.html`。

本指南属于内部填报资料。正文同步和正式公布条件统一见[对外文件维护与上架采用](ios-user-documents.md)。

## 概念与规则

政策正文目前为未生效准备稿。先核定接收方、处理地区、保存和删除规则，再完成公开采用与App内访问。商店字段使用实际公开HTTPS网址。服务接收方及收费相关材料按[商业与AI填写指南](ios-commercial-and-ai-materials.md)准备，整体提交步骤见[上架手册](ios-app-store-release.md)。

## 一、准备填写材料

| 材料 | 填写内容 | 完成条件 |
| --- | --- | --- |
| 政策主体和联系 | 运营主体、隐私邮箱、生效及修订日期 | 与实际运营和公开联系方式一致 |
| 数据清单 | 账户、内容、附件、连接资源、模型请求、用量、支持及诊断的实际处理 | 区分设备内处理、设备外传输和保存，覆盖合作方 |
| 服务接收方 | 主体、用途、处理地区、政策、保存、训练使用及删除规则 | 覆盖可能实际接收内容的服务方 |
| 用户选择 | 政策入口、共享同意和撤回、账户及内容删除入口 | 在提交版本中可到达，结果可核对 |
| 权限和依赖清单 | 最终包的用途说明、required-reason API及SDK清单 | 与实际调用和拒绝后反馈一致 |

保存期限和删除方式按账户、内容、模型正文、诊断、账单及备份分别确定。未核定的事实先补齐，保留准备稿状态；发布时采用已确认内容。

## 二、公开政策并接入应用

1. 审阅[政策正文](../../frontend/public/privacy-policy.html)，核实主体、邮箱、接收方和处理规则。
2. 补齐实际用户入口、生效日期及未核定事项，确认后移除准备稿提示。
3. 随正常网站发布流程将文件放到稳定HTTPS地址；Next standalone制品需要包含对应`public/`文件。
4. 使用退出登录的浏览器窗口核对访问成功、正文完整、邮箱、窄屏阅读和证书。
5. 在App登录前及政策入口链接同一公开版本，核对返回与失败反馈。
6. 记录最终URL、政策版本、制品版本及页面截图，供填写商店资料使用。

[政策和数据要求](https://developer.apple.com/app-store/review/guidelines/#privacy)，查阅：2026-11-02。

## 三、填写App Privacy

### 操作位置与网址

| 操作位置 | 输入或准备材料 | 具体操作 | 预期结果 | 失败处理 |
| --- | --- | --- | --- | --- |
| [App Store Connect](https://appstoreconnect.apple.com/apps) → 目标App → App Privacy → Privacy Policy | 已生效政策的公开HTTPS网址 | Edit填写Privacy Policy URL并Save | 无需登录可访问正确版本 | 网址失效或仍为准备稿时先处理公开采用 |
| App Privacy → Get Started | 实际数据、用途、身份关联及合作方清单 | 回答收集问题，逐项选择数据类型和用途 | 覆盖实际数据处理范围 | 无法确定的项目先核对事实 |
| Product Page Preview | 完整问卷 | 核对Data Linked to You等展示，再由有权人员Publish | 公开披露与最终问卷一致 | 发现遗漏时修正并重新核对 |
| Privacy Choices URL（适用时） | 已提供的隐私管理页面 | 有对应页面时填写真实网址 | 页面提供所述管理能力 | 缺少相应页面时留空 |

[Apple填报操作](https://developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy/)，查阅：2026-11-02。

### 数据类型、用途、身份关联和跟踪

| Apple数据类型 | 申报条件与核对范围 |
| --- | --- |
| Email Address、Name、User ID | App接收并保存相应账户资料；核对注册、登录和合作登录返回字段 |
| Other User Content | 日记、对话、草稿、文档、资源及模型内容发生设备外保存 |
| Photos or Videos、Audio Data | 按首发实际上传和保存的附件类型申报；录音权限单独核对 |
| Customer Support | 支持渠道收集并保留用户发送的资料 |
| Product Interaction / Other Usage Data | 按任务、调用及用量实际字段选择；分析用途需有实际分析行为 |
| Purchase History | App产生、访问或发送购买和付费套餐历史 |
| Crash Data、Performance Data、Other Diagnostic Data | 对应诊断数据离开设备并保存；仅设备内显示与用户主动分享分别核对 |
| 其他类别 | 按位置、通讯录、广告、支付及服务方实际行为逐项核对 |

用途从问卷实际选项选择。与账户关联的数据按关联身份填写，具备符合Apple定义的处理依据后再调整。tracking逐项覆盖服务方实际用途。自由文本按其收集方式分类，避免仅根据用户可能输入的内容推定专用采集字段。[数据类型及收集定义](https://developer.apple.com/app-store/app-privacy-details/)，查阅：2026-11-02。

## 四、核对系统权限和隐私清单

| 检查项 | 操作与完成条件 |
| --- | --- |
| 相机 | 用途说明与真实拍摄和附件处理一致；验证允许、拒绝、取消及恢复授权 |
| 文件和目录 | 系统选择仅处理用户选中范围；核对副本、上传、取消及授权释放 |
| 本地网络 | 按首发是否实际连接局域网服务确定声明；互联网、包内loopback和局域网访问分别判断 |
| 相册及其他权限 | 按最终采用的API确定需要的用途说明；缺少对应需求时保留最小访问范围 |
| `NSPrivacyCollectedDataTypes` | 按App实际收集填写类型、用途、关联身份及tracking；与问卷核对 |
| required-reason API | 逐项确认FileTimestamp、UserDefaults、SystemBootTime等调用与所选reason条件一致 |
| SDK与归档报告 | 核对依赖自有清单及适用签名，使用最终Archive生成隐私报告并对照问卷 |

权限拒绝只限制依赖该权限的操作，保留已有编辑和任务状态。清单中已有的reason与tracking声明需要实际行为支持。[隐私清单](https://developer.apple.com/documentation/bundleresources/describing-data-use-in-privacy-manifests)、[SDK与清单要求](https://developer.apple.com/documentation/bundleresources/adding-a-privacy-manifest-to-your-app-or-third-party-sdk)、[本地网络说明](https://support.apple.com/en-us/102229)，查阅：2026-11-02。

## 五、提交前确认

- 政策已生效、公开可访问，App登录前和政策入口可到达同一版本。
- 实际接收方、处理地区、保存、训练使用及删除规则完整。
- 第三方AI共享前取得明确许可，拒绝和撤回具有对应结果。
- 支持注册时，App内可发起账户及关联数据删除，并说明时限、保留范围和结果。
- 权限用途、拒绝恢复、SDK清单、Archive报告和App Privacy一致。
- 发布记录留存政策版本、URL、问卷、候选版本及实际检查结果。

[AI数据共享](https://developer.apple.com/app-store/review/guidelines/#data-use-and-sharing)、[账户删除要求](https://developer.apple.com/help/app-review/guideline-reference/5-1-1-account-deletion)，查阅：2026-11-02。

## 历史引用

原有核查、评审与回执见[修订前原文](../exec/history/ios-release-documents-before-reader-revision-20261102.md#ios-privacy-and-permissionsmd)。

<a id="ink-memory-ios-隐私与权限上架材料"></a>
<a id="一数据处理范围与依据"></a>
<a id="二app-store-connect填写建议"></a>
<a id="三设备权限与用途说明"></a>
<a id="四privacyinfoxcprivacy与archive核对"></a>
<a id="五政策文件如何用于上架"></a>
<a id="六发布前尚需落实的事实与入口"></a>
<a id="七判断依据与交付状态"></a>
<a id="八验证记录"></a>

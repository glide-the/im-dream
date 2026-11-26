<!-- [Input] 2026-11-15 宿主与恢复合同中的推荐拓扑图。 -->
<!-- [Output] 原系统、宿主、Python 和拟议 TS 执行者关系。 -->
<!-- [Pos] 历史图示，保留当时的技术选择。 -->

# 2026-11-15 iOS 执行拓扑原图

原图包含当时拟议的 TS 接管步骤。2026-11-26 终止该路线，当前调用方向由[宿主与恢复合同](../mobile-background-execution-technical.md#推荐拓扑)维护。

```mermaid
flowchart TB
    OS["iOS系统：执行许可、挂起、终止"]
    subgraph APP["iOS App进程"]
        subgraph NATIVE["Swift / Objective-C"]
            I["InkRuntime / EmbeddedDreamBackend"]
            B["建议、未实现：宿主内许可方法与精确执行关联"]
        end
        subgraph UI["RN Hermes运行环境"]
            G["SessionGate / BackendRuntimeManager"]
            C["useNativeChatThread：页面订阅"]
        end
        subgraph PY["CPython运行环境"]
            H["mobile_runtime.ios / IOSHTTPServer / FastAPI"]
            F["ClaudeAgentThreadFactory / ClaudeAgentService"]
            D["AdminTurnPersistence / Python业务服务"]
        end
        subgraph NODE["嵌入式Node运行环境"]
            HOST["host.cjs：应用持有"]
            NEXT["Next Worker：登录、BFF、局部页面"]
            TS["建议、未实现：host.cjs持有TS Agent执行"]
            RUN["ClaudeAgentRunner：demo基础，IM适配待实现"]
            CLI["worker.mjs / 原Runtime入口"]
            CMD["ios-process-boundary / 包内guest工具"]
        end
    end
    ADMIN["远端Admin → 原PostgreSQL"]
    GW["原Gateway / 当前模型服务"]
    FILES["App容器：原thread workspace、transcript、草稿"]
    G --> I
    C -->|原Native HTTP| I
    I --> NEXT
    NEXT -->|原本地HTTP| H
    H --> F
    F --> D
    F -->|原ios_claude_transport| HOST
    HOST --> CLI
    CLI --> CMD
    D --> ADMIN
    CLI --> GW
    I -.-> B
    F -. 精确接受与终态观察 .-> B
    B -. 申请和释放 .-> OS
    HOST -. 后续整体接管Agent .-> TS
    TS -.-> RUN
    RUN -. SDK自定义spawn适配 .-> CLI
    TS -. 原认证DTO调用Python业务 .-> H
    CLI --> FILES
    D --> FILES
```

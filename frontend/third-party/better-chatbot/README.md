<!-- [Input] Upstream MIT UI source fetched on 2026-11-13 and IM's existing catalogs/configuration. -->
<!-- [Output] Source provenance, migration mapping and preserved data ownership. -->
<!-- [Pos] Technical attribution for adapted Chat components. -->

# Better Chatbot UI migration

The upstream [MIT notice](LICENSE) applies to the copied and adapted portions. Exact source text is retained in the adjacent `.txt` snapshots.

| Upstream source | Git blob SHA | Executable IM adapter |
| --- | --- | --- |
| [select-model.tsx](https://github.com/keinsaasforever/better-chatbot/blob/main/apps/web/src/components/select-model.tsx) | `66d816b04fd68b5240937c83ade50b478c9f4521` | `components/chat/SelectModel.tsx`, Native counterpart and `ComposerModelSelector` |
| [tool-select/index.tsx](https://github.com/keinsaasforever/better-chatbot/blob/main/apps/web/src/components/tool-select/index.tsx) | `01e93166969a62e980cb7d3c129719775dadf82a` | `ComposerToolsMenu` with one current-Agent trigger |
| [tool-select/agent-selector.tsx](https://github.com/keinsaasforever/better-chatbot/blob/main/apps/web/src/components/tool-select/agent-selector.tsx) | `02345becca155845047d87b0f978b5fa2a756b01` | `ComposerAgentSelector` and Native counterpart |

Migrated behavior includes the compact trigger, menu/group hierarchy, Agent submenu, model search, unique selection identities, current-item check, disabled unavailable rows, desktop popover and mobile sheet. `ComposerPopover` adapts the upstream Popover/Drawer presentation to installed IM components and tokens.

IM owns the Deck/Agent catalog and selection callbacks, MCP configuration, `gatewayModelsApi`, `useModelConfig`, Cookie/CSRF, model aliases, callability/default selection and confirmed preference saves. The model grouping uses the actual IM `protocol` field. The snapshots retain the upstream local-model, auto-routing, metadata and preset code for provenance; executable adapters use the data capabilities supplied by IM.

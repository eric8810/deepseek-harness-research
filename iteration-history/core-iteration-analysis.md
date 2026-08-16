# core 部分迭代变更说明（2026-06-10 → 2026-08-13）

> 本文是对 DeepSeek Harness 仓库 `packages/core` 组（含其扁平布局祖先与已消失的历史包）迭代历史的深度分析。只读 git 历史与文档产出，不包含对工作树的任何改动。

## ① 范围与方法

**范围**

- 现存 core 组 8 个包：`agent`、`agent-default-model`、`agent-loop`、`agent-tool-presentation`、`scope`、`session`、`system-prompt`、`tools`，外加组级文件。
- 扁平布局时代（06-11..06-20）的祖先路径：`packages/agent-loop`、`packages/agent`、`packages/tools`、`packages/session`、`packages/system-prompt`。
- 历史中属于 core 组、现已消失或移出的包：`agent-core`、`skill`、`skill-local`、`tool-skill`、`tool-ask-user`、`project-instructions`、`agent-execution`、`agent-tool-mode`、`user-interaction`。
- 时间范围 2026-06-10..08-13（HEAD = `abe560f`），author date 可信。

**方法**

1. `git log --no-merges` 按 core 全部现/历史路径收集非 merge 提交，产出 886 条；用消息关键词（`docs/test/ci/chore/build/style/lint/snapshot`、rename/move/format/typo/spelling）过滤出功能性提交 631 条，其余 255 条为维护类。
2. 用 [module-iteration-stats.csv](module-iteration-stats.csv) 的 Func/Maint 与周分布做交叉校验：core 组 809 次提交（Func 505 / Maint 304，Maint 约 37.6%），功能提交周峰值 113（07-20 那周），之后 86 → 69 → 25 递减。
3. 用 `--diff-filter=R` 查改名/移动（core 内重命名很频繁，本身是线索）；对重点重构用 `git show --stat` 看规模。
4. 交叉验证设计意图：读 `docs/architecture.md`、`docs/subsystems/*`（引用处）、`.agents/notes/implemented/architecture/` 下按日期的设计笔记（Problem/Decision/Consequences 三要素，是意图的权威记录）。

**数据规模**：分析 886 条 core 相关提交（631 功能 + 255 维护）；核对 200+ 条 architecture 笔记（06-11..08-13）与 `docs/architecture.md` 的 core 小节。

---

## ② 阶段总览表

阶段按日历周 + 提交密度 + 目录结构变化 + 消息主题定界（不照搬背景给的分界，用数据重新确认）。

| 阶段 | 日期 | 功能提交/周（core 组） | 主题 | 一句话意图 |
|---|---|---|---|---|
| P0 扁平奠基期 | 06-11 ~ 06-20 | 7（+扁平 agent-loop 34） | 事件溯源会话、agent loop 插件、持久化、ACP、branded id | 用「一切都是插件 + 事件溯源」把骨架立起来 |
| P1 分组重组期 | 06-20 ~ 06-28 | 14 | 扁平→分组、agent-core 抽出、skill/compaction/subagent 起步 | 用能力分组替代扁平包表，建立 seam 纪律 |
| P2 能力扩展期 | 06-29 ~ 07-05 | 31 | todo、compaction 细化、system-prompt 组装、subagent 结构化输出 | 补齐模型可见的提示词/工具/子代理能力 |
| P3 会话日志权威 + 作用域期 | 07-06 ~ 07-12 | 71 | 可重建请求不变式、scope、code mode、tool-timeout、approval | 确立「会话日志是唯一事实来源」，作用域化为每-agent 注册 |
| P4 生命周期硬化 + 并行期 | 07-13 ~ 07-19 | 89 | 并行工具、取消、包不变量、goal、canonical 输出、zstd | 把所有权/取消/不变量/持久输出契约焊死 |
| P5 消息机器重构 + 输出契约期 | 07-20 ~ 07-26 | 113（峰值） | unified send、消息机器简化、provider 路由、py-types、packed rows | 收敛 agent 的 inbox/状态机，统一 schema 与工具输出 |
| P6 稳态工程化 + 产品化期 | 07-27 ~ 08-13 | 86 → 69 → 25 | 不可变消息、session 族合并、token 投影、preset、命名契约、session 日志版本、工具展示 | 从高速迭代转入对外发布前的规范化与收尾 |

---

## ③ 各阶段详述

### P0 扁平奠基期（06-11 ~ 06-20）

**关键变更清单**

| commit | 日期 | subject |
|---|---|---|
| `d5a1d9bb` | 06-11 | Add abstract service interface packages |
| `43f42582` | 06-11 | Implement the agent loop plugin |
| `d2fb352f` | 06-11 | Enable maximum-strict TypeScript across our packages |
| `bfb03483` | 06-11 | Enforce 100% per-file test coverage on packages/*/src |
| `225ed051` | 06-11 | Add branded ID types: CallId, SessionId, AgentId |
| `36a30180` | 06-13 | feat(tools): validate model-generated tool args at the boundary |
| `11a29fde` | 06-13 | feat(invariants): dev-mode event-contract assertions + session-log freeze |
| `825b57af` | 06-14 | feat(llm): structured error taxonomy with a shared HarnessError base |
| `0731ed37` | 06-15 | feat(session): metadata seam + JSON-serializability invariant |
| `b0bc0b57` | 06-15 | feat(agent-loop): turn-enclosure invariant + post-turn error model |
| `df4b7d3d` | 06-15 | feat(session-persistence): abstract seam + JSONL backend + wiring |
| `9a4006cb` | 06-15 | feat(agent): create/resume factory seam |
| `0000cdb2` | 06-16 | feat(agent-loop): config-driven session resume via RESUME_SESSION_ID |
| `efee449c` | 06-16 | feat(session-persistence): preserve interrupted turns on crash; don't truncate |
| `fb9636db` | 06-16 | feat(acp): ACP bridge — drive the coding agent over JSON-RPC stdio |
| `c5a1c494` | 06-17 | feature(session): session surface |
| `7803c388` | 06-18 | feat(acp): tool-owned tool-call UI presentation |
| `2a4d89a4` | 06-20 | feat(agent): return an AgentHandle with an async per-agent disposer |
| `c4bc6e0e` | 06-20 | feat(agent): add queue-aware Agent.cancel() primitive |
| `a53a56ff` | 06-20 | fix(agent-loop): fold session lifecycle into the agent effect for ordered teardown |

**变更说明**

- 06-11 一天内完成从「抽象服务接口包」到「agent loop 插件」的实现，同步落地 strict TS、ESLint、100% 每文件覆盖率三套门禁（`d2fb352f`/`bfb03483`）。这是「先立门禁、再长功能」的起点。
- `session` 一开始就设计为 **事件溯源 + append-only**（对应笔记 06-11 `event-sourced-sessions`），随后叠加持久化抽象与 JSONL 后端、崩溃恢复（`df4b7d3d`/`efee449c`），以及 `session surface` 的投影层（`c5a1c494`，笔记 06-18 `session-surface`）。
- `agent` 的生命周期契约（`AgentHandle`、`cancel`、`whenIdle`、disposer）在本阶段末尾集中定型（06-20 的连续几条，对应笔记 06-18 `agent-lifecycle-and-ownership-contracts`）。
- 横切线索第一次出现：工具调用 UI 呈现（`7803c388`，`_meta` 约定）是后来 `agent-tool-presentation` 的最早雏形；`225ed051` 确立 opaque branded id。

**目的推断**

这一阶段的目的是 **用最严格的门禁换取一个可被信任的骨架**：先证明「插件化 + 事件溯源」这套架构能成立，并在第一周就把类型/测试/事件契约的机械校验做硬，让后续 500+ 功能提交都在可验证的地基上生长。设计思路是「先有不可伪造的事实流（session log），再有行为（loop）」，而不是传统的「先写业务逻辑」。

---

### P1 分组重组期（06-20 ~ 06-28）

**关键变更清单**

| commit | 日期 | subject |
|---|---|---|
| `d02e9f1b` | 06-20 | Reorganize packages into a modular hierarchy（191 files, +746/-548） |
| `e2bde290` | 06-21 | refactor(examples): extract the app spine into dsh-agent-core + app packages |
| `d6a2ab30` | 06-21 | feat(types): brand bash ids + stop brand erosion; extract Branded to dsh-brand |
| `6089e226` | 06-23 | refactor(session): make surface the sole derivation path, drop legacy fallback |
| `7aabd2a3` | 06-22 | Add in-process subagent backends: spawn (fresh) and fork (seeded) |
| `d091946f` | 06-25 | add project instruction file loading |
| `45be662e` | 06-25 | Add skill discovery and loading |
| `08fc8467` | 06-25 | Add ask_user_question interaction tool |
| `aa9afcef` | 06-25 | feat(compact-basic): baseline compaction backend |
| `dc95a788` | 06-30 | feat(events): interception seams — the typed-Decision surface for hooks |

**变更说明**

- `d02e9f1b` 是第一次大重构：扁平 `packages/{agent-loop,agent,session,system-prompt,tools}` 全部以 100% rename 移入 `packages/core/*`，同时 bash/fs 等能力也各自成组。这是「能力分组」而非「技术分层」的组织方式。
- `e2bde290` 把应用脊柱抽成 `dsh-agent-core`（后续又在 07-16 消失/并入 agent-loop），说明「可复用的核心脊柱」与「具体 app」开始分离。
- 一周内（06-22..06-25）长出第一批能力包：subagent（spawn/fork）、project-instructions、skill、tool-skill、ask_user、compaction。它们都短暂寄生在 core 组里，随后各自独立成组（见 ⑤）。
- `6089e226` 把 `surface` 定为 session 的唯一派生路径，砍掉 legacy 回退——这是「单一派生路径」理念的第一次明确落地。

**目的推断**

目的是 **用目录结构编码架构理念**：让「core / llm / bash / fs / skill…」成为一等公民，而不是一长串平级包。core 在此刻被定义为「agent 与会话的中枢」，而具体能力（skill、prompt、UI 交互）先放进来试探边界，成熟后移出——这解释了为什么后面 core 反复「瘦身」。设计思路是「先分组、再在组内定 seam」。

---

### P2 能力扩展期（06-29 ~ 07-05）

**关键变更清单**

| commit | 日期 | subject |
|---|---|---|
| `22a89847` | 06-29 | feat(session): add TodoItem + todo/write event vocabulary |
| `1a57d670` | 07-03 | refactor(tools): tagged render-intent union for tool-call presentation |
| `f256f396` | 07-05 | feat(system-prompt): prompt variables, persona-as-section, tool-guidance ownership |
| `00cf8b69` | 07-05 | feat(agent-loop): open every prompt with the harness identity section |
| `3f83a4ee` | 07-05 | review: the persona becomes the system-prompt plugin's deployment config |
| `dafb81be` | 07-05 | subagent: implement structured output for in-process backends |
| `a52cac00` | 07-03 | fix(project-instructions): load files through fs service |
| `1d43ea3c` | 07-05 | workflow: dynamic workflows — script-driven multi-agent orchestration |

**变更说明**

- `system-prompt` 在此阶段成型：从「字符串拼接」升级为「变量 + persona 作为 section + 工具引导归属」（`f256f396`），并明确 persona 是 system-prompt 插件的部署级 config（`3f83a4ee`，对应笔记 07-05 `prompt-variables-and-tool-guidance-ownership`）。
- `1a57d670` 把工具调用呈现改成 **带 tag 的 render-intent union**（`generic`/`terminal`/`diff` 等），对应笔记 07-02 `tool-render-intent-union`——这是「工具的 UI 呈现意图是设计的一部分」这条 AGENTS.md 规则的来源。
- `22a89847` 给 session 加 todo 事件词汇：模型可见状态第一次显式进入日志词汇。
- subagent 获得结构化输出（`dafb81be`），workflow 引入脚本驱动的多 agent 编排（`1d43ea3c`）。

**目的推断**

这一阶段的目的从「骨架正确」转向「模型体验完整」：把提示词组装、工具呈现、todo、子代理输出这些**模型可见**的界面逐一提炼成有类型、有事件、有归属的构件。它同时暴露出一个尚未回答的问题——这些模型可见的东西到底由谁保证可审计，直接为 P3 的「可重建请求」不变式铺路。

---

### P3 会话日志权威 + 作用域期（07-06 ~ 07-12）

**关键变更清单**

| commit | 日期 | subject |
|---|---|---|
| `a7b56985` | 07-06 | session: the request header becomes logged state — request/header events + fold/diff/apply |
| `a4f7e757` | 07-06 | session: cache the derived history — one projection per node, frozen and shared |
| `2093a889` | 07-06 | loop: every request is built from the log（+743/-66） |
| `c0808d51` | 07-06 | docs: the governing principle — every LLM request is reconstructable from the session log |
| `17bd71e5` | 07-07 | feat(agent): add the agent/request-messages request-only message seam |
| `32db205c` | 07-08 | feat(scope): dsh-scope scoped-context registration primitive |
| `3d16026e` | 07-09 | feat(core): scope-aware registries and session dispatch carriers |
| `f387b774` | 07-09 | feat(agent): the agent is a registration scope — Agent.ctx, setup slot, fused scoped dispatch |
| `7c513348` | 07-09 | refactor(core): every registry register-method returns the exact effect disposer |
| `8190016e` | 07-08 | feat(timeout): add tools/execute seam + tool-timeout policy plugin |
| `5d451bb2` | 07-08 | feat(tools): add ToolDefinition.timeoutMs declared+validated via defineTool |
| `ea4c10d7` | 07-08 | refactor(agent): replace the per-step advice seam with agent/session-prefix |
| `b59d245c` | 07-08 | feat: Code Mode — the registry's mode config, the SDK codegen, and the run_code bridge |
| `ef35007d` | 07-09 | feat(approval): the approval seam — one-shot permission decisions |
| `184e1640` | 07-09 | feat(tasks): background task runtime, task_* tools |
| `3263dab8` | 07-11 | fix(core): enforce agent-scoped ownership boundaries |
| `3529b3c1` | 07-12 | fix(scope): close final ownership races |
| `28e04ff4` | 07-12 | refactor(core): simplify scoped agent lifecycles |
| `7ea1bf11` | 07-13 | feat(agent-loop): run safe tool calls in parallel |

**变更说明**

- **本阶段最重要的事件**：`2093a889` + `c0808d51` 确立「**Model-visible ⟺ logged**」不变式。`request/header` 变成日志事件（`a7b56985`），派生历史按节点缓存并冻结（`a4f7e757`），loop 的每个请求都由日志重建。这条不变式至今仍写在 `docs/architecture.md`「Session log」小节，来源就是这里。
- `scope` 包在 07-08 诞生（`32db205c`），随后三天内完成「作用域感知注册表 + 分派载体 + Agent.ctx + 融合分派」（`3d16026e`/`f387b774`），并在 07-11..07-12 连打一串「harden ownership boundaries」补丁（`3263dab8`…`a9cb70d8`）。这是 core 从「全局注册」走向「每-agent 作用域注册」的转折。
- 工具执行获得 timeout seam（`8190016e`/`5d451bb2`），approval seam 出现（`ef35007d`），code mode 桥接（`b59d245c`），并行工具调用（`7ea1bf11`）——执行面开始膨胀。
- `7c513348` 把「注册是 effect，register() 返回 exact disposer」固化为惯例（至今在 AGENTS.md）。

**目的推断**

这一阶段回答了一个架构级问题：**一个可替换、可并行的 agent 里，模型看到的上下文靠什么保证可审计？** 答案是「日志是唯一事实来源」。`scope` 的出现则是同一问题的另一面：既然每个 agent 都有自己的注册，就必须有一个 primitive 把注册限定在单 agent 内，而不是全局污染。设计思路从「全局单例 + 事件溯源」演进为「每-agent 作用域 + 日志权威」的二元结构。

---

### P4 生命周期硬化 + 并行期（07-13 ~ 07-19）

**关键变更清单**

| commit | 日期 | subject |
|---|---|---|
| `e547980d` | 07-14 | feat(llm): route adapters by provider |
| `225796c9` | 07-14 | refactor: hide the concrete agent loop |
| `0236a123` | 07-14 | refactor: prune core tool and prompt surface |
| `c67c3d94` | 07-14 | refactor: derive event graphs and scope invariants from TypeScript |
| `f1d39921` | 07-15 | feat(acp): advertise and switch llm models |
| `3b1d1bfa` | 07-16 | refactor(agent-loop): unify tool-call scheduling on one rolling pool |
| `7bcae0cd` | 07-16 | feat(core): add agent execution context |
| `c238992f` | 07-16 | feat(core): make turn cancellation explicit |
| `aa4e6298` | 07-17 | feat(agent-loop): give each send its own turn |
| `c23214be` | 07-19 | refactor(core): fold initiator scope into agents |
| `765dfb21` | 07-19 | refactor(session): use one surface manager |
| `2bc4e05a` | 07-19 | fix(tools): enforce cooperative cancellation |
| `e8b95c87` | 07-19 | feat(tools): require cancellation signal on every invocation |
| `9d310ecc` | 07-19 | feat(invariants): add package-owned service seam |
| `941b0411` | 07-20 | feat(invariants): implement package runtime checks |
| `1145ee5f` | 07-20 | fix(invariants): assert runtime relationships, not API shapes |
| `0129063a` | 07-19 | feat(goal): add model-facing goal tools |
| `3b0b0cef` | 07-20 | feat: implement bounded LLM request recovery |
| `7ef21239` | 07-15 | feat(session): opt-in packed chunk rows in the JSONL log |

**变更说明**

- **取消语义**成为主线：`c238992f` 把 turn 取消显式化，`2bc4e05a`/`e8b95c87` 强制每个工具调用携带取消信号（对应笔记 07-16 `explicit-turn-cancellation`、07-19 `cooperative-tool-cancellation`）。这是从 P0 的 `Agent.cancel()` 到全链路协作取消的收敛。
- **不变量从 dev 断言升级为运行时契约**：`9d310ecc`/`941b0411` 引入 package-owned invariant service，`1145ee5f` 明确「断言运行时关系，而非 API 形状」——这条规则直接进入今天的 AGENTS.md。
- `e547980d` 让 LLM adapter 按 provider 路由（笔记 07-14 `provider-routed-llm-adapters`）；`f1d39921` 让 ACP 能选择/切换模型，是 `agent-default-model` 的前奏。
- `225796c9`「hide the concrete agent loop」+ `0236a123`「prune core tool and prompt surface」：core 开始主动收窄公开面，把具体 loop 藏到 Agent 接口后。
- `7ef21239` 给 JSONL 日志加 packed chunk rows（zstd 预研，笔记 07-19 `zstandard-jsonl-session-logs`），是日志体积优化的起点。
- `765dfb21`「use one surface manager」是对 P1 已确立的「surface 唯一派生」的再次收口。

**目的推断**

这一阶段的意图是 **把「可运行」变成「不可错」**：取消/所有权/不变量三个横切面被同时硬化，且不变量从静态类型检查推进到运行时关系断言。设计思路从「框架能用」转向「框架在异常、取消、卸载、并发下都有可验证的语义」，同时开始为多 provider / 多模型铺路。

---

### P5 消息机器重构 + 输出契约期（07-20 ~ 07-26，峰值）

**关键变更清单**

| commit | 日期 | subject |
|---|---|---|
| `8500974f` | 07-21 | feat: unify JSON value schema DSL |
| `66c36e73` | 07-21 | feat: add canonical typed tool outputs |
| `c1d7b0df` | 07-21 | feat: return typed values from Code Mode |
| `8351cdbe` | 07-21 | feat(scope): add scoped-layer storage |
| `44fd93fd` | 07-23 | feat(agent): unify send(target × wakeup), coalesce context/message into user/message（+1242/-721） |
| `aaa42d58` | 07-24 | refactor(agent-loop): simplify message machine（+1172/-2589） |
| `45fc7fda` | 07-24 | refactor(agent-loop): separate injected context from turns |
| `b3c1abac` | 07-24 | refactor(agent-loop): rely on eager session persistence |
| `b73eb766` | 07-24 | refactor(agent-loop): simplify observable state machine |
| `8372340f` | 07-25 | feat(llm): add model-specific reasoning effort controls |
| `fbf87e66` | 07-28 | refactor: identify and freeze messages at creation |
| `350c296c` | 07-28 | fix: complete immutable message migration |
| `4ff496c6` | 07-26 | feat(session): default JSONL writes to packed rows |
| `f773985e` | 07-28 | feat(typert): add compiler-independent type pipeline |

**变更说明**

- **agent 消息机器的彻底重写**是本阶段中心：`44fd93fd` 统一 `send`、把 context/message 合并进 user/message（笔记 07-22 `unified-send-and-coalesced-user-messages`），随后 `aaa42d58` 以 -2589 行净删减「simplify message machine」，`45fc7fda` 把「注入上下文」与「turn 执行」分离（笔记 07-24 `separate-context-injection-from-turn-execution`）。这是一次显著的复杂度削减。
- **输出契约统一**：`8500974f` 统一 JSON schema DSL，`66c36e73` 引入 canonical typed tool output（笔记 07-20 `canonical-tool-output-contract`、`unified-json-value-schema-dsl`）。`tools` 从此承担大量 py-types / schema 边界工作（07-26..08-02 的 `py-types` 一串提交）。
- `8351cdbe` 给 scope 加 scoped-layer storage（笔记 07-12 `scoped-layers-store` 的落地）。
- `fbf87e66`/`350c296c` 开启「消息在创建时识别并冻结」（不可变消息，笔记 07-28 `identified-immutable-message-values`），把「冻结」从 session 投影推进到消息本身。
- `f773985e` 引入 Typert（编译器无关类型管线，笔记 07-27 `compiler-independent-typert-model`），这是后续类型图/RPC 的地基。

**目的推断**

峰值周（113 功能提交）的主题是 **做减法与立契约**：把 agent 的 inbox/状态机从多状态、多通道简化为单一 send + 单一 pending 表示；把工具输出和 JSON schema 收敛为 canonical 类型化形式。设计思路明显是「复杂度达到拐点后的主动重构」——前几阶段堆出的能力面太宽，此时以「统一 send」和「不可变消息」为锚点，把 agent-loop 的核心状态机重新做小。

---

### P6 稳态工程化 + 产品化期（07-27 ~ 08-13）

**关键变更清单**

| commit | 日期 | subject |
|---|---|---|
| `7e445c3a` | 07-30 | refactor(session): fold the session family into packages/session/ |
| `48192101` | 07-30 | refactor(token-meter): make context occupancy durable projection state |
| `8b4cbe42` | 07-30 | feat(system-prompt): cache dynamic policy context |
| `b425a2c4` | 08-03 | refactor(agent): run maintenance between turns |
| `49e90695` | 08-03 | refactor(agent): complete inbox lifecycle migration |
| `cb2f01f4` | 08-03 | refactor(agent-loop): drop the steering/message session event |
| `8cbdd5b9` | 08-04 | refactor(session): route construction through Session.create |
| `c02871b9` | 08-04 | refactor(session): separate validation from snapshots |
| `9eaa9d22` | 08-05 | feat(tools): let one agent choose its tool presentation, and ship `code` |
| `0afc4230` | 08-05 | feat: add reusable session preparation |
| `ccebba23` | 08-06 | refactor(agent): unify agent-scoped event signatures as payload objects |
| `9d5eb376` | 08-09 | fix(headless): dsh run is a direct core front door（并抽出 agent-default-model 包） |
| `e18aa274` | 08-08 | refactor(scope,agent-presets): per-preset standing mounts over a scope parent chain |
| `9186824e` | 08-10 | feat(session): refuse session logs a build cannot faithfully read |
| `aa623b6e` | 08-09 | refactor(events): add stable conversation correlation ids |
| `a2d0f7f4` | 08-13 | refactor: apply repository naming contract（3281 files, ±21k） |
| `03675064` | 08-12 | feat: slot system + entries/priority/errorreport + typert generator |
| `c905c469` | 08-13 | Adopt MIT for DSH packages |

（注：`9186824e` 全号为 `9186824e87eb5b996add8ae6d87701f6457e5684`，见附录。）

**变更说明**

- **包名与命名契约**：`agent-tool-mode`（08-05 诞生）在 08-13 改名为 `agent-tool-presentation`（`a2d0f7f4` 的一次 R085/R092 等 8 文件 rename），配合仓库级「naming contract + rename ledger」（笔记 08-11 `repository-naming-contract-and-rename-ledger`）。这是发布前把包名语义钉死的最后动作。
- **agent-default-model 独立成包**：模型选择逻辑最早在 `agent/src/llm-target.ts`（07-22 概念，08-09 改名 `model-selection.ts`），08-09 被 `9d5eb376` 抽成独立包 `agent-default-model`，把「默认模型跟随 picker」这一部署关注点从 agent 里分离（对应笔记 08-07 `default-model-follows-the-picker`）。
- **session 日志版本机制**（`9186824e`，笔记 08-10 `session-log-version-mechanism`）：一个单调整数 + 逐事件 `ignorable` 标记，解决「旧 runtime 读新日志」的方向性拒绝问题。这是 `Model-visible ⟺ logged` 不变式在持久化边界上的最后一块拼图。
- **preset 与 scope 收口**：`e18aa274` 用 scope parent chain 支持 per-preset standing mounts（笔记 08-08 `per-preset-standing-mounts`）；`601c3f8`/`9186824e` 之后，headless 直连 core（`9d5eb376`，笔记 08-09 `headless-direct-core-entry-point`）。
- **session 族合并**（`7e445c3a`）：把 `session-title`、`session-persistence`、`session-query` 等收敛进 `packages/session/`，反映「session 能力归 session 组」的最终归属。

**目的推断**

这一阶段从「迭代功能」切到「**为发布做规范化**」：包名语义钉死、命名契约落地、会话格式获得版本机制、session 族归位、agent-default-model 从 agent 中抽离。设计思路是「pre-release 立场下，宁可重命名/重分组也不要兼容 shim」——把正确的地基在第一个 tag 前一次性定稿，外部消费者的包袱此刻还不存在。

---

## ④ 思路演变总结（按时间线）

1. **「先立门禁，再长功能」**（06-11）：strict TS、100% 覆盖率、事件契约断言在同一天落地，后续一切迭代都被这些机械闸门约束。这是整个 core 史最底层的方法论。

2. **从「扁平包表」到「能力分组」**（06-20）：`packages/{agent-loop,agent,session,…}` → `packages/core/{…}`。组织原则从「一个包一个文件角色」变为「一个能力一个组」，core 被定义为 agent/会话中枢。

3. **从「会话可持久化」到「会话日志是唯一事实来源」**（06-15 → 07-06）：session 从 JSONL 后端、崩溃恢复一路演进到「每个请求都能从日志逐字节重建」（`2093a889`），并固化为 `Model-visible ⟺ logged` 不变式。这是全 repo 最重要的一条设计公理。

4. **从「全局注册」到「每-agent 作用域」**（07-08 → 07-12 → 08-08）：`scope` 包的出现把注册 primitive 限定到单 agent，随后 scope 的所有权边界被反复焊死，最后支撑起 per-preset standing mounts。core 的注册模型从单例走向分层作用域。

5. **从「能力扩张」到「状态机做小」**（06-25..07-09 扩张 → 07-23..07-24 收缩）：skill/subagent/code mode/approval/tasks 快速堆出能力面后，峰值周以 unified send + 消息机器简化（-2589 行）+ 不可变消息，把 agent-loop 的核心状态机重新做小。扩张与收缩是同一设计在找平衡点。

6. **从「dev 断言」到「运行时不变量」到「发布前规范化」**（06-13 → 07-19/20 → 08-10..13）：不变量从 dev-mode 断言升级为 package-owned runtime 契约，最后以会话格式版本机制、命名契约、MIT 授权收尾——每次都在「正确性」与「可发布性」两个维度上各升一级。

---

## ⑤ 反复回炉与已定型的点

### 反复回炉的地方（信号：同一主题在一段时间内被多次重构）

1. **session 的派生/surface 机制**——从 `c5a1c494`（06-17 session surface）→ `6089e226`（06-23 surface 唯一派生）→ `765dfb21`（07-19 one surface manager）→ `7e445c3a`（07-30 session 族合并）→ `c02871b9`（08-04 分离 validation 与 snapshot）。这是 core 里被重构最多的横切面，反映「投影层 vs 存储层」的边界长期在找最稳的形态。

2. **agent 的消息/inbox 状态机**——`44fd93fd`（07-23 unified send）→ `aaa42d58`（07-24 简化）→ `f2e20c1e`（07-30 再简化）→ `fcc2b5e2`（07-31 pre-step inbox 生命周期）→ `dbdf270a`（08-02 inbox-driven turn admission）→ `49e90695`（08-03 inbox 迁移收口）。几乎每周都在动，直到 08-03 才定型。

3. **scope 的所有权边界**——07-11..07-12 连续 `enforce/harden/close ownership` 十余条，07-19 又 fold initiator scope into agents，07-21 加 scoped-layer storage，08-08 再为 preset 加 parent chain。说明「什么属于哪个作用域」是一个反复被边界条件打破的问题。

4. **工具/UI 呈现**——06-18 `_meta` 约定 → 07-03 render-intent union → 08-05 agent-tool-mode → 08-13 agent-tool-presentation。呈现机制从「工具的旁路约定」演进为「作用域可选的显式呈现层」，包名都改了两轮。

5. **默认模型 / 模型选择**——从 `agent/src/llm-target.ts`（07-22）→ `model-selection.ts`（08-09）→ 独立 `agent-default-model` 包（08-09）。模型选择一直在 agent 内反复挪位，最终才被承认为独立的部署关注点。

### 后来定型的共识（不再被动摇）

- **「一切都是插件」，没有特权 core**（06-11 起，`docs/architecture.md` 明确「There is no privileged core to patch」）。
- **append-only 事件溯源会话 + `Model-visible ⟺ logged`**（06-11 / 07-06），至今是 `docs/architecture.md` 的 Session log 小节。
- **capability seam = Service Definition / Provider / Consumer 三角色**（06-13 笔记），「一个 seam 不能只有一种角色」。
- **opaque branded id**（06-11/06-20），跨边界 id 一律 `Branded<B>`。
- **注册即 effect，register() 返回 disposer**（07-09），沿用至今。
- **scope 作为每-agent 注册 primitive**（07-08），成为 preset 与隔离的底座。
- **agent-loop 是「Agent 接口后的默认驱动」而非唯一实现**（07-14 hide concrete loop），`docs/architecture.md` 的 core 表里明确标为「default driver」。
- **session 日志版本 = 单调整数 + 逐事件 ignorable 标记**（08-10），发布前最后定稿的格式契约。

---

## ⑥ 附录：关键 commit 索引

| 缩写 | 完整 hash | 日期 | subject |
|---|---|---|---|
| `43f42582` | `43f425827781b95a1b66d7b3121b199e012ab9ad` | 06-11 | Implement the agent loop plugin |
| `225ed051` | `225ed051b11c0baf39b3e88e8bbe0de9868d60f6` | 06-11 | Add branded ID types |
| `36a30180` | `36a30180b8efb4cf66d226dc7b3f0c827969d065` | 06-13 | tool arg validation at boundary |
| `df4b7d3d` | `df4b7d3d9adf43bdf913e17b502f042f80379394` | 06-15 | session-persistence abstract seam + JSONL |
| `c5a1c494` | `c5a1c494e78278710a63257f0af7b64f7b6d9ce2` | 06-17 | session surface |
| `d02e9f1b` | `d02e9f1bd657393cb010d5d79faf753fe8f11abf` | 06-20 | Reorganize packages into a modular hierarchy |
| `6089e226` | `6089e226bc2423229eea942ae7e253cc847799f8` | 06-23 | surface as sole derivation path |
| `45be662e` | `45be662e85f5059bdf463ecc043688a444827f9e` | 06-25 | Add skill discovery and loading |
| `aa9afcef` | `aa9afcefc7dc85f7dc53b7f79430952ab94a9527` | 06-25 | baseline compaction backend |
| `f256f396` | `f256f3961d834391ac1210d8d84d7211221339a0` | 07-05 | system-prompt prompt variables / persona |
| `a7b56985` | `a7b569850b84a6a805cdb479a970bb85a28ae3b6` | 07-06 | request header becomes logged state |
| `2093a889` | `2093a8898bb4d27697188606b1561bf97e950885` | 07-06 | every request is built from the log |
| `c0808d51` | `c0808d5126d926b10f395a6be39d585c2f904c37` | 07-06 | governing principle (reconstructable requests) |
| `32db205c` | `32db205c100e9e5a7c8c6a1046f66fbd9c9edcad` | 07-08 | dsh-scope primitive |
| `7c513348` | `7c5133488a1fb8ca403796f86595fbcb50a3da70` | 07-09 | register() returns exact disposer |
| `7ea1bf11` | `7ea1bf119f76455bdb084a380a9c5738877244a8` | 07-13 | run safe tool calls in parallel |
| `e547980d` | `e547980d77368fe83f6e4ad20956dc64f2d4e20d` | 07-14 | route adapters by provider |
| `225796c9` | `225796c90dc5a6ea9b4afa2a9f4081f9d48606ae` | 07-14 | hide the concrete agent loop |
| `c238992f` | `c238992fbbba0b35f7bf2848712960a39e49ea0e` | 07-16 | make turn cancellation explicit |
| `765dfb21` | `765dfb217414295a81e0609fa704ba64316e52ee` | 07-19 | use one surface manager |
| `941b0411` | `941b0411d80fba789bdd237946d406593ee13df9` | 07-20 | implement package runtime checks |
| `8500974f` | `8500974fd466b2faadeda3c95cf9574e1a934a74` | 07-21 | unify JSON value schema DSL |
| `66c36e73` | `66c36e7325b1a496557a20e9c71c75e01a113692` | 07-21 | canonical typed tool outputs |
| `44fd93fd` | `44fd93fd06fff32e83351c77673b25c9af5dfb93` | 07-23 | unify send / coalesce context |
| `aaa42d58` | `aaa42d5844fd9691042c7923f5630b3011fe48a0` | 07-24 | simplify message machine |
| `fbf87e66` | `fbf87e660c7c622cf59b24a4ebaaf921d0f7664e` | 07-28 | identify and freeze messages |
| `7e445c3a` | `7e445c3a676596b373cc20478384352ad86d8299` | 07-30 | fold session family into packages/session/ |
| `49e90695` | `49e90695cc950ea9afb5bf2db0526c91b848152e` | 08-03 | complete inbox lifecycle migration |
| `9eaa9d22` | `9eaa9d22a5190eb1499974a0786d9411799251cf` | 08-05 | agent chooses its tool presentation |
| `ccebba23` | `ccebba2349b79a1d46bd40aa9736641a0cc646b3` | 08-06 | agent-scoped event payload objects |
| `9d5eb376` | `9d5eb37638b36948f2fd8d134e40d75d9fd3c3c7` | 08-09 | dsh run direct core front door (+agent-default-model) |
| `9186824e` | `9186824e87eb5b996add8ae6d87701f6457e5684` | 08-10 | refuse session logs a build cannot faithfully read |
| `a2d0f7f4` | `a2d0f7f41121ee81911dd1badbf248edd3f2ab70` | 08-13 | apply repository naming contract |

---

### 备注（不确定性）

- 「功能/维护」的二分依赖消息关键词过滤，与 [module-iteration-stats.csv](module-iteration-stats.csv) 的分类不完全一致（本分析得 631 功能 vs 统计 505）。差异主要来自扁平祖先路径与部分 `refactor` 提交的归类；不影响阶段划分与主线结论。
- `agent-default-model` 作为独立包的精确「出生」边界：包目录在 08-09 由 `9d5eb376` 一次性创建，但「默认模型」概念在 07-22 已存在于 `agent/src/llm-target.ts`，统计口径的不同会导致该包 First 标注差异。
- `skill / tool-skill / project-instructions / user-interaction / tool-ask-user` 从 core 移出的具体 rename 提交因移动时伴随内容变更，`--diff-filter=R` 未捕获到，改由统计 CSV 的 First/Last 时间窗与目标组（`packages/skill`、`packages/prompt`、`packages/ui`、`packages/interaction`）的出生时间交叉推断。

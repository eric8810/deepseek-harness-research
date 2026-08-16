# deployment:persona —— 部署人设槽位

`deployment:persona` 是 order-0 的部署人设槽位，由插件 `SystemPrompt` 构造时注册（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L364)）。槽位名与序位是导出的常量：`PERSONA_SECTION = 'deployment:persona'`（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L128)）、`PERSONA_ORDER = 0`（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L131)）。

## 逐字文本

槽位本身没有固定文本；其文本来自 `config.persona`（schema 默认 `''`，[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L342)），构造时以 `config.persona ?? ''` 解析为静态段（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L368)）。`persona` 是部署方经配置撰写的唯一提示片段，可含严格插值的 `{{variable}}` 引用（如 shipped loop 注册的 `{{model}}`/`{{cwd}}`），空字符串段在渲染时被丢弃（[README](../../../../packages/core/system-prompt/README.md)）。

## 替换机制

导出的目的正是让组合可替换该槽位：agent preset 可用自己的段遮蔽部署人设——两边命名同一 section 正是替换生效而非重复的原因（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L122)）。

- 替换路径：在某 agent 作用域注册 `{ name: PERSONA_SECTION, order: PERSONA_ORDER, text: … }`，该作用域的 `assemble` 因按名遮蔽（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L484)）只渲染新文本，全局仍渲染部署人设（[scoped.spec.ts](../../../../packages/core/system-prompt/tests/scoped.spec.ts#L33)）。
- 同层重复：在已注册该槽位的同一层再注册同名段抛错——全局 `agent.ctx` 提示、作用域 `already registered in this scope`（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L316)）。
- 序位语义：`PERSONA_ORDER = 0` 使 persona 是模型读到的第一个 section（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L130)），排在 `harness:identity`（order `-100`）之后、工具指引（`100–199`）之前（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L57)）。

正文：[01-system-prompt-registry.md](../01-system-prompt-registry.md)

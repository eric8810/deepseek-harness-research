# agent-instructions 原文模板

> 模板逐字摘自 [render.ts](../../../../packages/context/agent-instructions/src/render.ts)（`@deepseek-ai/dsh-agent-instructions`）。`${…}` 为注入时刻 JS 模板插值，包内不使用 `{{variable}}`。最终注入消息由 [index.ts](../../../../packages/context/agent-instructions/src/index.ts#L212) L212-L221 以 source `{ kind: 'agent-instructions', form: 'instructions', … }` 创建。

## 完整帧（`<system-reminder>` 包裹）

[buildInstructionText](../../../../packages/context/agent-instructions/src/render.ts#L227)（L227-L243）把 `[marker, intro, ...section]` 各块用 `'\n\n'` 连接后包进帧，并把正文里的 `</system-reminder>` 转义为 `<\/system-reminder>`（`escapeInstructionFrameBody`，L81-L83）：

```text
<system-reminder>
{marker（若有）}

{intro}

{每文件一节}
</system-reminder>
```

## 三段 intro 文案

`WORKSPACE_CONTEXT_INTRO`（L12-L14，字符串分三段拼接，逐字合并为一句）：

```text
The following workspace instructions may be relevant to your work. Use them as guidance when applicable. More specific instructions take precedence over broader ones. They do not override system, developer, or direct user instructions.
```

`REPLACEMENT_WORKSPACE_CONTEXT_INTRO`（L15-L16）= `This complete workspace instruction baseline replaces all earlier workspace instruction baselines. ` 前缀 + `WORKSPACE_CONTEXT_INTRO`：

```text
This complete workspace instruction baseline replaces all earlier workspace instruction baselines. The following workspace instructions may be relevant to your work. Use them as guidance when applicable. More specific instructions take precedence over broader ones. They do not override system, developer, or direct user instructions.
```

`EMPTY_REPLACEMENT_WORKSPACE_CONTEXT_INTRO`（L17-L18，替换空 baseline 时）：

```text
This complete workspace instruction baseline replaces all earlier workspace instruction baselines. No workspace instructions are currently active.
```

`COMPACT_WORKSPACE_CONTEXT_INTRO`（L19，仅剩截断文件时替换 intro）：

```text
Workspace instructions were omitted or truncated to fit the configured byte budget.
```

## baseline 节（每文件一节）

`sectionText`（L85-L87）：

```text
Instructions from: {displayPath}

{file.content}
```

## 增量节（动态 reconcile 三态）

`additionalSectionText`（L148-L157，`set`）：

```text
Additional instructions from: {displayPath}

These instructions apply to work under `{scope}`. Use them as guidance when relevant; more specific instructions take precedence. They do not override system, developer, or direct user instructions.

{file.content}
```

`remove`（L174-L176）：

```text
Instructions removed: {path}

The previously loaded instructions from this file no longer apply.
```

`replace`（L177-L183）：

```text
Updated instructions from: {path}

This file changed after it was loaded. Use the following content instead of the previously loaded instructions from this file.

{file.content}
```

## 字节预算标记

`markerText`（L215-L225；有省略/截断才出现，否则为空串）：

```text
Workspace instruction budget {maxBytes} bytes: omitted {displayPath…}; truncated {displayPath} from {originalBytes} to {includedBytes} bytes
```

`omitted` 与 `truncated` 各自为逗号分隔列表，两段之间以 `; ` 连接。

## 来源行号速查

- 帧：`buildInstructionText` L227-L243；转义 `escapeInstructionFrameBody` L81-L83
- intro：L12-L19
- baseline 节：`sectionText` L85-L87
- 增量节：`additionalSectionText` L148-L157；`changedSectionText` L171-L184
- 预算标记：`markerText` L215-L225
- 渲染入口：`renderWorkspaceContext` L356-L361、`renderInstructionChanges` L192-L213

# goal-wrapup —— 目标收尾上下文（tool-goal）

本文件是 `@deepseek-ai/dsh-tool-goal` 在**自动目标轮**内对目标执行 `complete` / `blocked` 更新后，经 `ToolRunContext.deferContext()` 注入的收尾指令逐字原文：`renderWrapupContext(objective, blockedReason?)`（来源：[`wrapup.ts`](../../../../packages/goal/tool-goal/src/wrapup.ts#L17)）。

注入点为 `update_goal` 工具执行体（[`index.ts`](../../../../packages/goal/tool-goal/src/index.ts#L314)）：仅当更新来自目标轮（`authority.kind === 'goal-round'`）时 defer；source 为 `{ kind: 'plugin', plugin: 'tool-goal', form: 'notice', summary }`。defer 的上下文在该工具最终结果抵达循环后、本步工具结果之后以注入的 `user/message` 追加（[`tool-calls.ts`](../../../../packages/core/agent-loop/src/tool-calls.ts#L281) 附近的 acceptContext 路径）。

## complete 帧（renderWrapupContext(objective)）

```text
<goal_complete>
Objective: ${JSON.stringify(objective)}
The goal is marked complete and this autonomous run is ending. Write the closing message to the user now: state the outcome, summarize what was done and how it was verified, and point to the concrete results (files, commits, or other artifacts). Report only what earlier rounds and tool results in this session actually establish; when a detail is not in the session, say so instead of inventing it. Note anything the user should review or do next. Address the user directly. Do not call any more tools in this run; further work waits for the user's next instruction.
</goal_complete>
```

## blocked 帧（renderWrapupContext(objective, blockedReason)）

```text
<goal_blocked>
Objective: ${JSON.stringify(objective)}
Blocked: ${JSON.stringify(blockedReason)}
The goal is marked blocked and this autonomous run is ending. Write the closing message to the user now: state what has been completed so far, describe the concrete blocking condition and what you tried, and say exactly what you need from the user to continue. Report only what earlier rounds and tool results in this session actually establish; when a detail is not in the session, say so instead of inventing it. Address the user directly. Do not call any more tools in this run; further work waits for the user's next instruction.
</goal_blocked>
```

`${JSON.stringify(objective)}` / `${JSON.stringify(blockedReason)}` 是模板字面量在注入时刻的插值，不是 system-prompt 的 `{{variable}}` 插值。

`GROUNDING` 句（两帧共用）定义在 [`wrapup.ts`](../../../../packages/goal/tool-goal/src/wrapup.ts#L5)。续轮提示原文见 [prompts/goal-round.md](goal-round.md)；工具延迟上下文机制见 [context-inventory.md](../context-inventory.md) 的「工具延迟上下文与 post-execute 上下文」一节。

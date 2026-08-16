# goal-round —— 目标续轮提示（goal-round-driver）

本文件是 `@deepseek-ai/dsh-goal-round-driver` 为**同会话目标自动续轮**生成的模型可见提示词逐字原文：`renderGoalRoundPrompt(goal, round)`（来源：[`prompt.ts`](../../../../packages/goal/goal-round-driver/src/prompt.ts#L12)）。

该提示由驱动器在 agent 空闲、目标 `active` 且 `armed`、且未达 `maxGoalRounds` 时生成，经 `agent.followup(message)` 进入 inbox 并认领为下一步消息（[`index.ts`](../../../../packages/goal/goal-round-driver/src/index.ts#L174)），source 为 `{ kind: 'goal', goalId, revision, round }`（round 从 `roundsStarted + 1` 起）。

## 逐字模板

```text
<goal_round>
Objective: ${JSON.stringify(goal.objective)}
Round: ${round}/${goal.maxGoalRounds}

Continue working toward the objective in this same session. Treat the current workspace, tool results, and durable session state as authoritative; inspect them instead of assuming earlier narration is still current. Make concrete progress and verify the result. Before claiming completion, gather evidence that the whole objective is achieved, read the current goal, and mark it complete. If work remains, leave the goal active for the next round. Follow the configured goal-tool policy before reporting a blocker.
</goal_round>
```

`${JSON.stringify(goal.objective)}` 与 `${round}/${goal.maxGoalRounds}` 是模板字面量在注入时刻的插值，不是 system-prompt 的 `{{variable}}` 插值。

目标域的读写工具与 `tool:goal` 指引段见 [context-inventory.md](../context-inventory.md) 的 system 段落表（`tool:goal`，order `114`）；续轮的认领/失效防护见 [09-injection-paths-subagents-and-hooks.md](../09-injection-paths-subagents-and-hooks.md) 的注入路径一节。

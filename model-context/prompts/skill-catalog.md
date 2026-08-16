# skill-catalog —— 会话技能目录帧（tool-skill）

本文件是 `@deepseek-ai/dsh-tool-skill` 发布给模型的**可用技能目录** user 消息的逐字原文，共两种帧：首次发布帧 `renderCatalogMessage` 与目录变化时的完整替换帧 `renderCatalogUpdate`（来源：[`index.ts`](../../../../packages/skill/tool-skill/src/index.ts#L254) / [`index.ts`](../../../../packages/skill/tool-skill/src/index.ts#L279)）。

目录由 `agent/pre-step` 监听器注入（[`index.ts`](../../../../packages/skill/tool-skill/src/index.ts#L213)）：仅当该 agent 可见 `skill` 工具的**精确定义**时才发布；条目是 `- \`name\`: description` 摘要行（`renderCatalogEntries`，[`index.ts`](../../../../packages/skill/tool-skill/src/index.ts#L319)），不含技能正文。发布进 enter 消息后经 `user/message` 落日志，source 为 `{ kind: 'skill-catalog', form: 'catalog', entries }`（替换帧带 `update: true`）。目录摘要由 sha256 摘要驱动重发布：可见摘要未变则不追加，目录变化则以新帧替换旧目录消息。

## 首次发布帧（renderCatalogMessage）

```text
<system-reminder>
A skill is a reusable set of task-specific instructions. The following skills are available in this session:

<available_skills>
- `${entry.name}`: ${escapeText(entry.description)}
</available_skills>

If the user names a skill, or the task clearly matches a skill's description, call the `skill` tool with the exact skill name before taking task actions. Load all applicable skills, then follow their full instructions. This catalog contains summaries only; do not infer or follow a skill's instructions until it has been loaded.
A user may also invoke a skill directly; its <skill_content> block then appears in this conversation. Follow it, and do not call the `skill` tool again for that skill.
</system-reminder>
```

`${entry.name}` / `${escapeText(entry.description)}` 是 `renderCatalogEntries` 按目录条目逐行插值的模板字面量（[`index.ts`](../../../../packages/skill/tool-skill/src/index.ts#L319)），每条目录占一行；description 经空白归一化并按 `catalogDescriptionMaxLength`（默认 500）截断（[`index.ts`](../../../../packages/skill/tool-skill/src/index.ts#L391)）。这是 JS 插值，不是 system-prompt 的 `{{variable}}` 插值。

## 完整替换帧（renderCatalogUpdate）

```text
<system-reminder>
The available skill catalog changed. This complete catalog replaces every earlier available-skills list in this session:

<available_skills>
- `${entry.name}`: ${escapeText(entry.description)}
</available_skills>

Use only names in this replacement catalog. If the user names a listed skill, or the task clearly matches its description, call the `skill` tool with the exact name before acting.
A user may also invoke a skill directly; its <skill_content> block then appears in this conversation. Follow it, and do not call the `skill` tool again for that skill.
</system-reminder>
```

目录为空时，替换帧的最后两行变为（[`index.ts`](../../../../packages/skill/tool-skill/src/index.ts#L280)）：

```text
No skills are currently available through the `skill` tool. Do not use names from earlier skill catalogs.
A user may still invoke a skill directly; its <skill_content> block then appears in this conversation. Follow it, and do not call the `skill` tool for it.
```

相关机制：目录的注入与替换语义见 [07-persona-presets-and-skills.md](../07-persona-presets-and-skills.md)；技能正文的 `<skill_content>` 帧见 [prompts/agent-instructions.md](agent-instructions.md) 所在系列的 [`renderSkillContent`](../../../../packages/skill/skill/src/index.ts#L171)。

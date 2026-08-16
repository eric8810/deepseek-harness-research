# persona-defaults —— 部署人设默认逐字文本

`deployment:persona` 槽位（order `0`）本身不携带固定文本；其文本来自 `dsh-system-prompt` 行的 `config.persona`（schema 默认 `''`，[index.ts](../../../../packages/core/system-prompt/src/index.ts#L342)）。shipped 模式 bundle 通过 patch 覆写该字段，文本可含严格插值的 `{{variable}}` 引用。

## 基础默认（base bundle）

`packages/bundle/base/cordis.patch.yml` 的 `system-prompt` 行把部署人设默认置为空串（[cordis.patch.yml](../../../../packages/bundle/base/cordis.patch.yml#L429)）：

```yaml
- id: system-prompt
  name: '@deepseek-ai/dsh-system-prompt'
  config:
    persona: ''
```

空串即“部署人设由部署方撰写”的默认：段存在但文本为空，`renderPrompt` 渲染时被丢弃（[index.ts](../../../../packages/core/system-prompt/src/index.ts#L212)）。

## 模式 bundle 默认（headless / web-app）

`headless` 与 `web-app` 两个模式 bundle 的 patch 把 persona 覆写为同一逐字模板（[headless/cordis.patch.yml](../../../../packages/bundle/headless/cordis.patch.yml#L7)、[web-app/cordis.patch.yml](../../../../packages/bundle/web-app/cordis.patch.yml#L16)）：

```yaml
- id: system-prompt
  config:
    persona: >-
      You are a coding agent powered by the {{model}} model. Your working directory is {{cwd}}.
```

逐字渲染文本（`{{…}}` 在渲染期被插值替换）：

```text
You are a coding agent powered by the {{model}} model. Your working directory is {{cwd}}.
```

`{{model}}` 与 `{{cwd}}` 由 `dsh-agent-loop` 注册为提示变量：`model` 来自 `agent.options.model`、`cwd` 来自 `agent.session.header.cwd`（[index.ts](../../../../packages/core/agent-loop/src/index.ts#L351)）；插值在 `renderPrompt` 阶段严格解析（[01-system-prompt-registry.md](../01-system-prompt-registry.md#渲染与严格变量插值)）。

## 随发行版 agent preset 的人设（standard / code）

随 Web surface 发行、写入 `apps/cli/config/agent-presets/` 的两个 preset（`standard` 与 `code`）各自带一个 `persona` 行，挂载 `@deepseek-ai/dsh-persona` 并以 `deployment:persona` 同名遮蔽部署人设（[standard/agent.cordis.yml](../../../../apps/cli/config/agent-presets/standard/agent.cordis.yml#L24)、[code/agent.cordis.yml](../../../../apps/cli/config/agent-presets/code/agent.cordis.yml#L31)）：

```yaml
- id: persona
  name: '@deepseek-ai/dsh-persona'
  config:
    text: >-
      You are a coding agent powered by the {{model}} model. Your working directory is {{cwd}}.
```

逐字渲染文本与 headless/web-app 的部署 persona 相同；区别在来源与遮蔽关系——该文本作为 preset 组合的一部分注册进 preset 作用域层，遮蔽的是全局 `deployment:persona` 槽位，且 `{{model}}`/`{{cwd}}` 从 agent 自身的路由与 workspace 解析。

## 相关文档

- 槽位语义与替换机制：[deployment-persona-slot.md](deployment-persona-slot.md)
- 注册清单与遮蔽规则：[07-persona-presets-and-skills.md](../07-persona-presets-and-skills.md)

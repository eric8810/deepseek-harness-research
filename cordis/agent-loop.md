# Agent Loop:驱动循环的解剖

> 承接 [runtime-pipeline.md](runtime-pipeline.md)(工具管线与 turn flow)。本笔记回答 loop 本身怎么运作、依赖哪些内容、为什么不依赖其他内容。依据:`packages/core/agent-loop/src/{index,agent,tool-calls}.ts`、`docs/subsystems/core.md`、`docs/agent-lifecycle.md`。

## 一、依赖清单:inject 声明就是全部答案

```ts
export class AgentLoop extends Service implements AgentFactory {
  static inject = ['agents', 'sessions', 'llm', 'tools', 'systemPrompt']
  // index.ts:297
}
```

| 依赖 | 循环拿它做什么 |
|---|---|
| `ctx.agents` | 注册自己为 AgentFactory;`withInitiator`/`requireInitiator`;发 `agent/*` 事件 |
| `ctx.sessions` | 唯一事实源:append 一切、`deriveMessages()` 派生模型历史、`requestHeader()` 读请求头 |
| `ctx.llm` | `prepareCall`(绑定适配器、算默认值)→ `stream` |
| `ctx.tools` | `executionMode` 分类 + 内部调度器 prepare/dispatch/finalize |
| `ctx.systemPrompt` | `assemble` 组装提示词;注册 `provider`/`model`/`cwd` 变量(按 agent 求值) |

两个机会式依赖(不在 inject 里):

- `ctx.get('sessionPersistence')`:resume 会话需要持久化,没有就不支持 resume
- settings section:`maxParallelToolCalls` 挂到 settings 文档热更新,getter 每次调度时读

零策略依赖:循环不知道沙箱、审批、spill、guard 的存在。循环的世界里只有「日志 + 五个缝 + 事件」。

## 二、一个 agent = 一个 ReactLoopAgent 实例

- `phase`:idle / maintenance / running(带各自 abort 控制器)
- `inbox`:消息队列,带 spliced/inserted/claimed/discarded 事件
- `scope`:每 agent 作用域;`ctx = scope.ctx.extend({ agent: this })`
- 输入面:`followup`(next-turn,唤醒)/ `steer`(next-step,唤醒)/ `inject`(next-step,不唤醒)/ `cancel`(中止,可选清 inbox)
- `wakeDriver` 闭锁:idle 直接启动;busy 时活 driver 自己认领队列,只有 maintenance 中或 abort 后唤醒才 latch `wakeRequested`,收敛后补跑

## 三、驱动循环:kick → turn → step

```
kick(): while (await this.turn()) {}

turn():
  turn/start 落日志
  claim(认领输入)
  agent/pre-step waterfall        // reject 或 enter(messages)
  loop:
    step/start + user/message 落日志
    step()                        // 一次模型请求 + 工具
    step/end 落日志
    turn-stopping serial(可选终检)
    有下一步输入?继续 claim : 结束
  turn/end 落日志
  队列还有活?再来一轮 : 结束

step():
  buildRequest:
    种子 = options + 持久化请求头
    agent/request waterfall       // 插件可换 provider/model/config
    llm.prepareCall               // 绑定适配器(NO_ADAPTER 才绕过)
    request/header 落日志         // initial/resume/change
    request/context 落日志        // provider/model/contextWindow 变化时
    deepFreeze 请求
  stream:assistant/chunk* 落日志
  失败:agent/request-error waterfall → retry 或抛 LlmError
  成功:assistant/message 落日志(带 usage、chunk seq)
  有工具调用?executeToolCalls() : completed
```

## 四、工具调度:循环只做三件事

- 按 `executionMode` 分组:exclusive → 屏障(一次一个);parallel → 有界滚动池
- 每次启动前重新分类:registry 运行中变化可制造新屏障
- 每个调用:`tool/call` 落日志(执行前)→ prepare(有序 pre+守卫)→ dispatch(并发 body)→ 按模型序 commit(finalize:有序 post + `tool/result` 落日志,带 callSeq 关联)
- abort:已启动的排空,未启动的补合成 `ABORTED_BEFORE_DISPATCH` 结果——保证重放合法
- 关键不变量:策略有序(pre/post 模型序),body 并发(池),结果按模型序提交(commitReady 只沿连续模型序槽推进)

## 五、循环的自我认知:三个角色

1. **日志写入者**:不持有「当前状态」,所有事实 append 进 session;连请求配置都先落 `request/header` 日志再冻结进请求
2. **事件分发者**:`agent/pre-step`(可拒绝)、`agent/request`(可换模型)、`agent/request-error`(可重试)、`agent/turn-stopping`(有序终检)
3. **调度器驱动者**:不执行工具(按序喂 registry 调度器)、不组装提示词(只调 assemble)、不流式请求(只消费 stream)

本质:循环是「日志 ←→ 模型」之间的搬运工,所有智能都长在它身边的插件上。循环提供的是节拍,不是功能——这解释了为什么 plan mode、goal、guard 能做到一行循环不改。

## 关键源码锚点

| 概念 | 位置 |
|---|---|
| 五依赖声明 | `packages/core/agent-loop/src/index.ts:297` |
| 工厂注册与 declarative agents | `packages/core/agent-loop/src/index.ts:296-359` |
| 实例状态机与输入面 | `packages/core/agent-loop/src/agent.ts:64-200` |
| turn 循环 | `packages/core/agent-loop/src/agent.ts:246-330` |
| step 循环 | `packages/core/agent-loop/src/agent.ts:332-401` |
| 请求构建与 header 日志 | `packages/core/agent-loop/src/agent.ts:407-495` |
| 工具调度(屏障/池/commit 序) | `packages/core/agent-loop/src/tool-calls.ts` |
| 官方时序图 | `docs/agent-lifecycle.md`(+ zh) |

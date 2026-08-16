# LLM 缝:数据结构与词汇表

> 承接 [cordis-agent-loop.md](agent-loop.md)(循环)。本笔记聚焦 LLM 缝的数据结构:`packages/llm/llm/src/{types,message}.ts` 定义的 harness 词汇表,以及服务面的请求/注册结构。官方出处:`docs/subsystems/llm-streaming.md`。

## 一、三个 merge-extensible 联合

设计手法统一:闭集用判别联合 + assertNever,开放集用 map + 声明合并扩展;switch 对未知类型文档化 fall-through。

### 1. ContentBlockMap — 消息的最小组成单元

| 类型 | 字段 | 性质 |
|---|---|---|
| `text` | `text` | 可见文本 |
| `reasoning` | `text` | 思考内容,区别于可见文本 |
| `image` | `attachment: ImageAttachmentRef` | 角色中立;字节归 attachment 服务 |
| `tool-call` | `id: CallId; name; arguments: string` | arguments 保持原始 JSON 字符串 |
| `tool-result` | `toolCallId; content: ContentBlock[]; isError?` | 嵌套 content,可含 image/嵌套 tool-result |

- tool-result 嵌套 → `contentHasImage` 是唯一的递归遍历,所有图片策略共用,防止嵌套深度理解不一致
- arguments 原样进日志,解析是工具侧的职责

### 2. FinishReasonMap — 为什么停

`stop` / `tool-calls` / `max-tokens` / `aborted{failure}` / `error{failure}`。停止原因与内容是正交维度;loop 里 max-tokens 粘性(一个 step 撞顶,后续完成不降级 turn 结局)。

### 3. MessageSourceMap — 消息从哪来

- `user` / `plugin{plugin, ContextFormed}` / `model{provider, model, replayState?}` / `tool{callId}`
- 两个独立轴:`kind` 答「谁产的」,`form` 答「什么东西」
- `ContextForm` 是语义词汇,永不视觉化:`instructions` / `catalog` / `snapshot`(后发替代前发)/ `notice`(summary ≤ 120 字符)/ `relay` / `recall`。颜色、图标、折叠方式是消费者的事,不得进联合

## 二、Message:共享的不可变表示

```ts
interface Message {
  readonly id: MessageId            // branded,跨表示边界稳定
  readonly role: 'system' | 'user' | 'assistant'
  readonly content: ContentBlock[]
  readonly source: MessageSource
}
```

- 构造即冻结:`createUserMessage`/`createAssistantMessage`/`createToolResultMessage` 全部 deepFreeze + 新 MessageId
- `ToolResultMessage.content` 是单元素元组 `[ToolResultBlock]`——工具结果消息永远恰好一个结果块
- `AssistantMessage.source` 必带 provider + model + 可选 `replayState`(适配器私有无损 JSON 重放状态)
- **replayState 安全边界**:只暴露给「同时拥有历史 provider 和目标 provider」的适配器实例——别家的重放数据别家看不到

## 三、StreamChunk:适配器的流协议契约

```ts
type StreamChunk =
  | { type: 'block-start'; index; blockType }
  | { type: 'text-delta'; index; text }
  | { type: 'reasoning-delta'; index; text }
  | { type: 'tool-call-delta'; index; id: CallId; name?; argumentsDelta }
  | { type: 'block-end'; index; block: ContentBlock }
  | { type: 'usage'; usage: TokenUsage }
  | { type: 'finish'; reason: FinishReason; replayState? }
```

契约条款:

1. block index 关联交错 delta,`block-end` 带组装完成的块——并发多块流靠 index 对齐
2. usage 在终局 finish 之前发,之后什么都不发
3. 适配器可抛错,`LlmRuntime.stream()` 归一成终局 `error`/`aborted` finish 才交给消费者——消费者只见词汇表,不见异常
4. `isTokenDelta` 定义首 token 边界:空 delta(心跳)不算;客户端首 token 计时与 sessionStats 共用

**TokenUsage 计数不相交**:`inputTokens` 只算未缓存输入,缓存命中/写入单独计;计费输入 = 三者之和。DeepSeek 的 `prompt_tokens` 折进缓存,适配器要减回去。

## 四、服务面:请求与注册

**GenerateOptions** = 完全组装的请求:provider(路由键)+ model + reasoningEffort(适配器拥有的 opaque id)+ messages + system + tools + stop + signal + `sessionId`(重放分游标)+ `purpose`('compaction' | 'session-title')。

**prepareCall → PreparedLlmCall**:

- `config`:冻结的、适配器默认值已物化的配置
- `retryPolicy`:注册时捕获的不可变重试策略
- `context`:上下文窗口元数据
- `adapterDefaults`:哪些字段是适配器物化的(不是调用方提的)——loop 的 `requestProposal` 依赖它:插件提议下一请求时先剥掉适配器物化值,否则它们固化成显式值
- `stream()`:走注册时捕获的实例,含 `llm/stream` waterfall

**注册侧**:`registerAdapter(providers, adapter)` 全有或全无;`replace()` 先整体校验、一次性同步替换、请求无缝隙观察;释放后再注册抛 `REGISTRATION_DISPOSED`。`llm/adapters-updated` 通知的监听器逐个隔离,一个坏了不饿死后面的。

## 五、设计要点

| 要点 | 机制 |
|---|---|
| 词汇 provider-neutral | 适配器翻译 wire 消息;loop/session/插件只见 harness 词汇 |
| 可扩展 | 三个 map 声明合并;switch 带文档化 fall-through |
| 身份稳定 | `MessageId` branded,跨边界不变;构造即 freeze |
| 无损 JSON 贯穿 | replayState、LlmFailure 可序列化;请求头落日志 |
| 语义与视觉分离 | ContextForm 语义化;渲染是消费者的事 |
| 计费准确 | TokenUsage 不相交计数 |
| 替换原子性 | validate-first + 同步 swap + disposed 后拒绝 |

## 关键源码锚点

| 概念 | 位置 |
|---|---|
| ContentBlockMap / FinishReasonMap / StreamChunk / TokenUsage | `packages/llm/llm/src/types.ts` |
| Message / MessageSourceMap / ContextForm / 构造冻结 | `packages/llm/llm/src/message.ts` |
| LlmRuntime 服务、注册与 prepareCall | `packages/llm/llm/src/index.ts:284+` |
| LlmAdapter 抽象(stream 唯一必需方法) | `packages/llm/llm/src/index.ts:180-233` |
| 首 token 边界 | `packages/llm/llm/src/message.ts:251-260` |
| 官方子系统页 | `docs/subsystems/llm-streaming.md`(+ zh) |

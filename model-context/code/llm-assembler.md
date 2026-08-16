# llm-assembler：从 PromptAssembly 到请求体的关键源码摘录

本文档逐字摘录「模型请求最终线格式」链路上的关键源码，供 [08-llm-adapter-and-wire-format.md](../08-llm-adapter-and-wire-format.md) 引用。

每段摘录标注来源文件与行号；链接使用相对路径加行锚。

## Message 词汇与 content 块类型

### `Message` 及三个角色特化

来源：[message.ts](../../../../packages/llm/llm/src/message.ts#L129-L156)

```ts
/** One immutable message representation shared by delivery, durable history, and model requests. */
export interface Message {
  /** Stable identity preserved across every representation boundary. */
  readonly id: MessageId
  /** Provider-neutral conversation role. */
  readonly role: 'system' | 'user' | 'assistant'
  /** Exact model-facing blocks. */
  readonly content: ContentBlock[]
  /** Required source fields supplied by the producer. */
  readonly source: MessageSource
}
```

```ts
/** A user-role specialization of the one shared message representation. */
export interface UserMessage extends Message {
  readonly role: 'user'
}
```

```ts
/** A model-produced assistant specialization of the shared message representation. */
export interface AssistantMessage extends Message {
  readonly role: 'assistant'
  readonly source: ModelMessageSource
}
```

```ts
/** A tool-result specialization whose model-facing block retains call correlation. */
export interface ToolResultMessage extends Message {
  readonly role: 'user'
  readonly content: [ToolResultBlock]
  readonly source: ToolMessageSource
}
```

说明：`message.ts` 中没有独立的 `SystemMessage` 接口——system 角色只是 `Message` 的一个 `role` 分支；agent-loop 发出的系统提示文本甚至不以 `Message` 形式进入 messages 数组，而是单独放在 `GenerateOptions.system` 字段（见下文「请求装配」）。

### `MessageSource` 词汇

来源：[message.ts](../../../../packages/llm/llm/src/message.ts#L96-L126)

```ts
export interface MessageSourceMap {
  user: { kind: 'user' }
  plugin: { kind: 'plugin'; plugin: string } & ContextFormed
  model: ModelMessageSource
  tool: ToolMessageSource
}
```

### `ContentBlockMap` 与 `ContentBlock`

来源：[types.ts](../../../../packages/llm/llm/src/types.ts#L99-L110)

```ts
export interface ContentBlockMap {
  'text': TextBlock
  'reasoning': ReasoningBlock
  'image': ImageBlock
  'tool-call': ToolCallBlock
  'tool-result': ToolResultBlock
}
```

### `ToolSchema`（tools 参数的模型侧形态）

来源：[types.ts](../../../../packages/llm/llm/src/types.ts#L305-L317)

```ts
export interface ToolSchema {
  name: string
  description: string
  /** JSON Schema object for the arguments. */
  parameters: Record<string, unknown>
}
```

### `GenerateOptions`（一次完整请求）

来源：[types.ts](../../../../packages/llm/llm/src/types.ts#L319-L355)

```ts
export interface GenerateOptions {
  provider: string
  model: string
  reasoningEffort?: ReasoningEffortId
  messages: Message[]
  /** System prompt text (adapters map to the provider's system slot). */
  system?: string
  /** Tool schemas (adapters map to the provider's `tools` field). */
  tools?: ToolSchema[]
  temperature?: number
  maxTokens?: number
  stop?: string[]
  signal?: AbortSignal
  sessionId?: Branded<'SessionId'>
  purpose?: 'compaction' | 'session-title'
}
```

## PromptAssembly 的渲染（system 文本）

### `renderPrompt`

来源：[index.ts](../../../../packages/core/system-prompt/src/index.ts#L212-L217)（`@deepseek-ai/dsh-system-prompt`）

```ts
export function renderPrompt(assembly: PromptAssembly): string {
  return assembly.sections
    .map(section => interpolate(section, assembly.variables, 'section'))
    .filter(text => text.length > 0)
    .join('\n\n')
}
```

### `PromptAssembly` 结构

来源：[index.ts](../../../../packages/core/system-prompt/src/index.ts#L111-L120)

```ts
export interface PromptAssembly {
  sections: AssembledSection[]
  contexts: AssembledContext[]
  tools: ToolSchema[]
  variables: Record<string, string | undefined>
}
```

### runtime-context 快照的拼接文本

来源：[index.ts](../../../../packages/core/system-prompt/src/index.ts#L236-L240)

```ts
export function joinContextSections(sections: readonly ContextSnapshotSection[]): string {
  const body = sections.map(section => section.text).join('\n\n')
  if (body.length === 0) return ''
  return `Current runtime context. This snapshot supersedes earlier runtime-context snapshots.\n\n${body}`
}
```

## 快照 user 消息的构造

来源：[runtime-context.ts](../../../../packages/core/agent-loop/src/runtime-context.ts#L64-L75)

```ts
project(current: string, sections: readonly ContextSnapshotSection[]): UserMessage | undefined {
  if (this.retained === undefined && current.length === 0) return
  const snapshot = current.length === 0 ? CLEARED : current
  if (this.retained?.text === snapshot) return
  return createUserMessage({
    content: [{ type: 'text', text: snapshot }],
    source: sections.length === 0
      ? { kind: 'plugin', plugin: SOURCE }
      : { kind: 'plugin', plugin: SOURCE, form: 'snapshot', sections },
  })
}
```

## agent-loop：组装与消费

### `preStep`：assemble + 投影快照 + 拼接 claimed

来源：[agent.ts](../../../../packages/core/agent-loop/src/agent.ts#L225-L243)

```ts
const assembly = await this.loopCtx.systemPrompt.assemble(assembleContextFor(this, signal))
signal.throwIfAborted()
const sections = renderContextSections(assembly)
const context = this.runtimeContext.project(joinContextSections(sections), sections)
const decision = await this.dispatch.waterfall(
  'agent/pre-step', { messages: claimed, ...position, signal },
  (): Promise<PreStepDecision> => Promise.resolve<PreStepDecision>({
    kind: 'enter',
    messages: context === undefined ? claimed : [...claimed, context],
  }),
)
```

### `turn`：把 decision.messages 写入会话

来源：[agent.ts](../../../../packages/core/agent-loop/src/agent.ts#L279-L287)

```ts
for (const message of decision.messages) {
  this.session.append('user/message', message, { surfaceOp: 'append' })
}
```

### `step`：`renderPrompt(assembly)` 与请求构建

来源：[agent.ts](../../../../packages/core/agent-loop/src/agent.ts#L332-L345)

```ts
const system = renderPrompt(assembly)

while (true) {
  const { request, preparedCall } = await this.buildRequest(
    turn, step, assembly.tools, system, this.session.deriveMessages(), signal,
  )
  const assembler = new BlockAssembler()
  const chunkSeqs: number[] = []
  const stream = preparedCall?.stream(request) ?? this.loopCtx.llm.stream(request)
```

### `buildRequest`：call-config 解析与最终 request 冻结

来源：[agent.ts](../../../../packages/core/agent-loop/src/agent.ts#L419-L495)

```ts
const persistedHeader = session.requestHeader()
const persistedConfig = persistedHeader?.config
const route = { provider: this.options.provider ?? '', model: this.options.model ?? '' }
const reasoningEffort = persistedConfig?.provider === route.provider
  && persistedConfig.model === route.model
  && persistedHeader?.adapterDefaults?.reasoningEffort !== true
  ? persistedConfig.reasoningEffort
  : undefined
const maxTokens = this.options.maxTokens
const seedConfig = deepFreeze(structuredClone(
  this.requestHeaderLogged
    ? requestProposal(persistedHeader!)
    : {
      ...route,
      ...reasoningEffort === undefined ? {} : { reasoningEffort },
      ...maxTokens === undefined ? {} : { maxTokens },
    },
))
const proposedConfig = await this.dispatch.waterfall(
  'agent/request', { turn, step, signal },
  () => Promise.resolve(seedConfig),
)
```

```ts
let config: LlmCallConfig
let preparedCall: PreparedLlmCall | undefined
try {
  preparedCall = await this.loopCtx.llm.prepareCall(proposedConfig, signal)
  config = preparedCall.config
} catch (error: unknown) {
  if (!(error instanceof LlmError) || error.code !== 'NO_ADAPTER') throw error
  config = proposedConfig
}
```

```ts
const header = canonicalHeader({
  config,
  ...preparedCall === undefined ? {} : { adapterDefaults: preparedCall.adapterDefaults },
  ...system ? { system } : {},
  ...tools.length > 0 ? { tools } : {},
})
```

```ts
const request = markAgentLoopRequest(deepFreeze({
  ...header.config,
  messages: boundaryMessages,
  ...header.system !== undefined ? { system: header.system } : {},
  ...header.tools !== undefined ? { tools: header.tools } : {},
  sessionId: this.session.id,
  signal,
}))
```

### `deriveMessages`：历史 Message[] 的来源

来源：[index.ts](../../../../packages/core/session/src/index.ts#L726-L747)（`@deepseek-ai/dsh-session`）

```ts
deriveMessages(): Message[] {
  const surface = this.surface
  const nodes = surface.nodes
  const generation = surface.replaceGeneration
  if (generation !== this.derivedGeneration) {
    this.derived = []
    this.derivedNodes = 0
    this.derivedGeneration = generation
  }
  for (const seq of nodes.slice(this.derivedNodes)) {
    const msg = this.deriveEventMessage(this.log[seq]!)
    if (msg) this.derived.push(msg)
  }
  this.derivedNodes = nodes.length
  return [...this.derived]
}
```

### 工具结果消息的来源（source: tool）

来源：[tool-calls.ts](../../../../packages/core/agent-loop/src/tool-calls.ts#L276-L288)

```ts
const message = createToolResultMessage({
  callId: block.id,
  content: result.content,
  isError: result.isError,
})
session.append('tool/result', {
  turn, step,
  message,
  ...result.error?.info ? { error: result.error.info } : {},
  ...result.meta !== undefined ? { meta: result.meta } : {},
}, { surfaceOp: 'append', sourceEventSeqs: [callSeq] })
```

## LlmRuntime：流式分派

### `stream` 与 `streamWithRegistration`（llm/stream 瀑布）

来源：[index.ts](../../../../packages/llm/llm/src/index.ts#L913-L927)

```ts
stream(options: GenerateOptions): AsyncIterable<StreamChunk> {
  return this.streamWithRegistration(options)
}

private streamWithRegistration(
  options: GenerateOptions,
  prepared?: { registration: AdapterRegistration; config: LlmCallConfig },
): AsyncIterable<StreamChunk> {
  return this.ctx.waterfall(
    this,
    'llm/stream',
    options,
    () => this.adapterStream(options, prepared),
  )
}
```

### `prepareCall`：按注册快照解析调用配置

来源：[index.ts](../../../../packages/llm/llm/src/index.ts#L779-L814)

```ts
async prepareCall(config: LlmCallConfig, signal?: AbortSignal): Promise<PreparedLlmCall> {
  const registration = this.registration(config.provider)
  const resolved = await this.resolveCallFor(registration, config, signal)
  const resolvedConfig = deepFreeze(structuredClone(resolved.config))
  const context = resolved.context === undefined
    ? undefined
    : deepFreeze(structuredClone(resolved.context))
  const adapterDefaults = deepFreeze<LlmCallConfigAdapterDefaults>({
    ...config.reasoningEffort === undefined && resolvedConfig.reasoningEffort !== undefined
      ? { reasoningEffort: true }
      : {},
    ...config.maxTokens === undefined && resolvedConfig.maxTokens !== undefined
      ? { maxTokens: true }
      : {},
  })
  let dispatched = false
  return Object.freeze({
    config: resolvedConfig,
    retryPolicy: registration.retryPolicy,
    adapterDefaults,
    ...context === undefined ? {} : { context },
    stream: (options: GenerateOptions): AsyncIterable<StreamChunk> => {
      if (dispatched) {
        throw new LlmError('a prepared LLM call can only be dispatched once', 'INVALID_PREPARED_CALL')
      }
      if (!callConfigEquals(options, resolvedConfig)) {
        throw new LlmError(
          'prepared LLM call config changed before adapter dispatch',
          'INVALID_PREPARED_CALL',
        )
      }
      dispatched = true
      return this.streamWithRegistration(options, { registration, config: resolvedConfig })
    },
  })
}
```

### `adapterStream`：最终适配器边界

来源：[index.ts](../../../../packages/llm/llm/src/index.ts#L843-L865)

```ts
const registration = prepared?.registration ?? this.registration(options.provider)
const resolvedConfig = prepared === undefined
  ? (await this.resolveCallFor(registration, options, options.signal)).config
  : prepared.config
if (prepared !== undefined && !callConfigEquals(options, resolvedConfig)) {
  throw new LlmError(
    'prepared LLM call config changed before adapter dispatch',
    'INVALID_PREPARED_CALL',
  )
}
const resolvedOptions = callConfigEquals(options, resolvedConfig)
  ? options
  : Object.isFrozen(options)
    ? deepFreeze({ ...options, ...resolvedConfig })
    : { ...options, ...resolvedConfig }
const adapter = registration.adapter
const stream = adapter.stream(this.forAdapter(resolvedOptions, adapter))
iterator = stream[Symbol.asyncIterator]()
```

## DeepSeek 适配器：最终 HTTP 请求体

### `WireRequest`（线格式字段结构）

来源：[types.ts](../../../../packages/llm/llm-deepseek/src/types.ts#L12-L30)

```ts
export interface WireRequest {
  model: string
  messages: WireMessage[]
  stream: true
  stream_options: { include_usage: true }
  thinking?: { type: 'enabled' | 'disabled' }
  reasoning_effort?: 'high' | 'max'
  tools?: WireTool[]
  temperature?: number
  max_tokens?: number
  stop?: string[]
}
```

### `serializeRequest`：messages 数组 + tools 的最终线格式

来源：[serialize.ts](../../../../packages/llm/llm-deepseek/src/serialize.ts#L151-L187)

```ts
export function serializeRequest(
  options: GenerateOptions,
  defaults: RequestDefaults = {},
): WireRequest {
  const messages: WireMessage[] = []
  if (options.system !== undefined) {
    messages.push({ role: 'system', content: options.system })
  }
  messages.push(...serializeMessages(options.messages))

  const tools: WireTool[] | undefined = options.tools?.map(tool => ({
    type: 'function',
    function: {
      name: tool.name,
      description: tool.description,
      parameters: tool.parameters,
    },
  }))
  const resolvedThinking = resolveThinking(options, defaults)

  return {
    model: options.model,
    messages,
    stream: true,
    stream_options: { include_usage: true },
    ...resolvedThinking.thinking !== undefined ? { thinking: { type: resolvedThinking.thinking } } : {},
    ...resolvedThinking.reasoningEffort !== undefined
      ? { reasoning_effort: resolvedThinking.reasoningEffort }
      : {},
    ...tools !== undefined && tools.length > 0 ? { tools } : {},
    ...options.temperature !== undefined ? { temperature: options.temperature } : {},
    ...options.maxTokens === undefined ? {} : { max_tokens: options.maxTokens },
    ...options.stop !== undefined ? { stop: options.stop } : {},
  }
}
```

### `serializeMessages`：历史 Message[] 的逐条线格式

来源：[serialize.ts](../../../../packages/llm/llm-deepseek/src/serialize.ts#L112-L141)

```ts
export function serializeMessages(messages: Message[]): WireMessage[] {
  const wire: WireMessage[] = []
  for (const message of messages) {
    assertTextOnly(message.content)
    if (message.role === 'system') {
      wire.push({ role: 'system', content: flattenText(message.content) })
      continue
    }
    if (message.role === 'assistant') {
      wire.push(serializeAssistant(message))
      continue
    }
    const toolResults = message.content.filter(block => block.type === 'tool-result')
    const text = flattenText(message.content)
    if (text.length > 0 || toolResults.length === 0) {
      wire.push({ role: 'user', content: text })
    }
    for (const result of toolResults) {
      wire.push({
        role: 'tool',
        tool_call_id: result.toolCallId,
        content: flattenText(result.content) || '(no output)',
      })
    }
  }
  return wire
}
```

### `serializeAssistant`：assistant 消息（text + reasoning + tool_calls）

来源：[serialize.ts](../../../../packages/llm/llm-deepseek/src/serialize.ts#L71-L102)

```ts
function serializeAssistant(message: Message): WireMessage {
  const text = flattenText(message.content)
  const reasoning = message.content
    .filter(block => block.type === 'reasoning')
    .map(block => block.text)
    .join('')
  const toolCalls = message.content
    .filter(block => block.type === 'tool-call')
    .map(block => ({
      id: block.id,
      type: 'function' as const,
      function: { name: block.name, arguments: block.arguments },
    }))

  return {
    role: 'assistant',
    content: text,
    ...toolCalls.length > 0 && reasoning.length > 0 ? { reasoning_content: reasoning } : {},
    ...toolCalls.length > 0 ? { tool_calls: toolCalls } : {},
  }
}
```

## HTTP 传输

### `request`：fetch 与请求头

来源：[adapter.ts](../../../../packages/llm/llm-deepseek/src/adapter.ts#L279-L306)

```ts
const body = serializeRequest(options, connection.defaults)
const payload = JSON.stringify(body)
const headers = {
  'authorization': `Bearer ${apiKey}`,
  'content-type': 'application/json',
  'accept': 'text/event-stream',
  ...attributionHeaders(),
  'x-deepseek-harness-user-id': String(userId),
  ...options.sessionId !== undefined
    ? { 'x-deepseek-harness-session-id': String(options.sessionId) }
    : {},
  ...options.purpose === 'compaction'
    ? { 'x-deepseek-harness-compact': '1' }
    : {},
}
```

```ts
response = await fetch(`${connection.baseURL}/chat/completions`, {
  method: 'POST',
  headers,
  body: payload,
  signal,
})
```

## 响应侧（StreamChunk 回流）

### DeepSeek SSE → StreamChunk（`translate`）

来源：[translate.ts](../../../../packages/llm/llm-deepseek/src/translate.ts#L101-L108)

```ts
if (payload === DONE) {
  for (const block of order) {
    yield { type: 'block-end', index: block.index, block: closeBlock(block) }
  }
  if (pendingUsage) yield { type: 'usage', usage: pendingUsage }
  const reason = pendingFinish ?? { kind: 'stop' as const }
  yield {
    type: 'finish',
    reason: reason.kind === 'stop' && order.length === 0
      ? {
        kind: 'error',
        failure: { message: 'model returned a completed response with no content', code: EMPTY_RESPONSE_CODE },
      }
      : reason,
  }
  return
}
```

### `BlockAssembler`：StreamChunk → assistant Message

来源：[assembler.ts](../../../../packages/llm/llm/src/assembler.ts#L161-L163)

```ts
message(source: MessageSource = { kind: 'plugin', plugin: 'dsh-llm/assembler' }): Message {
  return createMessage({ role: 'assistant', content: this.blocks(), source })
}
```

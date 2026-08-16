# 会话日志与历史派生 —— 源码摘录

本文件是 `03-session-log-and-history-derivation.md` 的代码摘录配套，逐字转录自对应源码文件，标注来源文件与行号。正文中的引用一律指向这里的段落。

## `deriveMessages` —— 派生历史的核心遍历（[index.ts](../../../../packages/core/session/src/index.ts#L726)）

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
      // Surface sequences are built from this.log — seq is always a valid
      // index by construction. The non-null assertion expresses that invariant.
      // oxlint-disable-next-line typescript/no-non-null-assertion
      const msg = this.deriveEventMessage(this.log[seq]!)
      // A surface node is one of the five message-producing types, but an
      // empty-content assistant/message (a max-tokens step that hosts only
      // usage) derives to null and must not enter the transcript.
      if (msg) this.derived.push(msg)
    }
    this.derivedNodes = nodes.length
    return [...this.derived]
  }
```

`index.ts:726-747`。缓存字段声明于 `index.ts:701-706`（`derived` / `derivedNodes` / `derivedGeneration`）。

## `deriveEventMessage` —— THE per-node projection rule（[surface.ts](../../../../packages/core/session/src/surface.ts#L83)）

```ts
export function deriveEventMessage(event: SessionEvent): Message | null {
  // Intentionally non-exhaustive: only message-producing events derive
  // history; turn/step boundaries, chunks, usage, and errors are trace/replay
  // data.
  switch (event.type) {
    // Ordinary prompts and injected context project in user role: the event's
    // model-facing content stays verbatim. Do NOT re-add per-type framing
    // (e.g. `<context>`) here: framing is caller-owned — a producer bakes it
    // into `content`, as agent-instructions does with `<system-reminder>` — or,
    // if reintroduced, must be driven by the event `meta` map and a dedicated
    // renderer, keeping this projection a verbatim pass-through. See the
    // deferred design note in
    // ../../../../.agents/notes/implemented/simplification/2026-07-20-unwrap-injected-content-envelopes.md
    case 'user/message': {
      return event.data
    }
    case 'assistant/message': {
      // Skip an empty-content assistant/message: it exists only to host a
      // max-tokens step's usage and must not inject a content-less assistant
      // turn into the provider transcript.
      if (event.data.message.content.length === 0) return null
      return event.data.message
    }
    case 'tool/result': {
      return event.data.message
    }
    default:
      // A non-surface event (boundary, chunk, log-only record) projects to
      // no message. Merge-extensible union: no assertNever here.
      return null
  }
}
```

`surface.ts:83-114`。辅助谓词：`isSurfaceEligibleType`（[surface.ts:26](../../../../packages/core/session/src/surface.ts#L26)）、`isSurfaceEvent`（[surface.ts:35](../../../../packages/core/session/src/surface.ts#L35)）、`isAppendSurfaceEvent`（[surface.ts:51](../../../../packages/core/session/src/surface.ts#L51)）、`isReplacementSurfaceEvent`（[surface.ts:64](../../../../packages/core/session/src/surface.ts#L64)）。

## Surface 折叠 —— 完整回放与增量管理器（[surface.ts](../../../../packages/core/session/src/surface.ts#L350)）

```ts
/** Apply one event and return replacement metadata only when one occurred. */
function applySurfaceEvent(
  state: SurfaceFoldState,
  event: SessionEvent,
  expectedSeq: number,
  events: readonly SessionEvent[],
  baseSeq: number,
): SurfaceFoldReplacement | undefined {
  const plan = planSurfaceEvent(state, event, expectedSeq, events, baseSeq)
  return applySurfacePlan(state, plan)
}
```

```ts
/** Commit one previously validated surface transition. */
function applySurfacePlan(
  state: SurfaceFoldState,
  plan: SurfacePlan | undefined,
): SurfaceFoldReplacement | undefined {
  if (plan?.kind === 'append') {
    state.nodes.push(plan.seq)
  } else if (plan?.kind === 'replace') {
    state.nodes.splice(plan.startIdx, plan.endIdx - plan.startIdx + 1, plan.seq)
    state.replaceGeneration += 1
  }
  if (plan?.kind !== 'replace') return
  return {
    seq: plan.seq,
    start: plan.start,
    end: plan.end,
    shadowedSeqs: plan.shadowedSeqs,
  }
}
```

`surface.ts:350-379`。替换范围定位 `replacementRange`（[surface.ts:246](../../../../packages/core/session/src/surface.ts#L246)）、来源引用校验 `assertProvenance`（[surface.ts:211](../../../../packages/core/session/src/surface.ts#L211)）、tool/result 重写限制 `assertToolResultRewrite`（[surface.ts:287](../../../../packages/core/session/src/surface.ts#L287)）。

```ts
export function foldSurface(events: readonly SessionEvent[]): SurfaceFoldResult {
  const state = createFoldState()
  const replacements: SurfaceFoldReplacement[] = []
  for (const [index, event] of events.entries()) {
    const replacement = applySurfaceEvent(state, event, index, events, 0)
    if (replacement !== undefined) replacements.push(replacement)
  }
  return { nodes: [...state.nodes], replacements }
}
```

`surface.ts:387-395`。增量 `SurfaceManager`（[surface.ts:398](../../../../packages/core/session/src/surface.ts#L398)）：`validateNext` 在事件进入 log 前校验候选（[surface.ts:421](../../../../packages/core/session/src/surface.ts#L421)），`nodes` / `replaceGeneration` 访问时推进 `_processDelta`（[surface.ts:438](../../../../packages/core/session/src/surface.ts#L438)、[surface.ts:444](../../../../packages/core/session/src/surface.ts#L444)）。

## 请求头 —— 规范化、比较、折叠（[request-header.ts](../../../../packages/core/session/src/request-header.ts#L21)）

```ts
export function canonicalHeader(header: EpochHeader): EpochHeader {
  const adapterDefaults = header.adapterDefaults
  return {
    config: header.config,
    ...adapterDefaults?.reasoningEffort === true || adapterDefaults?.maxTokens === true
      ? { adapterDefaults }
      : {},
    ...header.system !== undefined && header.system.length > 0 ? { system: header.system } : {},
    ...header.tools !== undefined && header.tools.length > 0 ? { tools: header.tools } : {},
  }
}
```

`request-header.ts:21-31`。`headerEquals`（[request-header.ts:44](../../../../packages/core/session/src/request-header.ts#L44)）对规范形做逐字段比较（config、adapterDefaults 标记、system、按序 tools）。

```ts
export function foldRequestHeader(events: readonly SessionEvent[], from?: EpochHeader): EpochHeader | undefined {
  let state = from
  for (const event of events) {
    if (event.type === 'request/header') state = canonicalHeader(event.data.header)
  }
  return state
}
```

`request-header.ts:65-71`。

## Session 上的增量折叠（[index.ts](../../../../packages/core/session/src/index.ts#L670)）

```ts
  requestHeader(): EpochHeader | undefined {
    if (this.headerFoldSeq < this.log.length) {
      // Frozen on update: the fold is session state exposed by reference — a
      // consumer mutating it in place (instead of building a replacement)
      // would desync every later comparison against the log, so mutation
      // throws instead.
      this.headerFold = deepFreeze(foldRequestHeader(this.log.slice(this.headerFoldSeq), this.headerFold))
      this.headerFoldSeq = this.log.length
    }
    return this.headerFold
  }
```

`index.ts:670-680`。`requestContext()` 的增量折叠（[index.ts:691](../../../../packages/core/session/src/index.ts#L691)）只取最新的 `request/context` 快照。

## 种子与 `session/end-seed` 标记（[index.ts](../../../../packages/core/session/src/index.ts#L508)）

```ts
    if (seed !== undefined) {
      // Validate the seed to the SAME invariants `append` enforces, so a
      // replay/fork (`ctx.sessions.create(id, { seed })`) cannot construct a
      // live log that no persistence backend could store: each event's `data`
      // must be JSON-serializable, and `seq` must be contiguous from 0 (the
      // `seq = log.length` contract the whole system relies on). Without this,
      // a bad seed would surface only later as a backend rejection or a silent
      // divergence between the live log and disk.
      for (const [index, source] of seed.entries()) {
        // The seed is a persistence/replay boundary: validate and detach the
        // complete event in one lossless-JSON pass.
        const snapshot = mode === 'restore' ? source : snapshotJsonValue(source)
        if (snapshot === undefined) {
          throw new Error(`seed event at index ${index} is not losslessly JSON-serializable`)
        }
        assertSessionEventEnvelope(snapshot, index)
        assertSupportedRequestHeader(snapshot.type, snapshot.data, `seed event at index ${index}`)
        if (snapshot.seq !== index) {
          throw new Error(`seed event at index ${index} has seq ${snapshot.seq} (expected ${index}); seed must be contiguous from 0`)
        }
        // A seed is accepted incrementally through the same transition as a
        // live append and a full-log fold. The candidate is planned before it
        // enters `log`, so a failure cannot partially mutate the surface.
        try {
          this.surfaceManager.validateNext(snapshot)
        } catch (error: unknown) {
          throw new Error(`invalid seed event at index ${index}: ${error instanceof Error ? error.message : 'invalid surface metadata'}`)
        }
        this.log.push(mode === 'restore' ? freezeRestoredObject(snapshot) : deepFreeze(snapshot))
      }
    }
    this.firstLiveSeq = this.log.length
    this.header = restoredHeader ?? snapshotSessionHeader(id, header)
    // Appended here so the marker is already in `events` when a backend
    // captures the creation seed: no load-time write. Re-marking is skipped
    // because a cold session is resumed on first touch, so repeatedly opening
    // one must not grow its log per open.
    if (seed !== undefined && this.log.at(-1)?.type !== 'session/end-seed') {
      this.append('session/end-seed', {})
    }
```

`index.ts:508-548`。恢复路径 `Session.fromRestore`（[index.ts:495](../../../../packages/core/session/src/index.ts#L495)）。

## Fork —— 前缀切片与校验（[index.ts](../../../../packages/core/session/src/index.ts#L1097)）

```ts
  private _forkSeed(session: Session, requestedBoundary: number | undefined): SessionEvent[] {
    const events = session.events
    const lastEvent = events.at(-1)
    let boundary: number
    if (requestedBoundary !== undefined) {
      boundary = requestedBoundary
    } else {
      if (lastEvent === undefined) return []
      boundary = lastEvent.seq
    }
    if (!Number.isSafeInteger(boundary) || boundary < 0) {
      throw new SessionForkError(
        `fork boundary for session "${session.id}" must be a non-negative safe integer, got ${String(boundary)}`,
        'INVALID_BOUNDARY',
      )
    }
    if (boundary >= events.length) {
      const lastSeq = events.at(-1)?.seq
      throw new SessionForkError(
        `fork boundary ${boundary} does not exist in session "${session.id}" (last seq: ${lastSeq ?? 'none'})`,
        'INVALID_BOUNDARY',
      )
    }

    const boundaryEvent = events[boundary]
    if (boundaryEvent === undefined || boundaryEvent.seq !== boundary) {
      throw new SessionForkError(
        `fork boundary ${boundary} does not match a contiguous event seq in session "${session.id}"`,
        'INVALID_BOUNDARY',
      )
    }
    const lastTurnBoundary = events.slice(0, boundary + 1)
      .findLast(event => event.type === 'turn/start' || event.type === 'turn/end')
    if (lastTurnBoundary?.type === 'turn/start') {
      throw new SessionForkError(
        `fork boundary ${boundary} in session "${session.id}" ends inside open turn ${lastTurnBoundary.data.turn}`,
        'OPEN_TURN',
      )
    }

    return events.slice(0, boundary + 1)
  }
```

`index.ts:1097-1138`。公开入口 `SessionStore.fork`（[index.ts:1081](../../../../packages/core/session/src/index.ts#L1081)）把切片作为 `seed` 创建子会话并写入 `parentSession` / `seedLength` 元数据。

## agent-loop 的调用与消费（[agent.ts](../../../../packages/core/agent-loop/src/agent.ts#L340)）

```ts
      const { request, preparedCall } = await this.buildRequest(
        turn, step, assembly.tools, system, this.session.deriveMessages(), signal,
      )
```

`agent.ts:340-342`。`assistant/message` 的写入（[agent.ts:373](../../../../packages/core/agent-loop/src/agent.ts#L373)）把本次流的全部 chunk seq 作为 `sourceEventSeqs`：

```ts
      const message = createAssistantMessage({
        content: assembler.blocks(),
        source: {
          provider: request.provider,
          model: request.model,
          ...assembler.replayState !== undefined ? { replayState: assembler.replayState } : {},
        },
      })
      this.session.append(
        'assistant/message',
        {
          turn,
          step,
          message,
          ...assembler.usage === undefined ? {} : { usage: assembler.usage },
        },
        { surfaceOp: 'append', sourceEventSeqs: chunkSeqs },
      )
```

`agent.ts:373-390`。`request/header` 的写入与 reason（[agent.ts:458](../../../../packages/core/agent-loop/src/agent.ts#L458)）：

```ts
    const header = canonicalHeader({
      config,
      ...preparedCall === undefined ? {} : { adapterDefaults: preparedCall.adapterDefaults },
      ...system ? { system } : {},
      ...tools.length > 0 ? { tools } : {},
    })
    const baseline = this.session.requestHeader()
    if (!this.requestHeaderLogged) {
      this.session.append('request/header', { header, reason: baseline === undefined ? 'initial' : 'resume' })
      this.requestHeaderLogged = true
    } else if (baseline === undefined || !headerEquals(baseline, header)) {
      this.session.append('request/header', { header, reason: 'change' })
    }
```

`agent.ts:458-470`。`request/context` 仅在路由或容量变化时写入（[agent.ts:472](../../../../packages/core/agent-loop/src/agent.ts#L472)）。

## runtime-context 投影（[runtime-context.ts](../../../../packages/core/agent-loop/src/runtime-context.ts#L64)）

```ts
  project(current: string, sections: readonly ContextSnapshotSection[]): UserMessage | undefined {
    if (this.retained === undefined && current.length === 0) return
    const snapshot = current.length === 0 ? CLEARED : current
    if (this.retained?.text === snapshot) return
    return createUserMessage({
      content: [{ type: 'text', text: snapshot }],
      // The cleared marker has no contributions left to attribute.
      source: sections.length === 0
        ? { kind: 'plugin', plugin: SOURCE }
        : { kind: 'plugin', plugin: SOURCE, form: 'snapshot', sections },
    })
  }
```

`runtime-context.ts:64-75`。`SOURCE` 与清空标记（[runtime-context.ts:12](../../../../packages/core/agent-loop/src/runtime-context.ts#L12)）：

```ts
const SOURCE = '@deepseek-ai/dsh-system-prompt'
const CLEARED = 'Current runtime context: none. Earlier runtime-context snapshots no longer apply.'
```

`runtime-context.ts:12-13`。`preStep` 中把候选追加进决策消息（[agent.ts:233](../../../../packages/core/agent-loop/src/agent.ts#L233)），随后在 [agent.ts:282](../../../../packages/core/agent-loop/src/agent.ts#L282) 逐条 `append('user/message', …, { surfaceOp: 'append' })`。

# Compaction 关键源码摘录

以下为压缩事务落日志与日志投影跳过被压缩区域的逐字摘录。出处均标注文件与行号；`ts ignore-check` 块因为引用块外类型而不参与 doc-typecheck 编译，内容与源码逐字一致。

## 1. checkpoint 落日志：compaction/summary + user/message replace

[region.ts](../../../../packages/compaction/compaction-basic/src/region.ts#L448)（`commitCompactionBody`，第 427–478 行）——先追加 `compaction/summary` 记账事件，再同步追加携带 `compactCheckpointSource` 的 `user/message` 替换：

```ts ignore-check
  const summaryEvent = session.append('compaction/summary', {
    compactionId: startEvent.data.compactionId,
    ...startEvent.data.sourceCommandId === undefined
      ? {}
      : { sourceCommandId: startEvent.data.sourceCommandId },
    summary,
    ...callProvenance,
    shadowedRange: { start, end },
    shadowedSeqs: [...shadowedSeqs],
    shadowedTokenCount,
    provider,
    model,
    ...maxTokens === undefined ? {} : { maxTokens },
    ...usage === undefined ? {} : { usage },
  })
  session.append('user/message', checkpointMessage, {
    surfaceOp: { op: 'replace', start, end },
    sourceEventSeqs: [startEvent.seq, summaryEvent.seq, ...shadowedSeqs],
  })
```

`checkpointMessage` 在 `summarizeCompaction` 中构造：`createUserMessage({ content: frameSummary(summaryResult.summary), source: compactCheckpointSource(compactionId, sourceCommandId) })`（[region.ts#L369](../../../../packages/compaction/compaction-basic/src/region.ts#L369)）。

## 2. checkpoint source：compactCheckpointSource

[checkpoint.ts](../../../../packages/compaction/compaction/src/checkpoint.ts#L33)：

```ts ignore-check
export function compactCheckpointSource(
  compactionId: CompactionId,
  sourceCommandId?: CommandId,
): CompactionCheckpointSource {
  return Object.freeze({
    ...COMPACT_CHECKPOINT_MARKER,
    compactionId,
    ...sourceCommandId === undefined ? {} : { sourceCommandId },
  })
}
```

`COMPACT_CHECKPOINT_MARKER = Object.freeze({ kind: 'plugin', plugin: 'compact' } as const)`（[checkpoint.ts#L19](../../../../packages/compaction/compaction/src/checkpoint.ts#L19)）；识别谓词 `isCompactCheckpointSource` 只检查 `source.kind === 'plugin' && source.plugin === 'compact'`（[checkpoint.ts#L49](../../../../packages/compaction/compaction/src/checkpoint.ts#L49)）。

## 3. 投影入口：Session.deriveMessages

[core/session/src/index.ts](../../../../packages/core/session/src/index.ts#L726)：

```ts ignore-check
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

方法 JSDoc 写明“a compaction `replace` deletes the shadowed nodes from the derivation”（[index.ts#L713](../../../../packages/core/session/src/index.ts#L713)）。

## 4. surface 折叠的 replace 分支：applySurfacePlan

[core/session/src/surface.ts](../../../../packages/core/session/src/surface.ts#L362)——replace 把 `[startIdx, endIdx]` 整段节点从 surface 移除并插入替换事件自身的 seq，同时令 `replaceGeneration` 自增：

```ts ignore-check
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

## 5. 逐节点投影：deriveEventMessage

[core/session/src/surface.ts](../../../../packages/core/session/src/surface.ts#L83)：

```ts ignore-check
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
    // renderer, keeping this projection a verbatim pass-through.
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

`compaction/*` 事件走 `default` 分支投影为 `null`，永远不进入模型请求（[surface.ts#L109](../../../../packages/core/session/src/surface.ts#L109)）。

## 6. 压缩区间选择：selectCompactableRange

[region.ts](../../../../packages/compaction/compaction-basic/src/region.ts#L98)：

```ts ignore-check
export function selectCompactableRange(
  session: Session,
  measurement: TokenMeasurement,
  retainTokens: number,
): { start: number; end: number } | null {
  const pricedNodes = measurement.nodes
  if (pricedNodes.length === 0) return null

  const surfaceNodes = session.surface.nodes
  if (surfaceNodes.length !== pricedNodes.length
    || surfaceNodes.some((seq, index) => seq !== pricedNodes[index]?.seq)) {
    throw new Error('compaction: token-meter surface does not match the current session surface')
  }

  let accumulated = 0
  let keepFromIdx = pricedNodes.length
  for (let index = pricedNodes.length - 1; index >= 0; index -= 1) {
    // oxlint-disable-next-line typescript/no-non-null-assertion
    accumulated += pricedNodes[index]!.tokens
    keepFromIdx = index
    if (accumulated >= retainTokens) break
  }
  if (keepFromIdx === 0) return null

  while (keepFromIdx > 0) {
    // oxlint-disable-next-line typescript/no-non-null-assertion
    if (toolPairingBalancedBefore(session, surfaceNodes[keepFromIdx]!)) break
    keepFromIdx -= 1
  }
  if (keepFromIdx === 0) return null

  // oxlint-disable-next-line typescript/no-non-null-assertion
  const first = surfaceNodes[0]!
  // oxlint-disable-next-line typescript/no-non-null-assertion
  const cutoff = surfaceNodes[keepFromIdx - 1]!
  return { start: first, end: cutoff }
}
```

## 7. 模型无关修剪的替换：pruneSession

[compaction-tool-result-pruner/src/index.ts](../../../../packages/compaction/compaction-tool-result-pruner/src/index.ts#L136)——先追加 `compaction/prune` 阴影价格事件，再追加 `tool/result` 替换：

```ts ignore-check
      // Shadow-price protocol: the metering event and its replacement are
      // appended synchronously adjacent, so pure consumers subtract the
      // shadowed node's heuristic price without retaining per-node state.
      session.append('compaction/prune', {
        shadowedRange: { start: seq, end: seq },
        shadowedSeqs: [seq],
        shadowedTokenCount: this.ctx.tokenMeter.estimateMessage(event.data.message),
      })
      const replacement = session.append('tool/result', {
        ...event.data,
        message,
      }, {
        surfaceOp: { op: 'replace', start: seq, end: seq },
        sourceEventSeqs: [seq],
      })
```

被剪掉的中间段替换成 `PRUNE_MARKER = '\n\n[... tool result middle pruned ...]\n\n'`（[config.ts#L7](../../../../packages/compaction/compaction-tool-result-pruner/src/config.ts#L7)），默认预算 `thresholdChars = 8192`、`headChars = 4096`、`tailChars = 1024`（[config.ts#L10](../../../../packages/compaction/compaction-tool-result-pruner/src/config.ts#L10)）。

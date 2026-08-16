# harness:identity —— Harness 身份槽位

`harness:identity` 是插件 `SystemPrompt` 构造时默认注册的固定开头段，来源仅在 [`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L357) 的构造路径。

## 逐字文本

```markdown
You are an AI agent powered by DeepSeek Harness.
```

## 注册细节

- name：`'harness:identity'`（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L359)）。
- order：`-100`（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L360)），即文档约定的 harness 身份序带（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L57)）。
- text：静态字符串 `'You are an AI agent powered by DeepSeek Harness.'`（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L361)），非函数、不引用任何变量。

## 启用与关闭

仅当 `config.includeHarnessIdentity ?? true` 为真时注册（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L357)）；schema 默认值为 `true`（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L340)）。置 `false` 仅省略该固定开头，供完全自持提示的部署使用（[system-prompt.spec.ts](../../../../packages/core/system-prompt/tests/system-prompt.spec.ts#L40)）。

## 归属与遮蔽

本插件拥有 `harness:identity` 与 `deployment:persona` 两个槽位（[README](../../../../packages/core/system-prompt/README.md)）；同一名字在同一层重复注册抛错（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L316)）。它是全局段，可在作用域层被同名段遮蔽（[`index.ts`](../../../../packages/core/system-prompt/src/index.ts#L484)）。

正文：[01-system-prompt-registry.md](../01-system-prompt-registry.md)

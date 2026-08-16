# time-context 原文模板

> 模板逐字摘自 [index.ts](../../../../packages/context/time-context/src/index.ts)（`@deepseek-ai/dsh-time-context`）。`${…}` 为每次注入时刻 JS 模板插值，包内不使用 `{{variable}}`。最终注入消息 source `{ kind: 'plugin', plugin: 'time-context', form: 'snapshot', sections: [{ name: 'time-context', text }] }`（[index.ts](../../../../packages/context/time-context/src/index.ts#L204) L204）。

## 读数全文

`renderText`（[index.ts](../../../../packages/context/time-context/src/index.ts#L110) L110-L125），三行文本：

```text
Time sampled while preparing turn {turn}, step {step}: {formatTimestamp(now, formatter, timeZone)}
{Browser time zone for this request: …}
Elapsed since the preceding {model-visible message | step context}: {unavailable | formatDuration(now - previous)}.
```

- `baseline`（L120）：`step === 1` 时 `model-visible message`，否则 `step context`。
- `elapsed`（L119）：`previous === undefined` 时为字面 `unavailable`，否则 `formatDuration` 结果。

## 时间戳

`formatTimestamp`（[timestamp.ts](../../../../packages/context/time-context/src/timestamp.ts#L31) L31-L37），ISO 形：

```text
{YYYY}-{MM}-{DD}T{HH}:{mm}:{ss}{offset}[{timeZone}]
```

- `offset` 来自 `timeZoneName`（`GMT` 先规整为 `GMT+00:00` 再去掉 `GMT` 前缀，得 `+00:00` 或 `+08:00` 形）。
- `timeZone` 为 canonical IANA 区名（如 `Asia/Shanghai`、`UTC`）。

## 耗时格式化

`formatDuration`（[index.ts](../../../../packages/context/time-context/src/index.ts#L41) L41-L55），整秒、紧凑复合单位，至少带 `{n}s`：

```text
{d}d {h}h {m}m {s}s
```

例如 `1d 2h 3m 4s`、`45s`。

## 浏览器时区行（三态）

`renderBrowserTimeZoneContext`（[request-zone.ts](../../../../packages/context/time-context/src/request-zone.ts#L66) L66-L80）：

`resolved`：

```text
Browser time zone for this request: {timeZone}. Interpret otherwise-unqualified dates and times in this zone.
```

`mixed`：

```text
Browser time zone for this request: mixed [{tz1}, {tz2}]. Ask the user to clarify otherwise-unqualified dates and times.
```

`missing`：

```text
Browser time zone for this request: unavailable. Ask the user to clarify otherwise-unqualified dates and times.
```

## 来源行号速查

- 读数全文：`renderText` index.ts L110-L125
- 时间戳：`formatTimestamp` timestamp.ts L31-L37；`createTimestampFormatter` timestamp.ts L10-L22
- 耗时：`formatDuration` index.ts L41-L55
- 浏览器时区：`deriveBrowserTimeZoneContext` request-zone.ts L48-L59；`renderBrowserTimeZoneContext` L66-L80
- 消息构建：index.ts L198-L207
- 格式校验正则：invariant.ts L14-L20

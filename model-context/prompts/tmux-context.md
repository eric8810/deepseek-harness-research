# tmux-context 原文模板

> 模板逐字摘自 [index.ts](../../../../packages/context/tmux-context/src/index.ts)（`@deepseek-ai/dsh-tmux-context`）。`${…}` 为每次注入时刻 JS 模板插值，包内不使用 `{{variable}}`。最终注入消息 source `{ kind: 'plugin', plugin: 'tmux-context', form: 'snapshot', sections: [{ name: 'tmux-context', text }] }`（[index.ts](../../../../packages/context/tmux-context/src/index.ts#L241) L241）。

## 读数全文

`renderReading`（[index.ts](../../../../packages/context/tmux-context/src/index.ts#L171) L171-L173）= 易变前缀 `tmux location (turn {turn}):` + 换行 + 稳定状态块：

```text
tmux location (turn {turn}):
{sessionName…稳定状态块}
```

`READING_PREFIX` 常量（L73）为 `tmux location (turn `，`renderReading` 在其后接 `{turn}):`。

## 稳定状态块

`renderState`（[index.ts](../../../../packages/context/tmux-context/src/index.ts#L162) L162-L168），两行，变化抑制只比较此块：

```text
session {sessionName}, window {windowIndex} {JSON.stringify(windowName)}, pane {paneIndex} {paneId}
window active={windowActive}, pane active={paneActive}, layout {windowLayout}
```

`windowName` 经 `JSON.stringify` 序列化（带引号与转义）。

## 字段来源（tmux 格式）

`TMUX_FIELDS`（L49-L58），`display-message` 按序取八个字段，`\t` 分隔（`FIELD_SEP`，L80）：

```text
#{session_name}  #{window_index}  #{window_name}  #{pane_index}  #{pane_id}  #{window_active}  #{pane_active}  #{window_layout}
```

`window_layout` 为 pane-tree 描述；pane/window 像素尺寸按包范围排除（L45-L48 注释）。

## 查询命令（只读 bash，经 `ctx.shell`）

`queryTmuxLocation` 的命令体（L114-L121），逐行：

```bash
[ -n "$TMUX_PANE" ] || exit 1
self_tty=$(ps -o tty= -p {processId} | tr -d ' ')
[ -n "$self_tty" ] || exit 1
pane_tty=$(tmux display-message -t "$TMUX_PANE" -p '#{pane_tty}') || exit 1
[ "$pane_tty" = "/dev/$self_tty" ] || exit 1
exec tmux display-message -t "$TMUX_PANE" -p '{八字段 \t 分隔格式}'
```

只有本进程控制 tty 与 pane 的 `#{pane_tty}` 一致时才输出字段（L117-L119），仅继承 `$TMUX`/`$TMUX_PANE` 的环境读取为"不在 tmux"，注入为空。

## 来源行号速查

- 读数全文：`renderReading` L171-L173；`READING_PREFIX` L73
- 稳定状态块：`renderState` L162-L168
- 字段：`TMUX_FIELDS` L49-L58；`FIELD_SEP` L80
- 查询：`queryTmuxLocation` L107-L155；命令体 L114-L121
- 变化抑制：`latestInjectedState` L181-L194
- 消息构建：index.ts L236-L245

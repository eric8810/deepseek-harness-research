# 15 —— 修改触发面与重载范围：什么改动重启什么

本页回答：编辑代码/配置/动态包时，重启范围如何划分；基础模块是否都要重启；动态插件能否覆盖静态声明；UI 变更经由什么通道。级联传播机制（fiber epoch）见 [14-cordis-restart-cascade-and-context.md](14-cordis-restart-cascade-and-context.md)，本页只负责「入口分类」。

## 一、六条修改通道与重载范围

| 修改对象 | 重载范围 |
|---|---|
| 启动链：`apps/cli/` 及其 import 图在 `node_modules` 之外能到达的所有模块（`packages/boot/`、`vendor/` 框架、它们静态引入的工作区包） | 整体重启请求。HMR 在启动时把这些模块归类为 CLI 入口的 externals——`process.argv[1]` 的依赖树，排除 `node:` 内建与 `/node_modules/`（[`vendor/hmr/src/index.ts#L218`](../../../vendor/hmr/src/index.ts#L218)）；改动落入该集合即调 `loader.exit()`（[`vendor/hmr/src/index.ts#L259`](../../../vendor/hmr/src/index.ts#L259)）。该钩子默认为空实现，由宿主决定是否真重启进程（[`vendor/loader/src/index.ts#L188`](../../../vendor/loader/src/index.ts#L188)）。注意：此路径只在模块 HMR 活跃时存在，而 shipped 配置下它并不活跃（见下行） |
| `cordis.yml` 条目挂载的插件模块（`@deepseek-ai/dsh-*` 业务包） | HMR 部分重载：文件在 ESM/CJS loadCache 中且依赖分析判定 accepted → 备份并清模块缓存、重新 import 插件入口文件、`registry.delete` 后原位重建该插件的 fiber，import 或 apply 失败回滚缓存与旧注册（[`vendor/hmr/src/index.ts#L400`](../../../vendor/hmr/src/index.ts#L400)）。但两个 shipped 组合包都禁用了 `hmr` 条目（web：[`packages/bundle/web-app/cordis.patch.yml#L22`](../../../packages/bundle/web-app/cordis.patch.yml#L22)；headless：[`packages/bundle/headless/cordis.patch.yml#L14`](../../../packages/bundle/headless/cordis.patch.yml#L14)），且 HMR 服务构造时要求 `--expose-internals`（[`vendor/hmr/src/index.ts#L121`](../../../vendor/hmr/src/index.ts#L121)），而该 flag 由 Node 的 `execArgv` 门控（[`vendor/loader/src/internal.ts#L110`](../../../vendor/loader/src/internal.ts#L110)）、dsh CLI 不传——因此模块级热路径仅存在于自定义 profile（保留 base 的 `hmr` 行 + 以 `--expose-internals` 启动） |
| profile 的 `cordis.patch.yml` 或 `$DSH_HOME/cordis.patch.yml` | 事务性配置重载，所有界面（含 web）：`include.refresh()`/`entry.update()` 只重启重排后 patch 栈发生变化的条目，被拒的刷新保留上一棵好树（[`apps/cli/src/profile-boot.ts#L285`](../../../apps/cli/src/profile-boot.ts#L285)；回滚语义测试 [`packages/boot/app-boot/tests/config-reload.spec.ts`](../../../packages/boot/app-boot/tests/config-reload.spec.ts)）。失败按阶段分类：import 失败保留旧插件、apply 失败恢复上一代 fiber、多行变更整树回滚——但坏 patch 仍在磁盘，下次冷启动 fail loud。`--patch` overlay 与组合包的 `cordis.patch.yml` 是启动输入，不受监视 |
| `$DSH_HOME/settings.yaml` | 零重载：settings 服务实时读取该文档（web 模型页负责写入），连条目级重启都不发生 |
| `packages/client/` 客户端插件源码，同时运行开发重建 watcher（`pnpm run dev:web`） | 浏览器侧 HMR：watcher 重写 bundle，页面按 `invalidate → prefetch → registry.delete → 排空旧 fiber → 重 import 重挂载` 序列重载单个插件，依赖方经激活 epoch 级联（[`packages/client/hmr/README.md`](../../../packages/client/hmr/README.md)）。宿主进程不重启 |
| 动态包（`cordis_run`/`cordis_stop`/`cordis_undefine`） | 零重载：host half 在 `node:vm` 沙箱求值后挂到 `cordis-dynamic` group fiber 旁，stop 只 drop handlers + dispose 该 fiber 至静默。定义仅存进程内存，不写盘、重启即失（[`packages/extensions/cordis-host-runner/README.md`](../../../packages/extensions/cordis-host-runner/README.md)） |

## 二、基础模块是不是都得重启

下文称启动链为 A 组、cordis.yml 行挂载的业务插件为 B 组。不是。externals 不是「全部基础模块」的固定名单，而是入口 import 图的计算结果：CLI 入口静态引入的只有启动链（`apps/cli`、app-boot、cmdline、vendor 框架及它们直接 import 的工作区包）；`dsh-llm`、`dsh-session`、`dsh-tools` 等业务插件由 loader 按 cordis.yml 行在运行时动态加载，不在入口 import 图里，改它们理论上走部分重载（loadCache 路径）。但见第一表：模块级热路径在 shipped 配置（web 与 headless 均禁 `hmr` 行、dsh CLI 不传 `--expose-internals`）下并不激活，因此**当前仓库里改任何主机侧插件源码，实际出路都只有重启进程**；配置热重载、settings 与动态包不受影响。

## 三、动态插件能覆盖原始声明吗

不能。同一 realm 下服务已被提供时 `provide` 直接抛错（`service "x" has been registered at <fiber>`，[`vendor/cordis/src/reflect.ts#L290`](../../../vendor/cordis/src/reflect.ts#L290)）；沙箱 façade 暴露的 `provide`（[`packages/extensions/cordis-host-runner/src/guard.ts#L636`](../../../packages/extensions/cordis-host-runner/src/guard.ts#L636)）同样受此约束。动态包只能：

- 提供新 key 的服务、注册新工具/监听器/提示词片段；
- 在 UI 座位上遮蔽出厂组件（第四节）。

替换静态声明（换 provider、开关某行）的唯一通道是组合层：patch 按 id 整行替换 config，可改 `name` 指向替代模块、`disabled: true` 关掉原行再插新行——即第一表的第三行通道，事务性、失败回滚。

## 四、UI 变更通道

UI 变更 = 双半包的 browser half + slots 座位：

1. `cordis_run` 求值 host half 后发 `cordis/request-run`，应答页面经 `getClientCode` 取 browser half 源码（代码不上广播，这是它唯一送达浏览器的路径）。
2. 页面把源码作 async 函数体求值（参数面 `React`/`console`/`styles`/`host`），经 guard 白名单代理通过 `loader.create` 挂成活浏览器插件（[`packages/extensions/cordis-client-runner/README.md`](../../../packages/extensions/cordis-client-runner/README.md)）。
3. 落点：`slots.register` 把 React 组件坐进 `SlotMap` 声明的座位（single/list/keyed/chain；root/session-maybe/session）。注册即遮蔽——browser half 的优先级低于所有 shipped 条目，所以新注册就是渲染的那个；`theme` 座位挂按包 id 固定的样式覆盖层；stop 卸载后 shipped UI 原样恢复。渲染期崩溃由 `slots.onEntryError` 上报，遮蔽座位的崩溃把条目退休、恢复出厂 UI。
4. 模型可注册面 = 生成式 client slot 目录（`cordis_inspect what:"client"`，42 个 shipped 座位：`root`、`conversation` 系、`sidebar`、`details`、`settings.*`、`shell.overlay` 等，[`packages/extensions/cordis-client-runner/src/client/slot-catalog.ts`](../../../packages/extensions/cordis-client-runner/src/client/slot-catalog.ts)）。目录之外的注册（未声明座位、路由、应用框架）被 guard 拒绝：路由与框架是静态客户端插件，不是 slot 座位，改它们属于常规开发变更而非动态包能力。

## 五、要点

1. 重启范围由「文件在哪张图上」决定，不是由「是否核心」决定：入口 import 图（externals）= 整体重启请求；loadCache（插件模块）= 部分重载；补丁层 = 事务性条目重载；动态包 = 零重载。
2. 模块级热路径（externals 重启请求与 loadCache 部分重载）在 shipped 配置下均未激活：web 与 headless 都禁用了 `hmr` 行，且 HMR 服务要求 `--expose-internals` 而 dsh CLI 不传；要启用需自定义 profile 保留 `hmr` 行并以该 flag 启动。配置热重载与动态包不受影响。因此 shipped 配置下任何源码文件的内容修改都只能靠冷启动生效；唯一例外是 patch 换行首次引入的新模块文件（从未被 import 过）会被热 import，之后再改同一文件同样需要冷启动。
3. 动态包「添加」而非「替换」：重复 `provide` 抛错是框架级硬约束，覆盖静态声明只能走组合层 patch。
4. UI 的可改面 = 42 个声明座位；路由与应用框架不在其中。

## 六、npm 包部署下的「改原始插件」

从源码跑（`pnpm dsh`）与安装 npm 包跑（built `lib/`），重启语义相同；差别在「改 shipped 插件」的路径：

- **直接编辑 `node_modules/@deepseek-ai/dsh-*` 里的构建产物**：无监视（shipped 配置下模块 HMR 未激活），运行中进程不受影响；重启进程后 Node 重新 import 编辑过的模块，技术上会生效——但 pnpm 内容寻址存储重装即覆盖、改动不可分享，不是受支持路径。
- **受支持路径是组合而非变异**：不编辑 shipped 包，而是 (1) 用自己的插件（profile 目录下的文件或 npm 包，经 `dsh plugin add` 装入 profile 自己的 `node_modules`，带 `dsh.bundle` 声明的包自动加入 bundle 层，[`apps/cli/src/plugin.ts#L59`](../../../apps/cli/src/plugin.ts#L59)）；(2) 在 `cordis.patch.yml` 里按 id 整行替换——`name` 指向自己的模块，或 `disabled: true` 关掉原行再插新行；(3) 保存即触发事务性配置重载，进程不重启。profile 目录在 Harness home 下，dsh 升级不覆盖。
- **运行期替代**：动态包只能新增（服务声明不能覆盖，见第三节），换 provider 只能走上面的配置层。
- 若确实要改 shipped 插件自身逻辑：fork 源码重建，发布自己的包。

## 七、替换通道：换 `name` 是行级操作，只对 B 组成立

「改源码」与「替换」是两条不同通道，适用对象不同：

- **A 组（启动链）**：CLI 本体、app-boot、cmdline、vendor 框架模块不是插件树里的行，没有 `name` 可换——动它们只能改源码，改源码只能冷启动。A 组中作为树行挂载的 vendor 插件（`timer`、`hmr` 等行）除外，它们同样可被换 `name`。
- **B 组（cordis.yml 行挂载的业务插件）**：全部是行，全部可换。换 `name` 走配置热重载：先 import 新模块（旧插件纹丝不动继续跑），import 成功后才 dispose 旧 fiber、apply 新插件，进程全程不重启。
- 替换瞬间的语义：旧插件的注册效果全部解除（工具、事件监听、提供的服务、prompt 段——注册即副作用）；注入链下游依赖者 epoch 变化随之级联重启。换 `tools` 这类中枢会把 agent-loop 拉下去再拉起来：进行中 turn 取消（`turn/end { aborted }`）、未认领 inbox 清空、配置的 agent 自动重建（[14](14-cordis-restart-cascade-and-context.md)）；换叶子插件只动它自己。
- 失败兜底：import 失败旧插件纹丝不动；apply 抛错恢复旧插件；多行变更整树回滚（[`packages/boot/app-boot/tests/config-reload.spec.ts`](../../../packages/boot/app-boot/tests/config-reload.spec.ts)）。坏 patch 留盘，下次冷启动 fail loud。
- 热的边界：新插件文件**首次**被换行引入是热 import；之后再改同一文件内容仍需冷启动（无模块监视）。
- 模型视角：下一请求的工具/提示词集合变化 → `request/header` 记 `reason: 'change'`，KV 前缀自首个变化的 schema token 失效；会话日志与 fiber 生命周期正交，不受影响。

## 相关文件

- 级联传播：[14-cordis-restart-cascade-and-context.md](14-cordis-restart-cascade-and-context.md)
- 配置重载回滚测试：[`packages/boot/app-boot/tests/config-reload.spec.ts`](../../../packages/boot/app-boot/tests/config-reload.spec.ts)
- 工具集设计：[`.agents/notes/implemented/feature/2026-07-08-self-referential-cordis-toolset.md`](../../../.agents/notes/implemented/feature/2026-07-08-self-referential-cordis-toolset.md)
- HMR 插件：[`vendor/hmr/src/index.ts`](../../../vendor/hmr/src/index.ts)

# Vendored Cordis 审计第三波:端到端裁决 + 模糊测试(2026-08-15)

> 收尾波。苏瑾(端到端装配,真实 chokidar + Include + HMR 完整链)裁决两波遗留的待验证项;何澈(模糊测试,≥24,000 记录步 + 70,000 纯函数轮)在随机操作序列下寻找新问题并检验收敛。全部只读,仓库零改动;材料在 `%TEMP%\dsh-e2e\`、`%TEMP%\dsh-fuzz\`,种子固定可复现。

## 一、端到端裁决(修正两波结论)

| 待验证项 | 裁决 | 修正后的结论 |
|---|---|---|
| **C1**(包装句柄脱同步)现实表现 | ✅ 成立,**表现修正** | 不是「双执行」:配置更新本身平衡(1 dispose + 1 exec)。真实危害 = **每次 HMR 模块重载静默回滚配置**:`partialReload` 的 `reload()` 用 `oldFiber._config` 重建,而真实 fiber 的 `_config` 从未被 wrapper 写入更新 → 插件重启到「上次模块加载时」的配置。终态三态分叉(文件/entry.options/运行中),无任何日志;`internal/status` 携带 wrapper 而非真实 fiber |
| **H1**(Windows 嵌套 ignore) | ⚠️ 条件成立,**后果修正** | 嵌套 `pkg\node_modules`、`x\.git` 逃逸 ignore 属实;缓存驱逐混杂属实(在用模块被逐出 ESM loadCache、0 插件重载、同进程新旧代码并存)。但 **`loader.exit()` 全量重启不可达**(externals 构建即排除 node_modules);顶层 node_modules 目录级仍生效。根因:chokidar v4 只对字符串型 ignored 归一化,函数型收到原始 Windows 路径 |
| L11(include 拼写不刷新) | ✅ 成立 | 大小写路径两条链(主 watcher、registerConfig)都静默永久失效:事件到达但拼写比对跳过;`.YML` 扩展名则 fail loud。8.3 短名本机无生成不可测(机制同构) |
| EMFILE/chokidar error 降级 | ❌ 不成立 | 注入 error 事件后双 watcher 存活且功能完整;真实句柄耗尽在 Windows 不可制造,降为纯理论风险 |
| M6(双 Include 同文件 + HMR) | ✅ 成立 | 仅第一个 include 刷新,第二个静默永久 stale;registerConfig 对同文件二次注册会 fail loud——静默的只有主 watcher 路径 |
| **H2**(epoch 假恢复)真实可达性 | ❌ 不成立(loader 场景) | 三条真实替换路径(入口 name 替换、模块 HMR、同 fiber 配置重启)全部正确恢复:provide 清理器删 store 后同步 notify,epoch 必经 INACTIVE,早退条件不可能跨过。降级为理论项(仅手工绕过 dispose-notify 可达) |

**装配过程新发现**:

1. **函数声明形插件的 disposer 被静默丢弃**:`export default function f(ctx,cfg){ return () => {} }` 因 `isConstructor` 为真走 `new` 路径,返回函数被当实例,disposer 从不注册、无警告——teardown 永不执行(上游同构)。方法论影响:任何执行/teardown 失衡测量必须先用箭头函数插件排除干扰。
2. C1 叠加 noSave 语义:补丁链 `entry.update(config, true)` 跳过持久化 → 文件保持原始内容,分叉进一步加剧。
3. `registerConfig` 初始扫描必然触发一次回调(`ignoreInitial:false`)——计数类测试需扣除。

## 二、模糊测试发现(全部为新发现)

### High

**W3-H1. 自指父组的 entry 使 `Entry._disabled` 陷入同步死循环,进程 100% CPU 永久挂死**
[vendor/loader/src/config/entry.ts:92-96](../../../vendor/loader/src/config/entry.ts#L92-L96)(环由 [group.ts:27](../../../vendor/loader/src/config/group.ts#L27) 无环校验引入,入口 [tree.ts:97-104](../../../vendor/loader/src/config/tree.ts#L97-L104))
3 步最小复现(种子 3000):把已存在的组 entry `x` 重新创建到它自己的子组下 → `x.parent === x.subgroup` → `while(entry)` 祖先上溯恒回自身,**纯同步零分配自旋,事件循环饿死**(watchdog/timer/信号全部失效,只能强杀)。**fuzz 命中率 ~55%**(run3 30/55 种子同签名挂死)。Loader 公共 API 既不校验也不报错。修复:`EntryGroup.create`/`EntryTree.update` 拒绝自指/环路 parent。

**W3-H2. 跨树 move 只搬 data 行不搬 entry:静默丢失持久化,entry 变为不可寻址**
[vendor/loader/src/config/tree.ts:114-142](../../../vendor/loader/src/config/tree.ts#L114-L142)
`loader.update('include:mv', {}, null)`:操作「成功」无报错,但运行中条目从持久化配置剥离(文件被清空、条目仍在运行,重启即消失);store/parent/data 三方分属两棵树;后续 `remove`/`update` 两种寻址都失败。run1+run3 37 次不变量违反的主要来源。

**W3-H3. YAML alias 共享 group config:两组共享同一 data 数组与行对象,互相污染并被写回文件**
[vendor/include/src/index.ts:63](../../../vendor/include/src/index.ts#L63)(`structuredClone` 保留行间引用)+ [group.ts:84](../../../vendor/loader/src/config/group.ts#L84)(直接收养共享数组)
用户 YAML 锚点 DRY(`config: &c [... ]` / `config: *c`)是合法输入;在 ga 下创建的子条目同时出现在 gb、单一 entry 挂载于两个组、写盘含两份行;后续单组操作触发另一组的连锁违反(knownHit 2311 次的主成分)。

### Medium

- **W3-M1.** id 含 `:` 的 create 部分成功:插件已挂载、抛错后留孤儿 entry、永久不可寻址([tree.ts:100](../../../vendor/loader/src/config/tree.ts#L100),`group.create` 完成后才 `resolve` 失败,半提交)
- **W3-M2.** `applyEntryPatches` 的 `insert` 非数组 → 原生 TypeError 透传([include/src/index.ts:94](../../../vendor/include/src/index.ts#L94))
- **W3-M3.** `buildMap` 遇 null 行 → 原生 TypeError([include/src/index.ts:69](../../../vendor/include/src/index.ts#L69))
- **W3-M4.** cordis.yml 顶层行非对象(`- null`、`- 5`)→ `ensureId` 原生 TypeError;Include 只校验顶层数组不校验行形状([tree.ts:68-70](../../../vendor/loader/src/config/tree.ts#L68-L70),40/40 B2 种子命中)

### Low / 边角

- patch 重放基于陈旧 `this.data`:静默卸载自上次读盘后创建的条目,文件与运行树背离(设计边角)
- `entry.ts:239` 回滚失败的 AggregateError detail 为空串,诊断性差

## 三、fuzz 收敛性判定

| 目标 | 规模 | 收敛性 |
|---|---|---|
| C·fiber 生命周期(随机树、交错 dispose/restart/update/provider 替换) | 65 集 9750 步 | **完全收敛**:零违反零崩溃,后 6000 步无新信号——fiber 状态机在受测操作谱下保持全部不变量 |
| B·patch/配置值(70k 纯函数轮 + 40 挂载集) | — | **收敛到 3 个稳定崩溃族**(M2/M3/M4),后 30k 轮无新类别 |
| A·配置操作序列 | ≥7200 步 | **饱和于 4 个家族**(H1 挂死、跨树 move、alias 共享、':'-id),run3 后 20 集(~1200 步)无新种类;家族内违反仍持续产出 |

**从未违反的不变量**(两波已知缺陷在此得到反向确认):fiber-double-mount、disabled-still-mounted、orphan-fiber、unhandledRejection(A/B/C 全程 0)、终态 tally 相等、终态 registry 清空、consumer 读值始终属存活 provider、fiber 无 LOADING/UNLOADING 卡死。

## 四、三波累计最终清单

| 级别 | 第一波 | 第二波(经裁决修正) | 第三波 |
|---|---|---|---|
| Critical | C1 包装句柄脱同步(→HMR 静默回滚配置) | — | — |
| High | H1 emit→进程崩溃、H2 status 观察者卡依赖、H3 root 直写遮蔽、H4 internal 钩子 | H1' Windows 嵌套 ignore(缓存混杂)、H2' epoch 假恢复(降理论) | W3-H1 自指父组死循环、W3-H2 跨树 move 丢持久化、W3-H3 alias 共享组 |
| Medium | 14 条 | 14 条(+修正) | 4 条 |
| Low/Info | 20+ | 30+ | 若干 |

**修复优先级总表**(跨三波合并):

1. **立即**:C1(`restart/update` 恢复 `this.ctx.fiber` 重锚定);W3-H1(parent 环校验);emit 的 thenable catch;`internal/status` 逐回调隔离。
2. **短期**:W3-H2(跨树 move 校验或迁移 entry);W3-H3(alias 共享深拷贝切断);Windows ignore 一行修复;W3-M2/M3/M4(patch/行形状校验 fail-loud);schemastery toJSON try/finally;schema-form rehydrate 剥 callback;cordis_run host-only 补审批。
3. **中期**:其余 fail-loud 违约类(`_hooks` null-proto、`Inject.resolve` 拒绝继承/symbol 键、嵌套 group id 树级唯一、双 include 去重、webserver 非 loopback 绑定)。
4. **记录**:同域类(设计接受)、理论项(H2'、EMFILE、8.3)。

## 五、收敛结论

三波共 15 个 agent、约 40,000 动态验证步 + 70,000 纯函数轮之后:

- **文件覆盖**:vendor 9 包全部 src 文件(46 个)逐文件穷尽 ✅
- **攻击面**:并发/元编程/配置/资源/供应链/契约/可达性,两轮正交 ✅
- **收敛信号**:fiber 生命周期 fuzz 完全收敛;patch fuzz 收敛;操作序列 fuzz 饱和于 4 家族且后 1200 步无新种类 ✅
- **仍未做**(诚实边界):真实 API 级长时 soak(多分钟级文件抖动)、跨平台(Linux/macOS 的 watcher 语义)、pnpm junction 穿透实测、Electron IPC 面、以及任何需要修改代码才能验证的修复回归

按「每个文件都挖、直到找不到」的工程判据,在当前工具方法(静态精读 + 动态探针 + 完整装配 + fuzz)下已达到收敛;剩余空白全部是环境/时长受限项,已在清单中列明。

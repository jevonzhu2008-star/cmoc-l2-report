# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目性质

「L2 集团合并报表」的 Power BI 项目（PBIP 格式），声明式项目：**没有构建、测试、lint 或「运行」入口**。开发只有三条路——Power BI Desktop 打开 `L2报表.pbip`、直接编辑 TMDL / PBIR 文本、或用 powerbi-modeling MCP 操作语义模型。提交信息与模型对象命名一律用中文。

## 常用命令

```bash
python update-version-html.py      # 手动重建版本迭代页（post-commit 会跑，一般不手工执行）
git add -A && git commit -m "…"    # 唯一的日常工作流入口
```

- 语义模型操作走 MCP：连目录（`powerbi-modeling` 的 connection 操作指向本目录）→ 改对象 / 跑 DAX → 断开。改完最好连一次确认表数、度量值数、错误数为预期。
- `generate_mock_data.py` 是一次性辅助脚本（依赖 `openpyxl`），给 L2-01-02 生成模拟 Excel。`OUTPUT_FILE` 仍是旧机器路径 `C:\Users\Zhujh\…`，用前先改。

## 顶层结构

- `L2报表.pbip` —— 入口，只声明 report artifact
- `L2报表.Report/` —— 报告定义（PBIR，definition version 2.0.0）
- `L2报表.SemanticModel/` —— 语义模型（TMDL，compatibilityLevel 1702）
- `L2报表HTML格式规范.md` —— HTML 度量值配色 / 数值格式规范（见文末）
- `update-version-html.py` + `L2报表项目版本迭代.html` —— 版本迭代页（见「Git 工作流」）
- `.git/hooks/post-commit` —— 提交后自动刷新版本迭代页

## 报表 ↔ 语义模型

`L2报表.Report/definition.pbir` 的 `datasetReference.byPath` 指向 `../L2报表.SemanticModel`，这是唯一连接点。两者是 PBIP 内的两个独立 artifact，改语义模型会直接影响报表。

## 语义模型（TMDL）

`L2报表.SemanticModel/definition/` 下：

- `database.tmdl` —— `compatibilityLevel: 1702`
- `model.tmdl` —— culture `zh-CN`、queryGroup（**参数 / 财经 / 辅助**）、全部 `ref table`、`PBI_QueryOrder`；`valueFilterBehavior: independent`
- `relationships.tmdl` —— **11 条关系**，一律「事实表.加载日期 → 日期表.日期」的多对一单列关系；报表里的「年月筛选」切片器就是靠它同时筛所有内容页
- `expressions.tmdl` —— 全部取数参数（`IsParameterQuery`），共 7 个：`QAS服务器`、`系统编号`、`客户端ID`、`p_月报起始日期`、`p_月报终止日期`、`财经SharePoint站点`、`动态年月偏移`
- `functions.tmdl` —— DAX 用户函数，只有两个：`FormatAmount`（`"#,0;(#,0);0"`）与 `FormatRatio`（`"+0.00%;-0.00%;0.00%"`），无参数、直接返回格式字符串，度量值通过 `formatStringDefinition` 引用
- `tables/` —— 每个表一个 `.tmdl`（11 张事实表 + `度量值` 表 + `日期表`）
- `cultures/zh-CN.tmdl` —— Q&A 语言架构（`linguisticMetadata`，约 2000 行自动生成）。改列名/表名后不必手改，里面有历史遗留的孤儿条目（如 `_has_…`）属正常现象

### 表的业务组织

11 张事实表，全部是 L2 编号的集团财经表，命名格式 `L2-编号 业务名称`：

`L2-01-02 集团合并利润汇总表`、`L2-01-03 快报-金融投资业务专属`、`L2-01-04 S3 C1成本变化步行图VS上月`、`L2-01-14 物料单耗月表`、`L2-01-25 工序成本完成情况`、`L2-03-01 销售管理费用预算执行汇总表`、`L2-03-02 财务费用汇总表`、`L2-03-06 矿石成本分析`、`L2-04-01 库存汇总表`、`L2-05-01 硫磺及硫酸价格分析月报`、`L2-06-01 主要产品价格波动汇总表`。

另有一张 `日期表`：由 `p_月报起始日期` ~ `p_月报终止日期` 在 M 里生成连续日期，派生 `年 / 月 / 年月 / 年排序 / 月排序 / 年月筛选`（`年月筛选` 把范围内最大年月显示为「最近月份」，其余为 `yyyy-MM`，供切片器用）。它是模型里唯一被所有事实表指向的维度表。

映射/排序数据**不进模型表**，而是在各自的 M 查询里读 SharePoint 上的「<表名>指标映射.xlsx」并 `NestedJoin` 物化进事实表（带出 `结构排序`、`指标名称排序` 等隐藏排序列，供 `sortByColumn` 使用）。

### M 取数统一模式

每张事实表的 M 查询骨架一致，读一张就能推断其余：

1. `SharePoint.Files(财经SharePoint站点, [ApiVersion=15])` 筛出该表的指标映射 xlsx，`Excel.Workbook` 取排序工作表
2. `SapBusinessWarehouse.Cubes(QAS服务器, 系统编号, 客户端ID, [Implementation="2.0", LanguageCode="ZH", …])` → `{[Name=Cube]}` → `{[Id="Cube/Query"]}`；**Cube 只在循环外实例化一次**，循环里只做 `Cube.Transform`
3. `List.Generate(() => p_月报起始日期, each _ <= p_月报终止日期, each Date.AddMonths(_, 1))` 生成月份序列，再转成 **YYYYMM 文本**
4. 每月 `Cube.Transform`：`Cube.ApplyParameter "[ZMSDQNY]"` → 展开维度 → `AddMeasureColumn`
5. 追加 `加载日期` = 该月 1 日（**date 类型**，格式 `yyyy-M-d`）
6. null → 0，`Table.UnpivotOtherColumns` 逆透视成「指标名称 / 指标值」长表（L2-01-02 例外：逆透视成「月份 / 实际值」，再派生 `月份排序`、`季度`；L2-04-01 例外：BW 度量名本身写成「金额(人民币) 当月实际」这类「指标 + 结构」格式，逆透视后再 `Table.SplitColumn` 按空格拆出 `结构` 列）
7. 左连接排序映射表，展开排序字段

**关键约束**：循环里的 `month` 变量是 **YYYYMM 文本**（BW 参数 `[ZMSDQNY]` 的要求），而 `加载日期` 列是 **date**。两者不能混用——直接把 `month` 赋给日期列会抛类型错误，必须 `#date(Number.From(Text.Start(month,4)), Number.From(Text.End(month,2)), 1)`。

### 度量值集中管理

24 个度量值全部在 `tables/度量值.tmdl` 的「度量值」表里，**不散落到事实表**。`displayFolder` 用**源表名**分组（如 `L2-01-02 集团合并利润汇总表`），新增度量值沿用；跨页共用的辅助度量（`当前月报期间`）放 `辅助`。

长表（指标名称 / 指标值）的表，度量值一律 `CALCULATE(SUM(<表>[指标值]), <表>[指标名称] = "…")`，不要直接 SUM 某个物理列——`L2-04-01` 的 `金额(人民币)`、`金额(原币)`、`量(吨)` 就是这种写法，报表里再用「结构」列区分当月/环比/去年同期/月-1~3。

格式约定：金额类 + `formatStringDefinition = FormatAmount()`；比率类 + `FormatRatio()`；混合口径的长表指标值（`L2-01-04指标值`、`L2-01-14指标值`、`L2-01-25指标值`、`L2-03-06指标值`、`L2-06-01指标值`）不用 UDF，改打 `annotation PBI_FormatHint = {"isGeneralNumber":true}`。

## 报告（PBIR）

`L2报表.Report/definition/pages/` 下每个页面是一个 **UUID 命名目录**（`page.json` + `visuals/<uuid>/visual.json`）。顺序、活动页、落地页都在 `pages/pages.json` 的 `pageOrder` / `activePageName` / `landingPageName` 里，值是页面目录的 UUID。

当前 **12 个页面，1 个可见 + 11 个隐藏**。按 `pageOrder`：

| UUID | displayName | 说明 |
|---|---|---|
| `e6f9a94ed6eff9e91d95` | L2报表 | **首页 / 落地页**，仅一个圆角矩形标题形状 |
| `50df5dd79c9c19213b42` | L2-01-02 集团合并利润汇总表 | 2 个矩阵 |
| `020a059bfd06b6347883` | L2-01-03 快报-金融投资业务专属 | |
| `8df4296b5610c7c60c7a` | L2-01-04 S3 C1成本变化步行图VS上月 | |
| `540ff71af184f11c2116` | L2-01-14 物料单耗月表 | |
| `98de86891699048a660e` | L2-01-25 工序成本完成情况 | |
| `e16279b10e3df23fa8cb` | L2-03-01 销售管理费用预算执行汇总表 | |
| `4effe47efe2ace12b72b` | L2-03-02 财务费用汇总表 | |
| `feed276a3075012f7e94` | L2-03-06 矿石成本分析 | |
| `72b8f9de0e30717743ca` | L2-04-01库存汇总表 | 多一个「矿体」切片器 |
| `4782da4e728bfbbefc8c` | L2-05-01 硫磺及硫酸价格分析月报 | |
| `e3b3b9f3eab1c72826c8` | L2-06-01 主要产品价格波动汇总表 | |

- 除首页外，11 个内容页都在 `page.json` 里带 `"visibility": "HiddenInViewMode"`，画布统一 1920 × 1080。
- **每个内容页的标准构成 = 1 个矩阵（`pivotTable`）+ 1 个「年月筛选」切片器 + 1 个「当前月报期间」卡片**。切片器取 `日期表.年月筛选`，默认选「最近月份」，并挂同名 `syncGroup`（`fieldChanges` / `filterChanges` 均开），翻页时筛选保持一致；卡片显示 `度量值.当前月报期间`（`当前月报期间: yyyy年MM月`）。
- 切片器能筛所有表，是因为每个事实表的 `加载日期` 都与 `日期表[日期]` 建了关系（见 `relationships.tmdl`）。新增事实表时别忘了补这条关系，否则新页的切片器对它无效。
- 首页导航按钮**尚未添加**——当前 view 模式只能看到首页那一个标题形状，这是预期状态，不要当成 bug。
- 主题在 `definition/report.json`：基础主题 `Fluent2-CY26SU09` + 自定义主题 `StaticResources/RegisteredResources/dba7299791721089146.json`。

## 数据源

- **SAP BW**：只保留了 QAS 环境 `10.43.15.32`（参数 `QAS服务器`，11 张表全部引用它）。切生产就是改这一个参数值，不存在单独的「生产服务器」参数。
- **SharePoint**：财经站点 `https://xsyzz.sharepoint.com/sites/CMOCGroup/`（参数 `财经SharePoint站点`），用于读指标映射 xlsx。
- 连接凭据在 `.pbi/localSettings.json`（已 gitignore）。

## Git 工作流

- 提交后 `post-commit` hook 自动跑 `python update-version-html.py` 刷新 `L2报表项目版本迭代.html`，再补录一次「更新 L2报表项目版本迭代页：补录本次提交」。**不要手动编辑或提交这个 html。**
- `update-version-html.py` 的 `NOTES` 字典按短 hash 手动维护里程碑「完整备注」；没写进 `NOTES` 的提交，其 **commit body 会自动作为备注显示在版本迭代页上**——所以提交信息要写正文，别只写标题。
- `.gitignore` 排除 `**/.pbi/localSettings.json` 与 `**/.pbi/cache.abf`。

## 已知坑

1. **`core.autocrlf=true` 造成假修改**：`.tmdl` 会出现仅行尾差异的「已修改」，`git diff` 却是空的。`git add -A` 会规范化掉，或加 `.gitattributes` 固定 `*.tmdl text eol=lf`。
2. **残留数据缓存导致类型错误**：改过列数据类型或表结构后，Desktop 刷新报「类型不匹配，无法对值 … 执行数据类型转换」——先关 Desktop，删 `L2报表.SemanticModel/.pbi/cache.abf`，再重新打开。
3. **Desktop 会重写文件**：打开再保存会补 `isHidden`、清理空 queryGroup、把整数坐标扩写成 `960.00000000000011` 这类浮点。提交前用 `git diff` 确认改动符合真实意图，别把无意义 diff 一起提交。
4. **PBIR 硬编码表名**：视觉对象用 `queryRef` / `SourceRef.Entity` 写死表名，模型里改表名后 Desktop 不会同步，必须全局搜 `Entity`、`queryRef` 一并替换，否则打开报「找不到表」或静默显示空。
5. **`p_月报终止日期` 是手写值**（当前 `2026-03-01`）：跨月后要手动往后调，否则取不到新月份数据。

## HTML 度量值规范

用「HTML 内容」视觉渲染的度量值，其配色、数值格式、颜色判断、表格结构必须遵循 `L2报表HTML格式规范.md`（项目根目录）。要点：金额 `#,0;(#,0);0` 正黑负红、百分比 2 位小数带 `+`/`-` 号正绿负红、颜色用内联 `style` 属性（不依赖 class）、分月值 0 不显示、无数据月份整列隐藏、环比MTD 末列。

注意：**当前模型内没有任何 HTML 度量值**（原「利润汇总表」已在 `3d8daa4` 删除）。规范文件保留，作为以后新增 HTML 视觉的标准。

## 可用工具

- **powerbi-modeling MCP**：连接本地 TMDL/PBIP、DAX 查询、增删改表/度量值/列/关系等。
- 涉及语义模型设计/重构决策时，参考 `powerbi-semantic-model-methodology` 技能（含 SAP BW 循环取数、维度建模决策、命名与注释规范）。

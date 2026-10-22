# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目性质

这是「L2 集团合并报表」的 Power BI 项目（PBIP 格式），属于声明式项目：没有构建、测试或 lint 命令，也没有「运行」入口。开发通过 Power BI Desktop 打开 `L2报表.pbip`，或直接编辑 TMDL / PBIR 定义文件，或用 powerbi-modeling MCP 工具操作语义模型。提交信息与模型对象命名均使用中文。

## 顶层结构

- `L2报表.pbip` —— 项目入口，声明 report artifact
- `L2报表.Report/` —— 报告定义（PBIR，报告定义版本 4.0）
- `L2报表.SemanticModel/` —— 语义模型（TMDL，版本 4.2，兼容级别 1702）
- `update-version-html.py` + `L2报表项目版本迭代.html` —— 版本迭代页（见「Git 工作流」）
- `.git/hooks/post-commit` —— 提交后自动刷新版本迭代页

## 报表 ↔ 语义模型的连接

`L2报表.Report/definition.pbir` 的 `datasetReference.byPath` 指向 `../L2报表.SemanticModel`，这是报表绑定语义模型的唯一连接点。两者是 PBIP 内两个独立 artifact，改动语义模型会影响报表。

## 语义模型（TMDL）

`L2报表.SemanticModel/definition/` 下：

- `database.tmdl` —— `compatibilityLevel: 1702`（支持最新 TMDL 特性）
- `model.tmdl` —— 模型级定义：culture `zh-CN`、queryGroup（参数/成本/财经/辅助）、全部表引用、`PBI_QueryOrder`
- `expressions.tmdl` —— Power Query 表达式与**取数参数**（`IsParameterQuery`），以及 L2-03-02 的「指标排序/结构排序」辅助查询
- `functions.tmdl` —— DAX 用户函数（UDF）
- `tables/` —— 每个表一个 `.tmdl` 文件
- `cultures/zh-CN.tmdl` —— 中文翻译（体积大，改动需谨慎）

### DAX 用户函数

- `FormatAmount` / `FormatRatio` —— 读取「单位」列（`%` / `t/t` / 吨）返回动态格式字符串，度量值通过 `formatStringDefinition` 引用
- `SameMonthPriorYear` —— 同期（去年同月）计算。解析「月份-筛选器」切片器的两种取值形态（「最近月份」或具体月份文本如 `202608`），利用 YYYYMM 编码减 100 得去年同月（`202608 → 202508`）

### 表的业务组织

语义模型是「集团合并」的单一模型，同时承载两套数据：

- **选冶厂事实表**（承自 L3）：`KFM选冶厂月报`、`L1-KFM日报`
- **集团财经事实表**（L2 编号规则）：`L2-01-02 集团合并利润汇总表`、`L2-01-03 快报-金融投资业务专属`、`L2-03-01 销售管理费用预算执行汇总表`、`L2-03-02 财务费用汇总表`、`L2-05-01 硫磺及硫酸价格分析月报`
- **映射表**：`日报指标映射`、`月报指标映射`

### 度量值集中管理

所有度量值集中在 `tables/度量值.tmdl` 的「度量值」表里，用 `displayFolder` 分组：`00辅助` / `01新口径` / `02月报` / `03日报`。新增/修改度量值时保持这个分组约定，不要把度量值散落到事实表。

## 报告（PBIR）

`L2报表.Report/definition/pages/` 下每个页面是一个 **UUID 命名的目录**（`page.json` + `visuals/`）。页面顺序、活动页、落地页由 `pages/pages.json` 的 `pageOrder` / `activePageName` / `landingPageName` 维护，值都是页面目录的 UUID。切换报告活动页只需改 `activePageName`。

页面 UUID → 业务名称对照（业务名在各页 `page.json` 的 `displayName`，改动 `activePageName` / `pageOrder` 时用）：

- `ad90dc3587cb9698b4f0` → 月报（落地页，隐藏）
- `f02a10333ccb89cb058b` → 日报（隐藏）
- `7237a172b79900aea0a2` → 月报数据导出（隐藏）
- `50df5dd79c9c19213b42` → 集团合并利润汇总表
- `e16279b10e3df23fa8cb` → 销售管理费用预算执行汇总表
- `4effe47efe2ace12b72b` → 财务费用汇总表
- `4782da4e728bfbbefc8c` → 硫磺及硫酸价格分析月报

主题在 `definition/report.json`：基础主题 Fluent2-CY26SU09 + 自定义主题（RegisteredResources）。

## 数据源

数据经 Power Query 从 **SAP BW**（服务器 `10.43.11.32` / QAS `10.43.15.32`）与 **SharePoint**（成本站点 `cmocco.sharepoint.com` / 财经站点 `xsyzz.sharepoint.com`）取数。连接参数全部在 `expressions.tmdl` 中以 `IsParameterQuery` 参数暴露（如 `服务器`、`系统编号`、`客户端ID`、`动态年月偏移`），本地连接凭据在 `.pbi/localSettings.json`（已 gitignore）。

## Git 工作流

- 提交后 `post-commit` hook 自动运行 `python update-version-html.py` 刷新 `L2报表项目版本迭代.html`，并补录一次「更新 L2报表项目版本迭代页：补录本次提交」提交。**不要手动编辑或提交这个 html。**
- `update-version-html.py` 的 `NOTES` 字典（按短 hash 键控）手动维护各里程碑的「完整备注」；提交信息正文（body）会自动作为「完整备注」的兜底。写提交信息时写清楚正文，它会显示在版本迭代页上。
- `.gitignore` 已排除 `**/.pbi/localSettings.json`（本地连接凭据）与 `**/.pbi/cache.abf`（数据缓存）。
- 已知坑：Windows 上 `core.autocrlf=true` 会让 `.tmdl` 文件出现仅行尾差异的「假修改」（`git diff` 为空）。遇到时 `git add -A` 会将其规范化掉，或加 `.gitattributes` 固定 `*.tmdl text eol=lf`。

## HTML 度量值规范

报表里用「HTML 内容」视觉渲染的度量值（生成 HTML 表格，如「利润汇总表」），其**配色、数值格式、颜色判断、表格结构**必须遵循 `L2报表HTML格式规范.md`（项目根目录）。要点：金额 `#,0;(#,0);0` 正黑负红、百分比 2 位小数带 `+`/`-` 号正绿负红、颜色用内联 `style` 属性（不依赖 `<style>` 的 class）、分月值 0 不显示、无数据月份整列隐藏、环比MTD 末列。

## 可用工具

- 语义模型操作可用 **powerbi-modeling MCP**（连接本地 TMDL/PBIP、DAX 查询、增删改表/度量值/列/关系等）。
- 涉及语义模型设计/重构决策时，参考 `powerbi-semantic-model-methodology` 技能（含本项目 SAP BW 取数、命名规范等约定）。

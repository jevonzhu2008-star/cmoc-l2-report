# L2 报表 HTML 度量值格式规范

本规范定义 Power BI 报表中「HTML 内容」视觉所用度量值的统一配色、数值格式与表格结构标准。所有新增或修改的 HTML 度量值必须遵循本标准，保证报表视觉风格一致。

---

## 一、配色方案

| 用途 | 色值 | 说明 |
|------|------|------|
| 表头背景 | `#1A2538` | 深蓝黑色，稳重的报表标题底色 |
| 表头文字 | `#FFFFFF` | 白字 |
| 表头边框 | `#111A29` | 比表头背景更深一档 |
| 单元格边框 | `#D9D9D9` | 浅灰细线 |
| 负值（全部指标） | `#DC3545` | 红色，表示下降/亏损/未达成 |
| 正值（百分比类） | `#28A745` | 绿色，表示增长/达成 |
| 金额正值 | `#000000` | 黑色（默认，不单独设色） |
| 斑马纹 | `#F5F8FC` | 偶数行浅蓝灰底 |

**字体**：`16px`，字体族 `'Segoe UI', 'Microsoft YaHei', sans-serif`。

---

## 二、数值格式方案

### 1. 金额类（当月YTD、预算YTD、分月实际值等）

- **格式字符串**：`#,0;(#,0);0`
  - 千分位分隔、0 位小数、负数用括号、零值显示 `0`
- **颜色**：正数黑色（默认）、负数红色 `#DC3545`
- **实现**（内联 style，最可靠）：

```dax
IF([值] < 0,
    "<td class='n' style='color:#DC3545;'>",
    "<td class='n'>"
) & FORMAT([值], "#,0;(#,0);0") & "</td>"
```

### 2. 百分比类（同比YTD、预算达成率、环比MTD等）

- **小数位数**：2 位（手动控制，不使用 `FORMAT` 的 `%` 格式，因其多段/百分比处理不稳定）
- **符号**：正值加 `+`、负值加 `-`、零值不加符号
- **颜色**：正值绿色 `#28A745`、负值红色 `#DC3545`、零值绿色
- **实现**：手动乘 100 + 普通数字格式 `0.00` + 手动拼符号与 `%`

```dax
SWITCH(TRUE(),
    [值] < 0, "<td class='n' style='color:#DC3545;'>-"
              & FORMAT(ABS([值]) * 100, "0.00") & "%</td>",
    [值] = 0, "<td class='n' style='color:#28A745;'>"
              & FORMAT([值] * 100, "0.00") & "%</td>",
    "<td class='n' style='color:#28A745;'>+"
              & FORMAT([值] * 100, "0.00") & "%</td>"
)
```

> **要点**：百分比值（如 0.156 表示 15.6%）是小数，需 `* 100` 后按普通数字 `0.00` 格式化，`%` 号手动拼接。不要用 `FORMAT(值, "0.00%")`，它在不同环境中小数位数和符号处理不可靠。

---

## 三、颜色判断规则

| 类型 | 判断逻辑 | 显示 |
|------|---------|------|
| 金额 | `值 < 0` → 红；否则黑 | `-1,234` → `(1,234)` 红；正数黑 |
| 百分比 | `值 < 0` → 红带 `-`；`值 = 0` → 绿无符号；`值 > 0` → 绿带 `+` | `+15.60%` 绿 / `-15.60%` 红 |

颜色一律写在 `<td>` 的**内联 `style` 属性**里（`style='color:#DC3545;'`），不要依赖 `<style>` 标签里的 class 选择器——部分 HTML 视觉的沙箱环境会忽略 `<style>` 中的 class 规则。

---

## 四、表格结构

- **两行表头**：
  - 第一行：`项目`、各 YTD 指标（`rowspan='2'` 纵向合并）、季度分组 `Q1~Q4`（`colspan` 横跨对应月份）、`环比MTD`（`rowspan='2'`）
  - 第二行：`1月~12月`（落在季度分组下）
- **项目列**：左对齐、字重 500、不换行（class `c`）
- **数值列**：右对齐、等宽数字、不换行（class `n`）
- **季度分组**：Q1=1~3月、Q2=4~6月、Q3=7~9月、Q4=10~12月

---

## 五、特殊规则

1. **分月值为 0 不显示**：`IF([值] = 0, "", FORMAT(...))`，值为 0 的单元格留空。
2. **无数据月份整列隐藏**：先算月总计 `_m1.._m12`，再生成 `_hasM1.._hasM12` 标志（`NOT ISBLANK(_m) && _m <> 0`），无数据的月份其表头 `<th>` 与表体 `<td>` 都不输出；季度 `colspan` 随之动态计算（`_cQ1.._cQ4`）。
3. **环比MTD 固定为最后一列**。

---

## 六、标准 CSS 模板

```
.tb{border-collapse:collapse;font-family:'Segoe UI','Microsoft YaHei',sans-serif;font-size:16px;width:100%;}
.tb th{background:#1A2538;color:#fff;padding:6px 6px;border:1px solid #111A29;text-align:center;font-weight:normal;white-space:nowrap;}
.tb td{padding:4px 6px;border:1px solid #D9D9D9;}
.tb .c{text-align:left;font-weight:500;white-space:nowrap;}
.tb .n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;}
.tb tbody tr:nth-child(even){background:#F5F8FC;}
```

> 说明：`.neg` / `.pos` 类不再依赖（颜色用内联 style），此处仅供颜色定义参考：`.neg{color:#DC3545;}`、`.pos{color:#28A745;}`。

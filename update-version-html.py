# -*- coding: utf-8 -*-
"""
update-version-html.py
从 git log 自动生成 / 更新 L2报表项目版本迭代.html

用法：
    python update-version-html.py

行为：
    1. 读取 main 分支的全部提交记录（hash / 日期 / 提交信息 / 变更规模）。
    2. 按变更规模自动判定里程碑（文件数 >= 20 或新增行 >= 1500）。
    3. 「完整备注」优先取 NOTES 手动维护，否则自动取提交正文（body）；
       据此生成自包含的 L2报表项目版本迭代.html。

维护说明：
    - 提交时写好 commit message 正文（body），版本迭代页会自动展示为「完整备注」；
    - 需要额外补充时，再在 NOTES 里按短 hash 添加条目覆盖；
    - 已接入 post-commit hook，每次提交后自动刷新版本迭代页。
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime

# Windows 控制台默认 cp1252，打印中文会报错；统一改为 UTF-8 输出。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# ---------------------------------------------------------------------------
# 完整提交备注（按短 hash 键控）。提交信息里已能说明的，此处可省略或只补充细节。
# ---------------------------------------------------------------------------
NOTES = {
    "e0e1f3d": [
        "项目概述",
        "- 集团层（L2）合并报表，Power BI 项目格式（PBIP），语言文化 zh-CN",
        "- 含报告（PBIR）与语义模型（TMDL）两部分",
        "报告层（L2报表.Report，报告定义版本 4.0）",
        "- 共 7 个页面、27 个视觉对象、4 个书签",
        "· 月报 —— 落地页",
        "· 日报",
        "· 月报数据导出 —— 隐藏数据页",
        "· 集团合并利润汇总表 —— 活动页（L2-01-02）",
        "· 销售管理费用预算执行汇总表（L2-03-01）",
        "· 财务费用汇总表（L2-03-02）",
        "· 硫磺及硫酸价格分析月报（L2-05-01）",
        "- 主题：Fluent2-CY26SU09 基础主题 + 自定义资源",
        "语义模型（L2报表.SemanticModel，版本 4.2，兼容级别 1702）",
        "- 选冶厂事实表（承自 L3）：KFM选冶厂月报（19 列）、L1-KFM日报（17 列）",
        "- 集团财经事实表：L2-01-02 集团合并利润汇总表（14 列）、",
        "L2-03-01 销售管理费用预算执行汇总表（8 列）、",
        "L2-03-02 财务费用汇总表（7 列）、",
        "L2-05-01 硫磺及硫酸价格分析月报（14 列）",
        "- 映射表：日报指标映射（10 列）、月报指标映射（7 列）",
        "- 度量值表（27 个）：00辅助（7）、01新口径（4）、02月报（9）、03日报（7）",
        "- DAX 函数（UDF）：FormatAmount、FormatRatio、SameMonthPriorYear",
        "- Power Query 参数：p_月报起始日期=2025-01-01、p_日报起始日期=2026-01-01、",
        "服务器、系统编号=00、客户端ID=100、成本SharePoint站点、QAS服务器、",
        "动态年月偏移=-7、财经SharePoint站点",
        "- 表达式：L2-03-02指标排序、L2-03-02结构排序",
        "进度说明",
        "- 集团财经四张表（L2-01-02 / L2-03-01 / L2-03-02 / L2-05-01）已并入语义模型",
        "- 选冶厂月报/日报（KFM）与集团财经共享一套语义模型，度量值按 00辅助/01新口径/02月报/03日报 分组",
        "- .gitignore 已排除本地连接设置（localSettings.json）与数据缓存（cache.abf）",
    ],
}


def repo_root():
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, encoding="utf-8",
    ).stdout.strip()
    return out or os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
    ).stdout


def collect_commits(root):
    os.chdir(root)
    log = run([
        "git", "log", "main", "--format=%H%x1f%h%x1f%ad",
        "--date=format:%Y-%m-%d %H:%M",
    ])
    commits = []
    for line in log.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("\x1f")
        if len(parts) != 3:
            continue
        full, short, date = parts
        # 完整提交消息（subject + body）
        full_msg = run(["git", "show", "-s", "--format=%B", full]).strip()
        msg_lines = full_msg.splitlines()
        subject = msg_lines[0].strip() if msg_lines else ""
        # 过滤「补录本次提交」维护提交（由 post-commit 自动补录产生），
        # 避免版本迭代页在每次补录后自我引用、无限递归。
        if "补录本次提交" in subject:
            continue
        # body：去掉标题行、空行与 Co-Authored-By 署名行，作为自动「完整备注」
        body = [
            l.strip() for l in msg_lines[1:]
            if l.strip() and not l.strip().startswith("Co-Authored-By")
        ]
        stat = run(["git", "show", "--shortstat", "--format=", full])
        files = add = dele = 0
        m = re.search(r"(\d+) files? changed", stat)
        if m:
            files = int(m.group(1))
        m = re.search(r"(\d+) insertions?\(\+\)", stat)
        if m:
            add = int(m.group(1))
        m = re.search(r"(\d+) deletions?\(-\)", stat)
        if m:
            dele = int(m.group(1))
        commits.append({
            "short": short,
            "full": full,
            "date": date,
            "msg": subject,
            "body": body,
            "files": files,
            "add": add,
            "del": dele,
        })
    return commits


def is_milestone(c, index, total):
    # 根提交（初始化）一律视为里程碑；其余按规模判定。
    if index == total - 1:
        return True
    return c["files"] >= 20 or c["add"] >= 1500


def build_html(commits, notes):
    data = []
    for i, c in enumerate(commits):
        data.append({
            "short": c["short"],
            "date": c["date"],
            "msg": c["msg"],
            "files": c["files"],
            "add": c["add"],
            "del": c["del"],
            "ms": is_milestone(c, i, len(commits)),
        })

    # 迭代跨度（天）：最新提交 - 最早提交
    try:
        newest = datetime.strptime(commits[0]["date"], "%Y-%m-%d %H:%M")
        oldest = datetime.strptime(commits[-1]["date"], "%Y-%m-%d %H:%M")
        days = round((newest - oldest).total_seconds() / 86400.0, 1)
    except (IndexError, ValueError):
        days = 0.0

    data_json = json.dumps(data, ensure_ascii=False, indent=2)

    # 完整备注：手动 NOTES 优先，否则回退到提交正文（body）自动提取
    merged_notes = {}
    for c in commits:
        manual = notes.get(c["short"])
        if manual:
            merged_notes[c["short"]] = manual
        elif c.get("body"):
            merged_notes[c["short"]] = c["body"]
    notes_json = json.dumps(merged_notes, ensure_ascii=False, indent=2)

    return HTML_TEMPLATE.format(
        data_json=data_json,
        notes_json=notes_json,
        days=days,
    )


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>L2报表 · 项目版本迭代</title>
<style>
:root{{
  --surface-1:#fcfcfb; --plane:#f9f9f7;
  --ink-1:#0b0b0b; --ink-2:#52514e; --ink-muted:#898781;
  --grid:#e1e0d9; --axis:#c3c2b7;
  --accent:#2a78d6; --accent-strong:#1c5cab;
  --up:#0ca30c; --down:#d03b3b;
  --border:rgba(11,11,11,0.10);
  --mono:"Consolas","JetBrains Mono","Courier New",monospace;
  --sans:system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
}}
@media (prefers-color-scheme: dark){{
  :root:not([data-theme="light"]){{
    --surface-1:#1a1a19; --plane:#0d0d0d;
    --ink-1:#f0efec; --ink-2:#c3c2b7; --ink-muted:#898781;
    --grid:#2c2c2a; --axis:#383835;
    --accent:#3987e5; --accent-strong:#6da7ec;
    --up:#0ca30c; --down:#e66767;
    --border:rgba(255,255,255,0.10);
  }}
}}
:root[data-theme="dark"]{{
  --surface-1:#1a1a19; --plane:#0d0d0d;
  --ink-1:#f0efec; --ink-2:#c3c2b7; --ink-muted:#898781;
  --grid:#2c2c2a; --axis:#383835;
  --accent:#3987e5; --accent-strong:#6da7ec;
  --up:#0ca30c; --down:#e66767;
  --border:rgba(255,255,255,0.10);
}}
*{{box-sizing:border-box}}
body{{
  margin:0; padding:28px 20px 56px;
  background:var(--plane); color:var(--ink-1);
  font-family:var(--sans); font-size:14px; line-height:1.55;
}}
.wrap{{max-width:1500px; margin:0 auto}}
header h1{{margin:0 0 6px; font-size:clamp(22px,4vw,30px); letter-spacing:-.01em}}
header .sub{{color:var(--ink-2); margin:0 0 20px; font-size:13.5px}}
.kpis{{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:16px 0 28px}}
.kpi{{background:var(--surface-1); border:1px solid var(--border); border-radius:10px; padding:14px 16px}}
.kpi .n{{font-size:24px; font-weight:700; font-variant-numeric:tabular-nums; letter-spacing:-.02em}}
.kpi .l{{font-size:12px; color:var(--ink-2); margin-top:2px}}
.card{{background:var(--surface-1); border:1px solid var(--border); border-radius:12px; padding:20px 22px; margin-bottom:24px}}
.card h2{{font-size:16px; margin:0 0 14px; padding-bottom:10px; border-bottom:1px solid var(--border)}}
svg text{{font-family:var(--sans)}}
.timeline{{position:relative; padding-left:24px}}
.timeline::before{{content:""; position:absolute; left:6px; top:8px; bottom:8px; width:2px; background:var(--grid)}}
.tl-item{{position:relative; padding:10px 0 10px 0}}
.tl-dot{{position:absolute; left:-24px; top:15px; width:14px; height:14px; border-radius:50%; background:var(--accent); border:2px solid var(--surface-1); box-shadow:0 0 0 2px var(--border)}}
.tl-item.milestone .tl-dot{{background:var(--down); box-shadow:0 0 0 2px var(--border)}}
.tl-head{{display:flex; align-items:baseline; gap:10px; flex-wrap:wrap}}
.tl-time{{font-family:var(--mono); font-size:12px; color:var(--ink-muted); white-space:nowrap}}
.tl-hash{{font-family:var(--mono); font-size:12px; color:var(--accent); cursor:default}}
.tl-msg{{font-size:13.5px; margin:2px 0 0}}
.tl-delta{{font-family:var(--mono); font-size:12px; margin-top:3px}}
.tl-delta .add{{color:var(--up)}}
.tl-delta .del{{color:var(--down)}}
.tl-delta .files{{color:var(--ink-muted)}}
.note{{font-size:12px; color:var(--ink-muted); margin-top:12px}}
@media(max-width:560px){{
  body{{padding:20px 14px 40px}}
  .card{{padding:16px 14px}}
}}

.tl-notes{{margin-top:6px; font-size:12.5px; color:var(--ink-2)}}
.tl-notes summary{{cursor:pointer; color:var(--accent); font-size:12px; user-select:none}}
.tl-notes summary:hover{{color:var(--accent-strong)}}
.tl-notes ul{{margin:6px 0 0 18px; padding:0}}
.tl-notes li{{margin:3px 0; line-height:1.5}}

/* ============ 日历视图 ============ */
.lv-0{{--o:0}} .lv-1{{--o:.10}} .lv-2{{--o:.20}} .lv-3{{--o:.32}} .lv-4{{--o:.45}}
.cal-legend{{display:flex; align-items:center; gap:6px; flex-wrap:wrap; font-size:12px; color:var(--ink-muted); margin:-4px 0 18px}}
.cal-swatch{{position:relative; width:12px; height:12px; border:1px solid var(--border); border-radius:3px}}
.cal-swatch::before{{content:""; position:absolute; inset:0; border-radius:2px; background:var(--accent); opacity:var(--o,0)}}
.cal-legend .ms-dot{{width:7px; height:7px; border-radius:50%; background:var(--down); margin-left:10px}}
.cal-wrap{{display:flex; flex-wrap:wrap; gap:24px; align-items:flex-start}}
.cal-month{{flex:1 1 260px; max-width:340px}}
.cal-month-title{{font-size:13px; font-weight:600; margin-bottom:10px; display:flex; align-items:baseline; gap:8px}}
.cal-month-title .cnt{{font-size:11.5px; font-weight:400; color:var(--ink-muted)}}
.cal-weekdays,.cal-days{{display:grid; grid-template-columns:repeat(7,1fr); gap:5px}}
.cal-weekdays div{{font-size:11px; color:var(--ink-muted); text-align:center}}
.cal-cell{{position:relative; aspect-ratio:1/1; border:1px solid var(--border); border-radius:6px; display:flex; align-items:center; justify-content:center; font-family:var(--mono); font-size:13px; color:var(--ink-2)}}
.cal-cell::before{{content:""; position:absolute; inset:0; border-radius:5px; background:var(--accent); opacity:var(--o,0); transition:opacity .15s}}
.cal-cell.empty{{border-color:transparent}}
.cal-cell.empty::before{{content:none}}
.cal-cell.has-data{{color:var(--ink-1); cursor:pointer}}
.cal-cell.has-data:hover::before{{opacity:calc(var(--o,0) + .12)}}
.cal-cell.has-data:focus-visible{{outline:2px solid var(--accent-strong); outline-offset:1px}}
.cal-cell.selected{{box-shadow:0 0 0 2px var(--accent-strong)}}
.cal-num{{position:absolute; top:2px; left:5px; font-size:9.5px; opacity:.65; z-index:1}}
.cal-cnt{{position:relative; z-index:1; font-weight:700}}
.cal-cell.ms::after{{content:""; position:absolute; z-index:2; bottom:3px; left:50%; transform:translateX(-50%); width:4px; height:4px; border-radius:50%; background:var(--down)}}
.cal-detail{{margin-top:20px; border-top:1px solid var(--border); padding-top:14px}}
.cd-head{{display:flex; align-items:baseline; gap:12px; flex-wrap:wrap; margin-bottom:8px}}
.cd-date{{font-weight:600; font-size:13.5px}}
.cd-meta{{font-family:var(--mono); font-size:12px; color:var(--ink-muted)}}
.cd-meta .add{{color:var(--up)}}
.cd-meta .del{{color:var(--down)}}
.cd-list{{list-style:none; margin:0; padding:0}}
.cd-list>li{{padding:8px 0; border-top:1px dashed var(--border)}}
.cd-list>li:first-child{{border-top:none}}
.cd-row{{display:flex; align-items:baseline; gap:10px; flex-wrap:wrap}}
.cd-time{{font-family:var(--mono); font-size:12px; color:var(--ink-muted); white-space:nowrap}}
.cd-msg{{font-size:13px}}
@media(max-width:560px){{
  .cal-month{{max-width:none}}
}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>L2报表 · 项目版本迭代</h1>
    <p class="sub">基于 <code style="font-family:var(--mono)">git log</code>（main 分支）自动生成，展示 L2 集团合并报表从初始化到当前版本的演进轨迹。</p>
  </header>

  <div class="kpis" id="kpis"></div>

  <div class="card">
    <h2>提交日历</h2>
    <div class="cal-legend">
      <span>提交密度</span>
      <i class="cal-swatch lv-0"></i><i class="cal-swatch lv-1"></i><i class="cal-swatch lv-2"></i><i class="cal-swatch lv-3"></i><i class="cal-swatch lv-4"></i>
      <span>少 → 多</span>
      <i class="ms-dot"></i><span>里程碑提交</span>
    </div>
    <div class="cal-wrap" id="calendar"></div>
    <div class="cal-detail" id="calDetail"></div>
  </div>

  <div class="card">
    <h2>版本迭代时间线</h2>
    <div class="timeline" id="timeline"></div>
  </div>

</div>


<script>
const DATA = {data_json};

// 完整提交备注（由 update-version-html.py 维护，去 Co-Authored-By）
const NOTES = {notes_json};

// 摘要统计
const totalAdd = DATA.reduce((s,d)=>s+d.add,0);
const totalDel = DATA.reduce((s,d)=>s+d.del,0);
const totalFiles = DATA.reduce((s,d)=>s+d.files,0);
const days = "{days}";

document.getElementById('kpis').innerHTML = `
  <div class="kpi"><div class="n">${{DATA.length}}</div><div class="l">提交数（main）</div></div>
  <div class="kpi"><div class="n">${{days}} 天</div><div class="l">迭代跨度</div></div>
  <div class="kpi"><div class="n">${{totalFiles}}</div><div class="l">累计变更文件</div></div>
  <div class="kpi"><div class="n" style="color:var(--up)">+${{totalAdd.toLocaleString()}}</div><div class="l">累计新增行</div></div>
  <div class="kpi"><div class="n" style="color:var(--down)">−${{totalDel.toLocaleString()}}</div><div class="l">累计删除行</div></div>
`;

// ============ 时间线 ============
document.getElementById('timeline').innerHTML = DATA.map(d=>`
  <div class="tl-item${{d.ms?' milestone':''}}">
    <span class="tl-dot"></span>
    <div class="tl-head">
      <span class="tl-time">${{d.date}}</span>
      <span class="tl-hash" title="${{d.msg}}">${{d.short}}</span>
    </div>
    <div class="tl-msg">${{d.msg}}</div>
    <div class="tl-delta">
      <span class="add">+${{d.add.toLocaleString()}}</span> /
      <span class="del">−${{d.del.toLocaleString()}}</span>
      <span class="files"> · ${{d.files}} 文件</span>
    </div>
    ${{(NOTES[d.short]||[]).length ? `<details class="tl-notes"><summary>完整备注</summary><ul>${{(NOTES[d.short]||[]).map(x=>`<li>${{x}}</li>`).join('')}}</ul></details>` : ''}}
  </div>
`).join('');

// ============ 日历视图 ============
(function(){{
  const host = document.getElementById('calendar');
  const detail = document.getElementById('calDetail');
  if(!host || !detail) return;

  // 按自然日归并提交
  const byDate = new Map();
  DATA.forEach(d=>{{
    const day = (d.date||'').slice(0,10);
    if(!day) return;
    if(!byDate.has(day)) byDate.set(day, []);
    byDate.get(day).push(d);
  }});
  const dayKeys = [...byDate.keys()].sort();
  if(!dayKeys.length){{ host.innerHTML = '<p class="note">暂无提交记录。</p>'; return; }}
  const maxCount = Math.max(...dayKeys.map(k=>byDate.get(k).length));

  // 提交数 → 密度等级 1~4
  function level(n){{
    if(maxCount <= 1) return 4;
    const r = n / maxCount;
    if(r <= .25) return 1;
    if(r <= .50) return 2;
    if(r <= .75) return 3;
    return 4;
  }}

  const pad = n => String(n).padStart(2, '0');
  const WEEK = ['日','一','二','三','四','五','六'];
  const HEAD = ['一','二','三','四','五','六','日'];

  // 首末提交之间覆盖到的所有月份
  const [fy, fm] = dayKeys[0].split('-').map(Number);
  const [ly, lm] = dayKeys[dayKeys.length-1].split('-').map(Number);
  const months = [];
  for(let y = fy, m = fm; y < ly || (y === ly && m <= lm); m++){{
    months.push([y, m]);
    if(m === 12){{ m = 0; y++; }}
  }}

  let html = '';
  months.forEach(([y, m])=>{{
    const lead = (new Date(y, m-1, 1).getDay() + 6) % 7;   // 周一为第一列
    const total = new Date(y, m, 0).getDate();
    let hits = 0, busyDays = 0, cells = '';
    for(let i = 0; i < lead; i++) cells += '<div class="cal-cell empty"></div>';
    for(let d = 1; d <= total; d++){{
      const key = `${{y}}-${{pad(m)}}-${{pad(d)}}`;
      const list = byDate.get(key);
      if(!list){{
        cells += `<div class="cal-cell"><span class="cal-num">${{d}}</span></div>`;
        continue;
      }}
      hits += list.length; busyDays += 1;
      const ms = list.some(x=>x.ms) ? ' ms' : '';
      cells += `<div class="cal-cell has-data lv-${{level(list.length)}}${{ms}}" data-date="${{key}}" tabindex="0" role="button"`
             + ` title="${{key}} · ${{list.length}} 次提交" aria-label="${{key}}，${{list.length}} 次提交">`
             + `<span class="cal-num">${{d}}</span><span class="cal-cnt">${{list.length}}</span></div>`;
    }}
    html += `<div class="cal-month">`
          + `<div class="cal-month-title">${{y}} 年 ${{m}} 月<span class="cnt">${{hits}} 次提交 · ${{busyDays}} 天</span></div>`
          + `<div class="cal-weekdays">${{HEAD.map(w=>`<div>${{w}}</div>`).join('')}}</div>`
          + `<div class="cal-days">${{cells}}</div>`
          + `</div>`;
  }});
  host.innerHTML = html;

  // 选中某天 → 展开当天明细
  function renderDetail(key){{
    host.querySelectorAll('.cal-cell.selected').forEach(el=>el.classList.remove('selected'));
    const cell = host.querySelector(`.cal-cell[data-date="${{key}}"]`);
    if(cell) cell.classList.add('selected');
    const list = byDate.get(key) || [];
    if(!list.length){{ detail.innerHTML = ''; return; }}
    const add = list.reduce((s,d)=>s+d.add, 0);
    const del = list.reduce((s,d)=>s+d.del, 0);
    const files = list.reduce((s,d)=>s+d.files, 0);
    const wd = WEEK[new Date(key + 'T00:00:00').getDay()];
    detail.innerHTML = `<div class="cd-head">`
        + `<span class="cd-date">${{key}} 周${{wd}}</span>`
        + `<span class="cd-meta">${{list.length}} 次提交 · ${{files}} 文件 · `
        + `<span class="add">+${{add.toLocaleString()}}</span> / <span class="del">−${{del.toLocaleString()}}</span></span>`
      + `</div><ul class="cd-list">`
      + list.map(d=>`<li>`
          + `<div class="cd-row"><span class="cd-time">${{(d.date||'').slice(11)}}</span>`
          + `<span class="tl-hash">${{d.short}}</span><span class="cd-msg">${{d.msg}}</span></div>`
          + `<div class="tl-delta"><span class="add">+${{d.add.toLocaleString()}}</span> / `
          + `<span class="del">−${{d.del.toLocaleString()}}</span><span class="files"> · ${{d.files}} 文件</span></div>`
          + `${{(NOTES[d.short]||[]).length ? `<details class="tl-notes"><summary>完整备注</summary><ul>${{NOTES[d.short].map(x=>`<li>${{x}}</li>`).join('')}}</ul></details>` : ''}}`
          + `</li>`).join('')
      + `</ul>`;
  }}

  host.addEventListener('click', e=>{{
    const cell = e.target.closest('.cal-cell.has-data');
    if(cell) renderDetail(cell.dataset.date);
  }});
  host.addEventListener('keydown', e=>{{
    if(e.key !== 'Enter' && e.key !== ' ') return;
    const cell = e.target.closest('.cal-cell.has-data');
    if(cell){{ e.preventDefault(); renderDetail(cell.dataset.date); }}
  }});

  // 默认选中最近一个有提交的日子
  renderDetail(dayKeys[dayKeys.length-1]);
}})();

</script>
</body>
</html>
"""


def main():
    root = repo_root()
    commits = collect_commits(root)
    if not commits:
        print("未找到任何提交记录。")
        return
    html = build_html(commits, NOTES)
    out_path = os.path.join(root, "L2报表项目版本迭代.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成 {out_path}（共 {len(commits)} 个提交）")


if __name__ == "__main__":
    main()

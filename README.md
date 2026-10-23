# 耿想 · AI 产品 / 用户研究作品集

> 我把用户洞察，变成可落地的产品方案。

康奈尔高级城市设计硕士在读，建筑学背景，转向 AI 产品方向。做过问卷调研、评论数据挖掘和多方需求取舍，独立完成 AI 作品集点评助手原型（纯前端 + DeepSeek API）并部署上线。

## 线上地址

**https://xg366-source.github.io/portfolio/**

部署在 GitHub Pages（仓库：`xg366-source/portfolio`）。推送 `main` 分支后自动更新。

## 站点内容

| 板块 | 说明 |
|---|---|
| 产品与研究案例 | AI 作品集点评助手（独立完成的 AI 产品原型）、Conflux Strand（社媒数据挖掘 + 多情景取舍）、The Topology Engine（两轮问卷 + 多准则评估） |
| 设计背景 | 4 个建筑设计作品（疗愈滨水空间 / 纪念性建筑 / 幼儿园 / 社区改造），折叠展示 |
| 关于 | 产品化中文自我介绍 · 工具（AI/产品前置）· 研究焦点 |
| 联系 | 邮箱 / GitHub / 产品方向简历下载 / 建筑作品集 PDF |

## 目录结构

```
portfolio-website/
├── index.html                        # 中文产品定位首页（hero + 案例 + 设计背景折叠 + 关于 + 联系）
├── projects/
│   ├── ai-portfolio-reviewer.html    # 案例 01 · AI 产品原型（含在线体验入口）
│   ├── conflux-strand.html           # 案例 02 · 用户研究
│   ├── the-topology-engine.html      # 案例 03 · 需求调研
│   └── design/                       # 设计背景（4 个建筑作品详情页）
├── ai-portfolio-reviewer/            # AI 作品集点评助手原型（单页应用，可独立运行）
├── assets/
│   ├── css/style.css                 # 全局样式（系统字体栈 + 苔绿强调）
│   ├── js/main.js                    # 滚动淡入 / 导航状态 / 折叠交互 / 回到顶部
│   └── images/                       # 案例封面、图纸与原型截图（均已压缩）
└── downloads/
    ├── 耿想简历-产品方向.pdf          # 产品方向简历（主下载）
    └── Geng-Xiang-Portfolio.pdf      # 建筑作品集 PDF（次要下载）
```

## AI 作品集点评助手（可独立部署）

`ai-portfolio-reviewer/index.html` 是自包含的单页原型，无外部依赖：

- 上传 PDF → 本地渲染页面截图 → 调用 DeepSeek API 返回带页码证据、具体改法与置信度的 Top3 建议
- API Key 仅存浏览器 localStorage，PDF 原文件不离开本机（隐私优先）
- 无 Key 时可走内置演示模式，完整体验点评流程

## 本地预览

在目录下启动静态服务器：

```bash
python -m http.server 8000
# 浏览器访问 http://localhost:8000
```

## 维护说明

- 改文案：编辑 `index.html` 与 `projects/*.html`（案例页按"背景与目标 / 用户与问题 / 洞察 / 方案与取舍 / 方法与数据 / 结果 / 我的角色与复盘"七段结构维护）
- 换图片：替换 `assets/images/` 下同名文件，新图压缩到 400KB 以内
- 改配色：编辑 `assets/css/style.css` 顶部 `--moss`（强调色）、`--mist`（背景色）变量
- 案例页缺失的真实数据（问卷份数、评论条数等）以"待补充"占位标注，取得真实数字后同步更新

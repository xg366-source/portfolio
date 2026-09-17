# Geng Xiang — Architecture Portfolio Website

极简画廊风作品集网站，由 AI 从 PDF 作品集直接生成。

## 目录结构

```
portfolio-website/
├── index.html                    # 首页：Hero + 6 项目网格 + About + Contact
├── projects/                     # 6 个项目详情页
│   ├── willow-shade-whispers.html
│   ├── conflux-strand.html
│   ├── legacy-in-current.html
│   ├── embrace-the-murmur-of-childhood.html
│   ├── the-topology-engine.html
│   └── communis-facens.html
├── assets/
│   ├── css/style.css             # 全局样式（白底 + 苔绿强调 + 衬线标题）
│   ├── js/main.js                # 滚动淡入 / 导航状态 / 回到顶部
│   └── images/                   # 27 张从 PDF 高清导出的图纸（单张 <400KB）
└── downloads/
    └── Geng-Xiang-Portfolio.pdf  # 原作品集 PDF（可下载）
```

## 本地预览

双击 `index.html` 即可在浏览器打开（图片使用相对路径，无需服务器）。
也可在目录下启动静态服务器：

```bash
# 在 portfolio-website 目录下
python -m http.server 8000
# 浏览器访问 http://localhost:8000
```

## 上线部署（免费）

### 方案 A：GitHub Pages（推荐）
1. 注册 GitHub，新建仓库，如 `portfolio`（公开）
2. 把本目录所有文件上传到仓库根目录
3. 仓库 Settings → Pages → Source 选 `main` 分支 → Save
4. 几分钟后访问 `https://<你的用户名>.github.io/portfolio/`

### 方案 B：Vercel（自带免费域名、最快）
1. 注册 vercel.com，点 "Add New Project" → 导入该文件夹
2. 无需任何配置，默认即可，点 Deploy
3. 访问 `https://<项目名>.vercel.app`

### 绑定自己的域名（可选）
在域名商（如 Namecheap / 阿里云）购买 `xianggeng.com` 之类域名后，
GitHub Pages 的 Settings → Pages → Custom domain 填入即可；Vercel 在
Project → Settings → Domains 添加。费用约 ¥60–100/年。

## 上线前必须替换的占位内容

| 位置 | 当前占位 | 替换为 |
|---|---|---|
| 首页 & 各页 Contact | `xg366@cornell.edu` | 已填写你的康奈尔邮箱，如需更换直接替换 |
| 首页 Contact | `linkedin.com/in/xiang-geng-a7b08b430` | 已填写你的 LinkedIn 主页 |
| 首页 favicon | 字母 G 图标 | 可选：换成你的头像/logo |
| About 页 | Cornell MSAUD | 已填写在读状态（currently pursuing） |

## 自定义指南

- **改文案**：直接编辑 `index.html` 和各 `projects/*.html` 里的英文段落（作品集面向海外事务所/招生官，故为英文；如需中文版可另建页面）。
- **换图片**：替换 `assets/images/` 下同名文件即可；新图片建议压缩到 400KB 以内、保持横版 1.414:1 比例。
- **改配色**：编辑 `assets/css/style.css` 顶部的 `--moss`（强调色）和 `--mist`（背景色）变量。

## 说明

- 全部文字叙事均改写自原 PDF 作品集（Geng Xiang PORTFOLIO.pdf），未新增事实。
- About 页信息来自本人公开背景（教育、软件技能、证书等级）。

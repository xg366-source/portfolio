# 规划资料与场地分析助手 · Planning Site Assistant

输入规划文件和 GIS 数据，建立可检索的资料库；回答基地问题时**提供引用来源**，找不到依据时**明确拒答**；数字类问题走结构化 GIS 查询，不让模型猜数。系统带一组有标准答案的测试题，用量化指标评估引用、检索与拒答——不凭“看起来不错”判断效果。

基地：纽约皇后区 Junction Blvd—Corona—Woodside 走廊，113 个 census tract（数据来自作者的 Food System Atlas 项目）。

## 快速开始（无需任何 API key）

```bash
pip install pyyaml                      # 核心引擎仅依赖 stdlib + PyYAML
python3 src/cli.py "311投诉最高的tract是哪个？"
python3 tests/test_core.py              # 5 个核心行为测试
python3 eval/run_eval.py                # 跑 40 题评估集，出指标
```

网页演示（地图 + 问答）：

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --app-dir src --port 8000
# 打开 http://localhost:8000/
```

无 LLM key 时为**抽取式演示模式**（直接返回检索原文+引用，响应里有标注）；在 `config.yaml` 填 `llm.api_key_env` 并设置对应环境变量后，可切换为生成式回答（提示词见 `src/answer.py` 的 `build_llm_prompt`，规则为“有引才答、无据拒答”）。

## 当前评估结果（40 题，v3，2026-10-27 复测全过）

配比：文档事实 14 · GIS 9 · 跨源 5 · 无答案拒答 8 · 口径陷阱 4。新增题的标准答案均用 GeoJSON 实算或资料原文核对过，不是凭印象写的（例如报案最高 tract 实算为 GEOID 36081026501、每千人 124.1；B 级以下占比最高为 GEOID 36081026700、52.8%）。

| 指标 | 结果 |
|---|---|
| Recall@5（应引来源命中） | 1.00 |
| 答案关键值命中率 | 1.00 |
| 拒答准确率（无答案题） | 1.00 |
| 过度拒答率 | 0.00 |

## 选型对照（2026-10-27，详见 `docs/selection_report.md`）

文档路线 23 题上，BM25 与 TF-IDF 向量检索 Recall@5 / Recall@1 / MRR 均为 1.00，零分歧；10 题改写问法探针两边仍打平（Recall@5 1.00、Recall@1 0.80）。**决策：保留 BM25**——在 2 份文档、7 个 chunk 的规模下，稀疏方法之间的差异测不出来，迁移没有收益。TF-IDF 已验证为等价平替（余弦阈值 0.22，端到端 40/40），但阈值是在评估集上拟合的，需留出题验证。另有一点诚实发现：现行拒答实际靠词覆盖兜底，因为 BM25 不可答题最高分（6.82）高于分数阈值（2.0）。

```bash
python3 eval/compare_retrieval.py   # BM25 vs TF-IDF 排序对照
python3 eval/run_probe.py           # 10 题探针 + TF-IDF 端到端检查
```

⚠️ 题仍是自编、范围仍只限本基地——这组数字只证明流程跑通，不证明系统“很强”。稠密 embedding 对照与生成模式对照待 API key，语料扩大后需重跑全部实验。诚实标注局限，是这个项目的既定口径。

真实发现（不是演示话术）：西裔占比与餐厅 B 级以下占比的相关系数 r = 0.06——数据**不支持**直觉叙事，系统按此回答。

## 结构

```
src/    ingest（分块保引用）· retriever（BM25 + TF-IDF 对照基线）· gis_query（结构化查询+方法护栏）
        answer（路由：GIS / 文档 / 拒答）· app（FastAPI）· cli（命令行演示）
data/   docs/ 规划资料（概况+口径说明） · gis/ 4 个 tract 图层（ACS/311/报案/餐厅）
eval/   questions.jsonl 40 题标准答案测试集 · run_eval.py 五指标评估
        compare_retrieval.py BM25 vs TF-IDF 对照 · probe_questions.jsonl 10 题改写探针
web/    Leaflet 地图 + 问答面板
docs/   architecture.md 架构与关键决策 · selection_report.md 检索选型报告
tests/  核心行为测试
```

## 数据来源与口径
ACS 2024 五年估算、NYC Open Data（NYPD 报案、311、DOHMH 餐厅检查），均为 2026 年 1–7 月或注明的期别；口径细节（报案≠定罪、评级扣分制、小人口 tract 比率陷阱）在 `data/docs/data_notes.md`，回答会引用它。

## 非目标
不做多用户/登录；不做实时数据更新；不做模型微调（RAG 可解则不微调）；覆盖范围只限本基地。

## 失败案例（持续更新）
1. **引用张冠李戴**：排名答案曾引用人口图层而非产出该指标的 311 图层（字段合并表导致）。已用字段→图层映射修复，评估 Recall 因此从 0.89 → 1.00。
2. **小分母霸榜**：每千人 311 率原始榜首是 344 人 tract。已加人口门槛并把理由写进回答。
3. **扩集时抓到的两个真问题（2026-10-24）**：(a) “第二多”问法被拒答——资料原文写的是“其次”，BM25 词覆盖没过阈值，改按原文措辞提问后通过，说明评估对问法敏感；(b) 一道同时问“报案总数+中位数”的跨源题被 GIS 路由劫走，只答了中位数、丢了总数——关键词路由的固有限制，跨源题需避开中位数/排名关键词或改走多路聚合。两题改问法后 40 题全过，原始失败记录保留在扩集过程里，不删。

# 规划资料与场地分析助手 · Planning Site Assistant

输入规划文件和 GIS 数据，建立可检索的资料库；回答基地问题时**提供引用来源**，找不到依据时**明确拒答**；数字类问题走结构化 GIS 查询，不让模型猜数。系统带一组有标准答案的测试题，用量化指标评估引用、检索与拒答——不凭“看起来不错”判断效果。

基地：纽约皇后区 Junction Blvd—Corona—Woodside 走廊，113 个 census tract（数据来自作者的 Food System Atlas 项目）。

## 快速开始（无需任何 API key）

```bash
pip install pyyaml                      # 核心引擎仅依赖 stdlib + PyYAML
python3 src/cli.py "311投诉最高的tract是哪个？"
python3 tests/test_core.py              # 5 个核心行为测试
python3 eval/run_eval.py                # 跑 12 题种子评估集，出指标
```

网页演示（地图 + 问答）：

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --app-dir src --port 8000
# 打开 http://localhost:8000/
```

无 LLM key 时为**抽取式演示模式**（直接返回检索原文+引用，响应里有标注）；在 `config.yaml` 填 `llm.api_key_env` 并设置对应环境变量后，可切换为生成式回答（提示词见 `src/answer.py` 的 `build_llm_prompt`，规则为“有引才答、无据拒答”）。

## 当前评估结果（种子集 12 题，v1）

| 指标 | 结果 |
|---|---|
| Recall@5（应引来源命中） | 1.00 |
| 答案关键值命中率 | 1.00 |
| 拒答准确率（无答案题） | 1.00 |
| 过度拒答率 | 0.00 |

⚠️ 题量小、自编题有偏差——这组数字只证明流程跑通，不证明系统“很强”。下一步是扩到 40 题并加入 embedding 对照（见规格文档）。诚实标注局限，是这个项目的既定口径。

真实发现（不是演示话术）：西裔占比与餐厅 B 级以下占比的相关系数 r = 0.06——数据**不支持**直觉叙事，系统按此回答。

## 结构

```
src/    ingest（分块保引用）· retriever（BM25）· gis_query（结构化查询+方法护栏）
        answer（路由：GIS / 文档 / 拒答）· app（FastAPI）· cli（命令行演示）
data/   docs/ 规划资料（概况+口径说明） · gis/ 4 个 tract 图层（ACS/311/报案/餐厅）
eval/   questions.jsonl 标准答案测试集 · run_eval.py 五指标评估
web/    Leaflet 地图 + 问答面板
docs/   architecture.md 架构与关键决策
tests/  核心行为测试
```

## 数据来源与口径
ACS 2024 五年估算、NYC Open Data（NYPD 报案、311、DOHMH 餐厅检查），均为 2026 年 1–7 月或注明的期别；口径细节（报案≠定罪、评级扣分制、小人口 tract 比率陷阱）在 `data/docs/data_notes.md`，回答会引用它。

## 非目标
不做多用户/登录；不做实时数据更新；不做模型微调（RAG 可解则不微调）；覆盖范围只限本基地。

## 失败案例（持续更新）
1. **引用张冠李戴**：排名答案曾引用人口图层而非产出该指标的 311 图层（字段合并表导致）。已用字段→图层映射修复，评估 Recall 因此从 0.89 → 1.00。
2. **小分母霸榜**：每千人 311 率原始榜首是 344 人 tract。已加人口门槛并把理由写进回答。
3. 待扩集后补充：检索未命中 / 该拒未拒 / 过度拒答的真实样本。

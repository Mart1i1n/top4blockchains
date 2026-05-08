# sec-blockchain-papers

从 DBLP 抽取 NDSS / USENIX Security / IEEE S&P / ACM CCS 中区块链相关论文，输出 Markdown 清单和作者统计。

数据源是 DBLP 的会议 XML（带作者 PID，所以可以靠 PID 合并不同写法）。分类靠关键词 + 人工拍板，**不调 LLM**。

---

## 安装

需要 Python 3.11+ 和 [uv](https://github.com/astral-sh/uv)。

```bash
uv sync --extra dev
```

---

## 三种典型用法

### 用法 1：直接看 2025 年的结果

2025 年的 `manual_overrides.yaml` 已经填好，跑一把就出结果：

```bash
make 2025
```

产出：
- [output/2025/papers.md](output/2025/papers.md) — 57 篇区块链论文清单
- [output/2025/authors.md](output/2025/authors.md) — 作者统计

想确认没坏：

```bash
make test    # pytest，锁住 Sisi Duan=5 / Aniket Kate=4 / Xiapu Luo=4 等
make lint    # ruff
```

### 用法 2：跑新年份（最常见）

比如 CCS 2026 出了新论文：

#### 第 1 步：拉数据 + 跑初分类

```bash
make YEAR=2026 fetch classify
```

输出会告诉你三个桶各多少：

```
[classify] 1XXX papers -> data/2026/classified.yaml
    exclude: 12XX
    include: ~50
    needs_review: ~30
```

`include` 是关键词强匹配，基本可以信。`exclude` 量大但绝大多数确实无关。**人工工作集中在 `needs_review`**。

#### 第 2 步：审 needs_review

打开 `data/2026/classified.yaml`，搜 `status: needs_review`。每条长这样：

```yaml
- dblp_key: conf/ccs/Yu0WD025
  title: AD-MPC: Asynchronous Dynamic MPC with Guaranteed Output Delivery
  conference: ACM CCS
  year: 2026
  auto_status: needs_review
  matched_keywords: [mpc]
  status: needs_review
  reason: only in-context keyword(s) matched; abstract check or manual review required
```

逐条扫，必要时点 DBLP 链接读 abstract，判断是 include 还是 exclude，**写到 `config/manual_overrides.yaml`**：

```yaml
overrides:
  - dblp_key: conf/ccs/Yu0WD025
    status: include
    reason: "AD-MPC -- 异步动态 MPC，目标场景是 blockchain 委员会重配置"
```

> ⚠️ **不要直接改 `classified.yaml`。** 它每次 classify 重生成，改了会被覆盖。`manual_overrides.yaml` 才是源头，需要 commit。

#### 第 3 步（可选）：扫 exclude 找漏网之鱼

纯关键词匹配会漏掉标题完全看不出区块链信号的论文。比如 2025 年的 *Surviving in Dark Forest*——标题完全没有币圈词，但实际是 MEV 抢跑相关。

实操办法：

- 读会议官方接收列表（USENIX / IEEE S&P 官网都按 session 列了），扫一遍 blockchain / cryptocurrency / smart contract 相关 session。
- 每篇标题在 `classified.yaml` 里搜一搜，如果被 `exclude` 了就在 `manual_overrides.yaml` 里加一条 `status: include`。

#### 第 4 步：跑剩下三步

```bash
make YEAR=2026
```

全流程重跑（classify 应用刚加的 overrides → normalize → stats → render），输出 `output/2026/papers.md` 和 `authors.md`。

#### 第 5 步：检查作者统计

打开 `authors.md`，扫 ≥3 篇那张表。如果某个名字明显该高频但低了，多半是 DBLP 里他/她有两个 PID 没合并。在 `config/author_aliases.yaml` 里加一条：

```yaml
aliases:
  "Roi Bar Zur": "Roi Bar-Zur"
```

然后 `make YEAR=2026 normalize stats`。

### 用法 3：扩关键词

新公链 / 新热点出现了，比如 2026 年某个新 L2 叫 "Foochain"，几篇相关论文标题都带这个词但当前 keywords 不认。

编辑 `config/keywords.yaml`：

```yaml
positive_strong:
  - blockchain
  - ethereum
  - foochain          # 新加
  ...
```

`make YEAR=2026 classify normalize stats render` 即可。**不需要重 fetch**——raw JSON 已经缓存在 `data/2026/raw/` 里了。

---

## 一个迭代回路是这样的

```
fetch (~10s)
   ↓
classify (秒级)
   ↓
你看 classified.yaml needs_review 那几十条 ←─┐
   ↓                                          │
编辑 manual_overrides.yaml                    │
   ↓                                          │
classify normalize stats render (秒级)         │
   ↓                                          │
扫 papers.md 和 authors.md 看有没有怪          │
   ↓                                          │
发现 false negative / alias 问题 ─────────────┘
```

每轮迭代几秒，主要时间花在你读 needs_review 标题做判断上。

---

## 关键文件

只有这三个 YAML 是要 commit 且需要你维护的：

| 文件 | 谁来改 | 用途 |
|---|---|---|
| `config/keywords.yaml` | 偶尔（出现新领域词时） | 决定哪些 title 关键词触发 include / needs_review |
| `config/manual_overrides.yaml` | 每个新年份 | 强制设置某篇的最终状态（DBLP key 索引） |
| `config/author_aliases.yaml` | 偶尔（DBLP 漏合并时） | 把不同写法映射到同一个 canonical 名字 |

下面这些是**生成的**，可以 commit 也可以 .gitignore：

| 文件 | 谁来生成 |
|---|---|
| `data/<year>/raw/*.json` | `fetch.py`（DBLP 原始数据，只在重跑时变） |
| `data/<year>/classified.yaml` | `classify.py`（每次重生成） |
| `data/<year>/papers.yaml` | `normalize.py` |
| `output/<year>/papers.md` | `render.py` |
| `output/<year>/authors.md` | `stats.py` |

---

## 分类规则

`classify.py` 对标题做大小写不敏感的 word-boundary 匹配（允许复数尾 `s`，把 `-`/`_` 归一为空格）：

| 命中情况 | 状态 |
|---|---|
| 任意 `positive_strong` 命中，且无 `negative_overrides` | `include` |
| 仅 `positive_in_context` 命中 | `needs_review` |
| 任意 positive 命中且 `negative_overrides` 也命中 | `needs_review` |
| 都没命中 | `exclude` |

`positive_strong` 是无歧义的区块链词（"blockchain"、"ethereum"、"smart contract"…）。
`positive_in_context` 是密码学/分布式系统也用的词（"bft"、"mpc"、"consensus"、"dag"…），命中后需要确认是不是用在区块链场景。
`negative_overrides` 是"即使命中正向词也很可能不是区块链"的信号（"homomorphic encryption"、"federated learning"…）。

最后 `manual_overrides.yaml` 一锤定音。`classified.yaml` 里保留 `auto_status` 字段供审阅。

抽象/摘要二次确认暂未实现，`needs_review` 全部走人工。

---

## 命令速查

```bash
make 2025                         # 跑 2025 全流程
make YEAR=2026 fetch              # 只拉 2026 raw
make YEAR=2026 classify           # 只跑分类（应用 overrides）
make YEAR=2026 normalize          # 只做作者归一
make YEAR=2026 stats              # 只生成 authors.md
make YEAR=2026 render             # 只生成 papers.md
make YEAR=2026                    # 全流程

make test                         # pytest
make lint                         # ruff
make clean                        # 删除某年生成产物（YEAR=...）
```

也可以直接调脚本：

```bash
uv run python -m scripts.fetch     --year 2026
uv run python -m scripts.classify  --year 2026
uv run python -m scripts.normalize --year 2026
uv run python -m scripts.stats     --year 2026
uv run python -m scripts.render    --year 2026
```

---

## 2025 当前状态

跑完 `make 2025`，输出共 **57 篇**（NDSS 13 + USENIX 18 + CCS 12 + S&P 14），与手工核对的 `blockchain_papers_2025.md` 完全对齐。

回归测试 (`tests/test_pipeline_2025.py`) 锁住的合并 case：

- `Sisi Duan` = 5 篇
- `Aniket Kate` = 4 篇
- `Xiapu Luo` = 4 篇
- `Surviving in Dark Forest` 第二作者 = `Muhui Jiang`
- `AD-MPC` 在关键词阶段被分到 `needs_review`（仅命中 `mpc`），由 `manual_overrides.yaml` 升为 include

### 已被 manual_overrides 排除的边界论文

自动分类捞出 6 篇标题确实带区块链信号、但手工版没收的论文。当前默认跟手工版对齐：

| DBLP key | 标题 |
|---|---|
| `conf/ccs/CaprettoCAM025` | A Secure Sequencer and Data Availability Committee for Rollups |
| `conf/ccs/ChakrabartiMMS25` | Silent Threshold Traitor Tracing & Enhancing Mempool Privacy |
| `conf/ccs/Fu25` | Towards Explainable and Effective Anti-Money Laundering for Cryptocurrency |
| `conf/sp/ZhaoSCZ25` | MicroNova: Folding-Based Arguments with Efficient (On-Chain) Verification |
| `conf/uss/BormetFOQ25` | BEAT-MEV: Epochless Approach to Batched Threshold Encryption for MEV Prevention |
| `conf/uss/ChoudhuriGP025` | Practical Mempool Privacy via One-time Setup Batched Threshold Encryption |

如果想要更宽口径，把它们在 `manual_overrides.yaml` 里改成 `status: include` 即可。

### 已知 DBLP 数据差异

USENIX 那篇 *Polygon zkEVM*，DBLP 给的作者列表与手工版有两个名字不同：

- DBLP：`Kunsong Zhao` / `Zuchao Ma`
- 手工版：`Kaidi Zhao` / `Zheyuan Ma`

仓库默认信 DBLP，不做特殊处理。

---

## 仓库结构

```
sec-blockchain-papers/
├── config/
│   ├── keywords.yaml             # positive_strong / positive_in_context / negative_overrides
│   ├── author_aliases.yaml       # 给 DBLP 漏合并的少数作者
│   └── manual_overrides.yaml     # 强制 include / exclude 某篇 (DBLP key)
├── data/<year>/
│   ├── raw/                      # DBLP 原始 JSON（fetch.py 产出）
│   ├── classified.yaml           # 分类结果（classify.py 产出，每次重生成）
│   └── papers.yaml               # 最终入选（normalize.py 产出）
├── scripts/
│   ├── conferences.py            # 会议元数据
│   ├── fetch.py                  # DBLP XML -> JSON
│   ├── classify.py               # 关键词两段式分类
│   ├── normalize.py              # PID 归一 + 别名
│   ├── stats.py                  # output/<year>/authors.md
│   └── render.py                 # output/<year>/papers.md
├── output/<year>/
│   ├── papers.md
│   └── authors.md
└── tests/
```

---

## 第一期不做

- 完整机构补抓（DBLP 没有，需要从会议官网二次抓）
- LLM 辅助分类 / 摘要二次确认（现在全靠人工 needs_review）
- GitHub Actions 自动化
- 历史年份回填（脚本本身已支持，只是没人填过往年份的 manual_overrides）

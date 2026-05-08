# Reddit User Churn Prediction

## Research Question

Do Reddit users show detectable behavioral shifts in language use and social network activity before they disengage, and does combining NLP-based features with social network features produce meaningfully better churn predictions than either feature type used alone?

---

## Data

Three subreddits collected via Arctic Shift (observation window: subreddit creation to January 1, 2026):

| Subreddit | Type | Raw Posts | Raw Comments |
|---|---|---|---|
| r/learnprogramming | Technology learning | ~646K | ~4.51M |
| r/loseit | Lifestyle / weight loss | ~704K | ~8.59M |
| r/depression | Mental health | ~1.96M | ~6.82M |

**Filtering steps applied to all three subreddits:**
1. Remove `[deleted]` / `[removed]` authors
2. Remove duplicate posts/comments (same author + same content)
3. Remove known bots
4. Remove users in the bottom 5% of activity (threshold computed per subreddit)

---

## Pipeline

```
EDA 
    │
    ▼
Phase 1: Churn Labeling (holdout-based)
    │   └─ Output: churned / active label per user (Y)
    │
    ▼
Phase 2: Feature Engineering (X)
    │   ├─ NLP features (content-level)
    │   └─ Network features (structural-level)
    │
    ▼
Phase 3: Model Training
    │   ├─ Model A: NLP features only
    │   ├─ Model B: Network features only
    │   └─ Model C: NLP + Network (combined)
    │   Each model trained with Logistic Regression + Random Forest
    │
    ▼
Phase 4: Evaluation & Cross-subreddit Comparison
        └─ AUC-ROC, F1, SHAP feature importance
```

---

## Phase 1: Churn Labeling

Churn is defined using a holdout period. A user is classified as **churned** (`y = 1`) if they made no posts or comments during the holdout period; otherwise they are classified as **active** (`y = 0`).

**Calibration period:** subreddit creation -> July 1, 2025

**Holdout period:** July 1, 2025 -> January 1, 2026 (6 months)

**Procedure:**
1. Split each user's activity into calibration and holdout periods
2. For each user, check whether they posted or commented at any point during the holdout period
3. Label as **churned** (`y = 1`) if no activity in holdout; otherwise **active** (`y = 0`)

**Note on BG/NBD:** The BG/NBD model was initially considered for churn labeling because it estimates each user's dropout probability from their posting history, which is better suited for users with irregular activity patterns. However, the model failed to converge on all three subreddits, most likely due to the wide range of observation periods in the data (from a few weeks to over 15 years). The holdout-based definition is used instead, which is standard practice in non-contractual churn research.

---

## Phase 2: Feature Engineering

All features are computed from the **calibration period only**.

### NLP Features (content-level signals)

| Feature | Description | Method |
|---|---|---|
| Sentiment trajectory | Weekly average VADER sentiment score + slope of change over time | VADER |
| Lexical diversity | Type-token ratio per time window (unique words / total words) | Text stats |
| Average post length | Mean word count per text post | Text stats |
| Average comment length | Mean word count per comment | Text stats |
| Post-to-comment ratio | Share of contributions that are posts vs. comments | Activity stats |

### Network Features (structural signals)

Features are computed from the reply graph (directed: user A replied to user B).

**Static structural features** (Krebs 2002; ICTS 2002; Homophily & Descriptive Measures):

| Feature | Description |
|---|---|
| Out-degree | Number of replies sent |
| In-degree | Number of replies received |
| Local clustering coefficient | How tightly connected a user's neighbors are to each other |
| K-core number | Maximum k-core the user belongs to; distinguishes core vs. peripheral users |

**Dynamic/temporal features:**

| Feature | Description |
|---|---|
| Interaction diversity | Number of unique users interacted with per time window + trend (slope) |
| Temporal interaction frequency | Interaction count per time window + trend (slope) |

**Community-level features** (Modularity / Community Detection; Structural Holes):

| Feature | Description |
|---|---|
| Community size | Size of the Louvain community the user belongs to |
| Within-community activity share | Fraction of interactions within vs. outside the user's community |

---

## Phase 3: Model Training

Three feature configurations are tested on **all three subreddits**:

| Model | Features Used |
|---|---|
| Model A | NLP features only |
| Model B | Network features only |
| Model C | NLP + Network (combined) |

Each configuration is trained with two classifiers:
- **Logistic Regression** (interpretable baseline)
- **Random Forest** (captures nonlinear interactions)

**Class imbalance:** Handled with SMOTE oversampling or class-weighted loss.

---

## Phase 4: Evaluation

**Primary metrics:** AUC-ROC, F1-score

**Secondary metrics:** Precision, Recall

**Feature importance:** SHAP values applied to Model C (combined) to identify which features drive predictions.

**Cross-subreddit comparison:** If Model C consistently outperforms Models A and B across all three subreddits, this supports the conclusion that NLP and network features capture complementary dimensions of user disengagement. If the improvement is community-specific, that is also an informative finding about how disengagement works differently across contexts.

---


## Project Structure

```
final_proposal/
├── code/
│   └── EDA.ipynb          # Exploratory data analysis (all 3 subreddits)
├── data/
│   ├── learnprogramming/  # r/learnprogramming posts + comments
│   ├── loseit/            # r/loseit posts + comments
│   └── depression/        # r/depression posts + comments
├── figures/               # EDA figures
├── 参考/                  # Reference papers and prior proposals
└── README.md
```








## 我自己看的

**整个研究的逻辑，只有一条主线：**
"能不能用用户的行为数据，预测他们会不会离开这个社区（churn）？"

**第一步：制造答案（Y标签）—— BG/NBD 的作用**
BG/NBD 模型只做一件事：判断每个用户"还活着"还是已经"流失"了。

它的输入就是你 EDA 里已经算好的三个数：

frequency：这个用户回来过几次
recency：第一次到最后一次之间隔了多久
T：他从加入到现在总共多久
输出就是每个用户一个概率值 p_alive：

p_alive 接近 1 → 用户还活跃
p_alive 接近 0 → 用户已经流失（churn）
然后你设一个门槛，比如 p_alive < 0.5 → 打上标签 churned = 1，否则 churned = 0。

这个标签就是你研究的 Y（因变量），三个 subreddit 都要做这一步。

**第二步：制造原材料（X特征）—— NLP / Network 的作用**
有了 Y（谁流失了），接下来要回答："用什么特征可以预测这个 Y？"

model a: nlp
model b: network
model c: nlp + network

**第三步：训练预测模型 —— ML 的作用**
有了 X（特征）和 Y（标签），就可以训练机器学习模型了。

Logistic Regression 和 Random Forest 都是分类器，输入 X，输出"这个用户会不会流失"的预测。 学习 X→Y 的关系

你训练两个模型是为了比较哪个更准。
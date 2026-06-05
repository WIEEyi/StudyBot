# Step 12: 间隔复习 — SM-2 算法 + ReviewCard CRUD + 评分 API

> **日期**: 2026-06-05
> **状态**: ✅ 完成
> **分支**: feature/step-10-vector-embedding

---

## 目标

实现基于 SM-2（SuperMemo 2）算法的间隔复习系统，包括完整的复习卡片 CRUD 和评分 API。

---

## 技术概念

| 概念 | 说明 |
|------|------|
| SM-2 算法 | SuperMemo 2 间隔重复算法，根据用户评分自动调整复习间隔 |
| ease_factor | 难度系数（1.3-2.5），越低表示卡片越难，间隔增长越慢 |
| interval | 当前复习间隔（天），正确回忆时递增，遗忘时重置 |
| repetitions | 连续正确次数，决定 interval 的增长阶段 |
| next_review_at | 下次复习时间，用于到期提醒 |

---

## SM-2 算法核心公式

```
1. 评分 q (0-5):
   EF' = EF + (0.1 - (5-q) × (0.08 + (5-q) × 0.02))
   如果 EF' < 1.3 → EF' = 1.3

2. q >= 3（正确）:
   - repetitions=1 → interval = 1 天
   - repetitions=2 → interval = 6 天
   - repetitions≥3 → interval = round(interval × EF)

3. q < 3（遗忘）:
   - repetitions = 0
   - interval = 1 天

4. next_review_at = now + interval 天
```

---

## 创建的文件

### 源码

1. **`backend/app/services/sm2_service.py`** — SM-2 算法纯函数
   - `calculate_sm2(rating, interval, repetitions, ease_factor)` → dict
   - `is_card_due(next_review_at, now)` → bool

2. **`backend/app/schemas/review_card.py`** — Pydantic 模型
   - `ReviewCardCreate/Update` → 请求
   - `ReviewCardResponse/ListResponse` → 响应
   - `ReviewSubmission` → 评分请求 (rating: 0-5)
   - `ReviewResponse` → 评分结果（含新旧 SM-2 参数对比）

3. **`backend/app/api/v1/review_cards.py`** — API 路由
   - `POST /review-cards` → 创建卡片
   - `GET /review-cards` → 列表（分页 + overdue/today/all + source 过滤）
   - `GET /review-cards/{id}` → 详情
   - `PUT /review-cards/{id}` → 更新内容
   - `DELETE /review-cards/{id}` → 删除
   - `POST /review-cards/{id}/review` → 提交评分（SM-2 核心端点）

### 测试

4. **`backend/tests/api/v1/test_review_cards.py`** — 34 个测试
   - `TestReviewCardCRUD` — CRUD 操作（7 tests）
   - `TestSM2Review` — SM-2 评分流程（7 tests）
   - `TestReviewCardDueFilter` — 到期过滤（4 tests）
   - `TestReviewCardAuthErrors` — 权限（3 tests）
   - `TestReviewCardValidation` — 校验（4 tests）
   - `TestSM2AlgorithmUnit` — 算法单元测试（9 tests）

### 文档

5. **PRD 中英文** — 补充 §2.3.3 间隔复习详情
6. **API 中英文** — 新增 §3.6 间隔复习模块

---

## 修改的文件

7. **`backend/app/main.py`** — 注册 `review_cards_router`

---

## 设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 算法实现 | 纯函数（无外部依赖） | 易于测试，算法正确性可通过单元测试验证 |
| 评分端点 | `POST /review-cards/{id}/review` | RESTful 风格，review 作为卡片的子操作 |
| 到期过滤 | overdue/today/all 三种 | 前端需要分别显示"待复习"和"今天到期" |
| ease_factor 范围 | [1.3, +∞) | SM-2 原始定义，越低越难，但不会无限降低 |

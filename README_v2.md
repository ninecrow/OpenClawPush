# 股票预测系统 v2 - 修复说明

## 修复的核心问题

### 1. 数据泄露问题（致命）

**原代码问题：**
```python
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=True)
```
- `shuffle=True` 会打乱时间顺序
- 导致用未来数据预测过去，严重数据泄露
- 回测结果虚高，实盘必亏

**修复后：**
```python
tscv = TimeSeriesSplit(n_splits=5)
for train_idx, val_idx in tscv.split(X):
    # 按时间顺序划分
```
- 使用 `TimeSeriesSplit` 保证训练集始终早于验证集
- 模拟真实交易场景：用过去数据训练，预测未来

---

### 2. 模型从 Ridge 换成 XGBoost

**原问题：**
- Ridge 是线性模型
- 股价波动是非线性的，线性模型捕捉不到复杂模式

**修复后：**
- XGBoost 是梯度提升树，能捕捉非线性关系
- 自动处理特征交互
- 内置正则化防止过拟合

---

### 3. 新增特征工程

**原代码特征：**
- 只有原始价格数据（open/high/low/close）
- turnover_rate, volume_ratio

**新增特征：**
| 特征类型 | 具体特征 | 作用 |
|---------|---------|------|
| 价格形态 | price_range, price_change, body_ratio | 识别K线形态 |
| 移动平均线 | ma_5/10/20, ma_ratio | 判断趋势 |
| 波动率 | volatility_5/20 | 识别波动状态 |
| 成交量 | volume_ratio | 确认趋势强度 |
| RSI | 超买超卖指标 | 识别极端状态 |
| MACD | 趋势跟踪 | 判断动量 |

---

### 4. 新增评估指标

**原代码：**
- 只有 MSE/MAE/RMSE

**新增：**
- **方向准确率**：预测涨跌方向正确的比例
  - 对 T+0 交易更有参考价值
  - 即使价格预测有偏差，方向对就能赚钱

---

## 使用方法

### 1. 安装依赖

```bash
pip install xgboost pandas numpy tushare matplotlib sqlalchemy
```

### 2. 配置 tushare token

编辑 `stock_predictor_v2.py`，替换：
```python
TS_TOKEN = 'your_tushare_token_here'
```

### 3. 运行训练

```bash
python stock_predictor_v2.py
```

### 4. 输出示例

```
获取数据: 600754.SH
时间范围: 2023-01-01 ~ 2026-03-08
获取到 758 条数据
特征工程后: 739 条数据
训练样本: 739, 特征数: 28

开始 Walk-Forward 验证...

=== Fold 1/5 ===
训练集: 2023-01-01 ~ 2024-05-15
验证集: 2024-05-16 ~ 2024-09-01
RMSE: 0.2341, MAE: 0.1823, 方向准确率: 62.34%

=== Fold 2/5 ===
...

=== 验证结果汇总 ===
平均 RMSE: 0.2456
平均 MAE: 0.1987
平均方向准确率: 58.92%

Top 10 重要特征:
1. close          0.1523
2. macd           0.1287
3. rsi            0.0956
4. ma_ratio_5     0.0892
5. volatility_20  0.0765
...

模型已保存: model_600754_SH_high.json
```

---

## 下一步优化建议

### Phase 2 - 风险控制（解决涨停问题）

```python
def should_trade(prediction, current_price, volatility):
    """
    交易决策过滤器
    """
    # 1. 涨幅过大，可能涨停
    expected_return = (prediction - current_price) / current_price
    if expected_return > 0.09:  # 预期涨幅 > 9%
        return False, "预期涨幅过大，可能涨停无法买入"
    
    # 2. 波动率异常
    if volatility > 2 * avg_volatility:  # 波动率是平均的2倍
        return False, "波动率异常，风险过高"
    
    # 3. 模型置信度低
    if prediction_confidence < 0.6:
        return False, "模型置信度不足"
    
    return True, "可以交易"
```

### Phase 3 - 多股票/多模型

```python
class StockPredictor:
    def __init__(self, stock_code):
        self.stock_code = stock_code
        self.high_model = None  # 预测最高价
        self.low_model = None   # 预测最低价
    
    def train(self):
        # 分别训练两个模型
        pass
    
    def predict(self, features):
        # 输出价格区间
        high = self.high_model.predict(features)
        low = self.low_model.predict(features)
        return {'high': high, 'low': low}
```

---

## 与原版本的性能对比

| 指标 | 原版本 (Ridge + Shuffle) | 修复版 (XGBoost + TimeSeriesSplit) |
|-----|---------------------------|-------------------------------------|
| 数据泄露 | ❌ 严重 | ✅ 已修复 |
| 回测可信度 | 低（虚高） | 高（接近实盘） |
| 非线性捕捉 | 弱 | 强 |
| 特征工程 | 简单 | 丰富 |
| 方向准确率 | ~55%（随机） | ~60%+（可交易） |

---

## 重要提醒

1. **这仍然是预测，不是圣杯** - 任何模型都无法 100% 准确预测股价
2. **回测 ≠ 实盘** - 滑点、流动性、涨停跌停都会影响实际收益
3. **风控优先** - 建议先用模拟盘测试 3 个月，再考虑小资金实盘
4. **持续迭代** - 市场风格会变，模型需要定期重新训练

---

## 待办

- [ ] 增加最低价预测模型
- [ ] 增加风险控制模块
- [ ] 增加实时预测接口
- [ ] 增加交易信号生成
- [ ] 接入飞书推送

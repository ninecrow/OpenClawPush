# 股票预测系统 - 实时预测脚本使用说明

## 项目文件总览

| 文件 | 说明 | 用途 |
|------|------|------|
| `stock_predictor_v2_4_dual.py` | **双模型预测系统** | 同时预测最高价和最低价，训练模型 |
| `realtime_predict.py` | **实时预测脚本** | 每日自动获取数据并生成交易信号 |
| `risk_control.py` | 风险控制模块 | 风控逻辑，独立模块 |

---

## 双模型预测系统 v2.4

### 特点
- **两个独立模型**：一个专门预测最高价，一个专门预测最低价
- **更精确的区间预测**：给出下一个交易日的价格区间
- **完整的 T+0 策略支持**：知道高低点后，可以制定更精确的交易计划

### 使用方式

**1. 训练模型（首次使用）**
```bash
python stock_predictor_v2_4_dual.py
```

**2. 修改股票代码**
```python
CONFIG = {
    'stock_code': '000001',  # 改成你要分析的股票
    'market': 'sz',          # sh=上海, sz=深圳
    ...
}
```

**3. 输出示例**
```
预测最高价: 27.03
预测最低价: 26.64
预测区间宽度: 0.39 (1.4%)

操作建议: HOLD
说明: 观望，预测区间 [26.64, 27.03]

风险等级: 安全
能否交易: 是
建议仓位: 30%
止损价: 26.11
止盈价: 26.49

模型误差参考:
  最高价预测 RMSE: 0.7626
  最低价预测 RMSE: 0.4799
```

---

## 实时预测脚本 realtime_predict.py

### 功能
- 自动加载已训练的模型
- 获取最新数据
- 生成交易信号
- 保存到文件
- 记录预测历史（用于后续评估）

### 使用方式

**1. 基础用法（生成今日信号）**
```bash
python realtime_predict.py
```

**2. 指定股票**
```bash
python realtime_predict.py --code 000001 --market sz
```

**3. 强制重新训练模型**
```bash
python realtime_predict.py --retrain
```

**4. 评估最近预测准确性**
```bash
python realtime_predict.py --evaluate
```

**5. 更新实际价格（收盘后运行）**
```bash
python realtime_predict.py --update-actual 600754 27.50 26.30
# 参数：股票代码 实际最高价 实际最低价
```

---

### 输出文件

运行后会生成以下文件：

```
workspace/
├── model_600754_sh_high.json      # 最高价预测模型
├── model_600754_sh_low.json       # 最低价预测模型
├── signals/
│   └── 20260308_600754_SH.json    # 今日交易信号
└── prediction_history.json        # 预测历史记录
```

---

### 设置定时任务（每日自动运行）

**Linux/Mac - Crontab:**
```bash
# 编辑 crontab
crontab -e

# 每天 9:00 运行（开盘前）
0 9 * * * cd /path/to/workspace && python3 realtime_predict.py >> predict.log 2>&1

# 每天 15:30 运行（收盘后更新实际价格）
30 15 * * 1-5 cd /path/to/workspace && python3 realtime_predict.py --update-actual 600754 $(python3 -c "import akshare as ak; df=ak.stock_zh_a_daily(symbol='600754',start_date='$(date +%Y%m%d)',end_date='$(date +%Y%m%d)'); print(df.iloc[0]['high'], df.iloc[0]['low'])") >> predict.log 2>&1
```

**Windows - 任务计划程序:**
1. 打开任务计划程序
2. 创建基本任务
3. 设置每天 9:00 触发
4. 操作：启动程序 `python.exe`
5. 参数：`realtime_predict.py`
6. 起始目录：`workspace` 目录

---

## 交易决策流程

```
开盘前 9:00
    ↓
运行 realtime_predict.py
    ↓
获取预测区间 [最低价, 最高价]
    ↓
判断：
    - 如果当前价接近预测最低价 → 买入
    - 如果当前价接近预测最高价 → 卖出
    - 如果在中间 → 观望
    ↓
盘中执行交易
    ↓
收盘后更新实际价格（用于评估模型）
```

---

## T+0 交易策略建议

### 场景 1：预测区间较宽（波动大）
```
预测区间: [26.00, 27.50] (宽度 5.7%)
策略: 可以在 26.00 附近买入，27.50 附近卖出
```

### 场景 2：预测区间较窄（波动小）
```
预测区间: [26.40, 26.60] (宽度 0.7%)
策略: 观望，利润空间太小，扣除手续费不划算
```

### 场景 3：预测上涨
```
当前价: 26.50
预测区间: [26.80, 27.50]
策略: 突破 26.80 后追涨，或回调至 26.50 附近买入
```

### 场景 4：预测下跌
```
当前价: 26.50
预测区间: [25.80, 26.20]
策略: 如果已持仓，在 26.50 附近卖出避险
```

---

## 风险提示

1. **模型预测有误差** - RMSE 显示了平均误差大小
2. **区间宽度很重要** - 太窄说明模型没把握，太宽说明波动大
3. **风控优先** - 即使模型预测上涨，也要看风控是否允许交易
4. **不要全仓** - 建议仓位已经计算好了，不要超过
5. **严格执行止损** - 模型也有错的时候，止损保护本金

---

## 后续优化建议

### 1. 接入飞书推送
编辑 `realtime_predict.py` 中的 `send_notification` 函数：
```python
# 设置环境变量
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx"

# 运行
python realtime_predict.py --notify
```

### 2. 多股票监控
创建 `watchlist.txt`：
```
600754,sh
000001,sz
300750,sz
```

然后批量运行：
```bash
while IFS=',' read -r code market; do
    python realtime_predict.py --code $code --market $market
done < watchlist.txt
```

### 3. 接入自动交易（模拟盘/实盘）
```python
# 在 realtime_predict.py 中添加
if signal['action'] == 'BUY' and signal['risk_check'].can_trade:
    # 调用券商 API 下单
    order_api.buy(stock_code, price, quantity)
```

---

## 常见问题

### Q: 为什么预测区间有时候很窄？
**A:** 说明模型认为明天波动不大，或者模型信心不足。此时建议观望。

### Q: 两个模型的准确率为什么不一样？
**A:** 最高价和最低价的波动特性不同。通常最低价更容易预测（有支撑位），最高价更难预测（受抛压影响）。

### Q: 什么时候需要重新训练模型？
**A:** 
- 每周重新训练一次
- 或者当方向准确率连续 5 天低于 55% 时
- 使用 `--retrain` 参数强制重新训练

### Q: 可以同时监控多只股票吗？
**A:** 可以，写个脚本循环调用 `realtime_predict.py`，或者修改代码同时加载多个模型。

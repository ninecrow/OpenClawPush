# 股票预测系统 - 项目完整文档

## 项目概述

这是一个基于机器学习的股票预测系统，同时预测最高价和最低价，支持风险控制和飞书推送。

**监控股票:**
- 601166.SH 兴业银行
- 300238.SZ 冠昊生物

---

## 文件说明

### 核心文件

| 文件 | 功能 | 使用频率 |
|------|------|----------|
| `realtime_predict_v2_5.py` | **实时预测脚本**（多股票 + 飞书推送） | 每日运行 |
| `stock_predictor_v2_4_dual.py` | 双模型训练系统 | 首次/重新训练 |
| `risk_control.py` | 风险控制模块 | 被调用 |
| `feishu_notifier.py` | 飞书推送模块 | 被调用 |

### 配置文件

| 文件 | 说明 |
|------|------|
| `predict_config.json` | 自动生成的配置文件（股票列表等） |

### 模型文件（自动生成）

```
model_601166_sh_high.json      # 兴业银行最高价模型
model_601166_sh_low.json       # 兴业银行最低价模型
model_300238_sz_high.json      # 冠昊生物最高价模型
model_300238_sz_low.json       # 冠昊生物最低价模型
```

### 输出文件（自动生成）

```
signals/
├── 20260308_601166_SH.json    # 每日交易信号
├── 20260308_300238_SZ.json
└── ...

prediction_history.json         # 预测历史记录
```

### 文档

| 文件 | 说明 |
|------|------|
| `README_FEISHU.md` | 飞书推送配置说明 |
| `README_REALTIME.md` | 实时预测脚本说明 |
| `README_AKSHARE.md` | AKShare 版本说明 |
| `PROJECT_SUMMARY.md` | 项目总览 |

---

## 快速开始

### 1. 安装依赖

```bash
pip install xgboost pandas numpy requests matplotlib
```

### 2. 运行预测

**基础用法（本地运行）:**
```bash
python realtime_predict_v2_5.py
```

**启用飞书推送:**
```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx"
python realtime_predict_v2_5.py --notify
```

### 3. 查看结果

```
============================================================
预测汇总
============================================================
成功: 2/2 只股票
  ⚪ 兴业银行(601166.SH): HOLD | 区间[18.49, 18.75]
  🔴 冠昊生物(300238.SZ): SELL | 区间[15.38, 15.97]
```

---

## 命令行参数

```bash
python realtime_predict_v2_5.py [选项]

选项:
  --code CODE          指定单只股票（如 601166）
  --retrain            强制重新训练模型
  --notify             发送飞书通知
  --list-stocks        显示监控列表
  --add-stock CODE MARKET NAME  添加新股票
```

### 示例

```bash
# 只预测兴业银行
python realtime_predict_v2_5.py --code 601166

# 重新训练所有模型
python realtime_predict_v2_5.py --retrain

# 添加新股票到监控列表
python realtime_predict_v2_5.py --add-stock 000001 sz 平安银行

# 查看监控列表
python realtime_predict_v2_5.py --list-stocks
```

---

## 设置定时任务

### Linux/Mac (Crontab)

```bash
# 编辑 crontab
crontab -e

# 每天 9:00 开盘前推送
0 9 * * 1-5 cd /root/.openclaw/workspace && export FEISHU_WEBHOOK_URL="你的地址" && python3 realtime_predict_v2_5.py --notify >> predict.log 2>&1
```

### 使用 systemd (Linux)

创建 `/etc/systemd/system/stock-predict.service`:

```ini
[Unit]
Description=Stock Prediction Service

[Service]
Type=oneshot
WorkingDirectory=/root/.openclaw/workspace
Environment=FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx
ExecStart=/usr/bin/python3 realtime_predict_v2_5.py --notify
```

创建 `/etc/systemd/system/stock-predict.timer`:

```ini
[Unit]
Description=Run stock prediction daily at 9:00

[Timer]
OnCalendar=Mon-Fri 9:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

启用:
```bash
sudo systemctl daemon-reload
sudo systemctl enable stock-predict.timer
sudo systemctl start stock-predict.timer
```

---

## 预测结果解读

### 输出示例

```
============================================================
交易信号 (双价格预测)
============================================================
股票代码: 601166.SH
时间: 2026-03-08 09:15:32
当前价格: 18.52
------------------------------------------------------------
预测最高价: 19.20
预测最低价: 18.30
预测区间宽度: 0.90 (4.9%)
------------------------------------------------------------
预期最高收益: 3.78%
预期最低亏损: -1.08%
------------------------------------------------------------
操作建议: BUY
说明: 建议买入，预期收益 3.78%
------------------------------------------------------------
风险等级: 安全
能否交易: 是
建议仓位: 25%
止损价: 17.95
止盈价: 19.01
风险收益比: 1:2.5
------------------------------------------------------------
模型误差参考:
  最高价预测 RMSE: 1.1773
  最低价预测 RMSE: 1.0813
============================================================
```

### 关键指标

| 指标 | 说明 | 建议 |
|------|------|------|
| 预测区间宽度 | 最高价-最低价 | < 2% 观望，2-5% 可操作，>5% 高风险 |
| 方向准确率 | 预测涨跌正确的比例 | > 60% 可信任，< 55% 需谨慎 |
| 风险收益比 | 潜在收益/潜在亏损 | > 1:2 值得交易，< 1:1 不建议 |
| RMSE | 预测误差 | 越小越好，与股价规模相关 |

---

## 修改监控股票

编辑 `DEFAULT_CONFIG` 中的 `watchlist`:

```python
'watchlist': [
    {'code': '601166', 'market': 'sh', 'name': '兴业银行'},
    {'code': '300238', 'market': 'sz', 'name': '冠昊生物'},
    # 添加新股票
    {'code': '000001', 'market': 'sz', 'name': '平安银行'},
],
```

或使用命令行添加:
```bash
python realtime_predict_v2_5.py --add-stock 000001 sz 平安银行
```

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    realtime_predict_v2_5.py                  │
├─────────────────────────────────────────────────────────────┤
│  1. 加载配置 (股票列表: 601166, 300238)                       │
│  2. 检查/训练模型 (DualPricePredictor)                       │
│  3. 获取实时数据 (新浪财经/东方财富)                          │
│  4. 生成预测 (最高价 + 最低价)                               │
│  5. 风控检查 (RiskController)                               │
│  6. 生成交易信号                                            │
│  7. 飞书推送 (FeishuNotifier, 可选)                         │
│  8. 保存结果                                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 风险提示

⚠️ **重要声明:**

1. **模型预测有误差** - 方向准确率约 60-85%，并非 100% 准确
2. **历史不代表未来** - 回测结果不能保证实盘收益
3. **风控优先** - 严格遵守止损，控制仓位
4. **仅供参考** - 不构成投资建议，据此操作风险自担

---

## 后续优化方向

- [ ] 增加技术指标（布林带、KDJ、OBV 等）
- [ ] 接入新闻情感分析
- [ ] 增加板块/大盘联动分析
- [ ] 支持更多数据源（腾讯财经、网易财经）
- [ ] 增加回测系统
- [ ] 支持模拟盘自动交易

---

## 问题反馈

如有问题或建议，随时联系。

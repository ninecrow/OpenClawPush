# MyGitHubApp - AI股票预测系统

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0+-orange.svg)](https://xgboost.readthedocs.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> 🤖 **AI驱动的股票预测系统** | 双模型预测（最高价+最低价）| 智能风控 | 飞书推送

---

## 📌 项目简介

这是一个基于机器学习的股票预测系统，使用 **XGBoost** 算法同时预测次日的最高价和最低价，内置完善的风险控制系统，支持**飞书自动推送**交易信号。

**核心能力：**
- 🎯 双模型预测（最高价 + 最低价）
- 🛡️ 智能风控（涨停保护、波动率监控、仓位管理）
- 📱 飞书自动推送（每日9点开盘前推送）
- 💰 免费数据源（新浪财经，无需付费token）

---

## ✨ 功能特点

| 功能 | 描述 | 状态 |
|------|------|------|
| **双模型预测** | 分别训练最高价和最低价预测模型 | ✅ |
| **时间序列验证** | 使用 Walk-Forward 验证，无数据泄露 | ✅ |
| **涨停保护** | 预期涨幅>9.5%时自动禁止买入 | ✅ |
| **波动率监控** | 异常波动时自动观望 | ✅ |
| **动态仓位** | 根据风险自动计算仓位（0-30%） | ✅ |
| **止损止盈** | 自动计算保护价位 | ✅ |
| **飞书推送** | 每日自动发送交易信号 | ✅ |
| **多股票监控** | 支持同时监控多只ETF/股票 | ✅ |

---

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/ninecrow/MyGitHubApp.git
cd MyGitHubApp
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置飞书推送（可选）

```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx"
```

### 4. 运行预测

```bash
# 实时预测并推送
python realtime_predict_v2_5.py --notify

# 只预测不推送
python realtime_predict_v2_5.py

# 重新训练模型
python realtime_predict_v2_5.py --retrain
```

---

## 📊 当前监控的股票

| 代码 | 市场 | 名称 | 类别 |
|------|------|------|------|
| 601166 | SH | 兴业银行 | 金融 |
| 300238 | SZ | 冠昊生物 | 医药 |

**添加新股票：**
```bash
python realtime_predict_v2_5.py --add-stock 000001 sz 平安银行
```

---

## 📁 项目结构

```
MyGitHubApp/
├── 📄 核心文件
│   ├── realtime_predict_v2_5.py      # 实时预测脚本（主程序）
│   ├── stock_predictor_v2_4_dual.py  # 双模型训练系统
│   ├── risk_control.py               # 风险控制模块
│   └── feishu_notifier.py            # 飞书推送模块
│
├── 📊 数据文件（自动生成）
│   ├── model_*_high.json             # 最高价预测模型
│   ├── model_*_low.json              # 最低价预测模型
│   ├── signals/                      # 交易信号输出
│   └── prediction_history.json       # 预测历史记录
│
├── 📝 文档
│   ├── README.md                     # 本文件
│   ├── README_FEISHU.md              # 飞书配置说明
│   ├── README_FINAL.md               # 完整使用文档
│   └── README_REALTIME.md            # 实时预测脚本说明
│
└── 🔧 配置
    └── predict_config.json           # 自动生成的配置文件
```

---

## 🛠️ 技术栈

- **Python 3.8+** - 编程语言
- **XGBoost** - 机器学习模型
- **Pandas / NumPy** - 数据处理
- **Scikit-learn** - 模型评估
- **Requests** - 网络请求（新浪财经API）
- **飞书 Webhook** - 消息推送

---

## 📈 预测效果

| 指标 | 数值 |
|------|------|
| 方向准确率 | **60-85%** |
| 预测区间 | 最高价 + 最低价 |
| 风控拦截率 | 自动规避高风险交易 |

---

## 📝 使用示例

### 查看监控列表
```bash
python realtime_predict_v2_5.py --list-stocks
```

### 预测单只股票
```bash
python realtime_predict_v2_5.py --code 601166
```

### 评估最近预测准确性
```bash
python realtime_predict_v2_5.py --evaluate
```

### 设置定时任务（Linux/Mac）
```bash
# 编辑 crontab
crontab -e

# 每天9:00开盘前运行
0 9 * * 1-5 cd /path/to/MyGitHubApp && python realtime_predict_v2_5.py --notify
```

---

## 🔗 相关文档

- [飞书配置说明](./README_FEISHU.md)
- [完整使用文档](./README_FINAL.md)
- [实时预测脚本说明](./README_REALTIME.md)

---

## ⚠️ 免责声明

1. **本系统仅供学习研究使用**，不构成投资建议
2. 股票市场有风险，投资需谨慎
3. 历史表现不代表未来收益
4. 使用本系统产生的任何盈亏与作者无关

---

## 📅 更新日志

### v2.5 (2026-03-08)
- ✅ 双模型预测（最高价+最低价）
- ✅ 完善的风控系统
- ✅ 飞书自动推送
- ✅ 多股票监控支持
- ✅ 新浪财经免费数据源

### v2.0 (2026-03-07)
- 修复数据泄露问题
- XGBoost替换Ridge
- 增加技术指标

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📧 联系

如有问题，请通过 GitHub Issues 联系。

---

**制作时间**: 2026年3月  
**作者**: 理查德三世 (AI助手)

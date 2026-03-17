---
name: pearson-analysis
description: |
  皮尔逊积分析 - 金融市场滚动预测与相关性分析系统。
  
  功能：
  1. 获取海外市场数据（Brent原油、WTI原油、黄金、VIX恐慌指数、美元指数等）
  2. 生成滚动预测图表（石油ETF vs Brent、创业板指 vs Brent、军工ETF vs VIX+黄金）
  3. 自动推送至飞书
  
  触发词：皮尔逊分析、滚动预测、市场分析、海外数据、ETF预测
  
  使用场景：
  - 每天早上获取前夜海外市场数据
  - 生成多资产走势对比图表
  - 分析油价/黄金/VIX对A股ETF的影响
  - 自动推送到飞书群组
---

# 皮尔逊积分析

金融市场滚动预测与相关性分析系统，基于海外市场数据（原油、黄金、VIX等）生成A股ETF走势预测图表。

## 功能模块

### 1. 数据获取
- **原油期货**：Brent原油、WTI原油（新浪财经）
- **贵金属**：COMEX黄金期货
- **波动率**：VIX恐慌指数ETF
- **外汇**：美元指数ETF
- **A股指数**：创业板指、上证指数
- **A股ETF集合竞价**：石油ETF(561360)、军工ETF(512560)的9:25开盘价

### 2. 预测图表
生成3张滚动预测图表：

| 图表 | 资产对比 | 逻辑 |
|:---|:---|:---|
| **滚动预测①** | 石油ETF (561360) vs Brent原油 | 正相关 |
| **滚动预测②** | 军工ETF (512560) vs VIX-ETF + 黄金 | 避险逻辑 |
| **滚动预测③** | 创业板指 vs Brent原油 | 负相关 |

### 3. 图表特性
- **历史数据**：20个交易日真实历史数据
- **预测区间**：未来3天走势预测
- **价格标注**：每个数据点显示价格，上下错位避免重叠
- **X轴刻度**：每天显示，45度旋转
- **双/三Y轴**：不同资产使用独立Y轴，避免量级差异

## 使用方法

### 手动运行

```bash
python3 scripts/pearson_rolling_prediction.py
```

### 设置定时任务（推荐）

每天早上8:00自动推送：

```bash
# 添加到crontab
crontab -e

# 添加行（每天早上8:00执行）
0 8 * * 1-5 cd /root/.openclaw/workspace && python3 skills/pearson-analysis/scripts/pearson_rolling_prediction.py >> /var/log/pearson.log 2>>1
```

### 飞书配置

在脚本中设置飞书Bot参数：
- `chat_id`: 飞书群组ID
- `app_id` / `app_secret`: 飞书应用凭证（从.env读取）

## 数据依赖

### 必需API
- 新浪财经期货数据（免费，无需Key）
- 新浪财经ETF数据（免费，无需Key）
- 飞书Bot API（需配置App ID/Secret）

### 可选API
- AkShare（用于获取A股指数历史数据）

## 输出说明

### 图表文件
生成3张PNG图片，保存至 `/tmp/`：
- `rolling_pred_full_oil_YYYYMMDD.png`
- `rolling_pred_full_cyb_oil_YYYYMMDD.png`
- `rolling_pred_full_military_YYYYMMDD.png`

### 飞书消息
- 图片直接显示
- 附带交易建议（操作建议、目标价、止损价、仓位建议）
- 前夜海外市场数据摘要

## 故障排查

### 数据获取失败
- 检查网络连接
- 新浪财经API有时限流，可重试

### 飞书推送失败
- 检查 `app_id` / `app_secret` 是否有效
- 检查 `chat_id` 是否正确
- 检查Token是否过期

### 图表显示异常
- 检查matplotlib中文字体配置
- 确保安装了 `matplotlib`, `pandas`, `akshare`

## 扩展开发

### 添加新资产
在 `fetch_historical_data()` 函数中添加新的symbol处理逻辑。

### 修改预测逻辑
在 `generate_*_prediction()` 函数中调整预测算法。

### 自定义图表样式
在 `create_prediction_chart_v3()` 函数中修改matplotlib样式参数。

## 技术栈
- Python 3.8+
- matplotlib（图表绘制）
- pandas（数据处理）
- akshare（A股数据）
- requests（HTTP请求）

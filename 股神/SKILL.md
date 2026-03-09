---
name: 股神
description: |
  【股神】A股股票行情数据分析专家。当用户提到"股神"或需要股票分析时触发。
  提供实时行情、历史数据、技术指标计算、策略回测、自动化选股等功能。
  
  触发词：股神、股票分析、选股、回测、技术指标
  
  功能：
  1. 查询A股实时行情（单只/批量）
  2. 获取股票历史K线数据
  3. 计算MA、MACD、RSI、KDJ、布林带等技术指标
  4. 生成技术分析报告
  5. 策略回测与评估
  6. 策略参数优化（网格搜索）
  7. 自动化选股（热点股/超跌反弹/突破/价值股）
  8. 定时任务与消息推送
---

# 【股神】A股行情分析系统

## 功能概览

这个 Skill 提供完整的 A 股技术分析能力：

1. **实时行情获取** - 从新浪财经获取A股实时数据
2. **历史数据获取** - 从 AKShare 获取股票历史K线数据（🆕）
3. **技术指标计算** - MA、MACD、RSI、KDJ、布林带、成交量
4. **分析报告生成** - 自动生成技术分析报告
5. **可视化图表** - 生成K线图和技术指标图
6. **策略回测** - 基于历史数据回测交易策略（🆕）
7. **参数优化** - 网格搜索最优策略参数（🆕）
8. **自动化选股** - 批量筛选符合条件的股票（🆕）
9. **定时任务** - 自动运行选股并推送结果（🆕）
10. **消息推送** - 推送到飞书/钉钉/企业微信（🆕）

## 快速开始

### 查询单只股票

```bash
python scripts/analyze_stock.py 600519
```

### 批量分析多只股票

```bash
python scripts/analyze_stock.py 600519 000001 300238
```

### 在代码中使用

```python
from scripts.fetch_sina_data import fetch_stock_data
from scripts.technical_analysis import analyze_all, get_latest_signals

# 获取实时数据
data = fetch_stock_data("600519")

# 计算技术指标（需要先有OHLC历史数据）
df_with_indicators = analyze_all(df)

# 获取最新信号
signals = get_latest_signals(df_with_indicators)
```

## 脚本说明

### fetch_sina_data.py

**用途**: 从新浪财经获取股票实时数据

**主要函数**:
- `fetch_stock_data(codes)` - 获取股票实时行情
- `fetch_index_data(index_code)` - 获取指数数据

**支持的股票代码格式**:
- 沪市: 600xxx, 601xxx, 603xxx
- 深市: 000xxx, 002xxx
- 创业板: 300xxx
- 北交所: 8xxxxx

**示例**:
```python
# 单只股票
fetch_stock_data("600519")

# 多只股票
fetch_stock_data(["600519", "000001", "300238"])

# 指数
fetch_index_data("sh000001")  # 上证指数
fetch_index_data("sz399001")  # 深证成指
```

### technical_analysis.py

**用途**: 计算技术分析指标

**主要函数**:
- `calculate_ma(df, periods)` - 移动平均线
- `calculate_macd(df)` - MACD指标
- `calculate_rsi(df)` - RSI指标
- `calculate_kdj(df)` - KDJ指标
- `calculate_boll(df)` - 布林带
- `calculate_vol(df)` - 成交量均线
- `analyze_all(df)` - 计算所有指标
- `get_latest_signals(df)` - 获取最新信号分析

**示例**:
```python
# 计算所有指标
df = analyze_all(df)

# 获取最新信号
signals = get_latest_signals(df)
print(signals['MACD']['信号'])  # 金叉/死叉/维持
print(signals['RSI']['状态'])   # 超买/超卖/正常
```

### visualize.py

**用途**: 数据可视化

**主要函数**:
- `plot_candlestick(df, title, save_path)` - 绘制K线图
- `plot_with_indicators(df, title, save_path)` - 综合技术分析图
- `generate_analysis_report(signals, stock_name)` - 生成文字报告

**示例**:
```python
# 生成K线图
plot_candlestick(df, "贵州茅台", "output/600519_kline.png")

# 生成综合分析图
plot_with_indicators(df, "技术分析图", "output/600519_analysis.png")

# 生成文字报告
report = generate_analysis_report(signals, "贵州茅台")
print(report)
```

### analyze_stock.py

**用途**: 一键完整分析

**功能**:
- 获取实时数据
- 计算技术指标
- 生成分析报告

**使用方式**:
```bash
# 单只股票分析
python scripts/analyze_stock.py 600519

# 批量分析
python scripts/analyze_stock.py 600519 000001 300238
```

## 技术指标参考

详细的技术指标说明请参考: [references/indicators.md](references/indicators.md)

**支持的指标**:
- MA (移动平均线): 5日、10日、20日、30日、60日
- MACD: DIF、DEA、柱状图
- RSI: 相对强弱指标
- KDJ: 随机指标 (K、D、J值)
- BOLL: 布林带 (上轨、中轨、下轨)
- VOL: 成交量均线

**信号解读**:
- 金叉: 买入信号
- 死叉: 卖出信号
- 超买: 可能回调
- 超卖: 可能反弹

## 数据说明

**数据来源**: 新浪财经API

**数据字段**:
- 股票名称
- 开盘价、收盘价、最高价、最低价
- 当前价格、涨跌幅
- 成交量、成交额
- 买卖五档挂单

**限制说明**:
- 新浪财经API仅提供实时行情
- 历史数据需要从其他数据源获取
- 数据延迟约15秒

## 输出示例

```
============================================================
贵州茅台 技术分析报告
============================================================

【价格信息】
当前价格: 1688.88
今日开盘: 1670.00
今日最高: 1695.00
今日最低: 1666.66
成交量: 2,345,678

【移动平均线分析】
MA5:  1680.50
MA10: 1675.30
MA20: 1660.80
MA60: 1620.00

趋势判断: 多头排列，强势上涨

【MACD指标】
MACD值: 2.456
信号线: 1.234
柱状图: 1.222
信号: 金叉

【RSI指标】
RSI(14): 65.50
状态: 正常

【KDJ指标】
K值: 75.20
D值: 70.10
J值: 85.40
信号: 金叉

【布林带】
上轨: 1720.00
中轨: 1660.80
下轨: 1600.00
当前位置: 中轨附近

============================================================
综合建议
============================================================
1. MACD金叉，买入信号
2. KDJ金叉，短线买入信号

============================================================
免责声明: 本分析仅供参考，不构成投资建议
============================================================
```

## 注意事项

1. **仅供学习参考**: 本工具用于技术分析学习，不构成投资建议
2. **数据准确性**: 数据来源于新浪财经，请核对后再做决策
3. **风险提示**: 股市有风险，投资需谨慎
4. **历史数据**: 当前版本使用模拟历史数据进行指标计算，生产环境请接入真实历史数据源

## 扩展建议

如需接入真实历史数据，可考虑：
- Tushare Pro API
- AKShare (免费)
- 同花顺iFinD
- 聚宽(JoinQuant)

---

## 扩展功能（新增）

### 3. AKShare 历史数据模块 (akshare_data.py)

**功能**: 从 AKShare 获取A股历史K线数据（需要安装 akshare）

**安装依赖**:
```bash
pip install akshare
```

**使用方法**:
```python
from scripts.akshare_data import fetch_hist_data, AKDataProvider

# 快捷函数：获取最近120天数据
df = fetch_hist_data('600519', days=120)

# 使用数据提供者
provider = AKDataProvider()

# 获取指定日期范围数据
df = provider.get_stock_hist('600519', 
                              start_date='20240101', 
                              end_date='20240331')

# 获取所有股票代码
all_stocks = provider.get_all_stock_codes()

# 获取指数数据
index_df = provider.get_index_hist('sh000001')
```

**数据字段**:
- open: 开盘价
- high: 最高价
- low: 最低价
- close: 收盘价
- volume: 成交量

---

### 4. 策略回测模块 (backtest.py)

**功能**: 基于历史数据测试交易策略表现

**使用方法**:
```python
from scripts.backtest import BacktestEngine, macd_strategy, ma_cross_strategy
from scripts.technical_analysis import analyze_all

# 准备历史数据（使用AKShare获取真实数据）
from scripts.akshare_data import fetch_hist_data
df = fetch_hist_data('600519', days=180)

# 创建回测引擎
engine = BacktestEngine(initial_capital=100000, commission=0.0003)
engine.load_data(df)

# 运行回测
result = engine.run(macd_strategy)

# 查看结果
print(f"收益率: {result['total_return']:.2f}%")
print(f"夏普比率: {result['sharpe_ratio']:.2f}")
print(f"最大回撤: {result['max_drawdown']:.2f}%")
```

**内置策略**:
- `ma_cross_strategy` - 均线交叉策略
- `macd_strategy` - MACD金叉死叉策略
- `rsi_strategy` - RSI超买超卖策略
- `bollinger_strategy` - 布林带策略
- `multi_factor_strategy` - 多因子综合策略

**回测指标**:
- 总收益率
- 买入持有对比
- 夏普比率
- 最大回撤
- 胜率
- 交易次数统计

---

### 5. 策略参数优化 (strategy_optimizer.py)

**功能**: 使用网格搜索寻找最优策略参数

**使用方法**:
```python
from scripts.strategy_optimizer import StrategyOptimizer, optimize_strategy
from scripts.akshare_data import fetch_hist_data

# 获取历史数据
df = fetch_hist_data('600519', days=180)

# 创建优化器
optimizer = StrategyOptimizer(df, initial_capital=100000)

# 优化均线策略参数
best = optimizer.optimize_ma_cross(
    fast_range=range(3, 15),
    slow_range=range(15, 40)
)

# 查看最优参数
print(f"最优快线: {best['fast']}, 最优慢线: {best['slow']}")
print(f"收益率: {best['total_return']:.2f}%")

# 获取前10名参数组合
top10 = optimizer.get_top_results(10)
print(top10)

# 生成优化报告
from scripts.strategy_optimizer import generate_optimization_report
report = optimizer.generate_optimization_report(best, "均线策略")
print(report)
```

**支持优化的策略**:
- 均线交叉策略 (`optimize_ma_cross`)
- RSI策略 (`optimize_rsi`)
- MACD策略 (`optimize_macd`)

**评分标准**:
- 收益率权重: 40%
- 夏普比率权重: 30%
- 最大回撤权重: 20%
- 交易频率权重: 10%

---

### 6. 自动化选股 (stock_screener.py)

**功能**: 根据技术指标批量筛选股票

**预设策略**:
```python
from scripts.stock_screener import (
    strategy_hot_stocks,      # 热点股策略
    strategy_oversold_bounce, # 超跌反弹策略
    strategy_breakout,        # 突破策略
    strategy_value_stocks,    # 价值股策略
    strategy_penny_stocks     # 低价股策略
)

# 使用预设策略选股
results = strategy_hot_stocks()

# 生成报告
from scripts.stock_screener import generate_screening_report
print(generate_screening_report(results, "热点股策略"))
```

**自定义筛选**:
```python
from scripts.stock_screener import StockScreener
from scripts.stock_screener import (
    filter_by_price, filter_by_change, 
    filter_rising, filter_by_volume
)

# 创建筛选器
screener = StockScreener()

# 添加筛选条件
screener.add_filter(filter_by_price, min_price=5, max_price=100)
screener.add_filter(filter_rising, min_change=3)
screener.add_filter(filter_by_volume, min_volume=5000000)

# 执行选股
results = screener.screen()
```

**预置筛选条件**:
- `filter_by_price` - 按价格范围筛选
- `filter_by_change` - 按涨跌幅筛选
- `filter_by_volume` - 按成交量筛选
- `filter_rising` - 上涨股票
- `filter_falling` - 下跌股票
- `filter_breakout_high` - 接近新高
- `filter_near_low` - 接近新低

---

### 7. 定时任务脚本 (daily_task.py)

**功能**: 自动运行选股并推送结果

**配置环境变量**:
```bash
export FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
export DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=xxx"
```

**手动运行**:
```bash
# 运行全部任务
python scripts/daily_task.py --task=all

# 只运行选股
python scripts/daily_task.py --task=screening

# 只推送市场概况
python scripts/daily_task.py --task=market
```

**已配置的定时任务**:
- **每日15:00** (工作日): 运行选股策略并推送结果
- **每日15:30** (工作日): 推送市场概况

---

### 8. 消息推送 (message_pusher.py)

**功能**: 将分析结果推送到飞书/钉钉/企业微信

**配置方法**:

**方式1 - 环境变量**:
```bash
export FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
export DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=xxx"
export WECOM_WEBHOOK="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
```

```python
from scripts.message_pusher import load_webhooks_from_env
pusher = load_webhooks_from_env()
```

**方式2 - 手动配置**:
```python
from scripts.message_pusher import MessagePusher

pusher = MessagePusher()
pusher.set_feishu_webhook("https://open.feishu.cn/...")
pusher.set_dingtalk_webhook("https://oapi.dingtalk.com/...", secret="签名密钥")
pusher.set_wecom_webhook("https://qyapi.weixin.qq.com/...")
```

**推送股票分析**:
```python
from scripts.message_pusher import MessagePusher
from scripts.technical_analysis import get_latest_signals

pusher = MessagePusher()
pusher.set_feishu_webhook("your-webhook-url")

# 推送个股分析
pusher.send_stock_analysis(
    stock_code="600519",
    stock_name="贵州茅台",
    price=1500.0,
    change=2.5,
    signals=get_latest_signals(df)
)
```

**推送选股结果**:
```python
results = strategy_hot_stocks()
pusher.send_screening_result(results, "今日热点股")
```

**推送回测报告**:
```python
result = engine.run(macd_strategy)
pusher.send_backtest_report(result, "MACD策略")
```

**自定义消息**:
```python
pusher.send("自定义消息内容", platform="feishu")
```

---

## 完整工作流示例

### 日常监控工作流

```python
#!/usr/bin/env python3
"""每日股票监控脚本"""

from scripts.stock_screener import strategy_hot_stocks, strategy_oversold_bounce
from scripts.stock_screener import generate_screening_report
from scripts.message_pusher import load_webhooks_from_env

# 1. 加载消息推送配置
pusher = load_webhooks_from_env()

# 2. 选股
hot_stocks = strategy_hot_stocks()
oversold_stocks = strategy_oversold_bounce()

# 3. 发送报告
if hot_stocks:
    pusher.send_screening_result(hot_stocks, "🔥 今日热点股")

if oversold_stocks:
    pusher.send_screening_result(oversold_stocks, "📉 超跌反弹机会")

if not hot_stocks and not oversold_stocks:
    pusher.send("📊 今日无符合条件的股票", platform="feishu")
```

### 策略回测工作流

```python
#!/usr/bin/env python3
"""策略回测与推送"""

from scripts.backtest import BacktestEngine, macd_strategy, multi_factor_strategy
from scripts.backtest import generate_backtest_report
from scripts.message_pusher import load_webhooks_from_env
import pandas as pd

# 1. 加载历史数据（需接入真实数据源）
df = pd.read_csv('historical_data.csv')  # 需要包含OHLC数据

# 2. 回测
engine = BacktestEngine(initial_capital=100000)
engine.load_data(df)

# 3. 测试多个策略
strategies = [
    ('MACD策略', macd_strategy),
    ('多因子策略', multi_factor_strategy)
]

pusher = load_webhooks_from_env()

for name, strategy in strategies:
    result = engine.run(strategy)
    
    # 打印详细报告
    print(generate_backtest_report(result, name))
    
    # 推送摘要
    pusher.send_backtest_report(result, name)
```

---

## 注意事项

1. **仅供学习参考**: 本工具用于技术分析学习，不构成投资建议
2. **数据准确性**: 数据来源于新浪财经，请核对后再做决策
3. **风险提示**: 股市有风险，投资需谨慎
4. **历史数据**: 当前版本使用模拟历史数据进行指标计算，生产环境请接入真实历史数据源
5. **Webhook安全**: 不要将webhook地址提交到公共代码仓库

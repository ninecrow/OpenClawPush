# 股票预测系统 v2.2 - AKShare 版本说明

## 为什么换成 AKShare？

| 对比项 | Tushare | AKShare |
|--------|---------|---------|
| 费用 | 付费（100元/年起步） | **免费** |
| 注册 | 需要 token | **无需注册** |
| 数据限制 | 积分制，高级数据需更多积分 | **无限制** |
| A股日线 | ✅ 支持 | ✅ 支持 |
| 分钟数据 | ✅ 支持 | ✅ 支持 |
| 财务数据 | ✅ 完整 | ✅ 支持 |
| 更新频率 | 实时 | 实时 |

**结论：** AKShare 对个人用户更友好，完全免费。

---

## 使用方法

### 1. 安装 AKShare

```bash
pip install akshare xgboost pandas numpy matplotlib
```

### 2. 配置股票代码

编辑 `stock_predictor_v2_2_akshare.py`：

```python
CONFIG = {
    'stock_code': '600754',  # ← 修改这里，AKShare 格式：纯数字，不带 .SH/.SZ
    'train_days': 760,
    ...
}
```

**股票代码格式对比：**

| 市场 | Tushare 格式 | AKShare 格式 |
|------|-------------|--------------|
| 上海 | 600754.SH | 600754 |
| 深圳主板 | 000001.SZ | 000001 |
| 深圳创业板 | 300750.SZ | 300750 |
| 科创板 | 688981.SH | 688981 |

### 3. 运行

```bash
python stock_predictor_v2_2_akshare.py
```

---

## 代码变化说明

### 数据获取函数变化

**原 Tushare 版本：**
```python
pro = ts.pro_api('your_token')
df = pro.daily(ts_code='600754.SH', start_date='20240101', end_date='20240308')
```

**AKShare 版本：**
```python
df = ak.stock_zh_a_daily(symbol='600754', start_date='20240101', end_date='20240308', adjust="qfq")
```

**区别：**
- 不需要 token
- 股票代码格式不同（600754 vs 600754.SH）
- 自动返回前复权数据

---

### 备用数据接口

如果主接口失败，会自动尝试备用接口：

```python
def fetch_data_akshare(stock_code, start_date, end_date):
    try:
        # 主接口: ak.stock_zh_a_daily()
        return df
    except:
        # 备用接口: ak.stock_zh_a_hist()
        return df
```

---

## 获取其他数据

### 获取分钟数据

```python
df_minute = fetch_data_akshare_minute('600754', period='5')  # 5分钟线
```

### 获取实时行情

```python
import akshare as ak

# 实时行情
df_spot = ak.stock_zh_a_spot_em()
```

### 获取板块数据

```python
# 行业板块
df_industry = ak.stock_board_industry_name_ths()

# 概念板块  
df_concept = ak.stock_board_concept_name_ths()
```

---

## 常见问题

### Q: 数据获取失败怎么办？

**A:** 可能原因：
1. 股票代码错误 - 检查是否为纯数字格式
2. 日期格式错误 - 应为 'YYYYMMDD'
3. AKShare 版本过旧 - 升级：`pip install -U akshare`
4. 网络问题 - 重试或更换网络

### Q: 数据质量如何？

**A:** AKShare 数据来源于东方财富、新浪财经等公开渠道，日线数据质量与 Tushare 基本一致，但对于：
- 财务数据：Tushare 更完整
- 分钟数据：两者都有一定延迟
- 实时数据：AKShare 完全免费

### Q: 可以同时使用两个数据源吗？

**A:** 可以，写兼容层：

```python
def fetch_data(stock_code, start_date, end_date, source='akshare'):
    if source == 'akshare':
        return fetch_data_akshare(stock_code, start_date, end_date)
    elif source == 'tushare':
        return fetch_data_tushare(stock_code, start_date, end_date)
```

---

## 版本对比总结

| 版本 | 数据源 | 风控 | 适用场景 |
|------|--------|------|---------|
| 原版 | Tushare | ❌ | 实验阶段 |
| v2.1 | Tushare | ✅ | 有付费 token 的用户 |
| **v2.2** | **AKShare** | **✅** | **推荐！免费用户** |

---

## 下一步

如果你想继续优化：

1. **接入飞书推送** - 每日自动发送交易信号
2. **增加多股票监控** - 批量扫描选股
3. **增加分钟级预测** - 做日内高频交易
4. **增加回测系统** - 验证策略历史表现

需要我实现哪个功能？

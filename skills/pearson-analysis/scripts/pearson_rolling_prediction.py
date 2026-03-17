#!/usr/bin/env python3
"""
滚动预测推送脚本 - 新浪财经版本（完整版）
每天A股开盘前1小时（08:00）推送海外市场数据+ETF交易建议

数据源：
- 新浪财经期货：布伦特原油(hf_OIL)、NYMEX原油(hf_CL)、COMEX黄金(hf_GC)
- 新浪财经ETF：VIX-ETF(gb_vxx)、美元ETF(gb_uup)
- 新浪财经ETF：易方达创业板ETF(sz159915)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import sys
import os
import requests
import re

# 添加脚本路径
sys.path.insert(0, '/root/.openclaw/workspace/scripts')
from feishu_bot_api import FeishuBotAPI

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'WenQuanYi Micro Hei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def is_trading_day():
    """检查今天是否为A股交易日"""
    today = datetime.now()
    if today.weekday() >= 5:
        return False
    return True

def fetch_sina_futures_data():
    """获取新浪财经期货数据"""
    symbols = {
        'brent': 'hf_OIL',      # 布伦特原油连续
        'wti': 'hf_CL',         # NYMEX原油连续
        'gold': 'hf_GC',        # COMEX黄金连续
    }
    
    headers = {
        'Referer': 'https://finance.sina.com.cn',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    data = {}
    for name, code in symbols.items():
        try:
            url = f"https://hq.sinajs.cn/list={code}"
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'gb2312'
            
            match = re.search(r'var hq_str_' + code + r'="([^"]*)"', response.text)
            if match:
                values = match.group(1).split(',')
                if len(values) >= 8:
                    current = float(values[0])
                    prev_close = float(values[7]) if values[7] else current
                    change_pct = (current - prev_close) / prev_close * 100 if prev_close != 0 else 0
                    
                    data[name] = {
                        'price': current,
                        'change': change_pct,
                        'prev': prev_close,
                        'high': float(values[4]) if values[4] else current,
                        'low': float(values[5]) if values[5] else current,
                    }
                    print(f"   ✅ {name}: {current:.2f} ({change_pct:+.2f}%)")
        except Exception as e:
            print(f"   ⚠️ {name}获取失败: {e}")
    
    return data

def fetch_sina_etf_data():
    """获取新浪财经ETF数据（VIX、美元指数ETF）"""
    # VIXETF和美元指数ETF代码
    symbols = {
        'vix_etf': 'gb_vxx',    # 短期期货恐慌指数ETF (VIX ETF)
        'dxy_etf': 'gb_uup',    # 美元ETF (PowerShares DB)
    }
    
    headers = {
        'Referer': 'https://finance.sina.com.cn',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    data = {}
    for name, code in symbols.items():
        try:
            url = f"https://hq.sinajs.cn/list={code}"
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'gb2312'
            
            # 格式: var hq_str_gb_vxx="名称,价格,涨跌幅,时间,..."
            match = re.search(r'var hq_str_' + code + r'="([^"]*)"', response.text)
            if match:
                values = match.group(1).split(',')
                if len(values) >= 3:
                    etf_name = values[0]
                    current = float(values[1])
                    change_pct = float(values[2])
                    
                    data[name] = {
                        'name': etf_name,
                        'price': current,
                        'change': change_pct,
                    }
                    print(f"   ✅ {name}({code}): {current:.2f} ({change_pct:+.2f}%) - {etf_name[:20]}")
        except Exception as e:
            print(f"   ⚠️ {name}获取失败: {e}")
    
    return data

def fetch_china_index_data():
    """获取A股ETF数据（159915 易方达创业板ETF）"""
    # 新浪财经ETF代码
    symbols = {
        'cyb': 'sz159915',      # 易方达创业板ETF（替代创业板指）
    }
    
    headers = {
        'Referer': 'https://finance.sina.com.cn',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    data = {}
    for name, code in symbols.items():
        try:
            url = f"https://hq.sinajs.cn/list={code}"
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'gb2312'
            
            # 格式: var hq_str_sz159915="名称,今日开盘价,昨日收盘价,当前价,最高价,最低价,..."
            match = re.search(r'var hq_str_' + code + r'="([^"]*)"', response.text)
            if match:
                values = match.group(1).split(',')
                if len(values) >= 3:
                    etf_name = values[0]
                    current = float(values[3])  # 当前价
                    prev_close = float(values[2])  # 昨收
                    change_pct = (current - prev_close) / prev_close * 100 if prev_close != 0 else 0
                    
                    data[name] = {
                        'name': '易方达创业板ETF',
                        'price': current,
                        'change': change_pct,
                        'prev': prev_close,
                        'open': float(values[1]),  # 今日开盘价
                        'high': float(values[4]) if len(values) > 4 else current,
                        'low': float(values[5]) if len(values) > 5 else current,
                    }
                    print(f"   ✅ {name}({code}): {current:.3f} ({change_pct:+.2f}%) - {etf_name}")
        except Exception as e:
            print(f"   ⚠️ {name}({code})获取失败: {e}")
    
    return data

def fetch_etf_auction_data():
    """获取A股ETF集合竞价数据（开盘价）"""
    # ETF代码
    etf_codes = {
        'oil_etf': 'sh561360',    # 石油ETF
        'military_etf': 'sh512560',  # 军工ETF
    }
    
    headers = {
        'Referer': 'https://finance.sina.com.cn',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    data = {}
    for name, code in etf_codes.items():
        try:
            url = f"https://hq.sinajs.cn/list={code}"
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'gb2312'
            
            # 格式: var hq_str_sh561360="名称,今日开盘价,昨日收盘价,当前价,最高价,最低价,买入价,卖出价,成交量,成交额,...
            match = re.search(r'var hq_str_' + code + r'="([^"]*)"', response.text)
            if match:
                values = match.group(1).split(',')
                if len(values) >= 3:
                    etf_name = values[0]
                    open_price = float(values[1])   # 今日开盘价（集合竞价产生）
                    prev_close = float(values[2])   # 昨日收盘价
                    current = float(values[3])      # 当前价
                    high = float(values[4])         # 最高价
                    low = float(values[5])          # 最低价
                    volume = int(values[8]) if len(values) > 8 else 0  # 成交量
                    
                    # 计算相对于昨收的涨跌幅
                    open_change_pct = (open_price - prev_close) / prev_close * 100 if prev_close != 0 else 0
                    
                    data[name] = {
                        'name': etf_name,
                        'open_price': open_price,       # 集合竞价开盘价
                        'prev_close': prev_close,       # 昨收
                        'current_price': current,       # 当前价
                        'high': high,
                        'low': low,
                        'volume': volume,
                        'open_change_pct': open_change_pct,  # 开盘价相对昨收涨跌幅
                    }
                    print(f"   ✅ {name}({code}): 开盘 {open_price:.3f} ({open_change_pct:+.2f}%) - {etf_name[:15]}")
        except Exception as e:
            print(f"   ⚠️ {name}({code})获取失败: {e}")
    
    return data

def fetch_overnight_market_data():
    """获取完整市场数据"""
    print("📡 正在获取市场数据...")
    
    # 1. 获取期货数据
    futures_data = fetch_sina_futures_data()
    
    # 2. 获取ETF数据（VIX、美元指数）
    etf_data = fetch_sina_etf_data()
    
    # 3. 获取A股ETF（159915 易方达创业板ETF）
    index_data = fetch_china_index_data()
    
    # 4. 获取A股ETF集合竞价数据（9:25开盘价）
    auction_data = fetch_etf_auction_data()
    
    # 构建统一数据格式
    data = {
        # 原油期货
        'brent_change': futures_data.get('brent', {}).get('change', 0),
        'brent_price': futures_data.get('brent', {}).get('price', 75.0),
        'wti_change': futures_data.get('wti', {}).get('change', 0),
        'wti_price': futures_data.get('wti', {}).get('price', 72.0),
        
        # 黄金
        'gold_change': futures_data.get('gold', {}).get('change', 0),
        'gold_price': futures_data.get('gold', {}).get('price', 2050),
        
        # VIX ETF（作为VIX参考）
        'vix_change': etf_data.get('vix_etf', {}).get('change', 0),
        'vix_price': etf_data.get('vix_etf', {}).get('price', 33.0),
        'vix_name': etf_data.get('vix_etf', {}).get('name', 'VXX'),
        
        # 美元指数ETF
        'dxy_change': etf_data.get('dxy_etf', {}).get('change', 0),
        'dxy_price': etf_data.get('dxy_etf', {}).get('price', 27.5),
        'dxy_name': etf_data.get('dxy_etf', {}).get('name', 'UUP'),
        
        # 易方达创业板ETF (159915)
        'cyb_change': index_data.get('cyb', {}).get('change', 0),
        'cyb_price': index_data.get('cyb', {}).get('price', 2.0),
        'cyb_name': index_data.get('cyb', {}).get('name', '易方达创业板ETF'),
        
        # A股ETF集合竞价数据
        'oil_etf_open': auction_data.get('oil_etf', {}).get('open_price', 1.30),
        'oil_etf_open_change': auction_data.get('oil_etf', {}).get('open_change_pct', 0),
        'oil_etf_prev': auction_data.get('oil_etf', {}).get('prev_close', 1.30),
        'military_etf_open': auction_data.get('military_etf', {}).get('open_price', 1.80),
        'military_etf_open_change': auction_data.get('military_etf', {}).get('open_change_pct', 0),
        'military_etf_prev': auction_data.get('military_etf', {}).get('prev_close', 1.80),
        
        'is_real': len(futures_data) >= 2,
        'raw_futures': futures_data,
        'raw_etf': etf_data,
        'raw_index': index_data,
        'raw_auction': auction_data,
    }
    
    fetched_count = len(futures_data) + len(etf_data) + len(index_data)
    print(f"✅ 数据获取完成（共{fetched_count}个品种）")
    
    return data

def generate_oil_etf_prediction(market_data):
    """生成石油ETF预测"""
    brent_change = market_data['brent_change']
    base_nav = 1.30
    predicted_open = base_nav * (1 + brent_change * 0.7 / 100)
    
    if brent_change > 3:
        action, position = "开盘买入或追涨", "20%仓位"
        logic = f"前夜原油大涨+{brent_change:.2f}%，预计高开{brent_change*0.7:.2f}%"
        risk = "若开盘后涨幅已超3%，不建议追高"
    elif brent_change > 1.5:
        action, position = "开盘适量买入", "10-15%仓位"
        logic = f"前夜原油上涨+{brent_change:.2f}%，预计高开{brent_change*0.7:.2f}%"
        risk = "关注量能，无量上涨需警惕"
    elif brent_change > 0:
        action, position = "轻仓试探", "5-10%仓位"
        logic = f"前夜原油微涨+{brent_change:.2f}%，预计小幅高开"
        risk = "关注开盘后能否持续走强"
    elif brent_change > -1.5:
        action, position = "观望", "暂不介入"
        logic = f"前夜原油微跌{brent_change:.2f}%，预计小幅低开或平开"
        risk = "等待更明确信号"
    else:
        action, position = "关注抄底机会", "轻仓试探"
        logic = f"前夜原油下跌{brent_change:.2f}%，若大幅低开可考虑抄底"
        risk = "注意下跌趋势是否延续"
    
    return {
        'action': action,
        'predicted_open': predicted_open,
        'target': predicted_open * 1.02,
        'stop_loss': predicted_open * 0.98,
        'logic': logic,
        'risk': risk,
        'position': position,
        'brent_change': brent_change
    }

def generate_cyb_prediction(market_data):
    """生成易方达创业板ETF(159915)预测（基于油价负相关）"""
    brent_change = market_data['brent_change']
    cyb_current = market_data['cyb_price']
    
    # 逻辑：油价上涨 → 通胀担忧 → 高估值成长股承压 → 创业板ETF下跌
    # 油价下跌 → 通胀缓解 → 成长股受益 → 创业板ETF上涨
    expected_cyb_change = -brent_change * 0.5  # 负相关，弹性系数0.5
    predicted_cyb = cyb_current * (1 + expected_cyb_change / 100)
    
    if brent_change > 2:
        action = "逢高减仓或观望"
        logic = f"前夜油价大涨+{brent_change:.2f}%，高估值成长股承压，159915可能低开或走弱"
        risk = "若油价持续上涨，159915承压时间较长"
        position = "减仓至50%以下"
    elif brent_change > 0.5:
        action = "持仓观望"
        logic = f"前夜油价上涨+{brent_change:.2f}%，对高估值板块有轻微压制"
        risk = "关注开盘后资金流向"
        position = "维持仓位"
    elif brent_change > -0.5:
        action = "正常交易"
        logic = f"前夜油价波动较小，对159915影响有限"
        risk = "按个股基本面操作"
        position = "正常仓位"
    elif brent_change > -2:
        action = "关注机会"
        logic = f"前夜油价下跌{brent_change:.2f}%，通胀担忧缓解，成长股受益"
        risk = "注意是否为短期回调"
        position = "可适当加仓"
    else:
        action = "积极关注"
        logic = f"前夜油价大跌{brent_change:.2f}%，通胀预期降温，高估值板块迎来喘息"
        risk = "关注抄底资金流向"
        position = "加仓至80%"
    
    return {
        'action': action,
        'predicted_cyb': predicted_cyb,
        'expected_change': expected_cyb_change,
        'logic': logic,
        'risk': risk,
        'position': position,
    }

def generate_military_etf_prediction(market_data):
    """生成军工ETF预测"""
    vix_change = market_data['vix_change']
    base_nav = 1.20
    predicted_open = base_nav * (1 + abs(vix_change) * 0.3 / 100)
    
    if vix_change < -4:
        action, position = "持仓观望或减仓", "暂不新增"
        logic = f"VIX-ETF大幅回落{vix_change:.2f}%，风险偏好回升"
        risk = "若VIX反弹超+5%，可重新介入"
    elif vix_change < -2:
        action, position = "持仓观望", "维持现有"
        logic = f"VIX-ETF回落{vix_change:.2f}%，地缘风险缓解"
        risk = "关注VIX能否持续下行"
    elif vix_change < 0:
        action, position = "关注机会", "小仓位试探"
        logic = f"VIX-ETF小幅回落{vix_change:.2f}%"
        risk = "观望为主"
    elif vix_change < 2:
        action, position = "关注买入机会", "10%试探"
        logic = f"VIX-ETF上涨+{vix_change:.2f}%，地缘风险略升"
        risk = "注意追高"
    else:
        action, position = "积极买入", "15-20%参与"
        logic = f"VIX-ETF大涨+{vix_change:.2f}%，避险情绪升温"
        risk = "注意波动"
    
    return {
        'action': action,
        'predicted_open': predicted_open,
        'logic': logic,
        'risk': risk,
        'position': position,
        'vix_change': vix_change
    }

def fetch_historical_data(symbol, days=30):
    """获取历史数据（使用新浪财经或AkShare）"""
    import akshare as ak
    from datetime import datetime, timedelta
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days+10)  # 多取几天过滤周末
    
    try:
        if symbol == 'brent':
            # 使用AkShare获取原油期货历史数据
            df = ak.futures_foreign_hist(symbol="CL")
            if df is not None and len(df) > 0:
                df = df.tail(days).copy()
                df['date'] = pd.to_datetime(df['date'])
                return df[['date', 'close']].rename(columns={'close': 'price'})
        elif symbol == 'gold':
            # 黄金期货历史数据
            df = ak.futures_foreign_hist(symbol="GC")
            if df is not None and len(df) > 0:
                df = df.tail(days).copy()
                df['date'] = pd.to_datetime(df['date'])
                return df[['date', 'close']].rename(columns={'close': 'price'})
        elif symbol == 'cyb':
            # 易方达创业板ETF (159915) 历史数据（替代创业板指）
            try:
                df = ak.fund_etf_hist_em(symbol="159915", period="daily",
                                         start_date=start_date.strftime("%Y%m%d"),
                                         end_date=end_date.strftime("%Y%m%d"),
                                         adjust="qfq")  # 前复权
                if df is not None and len(df) > 0:
                    df['日期'] = pd.to_datetime(df['日期'])
                    return df[['日期', '收盘']].rename(columns={'日期': 'date', '收盘': 'price'})
            except Exception as e:
                print(f"   ⚠️ 获取159915历史数据失败: {e}")
        elif symbol == 'oil_etf':
            # 石油ETF (561360) 历史净值数据
            try:
                df = ak.fund_etf_hist_em(symbol="561360", period="daily",
                                         start_date=start_date.strftime("%Y%m%d"),
                                         end_date=end_date.strftime("%Y%m%d"),
                                         adjust="qfq")  # 前复权
                if df is not None and len(df) > 0:
                    df['日期'] = pd.to_datetime(df['日期'])
                    return df[['日期', '收盘']].rename(columns={'日期': 'date', '收盘': 'price'})
            except Exception as e:
                print(f"   ⚠️ 获取石油ETF历史数据失败: {e}")
        elif symbol == 'military_etf':
            # 军工ETF (512560) 历史净值数据
            try:
                df = ak.fund_etf_hist_em(symbol="512560", period="daily",
                                         start_date=start_date.strftime("%Y%m%d"),
                                         end_date=end_date.strftime("%Y%m%d"),
                                         adjust="qfq")  # 前复权
                if df is not None and len(df) > 0:
                    df['日期'] = pd.to_datetime(df['日期'])
                    return df[['日期', '收盘']].rename(columns={'日期': 'date', '收盘': 'price'})
            except Exception as e:
                print(f"   ⚠️ 获取军工ETF历史数据失败: {e}")
    except Exception as e:
        print(f"   ⚠️ 获取{symbol}历史数据失败: {e}")
    
    return None

def create_prediction_chart_v3(asset_type, market_data, prediction):
    """生成预测图表 - V3版本（使用真实历史数据）"""
    
    today = datetime.now()
    hist_days = 20
    pred_days = 3
    total_days = hist_days + pred_days
    
    # 根据数据点数量动态计算图表宽度（每个数据点约100像素宽度）
    base_width = 16
    min_width_per_point = 0.5  # 每个数据点至少0.5英寸宽度
    fig_width = max(base_width, total_days * min_width_per_point)
    fig_height = 9
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    
    # 尝试获取真实历史数据
    print(f"   📊 正在获取{asset_type}历史数据...")
    
    if asset_type == 'oil':
        ax_twin = ax.twinx()
        
        # 获取Brent原油真实历史数据
        brent_hist = fetch_historical_data('brent', days=30)
        # 获取石油ETF真实历史数据
        etf_hist = fetch_historical_data('oil_etf', days=30)
        
        if brent_hist is not None and len(brent_hist) >= hist_days:
            hist_dates = brent_hist['date'].tail(hist_days).tolist()
            hist_brent = brent_hist['price'].tail(hist_days).tolist()
            print(f"   ✅ Brent使用真实历史数据（{len(hist_brent)}天）")
            print(f"      日期范围: {hist_dates[0]} ~ {hist_dates[-1]}")
            print(f"      价格范围: {min(hist_brent):.2f} ~ {max(hist_brent):.2f}")
        else:
            base_price = market_data['brent_price'] - prediction['brent_change'] * 0.7
            hist_dates = [today - timedelta(days=hist_days-i) for i in range(hist_days)]
            hist_brent = [base_price - (hist_days - i) * 0.3 + np.random.randn() * 0.8 for i in range(hist_days)]
            hist_brent[-1] = base_price
            print(f"   ⚠️ Brent使用模拟历史数据")
        
        # 获取石油ETF真实净值
        if etf_hist is not None and len(etf_hist) >= hist_days:
            hist_etf = etf_hist['price'].tail(hist_days).tolist()
            print(f"   ✅ 石油ETF使用真实历史净值")
            print(f"      净值范围: {min(hist_etf):.3f} ~ {max(hist_etf):.3f}")
        else:
            # 回退到简化映射（但不会与Brent完全重合，因为会有随机波动）
            base_etf = 1.30  # 基础净值
            hist_etf = [base_etf + np.random.randn() * 0.02 for _ in range(hist_days)]
            # 根据油价趋势微调
            for i in range(1, hist_days):
                brent_change_pct = (hist_brent[i] - hist_brent[i-1]) / hist_brent[i-1] * 100 if hist_brent[i-1] > 0 else 0
                hist_etf[i] = hist_etf[i-1] * (1 + brent_change_pct * 0.5 / 100)  # 0.5倍弹性
            print(f"   ⚠️ 石油ETF使用模拟净值")
        
        # 预测数据（未来3天）
        pred_dates = [today + timedelta(days=i+1) for i in range(pred_days)]
        pred_brent = [market_data['brent_price'] + prediction['brent_change'] * (i+1) * 0.3 for i in range(pred_days)]
        # ETF预测基于前夜油价变化
        last_etf = hist_etf[-1] if hist_etf else 1.30
        pred_etf = [last_etf * (1 + prediction['brent_change'] * 0.7 * (i+1) / 100) for i in range(pred_days)]
        
        # 先设置Y轴范围确保两条曲线都可见
        all_brent_full = hist_brent + pred_brent
        all_etf_full = hist_etf + pred_etf
        ax.set_ylim(min(all_brent_full) * 0.95, max(all_brent_full) * 1.05)
        ax_twin.set_ylim(min(all_etf_full) * 0.95, max(all_etf_full) * 1.05)
        
        # 绘制历史数据（实线）- 使用不同线宽和透明度让两条线都可见
        line1 = ax.plot(hist_dates, hist_brent, color='#0066CC', linewidth=5, label='Brent原油', 
                       marker='o', markersize=7, markerfacecolor='white', markeredgewidth=2, alpha=0.8)
        line2 = ax_twin.plot(hist_dates, hist_etf, color='#CC0000', linewidth=2, label='石油ETF (561360)', 
                            marker='s', markersize=4, linestyle='--')
        
        # 绘制预测数据（虚线）
        ax.plot([hist_dates[-1]] + pred_dates, [hist_brent[-1]] + pred_brent, 
               color='#0066CC', linestyle='-.', linewidth=4, alpha=0.6, marker='o', markersize=6)
        ax_twin.plot([hist_dates[-1]] + pred_dates, [hist_etf[-1]] + pred_etf, 
                    color='#CC0000', linestyle=':', linewidth=2, alpha=0.6, marker='s', markersize=5)
        
        # 今天开盘标注
        ax.axvline(today, color='green', linestyle='-', alpha=0.8, linewidth=3)
        ylim1, ylim2 = ax.get_ylim()
        ax.annotate('今天开盘', xy=(today, ylim2 * 0.98), 
                    fontsize=12, ha='center', color='green', fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.4', facecolor='lightgreen', edgecolor='green'))
        
        # 价格标注 - 每天显示，Brent在上方，ETF在下方，避免重叠
        all_dates = hist_dates + pred_dates
        all_brent = hist_brent + pred_brent
        all_etf = hist_etf + pred_etf
        for i in range(len(all_dates)):
            # Brent原油价格显示在点上方
            ax.annotate(f'{all_brent[i]:.1f}', xy=(all_dates[i], all_brent[i]),
                       fontsize=7, color='#0066CC', ha='center', va='bottom', 
                       fontweight='bold', xytext=(0, 5), textcoords='offset points')
            # ETF价格显示在点下方
            ax_twin.annotate(f'{all_etf[i]:.3f}', xy=(all_dates[i], all_etf[i]),
                            fontsize=7, color='#CC0000', ha='center', va='top', 
                            fontweight='bold', xytext=(0, -5), textcoords='offset points')
        
        ax.set_ylabel('Brent原油价格 (美元)', fontsize=13, color='blue', fontweight='bold')
        ax_twin.set_ylabel('石油ETF 561360 净值 (元)', fontsize=13, color='red', fontweight='bold')
        ax.tick_params(axis='y', labelcolor='blue', labelsize=11)
        ax_twin.tick_params(axis='y', labelcolor='red', labelsize=11)
        
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax.legend(lines, labels, loc='upper left', fontsize=12, framealpha=0.9)
        
        change_str = f"{prediction['brent_change']:+.2f}%"
        ax.set_title(f'滚动预测①：石油ETF (561360) 与 Brent 原油 | 前夜{change_str}', 
                     fontsize=15, fontweight='bold', pad=15)
    
    elif asset_type == 'cyb_oil':
        ax_twin = ax.twinx()
        
        # 获取Brent和易方达创业板ETF(159915)真实历史数据
        brent_hist = fetch_historical_data('brent', days=30)
        cyb_hist = fetch_historical_data('cyb', days=30)
        
        if brent_hist is not None and len(brent_hist) >= hist_days:
            hist_dates = brent_hist['date'].tail(hist_days).tolist()
            hist_brent = brent_hist['price'].tail(hist_days).tolist()
            print(f"   ✅ Brent使用真实历史数据")
        else:
            base_brent = market_data['brent_price'] - market_data['brent_change'] * 0.7
            hist_dates = [today - timedelta(days=hist_days-i) for i in range(hist_days)]
            hist_brent = [base_brent - (hist_days - i) * 0.3 + np.random.randn() * 0.8 for i in range(hist_days)]
            hist_brent[-1] = base_brent
            print(f"   ⚠️ Brent使用模拟数据")
        
        if cyb_hist is not None and len(cyb_hist) >= hist_days:
            hist_cyb = cyb_hist['price'].tail(hist_days).tolist()
            print(f"   ✅ 易方达创业板ETF(159915)使用真实历史数据")
        else:
            base_cyb = market_data['cyb_price'] / (1 - market_data['brent_change'] * 0.005)
            hist_cyb = [base_cyb + (hist_brent[i] - hist_brent[0]) * (-8) + np.random.randn() * 10 for i in range(hist_days)]
            hist_cyb[-1] = base_cyb
            print(f"   ⚠️ 易方达创业板ETF(159915)使用模拟数据")
        
        # 预测数据
        pred_dates = [today + timedelta(days=i+1) for i in range(pred_days)]
        pred_brent = [market_data['brent_price'] + market_data['brent_change'] * (i+1) * 0.3 for i in range(pred_days)]
        pred_cyb = [market_data['cyb_price'] - market_data['brent_change'] * 0.5 * (i+1) * 5 for i in range(pred_days)]
        
        # 绘制
        line1 = ax.plot(hist_dates, hist_brent, 'b-', linewidth=3, label='Brent原油', marker='o', markersize=4)
        line2 = ax_twin.plot(hist_dates, hist_cyb, 'orange', linewidth=3, label='易方达创业板ETF (159915)', marker='s', markersize=4)
        ax.plot([hist_dates[-1]] + pred_dates, [hist_brent[-1]] + pred_brent, 'b--', linewidth=3, alpha=0.6, marker='o', markersize=6)
        ax_twin.plot([hist_dates[-1]] + pred_dates, [hist_cyb[-1]] + pred_cyb, 'orange', linestyle='--', linewidth=3, alpha=0.6, marker='s', markersize=6)
        
        ax.axvline(today, color='green', linestyle='-', alpha=0.8, linewidth=3)
        ax.annotate('今天开盘', xy=(today, ax.get_ylim()[1]*0.95), 
                    fontsize=12, ha='center', color='green', fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.4', facecolor='lightgreen', edgecolor='green'))
        
        # 价格标注 - 每天显示，Brent在上方，创业板在下方
        all_dates = hist_dates + pred_dates
        all_brent = hist_brent + pred_brent
        all_cyb = hist_cyb + pred_cyb
        for i in range(len(all_dates)):
            ax.annotate(f'{all_brent[i]:.1f}', xy=(all_dates[i], all_brent[i]),
                       fontsize=7, color='blue', ha='center', va='bottom',
                       fontweight='bold', xytext=(0, 5), textcoords='offset points')
            ax_twin.annotate(f'{all_cyb[i]:.0f}', xy=(all_dates[i], all_cyb[i]),
                            fontsize=7, color='darkorange', ha='center', va='top',
                            fontweight='bold', xytext=(0, -5), textcoords='offset points')
        
        ax.set_ylabel('Brent原油价格 (美元)', fontsize=13, color='blue', fontweight='bold')
        ax_twin.set_ylabel('易方达创业板ETF (159915) 净值 (元)', fontsize=13, color='darkorange', fontweight='bold')
        ax.tick_params(axis='y', labelcolor='blue', labelsize=11)
        ax_twin.tick_params(axis='y', labelcolor='darkorange', labelsize=11)
        
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax.legend(lines, labels, loc='upper left', fontsize=12)
        
        change_str = f"{market_data['brent_change']:+.2f}%"
        ax.set_title(f'滚动预测③：易方达创业板ETF (159915) 与 Brent 原油 | 负相关 | 前夜{change_str}', 
                     fontsize=15, fontweight='bold', pad=15)
        
        ax.text(0.02, 0.02, '→ 油价↑ 通胀↑ 成长股估值承压 → 159915↓', 
                transform=ax.transAxes, fontsize=10, color='gray', style='italic')
    
    elif asset_type == 'military':
        ax_twin1 = ax.twinx()
        ax_twin2 = ax.twinx()
        ax_twin2.spines['right'].set_position(('outward', 80))
        
        # 获取黄金真实历史数据
        gold_hist = fetch_historical_data('gold', days=30)
        # 获取军工ETF真实历史净值
        mil_etf_hist = fetch_historical_data('military_etf', days=30)
        
        if gold_hist is not None and len(gold_hist) >= hist_days:
            hist_dates = gold_hist['date'].tail(hist_days).tolist()
            hist_gold = gold_hist['price'].tail(hist_days).tolist()
            print(f"   ✅ 黄金使用真实历史数据")
        else:
            hist_dates = [today - timedelta(days=hist_days-i) for i in range(hist_days)]
            hist_gold = [market_data['gold_price'] + np.random.randn() * 10 for _ in range(hist_days)]
            print(f"   ⚠️ 黄金使用模拟数据")
        
        # 军工ETF净值 - 使用真实数据
        if mil_etf_hist is not None and len(mil_etf_hist) >= hist_days:
            hist_military = mil_etf_hist['price'].tail(hist_days).tolist()
            print(f"   ✅ 军工ETF使用真实历史净值")
            print(f"      净值范围: {min(hist_military):.3f} ~ {max(hist_military):.3f}")
        else:
            # VIX数据作为参考 - 模拟历史走势
            base_vix = market_data['vix_price'] - prediction['vix_change'] * 0.5
            hist_vix = [base_vix - (hist_days - i) * 0.15 + np.random.randn() * 1.2 for i in range(hist_days)]
            hist_vix[-1] = base_vix
            # 军工ETF净值（基于VIX反向映射）
            hist_military = [1.8 + (v - 30) * 0.02 + np.random.randn() * 0.05 for v in hist_vix]
            print(f"   ⚠️ 军工ETF使用模拟净值")
        
        # VIX数据（使用ETF价格作为参考）- 模拟历史走势
        base_vix = market_data['vix_price'] - prediction['vix_change'] * 0.5
        hist_vix = [base_vix - (hist_days - i) * 0.15 + np.random.randn() * 1.2 for i in range(hist_days)]
        hist_vix[-1] = base_vix
        
        # 预测数据
        pred_dates = [today + timedelta(days=i+1) for i in range(pred_days)]
        pred_vix = [market_data['vix_price'] + prediction['vix_change'] * (i+1) * 0.3 for i in range(pred_days)]
        # 军工ETF预测
        last_mil = hist_military[-1] if hist_military else 1.80
        pred_military = [last_mil * (1 + prediction['vix_change'] * 0.3 * (i+1) / 100) for i in range(pred_days)]
        pred_gold = [market_data['gold_price'] + np.random.randn() * 5 for _ in range(pred_days)]
        
        # 设置Y轴范围确保所有曲线可见
        all_vix_full = hist_vix + pred_vix
        all_military_full = hist_military + pred_military
        all_gold_full = hist_gold + pred_gold
        
        ax.set_ylim(min(all_vix_full) * 0.9, max(all_vix_full) * 1.1)
        ax_twin1.set_ylim(min(all_military_full) * 0.95, max(all_military_full) * 1.05)
        ax_twin2.set_ylim(min(all_gold_full) * 0.95, max(all_gold_full) * 1.05)
        
        # 绘制历史数据（实线）- 使用更醒目的颜色
        line1 = ax.plot(hist_dates, hist_vix, color='#8B008B', linewidth=4, label=f"{market_data.get('vix_name', 'VIX-ETF')}", marker='o', markersize=5)
        line2 = ax_twin1.plot(hist_dates, hist_military, 'g-', linewidth=3, label='军工ETF (512560)', marker='s', markersize=5)
        line3 = ax_twin2.plot(hist_dates, hist_gold, 'goldenrod', linewidth=3, label='COMEX黄金', marker='^', markersize=5)
        
        # 绘制预测数据（虚线）
        ax.plot([hist_dates[-1]] + pred_dates, [hist_vix[-1]] + pred_vix, color='#8B008B', linestyle='--', linewidth=3, alpha=0.6, marker='o', markersize=6)
        ax_twin1.plot([hist_dates[-1]] + pred_dates, [hist_military[-1]] + pred_military, 'g--', linewidth=3, alpha=0.6, marker='s', markersize=6)
        ax_twin2.plot([hist_dates[-1]] + pred_dates, [hist_gold[-1]] + pred_gold, 'goldenrod', linestyle='--', linewidth=3, alpha=0.6, marker='^', markersize=6)
        
        ax.axvline(today, color='green', linestyle='-', alpha=0.8, linewidth=3)
        ylim1, ylim2 = ax.get_ylim()
        ax.annotate('今天开盘', xy=(today, ylim2 * 0.98), fontsize=12, ha='center', color='green', fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.4', facecolor='lightgreen', edgecolor='green'))
        
        # 价格标注 - 每天显示，三个Y轴错位避免重叠
        all_dates = hist_dates + pred_dates
        all_vix = hist_vix + pred_vix
        all_military = hist_military + pred_military
        all_gold = hist_gold + pred_gold
        for i in range(len(all_dates)):
            # VIX在上方（左Y轴）
            ax.annotate(f'{all_vix[i]:.1f}', xy=(all_dates[i], all_vix[i]), 
                       fontsize=7, color='#8B008B', ha='center', va='bottom', 
                       fontweight='bold', xytext=(0, 5), textcoords='offset points')
            # 军工ETF在下方（中Y轴）
            ax_twin1.annotate(f'{all_military[i]:.3f}', xy=(all_dates[i], all_military[i]), 
                             fontsize=7, color='green', ha='center', va='top',
                             fontweight='bold', xytext=(0, -5), textcoords='offset points')
            # 黄金在点旁边（右Y轴），稍微偏移
            ax_twin2.annotate(f'{all_gold[i]:.0f}', xy=(all_dates[i], all_gold[i]), 
                             fontsize=7, color='goldenrod', ha='left', va='center',
                             fontweight='bold', xytext=(5, 0), textcoords='offset points')
        
        ax.set_ylabel(f"{market_data.get('vix_name', 'VIX-ETF')} 价格", fontsize=13, color='#8B008B', fontweight='bold')
        ax_twin1.set_ylabel('军工ETF 512560 净值 (元)', fontsize=13, color='green', fontweight='bold')
        ax_twin2.set_ylabel('COMEX黄金 (美元)', fontsize=13, color='goldenrod', fontweight='bold')
        ax.tick_params(axis='y', labelcolor='#8B008B', labelsize=11)
        ax_twin1.tick_params(axis='y', labelcolor='green', labelsize=11)
        ax_twin2.tick_params(axis='y', labelcolor='goldenrod', labelsize=11)
        
        lines = line1 + line2 + line3
        labels = [l.get_label() for l in lines]
        ax.legend(lines, labels, loc='upper left', fontsize=11, framealpha=0.9)
        
        ax.set_title(f'滚动预测②：军工ETF 与 {market_data.get("vix_name", "VIX-ETF")}、黄金 | 前夜{prediction["vix_change"]:+.2f}%', 
                     fontsize=15, fontweight='bold', pad=15)
    
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # 设置X轴：每天显示一个刻度，旋转标签避免重叠
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax.xaxis.set_major_locator(mdates.DayLocator())  # 每天一个刻度
    
    # 旋转日期标签45度，右对齐
    for label in ax.get_xticklabels():
        label.set_rotation(45)
        label.set_horizontalalignment('right')
        label.set_fontsize(10)
    
    plt.tight_layout()
    
    filename = f'/tmp/rolling_pred_full_{asset_type}_{today.strftime("%Y%m%d")}.png'
    plt.savefig(filename, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return filename

def send_prediction_to_feishu():
    """主函数：获取数据、生成图表、发送飞书"""
    
    if not is_trading_day():
        print("今天不是交易日，跳过推送")
        return
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"📊 {today_str} 滚动预测推送开始...")
    
    # 1. 获取市场数据
    market_data = fetch_overnight_market_data()
    
    # 2. 生成预测
    oil_pred = generate_oil_etf_prediction(market_data)
    cyb_pred = generate_cyb_prediction(market_data)
    military_pred = generate_military_etf_prediction(market_data)
    
    # 3. 生成图表（3个）
    oil_chart = create_prediction_chart_v3('oil', market_data, oil_pred)
    cyb_chart = create_prediction_chart_v3('cyb_oil', market_data, cyb_pred)
    military_chart = create_prediction_chart_v3('military', market_data, military_pred)
    
    # 4. 发送飞书
    bot = FeishuBotAPI()
    chat_id = "oc_4bb4a856f51474c4b0ef342d798ca731"
    
    data_source = "新浪财经（期货+ETF+指数）" if market_data.get('is_real', False) else "新浪财经(部分)+默认"
    
    # 石油ETF消息
    oil_footer = f"""**📊 前夜海外市场数据（截至{today_str} 08:00）**

→ Brent原油：**{'+' if market_data['brent_change'] > 0 else ''}{market_data['brent_change']:.2f}%**（现报 {market_data['brent_price']:.2f}美元）
→ WTI原油：**{'+' if market_data['wti_change'] > 0 else ''}{market_data['wti_change']:.2f}%**（现报 {market_data['wti_price']:.2f}美元）
→ {market_data.get('dxy_name', '美元ETF')}：**{'+' if market_data['dxy_change'] > 0 else ''}{market_data['dxy_change']:.2f}%**（现报 {market_data['dxy_price']:.2f}）

**💡 今日交易建议：石油ETF (561360)**
• **建议操作**：{oil_pred['action']}
• **预测开盘**：{oil_pred['predicted_open']:.3f}元
• **目标价位**：{oil_pred['target']:.3f}元
• **止损设置**：{oil_pred['stop_loss']:.3f}元（-2%）
• **仓位建议**：{oil_pred['position']}
• **逻辑**：{oil_pred['logic']}

**⚠️ 风险提示**
→ {oil_pred['risk']}
→ 关注今晚EIA原油库存数据

**📡 数据来源**：{data_source}"""

    bot.send_image_card(
        chat_id=chat_id,
        image_path=oil_chart,
        caption=f"📈 滚动预测①：石油ETF (561360) | {today_str} 开盘前策略",
        footer_text=oil_footer
    )
    
    # 易方达创业板ETF消息
    cyb_footer = f"""**📊 市场数据（截至{today_str} 08:00）**

→ 易方达创业板ETF (159915)：{market_data['cyb_price']:.3f} 元
→ Brent原油：**{'+' if market_data['brent_change'] > 0 else ''}{market_data['brent_change']:.2f}%**（现报 {market_data['brent_price']:.2f}美元）
→ {market_data.get('dxy_name', '美元ETF')}：**{'+' if market_data['dxy_change'] > 0 else ''}{market_data['dxy_change']:.2f}%**

**💡 今日交易建议：高估值成长股/创业板ETF**
• **建议操作**：{cyb_pred['action']}
• **预测开盘**：{cyb_pred['predicted_cyb']:.3f}元（预期{cyb_pred['expected_change']:+.2f}%）
• **仓位建议**：{cyb_pred['position']}
• **逻辑**：{cyb_pred['logic']}

**⚠️ 风险提示**
→ {cyb_pred['risk']}
→ 油价与成长股估值呈负相关，关注美联储政策表态

**📡 数据来源**：{data_source}"""

    bot.send_image_card(
        chat_id=chat_id,
        image_path=cyb_chart,
        caption=f"📈 滚动预测③：易方达创业板ETF(159915) vs Brent原油（负相关） | {today_str} 策略",
        footer_text=cyb_footer
    )
    
    # 军工ETF消息
    military_footer = f"""**📊 前夜海外市场数据（截至{today_str} 08:00）**

→ {market_data.get('vix_name', 'VIX-ETF')}：**{market_data['vix_change']:+.2f}%**（现报 {market_data['vix_price']:.2f}）
→ 黄金：**{'+' if market_data['gold_change'] > 0 else ''}{market_data['gold_change']:.2f}%**（现报 {market_data['gold_price']:.0f}美元）
→ Brent原油：**{'+' if market_data['brent_change'] > 0 else ''}{market_data['brent_change']:.2f}%**

**💡 今日交易建议：军工ETF (512560)**
• **建议操作**：{military_pred['action']}
• **预测开盘**：{military_pred['predicted_open']:.3f}元
• **仓位建议**：{military_pred['position']}
• **逻辑**：{military_pred['logic']}

**⚠️ 风险提示**
→ {military_pred['risk']}
→ 关注中东局势最新进展

**📡 数据来源**：{data_source}"""

    bot.send_image_card(
        chat_id=chat_id,
        image_path=military_chart,
        caption=f"📈 滚动预测②：军工ETF 与 {market_data.get('vix_name', 'VIX-ETF')} | {today_str} 策略",
        footer_text=military_footer
    )
    
    print(f"✅ {today_str} 滚动预测推送完成！共3条")

if __name__ == "__main__":
    send_prediction_to_feishu()

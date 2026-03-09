"""
技术分析指标计算
支持：MA(移动平均线), MACD, RSI, KDJ, BOLL(布林带), VOL(成交量)
"""
import pandas as pd
import numpy as np
import json
import sys
from typing import List, Dict

def calculate_ma(data: pd.DataFrame, periods: List[int] = [5, 10, 20, 30, 60]) -> pd.DataFrame:
    """
    计算移动平均线 (Moving Average)
    
    Args:
        data: DataFrame with 'close' column
        periods: MA周期列表，默认 [5, 10, 20, 30, 60]
    
    Returns:
        DataFrame with MA columns
    """
    df = data.copy()
    for period in periods:
        df[f'MA{period}'] = df['close'].rolling(window=period).mean()
    return df

def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """计算指数移动平均线"""
    return data.ewm(span=period, adjust=False).mean()

def calculate_macd(data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    计算MACD指标
    
    MACD = EMA(12) - EMA(26)
    Signal = EMA(MACD, 9)
    Histogram = MACD - Signal
    
    Args:
        data: DataFrame with 'close' column
        fast: 快线周期，默认12
        slow: 慢线周期，默认26
        signal: 信号线周期，默认9
    """
    df = data.copy()
    ema_fast = calculate_ema(df['close'], fast)
    ema_slow = calculate_ema(df['close'], slow)
    
    df['MACD'] = ema_fast - ema_slow
    df['MACD_Signal'] = calculate_ema(df['MACD'], signal)
    df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
    
    return df

def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    计算RSI指标 (Relative Strength Index)
    
    RSI = 100 - (100 / (1 + RS))
    RS = 平均涨幅 / 平均跌幅
    
    Args:
        data: DataFrame with 'close' column
        period: RSI周期，默认14
    """
    df = data.copy()
    delta = df['close'].diff()
    
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

def calculate_kdj(data: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
    """
    计算KDJ指标
    
    RSV = (收盘价 - N日内最低价) / (N日内最高价 - N日内最低价) * 100
    K = 2/3 * 前K值 + 1/3 * RSV
    D = 2/3 * 前D值 + 1/3 * K
    J = 3K - 2D
    
    Args:
        data: DataFrame with 'high', 'low', 'close' columns
        n: RSV周期，默认9
        m1: K平滑周期，默认3
        m2: D平滑周期，默认3
    """
    df = data.copy()
    
    low_list = df['low'].rolling(window=n, min_periods=n).min()
    high_list = df['high'].rolling(window=n, min_periods=n).max()
    
    rsv = (df['close'] - low_list) / (high_list - low_list) * 100
    
    df['K'] = rsv.ewm(com=m1-1, adjust=False).mean()
    df['D'] = df['K'].ewm(com=m2-1, adjust=False).mean()
    df['J'] = 3 * df['K'] - 2 * df['D']
    
    return df

def calculate_boll(data: pd.DataFrame, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
    """
    计算布林带 (Bollinger Bands)
    
    中轨 = MA20
    上轨 = MA20 + 2 * STD
    下轨 = MA20 - 2 * STD
    
    Args:
        data: DataFrame with 'close' column
        period: 周期，默认20
        std_dev: 标准差倍数，默认2
    """
    df = data.copy()
    
    df['BOLL_MID'] = df['close'].rolling(window=period).mean()
    df['BOLL_STD'] = df['close'].rolling(window=period).std()
    df['BOLL_UPPER'] = df['BOLL_MID'] + std_dev * df['BOLL_STD']
    df['BOLL_LOWER'] = df['BOLL_MID'] - std_dev * df['BOLL_STD']
    
    return df

def calculate_vol(data: pd.DataFrame, periods: List[int] = [5, 10, 20]) -> pd.DataFrame:
    """
    计算成交量均线
    
    Args:
        data: DataFrame with 'volume' column
        periods: 周期列表，默认 [5, 10, 20]
    """
    df = data.copy()
    for period in periods:
        df[f'VOL_MA{period}'] = df['volume'].rolling(window=period).mean()
    return df

def analyze_all(data: pd.DataFrame) -> pd.DataFrame:
    """
    计算所有技术指标
    
    Args:
        data: DataFrame with 'open', 'high', 'low', 'close', 'volume' columns
    
    Returns:
        DataFrame with all indicators
    """
    df = data.copy()
    
    # 计算所有指标
    df = calculate_ma(df)
    df = calculate_macd(df)
    df = calculate_rsi(df)
    df = calculate_kdj(df)
    df = calculate_boll(df)
    df = calculate_vol(df)
    
    return df

def get_latest_signals(df: pd.DataFrame) -> Dict:
    """
    获取最新行情的技术信号
    
    Returns:
        Dict with signal analysis
    """
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None
    
    signals = {
        "价格信息": {
            "当前价": round(latest['close'], 2),
            "开盘价": round(latest.get('open', 0), 2),
            "最高价": round(latest.get('high', 0), 2),
            "最低价": round(latest.get('low', 0), 2),
            "成交量": int(latest.get('volume', 0))
        },
        "移动平均线": {
            "MA5": round(latest.get('MA5', 0), 2),
            "MA10": round(latest.get('MA10', 0), 2),
            "MA20": round(latest.get('MA20', 0), 2),
            "MA60": round(latest.get('MA60', 0), 2)
        },
        "MACD": {
            "MACD": round(latest.get('MACD', 0), 4),
            "信号线": round(latest.get('MACD_Signal', 0), 4),
            "柱状图": round(latest.get('MACD_Histogram', 0), 4),
            "信号": "金叉" if prev is not None and prev.get('MACD', 0) < prev.get('MACD_Signal', 0) and latest.get('MACD', 0) > latest.get('MACD_Signal', 0) else 
                     "死叉" if prev is not None and prev.get('MACD', 0) > prev.get('MACD_Signal', 0) and latest.get('MACD', 0) < latest.get('MACD_Signal', 0) else 
                     "维持"
        },
        "RSI": {
            "RSI(14)": round(latest.get('RSI', 0), 2),
            "状态": "超买" if latest.get('RSI', 50) > 70 else "超卖" if latest.get('RSI', 50) < 30 else "正常"
        },
        "KDJ": {
            "K": round(latest.get('K', 0), 2),
            "D": round(latest.get('D', 0), 2),
            "J": round(latest.get('J', 0), 2),
            "信号": "金叉" if prev is not None and prev.get('K', 0) < prev.get('D', 0) and latest.get('K', 0) > latest.get('D', 0) else
                     "死叉" if prev is not None and prev.get('K', 0) > prev.get('D', 0) and latest.get('K', 0) < latest.get('D', 0) else
                     "维持"
        },
        "布林带": {
            "上轨": round(latest.get('BOLL_UPPER', 0), 2),
            "中轨": round(latest.get('BOLL_MID', 0), 2),
            "下轨": round(latest.get('BOLL_LOWER', 0), 2),
            "位置": "上轨附近" if latest['close'] > latest.get('BOLL_MID', 0) * 1.01 else
                    "下轨附近" if latest['close'] < latest.get('BOLL_MID', 0) * 0.99 else
                    "中轨附近"
        }
    }
    
    return signals

if __name__ == "__main__":
    print("技术分析指标计算模块")
    print("请使用 analyze_all() 函数计算所有指标")
    print("或使用 get_latest_signals() 获取最新信号")

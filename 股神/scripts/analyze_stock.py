"""
A股完整分析示例
一键获取数据、计算指标、生成报告和可视化
"""
import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fetch_sina_data import fetch_stock_data
from technical_analysis import analyze_all, get_latest_signals
from visualize import generate_analysis_report

def analyze_stock(stock_code: str, stock_name: str = None):
    """
    对单只股票进行完整分析
    
    Args:
        stock_code: 股票代码（如：600519、000001）
        stock_name: 股票名称（可选）
    
    Returns:
        dict: 分析结果
    """
    print(f"\n{'='*60}")
    print(f"正在分析股票: {stock_code}")
    print(f"{'='*60}\n")
    
    # 1. 获取实时数据
    print("[1/3] 获取实时行情数据...")
    real_time_data = fetch_stock_data(stock_code)
    
    if "error" in real_time_data:
        print(f"错误: {real_time_data['error']}")
        return None
    
    stock_key = list(real_time_data.keys())[0]
    data = real_time_data[stock_key]
    
    if "error" in data:
        print(f"错误: {data['error']}")
        return None
    
    name = data.get('name', stock_code)
    print(f"股票名称: {name}")
    print(f"当前价格: {data['price']}")
    print(f"涨跌幅: {data.get('change_percent', 0):.2f}%")
    
    # 2. 计算技术指标（使用模拟的历史数据）
    print("\n[2/3] 计算技术指标...")
    
    # 注意：新浪财经API只提供实时数据
    # 这里为了演示技术指标计算，使用模拟的OHLC数据
    # 实际使用时，你需要从历史数据源获取K线数据
    
    # 创建一个简单的模拟DataFrame来演示
    current_price = data['price']
    
    # 模拟60天的历史数据
    dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
    np.random.seed(42)
    
    # 基于当前价格生成模拟历史数据
    base_price = current_price * 0.95
    prices = [base_price]
    for i in range(59):
        change = np.random.normal(0, 0.02)
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    prices[-1] = current_price  # 确保最后一天是实时价格
    
    # 构造OHLC数据
    df = pd.DataFrame({
        'date': dates,
        'open': [p * (1 + np.random.normal(0, 0.005)) for p in prices],
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': [int(np.random.uniform(1000000, 10000000)) for _ in prices]
    })
    
    df.set_index('date', inplace=True)
    
    # 计算所有技术指标
    df = analyze_all(df)
    
    # 3. 生成分析报告
    print("\n[3/3] 生成分析报告...")
    signals = get_latest_signals(df)
    
    # 使用实时数据更新价格信息
    signals['价格信息']['当前价'] = data['price']
    signals['价格信息']['开盘价'] = data['open']
    signals['价格信息']['最高价'] = data['high']
    signals['价格信息']['最低价'] = data['low']
    signals['价格信息']['成交量'] = data['volume']
    signals['价格信息']['涨跌幅'] = f"{data.get('change_percent', 0):.2f}%"
    
    # 打印报告
    report = generate_analysis_report(signals, name)
    print(report)
    
    return {
        "stock_code": stock_code,
        "stock_name": name,
        "real_time_data": data,
        "technical_indicators": signals,
        "report": report
    }

def batch_analyze(stock_codes: list):
    """
    批量分析多只股票
    
    Args:
        stock_codes: 股票代码列表
    """
    results = []
    for code in stock_codes:
        result = analyze_stock(code)
        if result:
            results.append(result)
    
    # 汇总输出
    print(f"\n{'='*60}")
    print("批量分析汇总")
    print(f"{'='*60}")
    
    for r in results:
        data = r['real_time_data']
        change = data.get('change_percent', 0)
        emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        print(f"{emoji} {r['stock_name']} ({r['stock_code']}): {data['price']} ({change:+.2f}%)")
    
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python analyze_stock.py <股票代码> [股票代码2] ...")
        print("示例:")
        print("  python analyze_stock.py 600519")
        print("  python analyze_stock.py 600519 000001 300238")
        sys.exit(1)
    
    codes = sys.argv[1:]
    
    if len(codes) == 1:
        analyze_stock(codes[0])
    else:
        batch_analyze(codes)

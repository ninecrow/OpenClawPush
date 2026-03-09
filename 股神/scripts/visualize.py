"""
股票数据可视化
生成K线图、技术指标图、分析报告
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import pandas as pd
import numpy as np
import json
import sys
from typing import Optional
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def plot_candlestick(df: pd.DataFrame, title: str = "K线图", save_path: Optional[str] = None):
    """
    绘制K线图
    
    Args:
        df: DataFrame with 'open', 'high', 'low', 'close', 'volume' columns
        title: 图表标题
        save_path: 保存路径
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                    gridspec_kw={'height_ratios': [3, 1]}, 
                                    sharex=True)
    fig.suptitle(title, fontsize=16)
    
    # 绘制K线
    for idx, row in df.iterrows():
        x = idx
        open_price = row['open']
        high_price = row['high']
        low_price = row['low']
        close_price = row['close']
        
        color = 'red' if close_price >= open_price else 'green'
        
        # 绘制实体
        height = abs(close_price - open_price)
        bottom = min(open_price, close_price)
        rect = Rectangle((x - 0.4, bottom), 0.8, height, 
                         facecolor=color, edgecolor=color)
        ax1.add_patch(rect)
        
        # 绘制影线
        ax1.plot([x, x], [low_price, high_price], color=color, linewidth=1)
    
    ax1.set_ylabel('价格')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # 绘制成交量
    colors = ['red' if df.iloc[i]['close'] >= df.iloc[i]['open'] else 'green' 
              for i in range(len(df))]
    ax2.bar(range(len(df)), df['volume'], color=colors, alpha=0.7)
    ax2.set_ylabel('成交量')
    ax2.set_xlabel('时间')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"图表已保存: {save_path}")
    else:
        plt.show()
    
    plt.close()

def plot_with_indicators(df: pd.DataFrame, title: str = "技术分析图", save_path: Optional[str] = None):
    """
    绘制带技术指标的综合分析图
    
    Args:
        df: DataFrame with OHLC data and indicators
        title: 图表标题
        save_path: 保存路径
    """
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(4, 1, height_ratios=[3, 1, 1, 1], hspace=0.1)
    
    # 主图 - K线 + MA + BOLL
    ax1 = fig.add_subplot(gs[0])
    ax1.set_title(title, fontsize=14)
    
    # 绘制K线
    for idx, row in df.iterrows():
        x = idx
        color = 'red' if row['close'] >= row['open'] else 'green'
        
        # 影线
        ax1.plot([x, x], [row['low'], row['high']], color=color, linewidth=1)
        # 实体
        height = abs(row['close'] - row['open'])
        bottom = min(row['open'], row['close'])
        rect = Rectangle((x - 0.4, bottom), 0.8, height, 
                         facecolor=color, edgecolor=color)
        ax1.add_patch(rect)
    
    # 绘制MA
    if 'MA5' in df.columns:
        ax1.plot(df.index, df['MA5'], label='MA5', color='orange', linewidth=1)
    if 'MA10' in df.columns:
        ax1.plot(df.index, df['MA10'], label='MA10', color='blue', linewidth=1)
    if 'MA20' in df.columns:
        ax1.plot(df.index, df['MA20'], label='MA20', color='purple', linewidth=1)
    
    # 绘制布林带
    if 'BOLL_UPPER' in df.columns:
        ax1.fill_between(df.index, df['BOLL_UPPER'], df['BOLL_LOWER'], alpha=0.1, color='gray')
        ax1.plot(df.index, df['BOLL_UPPER'], '--', color='gray', linewidth=1, alpha=0.7)
        ax1.plot(df.index, df['BOLL_MID'], '-', color='gray', linewidth=1, alpha=0.7)
        ax1.plot(df.index, df['BOLL_LOWER'], '--', color='gray', linewidth=1, alpha=0.7)
    
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylabel('价格')
    
    # 成交量
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    colors = ['red' if df.iloc[i]['close'] >= df.iloc[i]['open'] else 'green' 
              for i in range(len(df))]
    ax2.bar(df.index, df['volume'], color=colors, alpha=0.7)
    ax2.set_ylabel('成交量')
    ax2.grid(True, alpha=0.3)
    
    # MACD
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    if 'MACD' in df.columns:
        ax3.plot(df.index, df['MACD'], label='MACD', color='blue', linewidth=1)
        ax3.plot(df.index, df['MACD_Signal'], label='Signal', color='orange', linewidth=1)
        
        # MACD柱状图
        hist_colors = ['red' if df.iloc[i]['MACD_Histogram'] >= 0 else 'green' 
                       for i in range(len(df))]
        ax3.bar(df.index, df['MACD_Histogram'], color=hist_colors, alpha=0.7)
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    ax3.legend(loc='upper left')
    ax3.set_ylabel('MACD')
    ax3.grid(True, alpha=0.3)
    
    # RSI
    ax4 = fig.add_subplot(gs[3], sharex=ax1)
    if 'RSI' in df.columns:
        ax4.plot(df.index, df['RSI'], label='RSI(14)', color='purple', linewidth=1.5)
        ax4.axhline(y=70, color='red', linestyle='--', linewidth=1, alpha=0.7, label='超买(70)')
        ax4.axhline(y=30, color='green', linestyle='--', linewidth=1, alpha=0.7, label='超卖(30)')
        ax4.fill_between(df.index, 30, 70, alpha=0.1, color='gray')
    
    ax4.legend(loc='upper left')
    ax4.set_ylabel('RSI')
    ax4.set_xlabel('时间')
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim(0, 100)
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"图表已保存: {save_path}")
    else:
        plt.show()
    
    plt.close()

def generate_analysis_report(signals: dict, stock_name: str = "股票") -> str:
    """
    生成文字分析报告
    
    Args:
        signals: 技术指标信号字典
        stock_name: 股票名称
    
    Returns:
        str: 分析报告文本
    """
    report = f"""
{'='*60}
{stock_name} 技术分析报告
{'='*60}

【价格信息】
当前价格: {signals['价格信息']['当前价']}
今日开盘: {signals['价格信息']['开盘价']}
今日最高: {signals['价格信息']['最高价']}
今日最低: {signals['价格信息']['最低价']}
成交量: {signals['价格信息']['成交量']:,}

【移动平均线分析】
MA5:  {signals['移动平均线']['MA5']}
MA10: {signals['移动平均线']['MA10']}
MA20: {signals['移动平均线']['MA20']}
MA60: {signals['移动平均线']['MA60']}

趋势判断: """
    
    # MA趋势判断
    ma5 = signals['移动平均线']['MA5']
    ma10 = signals['移动平均线']['MA10']
    ma20 = signals['移动平均线']['MA20']
    
    if ma5 > ma10 > ma20:
        report += "多头排列，强势上涨"
    elif ma5 < ma10 < ma20:
        report += "空头排列，下跌趋势"
    elif ma5 > ma10:
        report += "短期看涨，关注能否突破MA20"
    else:
        report += "短期看跌，关注MA20支撑"
    
    report += f"""

【MACD指标】
MACD值: {signals['MACD']['MACD']}
信号线: {signals['MACD']['信号线']}
柱状图: {signals['MACD']['柱状图']}
信号: {signals['MACD']['信号']}

【RSI指标】
RSI(14): {signals['RSI']['RSI(14)']}
状态: {signals['RSI']['状态']}

【KDJ指标】
K值: {signals['KDJ']['K']}
D值: {signals['KDJ']['D']}
J值: {signals['KDJ']['J']}
信号: {signals['KDJ']['信号']}

【布林带】
上轨: {signals['布林带']['上轨']}
中轨: {signals['布林带']['中轨']}
下轨: {signals['布林带']['下轨']}
当前位置: {signals['布林带']['位置']}

{'='*60}
综合建议
{'='*60}
"""
    
    # 综合建议
    suggestions = []
    
    # MACD信号
    if signals['MACD']['信号'] == '金叉':
        suggestions.append("MACD金叉，买入信号")
    elif signals['MACD']['信号'] == '死叉':
        suggestions.append("MACD死叉，卖出信号")
    
    # RSI信号
    if signals['RSI']['状态'] == '超买':
        suggestions.append("RSI超买，注意回调风险")
    elif signals['RSI']['状态'] == '超卖':
        suggestions.append("RSI超卖，可能存在反弹机会")
    
    # KDJ信号
    if signals['KDJ']['信号'] == '金叉':
        suggestions.append("KDJ金叉，短线买入信号")
    elif signals['KDJ']['信号'] == '死叉':
        suggestions.append("KDJ死叉，短线卖出信号")
    
    if not suggestions:
        report += "暂无明确信号，建议观望"
    else:
        for i, s in enumerate(suggestions, 1):
            report += f"{i}. {s}\n"
    
    report += "\n" + "="*60 + "\n"
    report += "免责声明: 本分析仅供参考，不构成投资建议\n"
    report += "="*60 + "\n"
    
    return report

if __name__ == "__main__":
    print("股票可视化模块")
    print("可用函数: plot_candlestick, plot_with_indicators, generate_analysis_report")

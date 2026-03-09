"""
策略回测模块
支持多种交易策略的回测和评估
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Callable, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from technical_analysis import analyze_all

class BacktestEngine:
    """
    回测引擎
    
    使用方法:
    1. 加载历史数据
    2. 设置策略
    3. 运行回测
    4. 获取结果
    """
    
    def __init__(self, initial_capital: float = 100000.0, commission: float = 0.0003):
        """
        初始化回测引擎
        
        Args:
            initial_capital: 初始资金，默认10万
            commission: 手续费率，默认万分之3
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.positions = 0  # 持仓数量
        self.cash = initial_capital  # 现金
        self.trades = []  # 交易记录
        self.daily_returns = []  # 每日收益
        
    def load_data(self, df: pd.DataFrame):
        """
        加载历史数据
        
        Args:
            df: DataFrame with 'open', 'high', 'low', 'close', 'volume' columns
        """
        self.data = df.copy()
        self.data = analyze_all(self.data)  # 计算技术指标
        
    def run(self, strategy: Callable, **strategy_params) -> Dict:
        """
        运行回测
        
        Args:
            strategy: 策略函数，接收df和参数，返回(signal, weight)
                     signal: 1买入, -1卖出, 0持仓
            **strategy_params: 策略参数
        
        Returns:
            Dict: 回测结果
        """
        if not hasattr(self, 'data'):
            raise ValueError("请先调用load_data()加载数据")
        
        self.positions = 0
        self.cash = self.initial_capital
        self.trades = []
        self.daily_returns = []
        
        portfolio_values = []
        
        for i in range(1, len(self.data)):
            current_data = self.data.iloc[:i+1]
            current_price = self.data.iloc[i]['close']
            current_date = self.data.index[i]
            
            # 获取策略信号
            signal = strategy(current_data, **strategy_params)
            
            # 执行交易
            if signal == 1 and self.positions == 0:  # 买入信号
                # 全仓买入
                max_shares = int(self.cash / (current_price * (1 + self.commission)))
                if max_shares > 0:
                    cost = max_shares * current_price * (1 + self.commission)
                    self.cash -= cost
                    self.positions = max_shares
                    self.trades.append({
                        'date': current_date,
                        'type': 'buy',
                        'price': current_price,
                        'shares': max_shares,
                        'cost': cost
                    })
                    
            elif signal == -1 and self.positions > 0:  # 卖出信号
                # 全部卖出
                revenue = self.positions * current_price * (1 - self.commission)
                self.trades.append({
                    'date': current_date,
                    'type': 'sell',
                    'price': current_price,
                    'shares': self.positions,
                    'revenue': revenue
                })
                self.cash += revenue
                self.positions = 0
            
            # 计算当日组合价值
            portfolio_value = self.cash + self.positions * current_price
            portfolio_values.append(portfolio_value)
            
            # 计算日收益
            if i > 1:
                daily_return = (portfolio_values[-1] / portfolio_values[-2]) - 1
                self.daily_returns.append(daily_return)
        
        # 计算最终收益
        final_value = portfolio_values[-1] if portfolio_values else self.initial_capital
        total_return = (final_value - self.initial_capital) / self.initial_capital * 100
        
        # 计算基准收益（买入持有）
        buy_hold_return = (self.data.iloc[-1]['close'] / self.data.iloc[0]['close'] - 1) * 100
        
        # 计算风险指标
        if self.daily_returns:
            sharpe_ratio = np.mean(self.daily_returns) / np.std(self.daily_returns) * np.sqrt(252) if np.std(self.daily_returns) > 0 else 0
            max_drawdown = self._calculate_max_drawdown(portfolio_values)
            win_rate = len([t for t in self.trades if t['type'] == 'sell' and t.get('revenue', 0) > t.get('cost', 0)]) / max(len([t for t in self.trades if t['type'] == 'sell']), 1) * 100
        else:
            sharpe_ratio = 0
            max_drawdown = 0
            win_rate = 0
        
        return {
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'buy_hold_return': buy_hold_return,
            'excess_return': total_return - buy_hold_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'trade_count': len(self.trades),
            'trades': self.trades,
            'portfolio_values': portfolio_values,
            'daily_returns': self.daily_returns
        }
    
    def _calculate_max_drawdown(self, portfolio_values: List[float]) -> float:
        """计算最大回撤"""
        peak = portfolio_values[0]
        max_dd = 0
        for value in portfolio_values:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            max_dd = max(max_dd, dd)
        return max_dd * 100


# ==================== 内置策略 ====================

def ma_cross_strategy(df: pd.DataFrame, fast: int = 5, slow: int = 20) -> int:
    """
    均线交叉策略
    
    Args:
        df: 历史数据
        fast: 快线周期
        slow: 慢线周期
    
    Returns:
        int: 1买入, -1卖出, 0持仓
    """
    if len(df) < slow + 1:
        return 0
    
    ma_fast = df[f'MA{fast}'].iloc[-1]
    ma_slow = df[f'MA{slow}'].iloc[-1]
    ma_fast_prev = df[f'MA{fast}'].iloc[-2]
    ma_slow_prev = df[f'MA{slow}'].iloc[-2]
    
    # 金叉：快线上穿慢线
    if ma_fast > ma_slow and ma_fast_prev <= ma_slow_prev:
        return 1
    # 死叉：快线下穿慢线
    elif ma_fast < ma_slow and ma_fast_prev >= ma_slow_prev:
        return -1
    
    return 0

def macd_strategy(df: pd.DataFrame) -> int:
    """
    MACD策略
    
    Returns:
        int: 1买入, -1卖出, 0持仓
    """
    if len(df) < 2 or 'MACD' not in df.columns:
        return 0
    
    macd_current = df['MACD'].iloc[-1]
    signal_current = df['MACD_Signal'].iloc[-1]
    macd_prev = df['MACD'].iloc[-2]
    signal_prev = df['MACD_Signal'].iloc[-2]
    
    # MACD金叉
    if macd_current > signal_current and macd_prev <= signal_prev:
        return 1
    # MACD死叉
    elif macd_current < signal_current and macd_prev >= signal_prev:
        return -1
    
    return 0

def rsi_strategy(df: pd.DataFrame, overbought: int = 70, oversold: int = 30) -> int:
    """
    RSI策略
    
    Args:
        df: 历史数据
        overbought: 超买阈值
        oversold: 超卖阈值
    
    Returns:
        int: 1买入, -1卖出, 0持仓
    """
    if len(df) < 2 or 'RSI' not in df.columns:
        return 0
    
    rsi_current = df['RSI'].iloc[-1]
    rsi_prev = df['RSI'].iloc[-2]
    
    # 从超卖区回升：买入
    if rsi_prev < oversold and rsi_current >= oversold:
        return 1
    # 进入超买区：卖出
    elif rsi_current > overbought:
        return -1
    
    return 0

def bollinger_strategy(df: pd.DataFrame) -> int:
    """
    布林带策略
    
    Returns:
        int: 1买入, -1卖出, 0持仓
    """
    if len(df) < 2 or 'BOLL_UPPER' not in df.columns:
        return 0
    
    close = df['close'].iloc[-1]
    close_prev = df['close'].iloc[-2]
    upper = df['BOLL_UPPER'].iloc[-1]
    lower = df['BOLL_LOWER'].iloc[-1]
    
    # 触及下轨反弹：买入
    if close_prev <= lower and close > lower:
        return 1
    # 触及上轨回落：卖出
    elif close_prev >= upper and close < upper:
        return -1
    
    return 0

def multi_factor_strategy(df: pd.DataFrame) -> int:
    """
    多因子综合策略
    结合MACD、RSI、MA多个指标
    
    Returns:
        int: 1买入, -1卖出, 0持仓
    """
    if len(df) < 30:
        return 0
    
    signals = []
    
    # MACD信号
    macd_sig = macd_strategy(df)
    signals.append(macd_sig)
    
    # RSI信号
    rsi_sig = rsi_strategy(df)
    signals.append(rsi_sig)
    
    # MA信号
    ma_sig = ma_cross_strategy(df, fast=5, slow=20)
    signals.append(ma_sig)
    
    # 投票机制：2个及以上同向信号才执行
    buy_votes = sum(1 for s in signals if s == 1)
    sell_votes = sum(1 for s in signals if s == -1)
    
    if buy_votes >= 2:
        return 1
    elif sell_votes >= 2:
        return -1
    
    return 0


def generate_backtest_report(result: Dict, strategy_name: str = "策略") -> str:
    """
    生成回测报告
    
    Args:
        result: 回测结果字典
        strategy_name: 策略名称
    
    Returns:
        str: 报告文本
    """
    report = f"""
{'='*60}
{strategy_name} 回测报告
{'='*60}

【基本参数】
初始资金: {result['initial_capital']:,.2f} 元
最终资产: {result['final_value']:,.2f} 元

【收益表现】
策略收益率: {result['total_return']:.2f}%
买入持有收益率: {result['buy_hold_return']:.2f}%
超额收益: {result['excess_return']:.2f}%

【风险指标】
夏普比率: {result['sharpe_ratio']:.2f}
最大回撤: {result['max_drawdown']:.2f}%
胜率: {result['win_rate']:.1f}%

【交易统计】
交易次数: {result['trade_count']} 次

【详细交易记录】
"""
    
    for i, trade in enumerate(result['trades'][:20], 1):  # 只显示前20条
        if trade['type'] == 'buy':
            report += f"{i}. [{trade['date']}] 买入 {trade['shares']}股 @ {trade['price']:.2f}元\n"
        else:
            report += f"{i}. [{trade['date']}] 卖出 {trade['shares']}股 @ {trade['price']:.2f}元\n"
    
    if len(result['trades']) > 20:
        report += f"... 共 {len(result['trades'])} 笔交易\n"
    
    report += f"\n{'='*60}\n"
    
    # 评价
    if result['total_return'] > result['buy_hold_return'] and result['sharpe_ratio'] > 1:
        report += "评价: 策略表现优秀，建议实盘测试\n"
    elif result['total_return'] > 0:
        report += "评价: 策略有正收益，可继续优化\n"
    else:
        report += "评价: 策略表现不佳，需调整参数或逻辑\n"
    
    report += "="*60 + "\n"
    
    return report


if __name__ == "__main__":
    print("策略回测模块")
    print("\n内置策略:")
    print("  1. ma_cross_strategy - 均线交叉策略")
    print("  2. macd_strategy - MACD策略")
    print("  3. rsi_strategy - RSI策略")
    print("  4. bollinger_strategy - 布林带策略")
    print("  5. multi_factor_strategy - 多因子综合策略")
    print("\n使用方法:")
    print("  engine = BacktestEngine(initial_capital=100000)")
    print("  engine.load_data(df)")
    print("  result = engine.run(macd_strategy)")
    print("  print(generate_backtest_report(result, 'MACD策略'))")

"""
策略参数优化模块
使用网格搜索寻找最优策略参数
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Callable
from itertools import product
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import BacktestEngine
from technical_analysis import analyze_all


class StrategyOptimizer:
    """
    策略优化器
    
    使用网格搜索寻找最优策略参数组合
    """
    
    def __init__(self, df: pd.DataFrame, initial_capital: float = 100000):
        """
        初始化优化器
        
        Args:
            df: 历史数据DataFrame
            initial_capital: 初始资金
        """
        self.df = analyze_all(df)
        self.initial_capital = initial_capital
        self.results = []
    
    def optimize_ma_cross(self, 
                          fast_range: range = range(3, 15),
                          slow_range: range = range(15, 40)) -> Dict:
        """
        优化均线交叉策略参数
        
        Args:
            fast_range: 快线周期范围
            slow_range: 慢线周期范围
        
        Returns:
            Dict: 最优参数和结果
        """
        print(f"开始优化均线交叉策略...")
        print(f"快线范围: {list(fast_range)}")
        print(f"慢线范围: {list(slow_range)}")
        
        best_result = None
        best_score = -np.inf
        
        total_combinations = len(fast_range) * len(slow_range)
        current = 0
        
        for fast, slow in product(fast_range, slow_range):
            if fast >= slow:
                continue
            
            current += 1
            if current % 10 == 0:
                print(f"  进度: {current}/{total_combinations}")
            
            # 运行回测
            engine = BacktestEngine(self.initial_capital)
            engine.load_data(self.df.copy())
            
            result = engine.run(self._ma_cross_strategy_wrapper, fast=fast, slow=slow)
            
            # 评分：综合考虑收益率和夏普比率
            score = self._calculate_score(result)
            
            param_result = {
                'fast': fast,
                'slow': slow,
                'total_return': result['total_return'],
                'sharpe_ratio': result['sharpe_ratio'],
                'max_drawdown': result['max_drawdown'],
                'trade_count': result['trade_count'],
                'score': score
            }
            
            self.results.append(param_result)
            
            if score > best_score:
                best_score = score
                best_result = param_result
        
        print(f"\n最优参数: 快线={best_result['fast']}, 慢线={best_result['slow']}")
        print(f"收益率: {best_result['total_return']:.2f}%, 夏普比率: {best_result['sharpe_ratio']:.2f}")
        
        return best_result
    
    def optimize_rsi(self,
                     oversold_range: range = range(15, 40),
                     overbought_range: range = range(60, 85)) -> Dict:
        """
        优化RSI策略参数
        
        Args:
            oversold_range: 超卖阈值范围
            overbought_range: 超买阈值范围
        
        Returns:
            Dict: 最优参数和结果
        """
        print(f"开始优化RSI策略...")
        
        best_result = None
        best_score = -np.inf
        
        for oversold, overbought in product(oversold_range, overbought_range):
            if oversold >= overbought:
                continue
            
            engine = BacktestEngine(self.initial_capital)
            engine.load_data(self.df.copy())
            
            result = engine.run(self._rsi_strategy_wrapper, 
                               oversold=oversold, overbought=overbought)
            
            score = self._calculate_score(result)
            
            param_result = {
                'oversold': oversold,
                'overbought': overbought,
                'total_return': result['total_return'],
                'sharpe_ratio': result['sharpe_ratio'],
                'max_drawdown': result['max_drawdown'],
                'trade_count': result['trade_count'],
                'score': score
            }
            
            self.results.append(param_result)
            
            if score > best_score:
                best_score = score
                best_result = param_result
        
        print(f"\n最优参数: 超卖={best_result['oversold']}, 超买={best_result['overbought']}")
        print(f"收益率: {best_result['total_return']:.2f}%, 夏普比率: {best_result['sharpe_ratio']:.2f}")
        
        return best_result
    
    def optimize_macd(self,
                      fast_range: range = range(8, 16),
                      slow_range: range = range(20, 30),
                      signal_range: range = range(7, 12)) -> Dict:
        """
        优化MACD策略参数
        
        Args:
            fast_range: 快线EMA范围
            slow_range: 慢线EMA范围
            signal_range: 信号线范围
        
        Returns:
            Dict: 最优参数和结果
        """
        print(f"开始优化MACD策略...")
        
        best_result = None
        best_score = -np.inf
        
        for fast, slow, signal in product(fast_range, slow_range, signal_range):
            if fast >= slow:
                continue
            
            engine = BacktestEngine(self.initial_capital)
            engine.load_data(self.df.copy())
            
            result = engine.run(self._macd_strategy_wrapper,
                               fast=fast, slow=slow, signal=signal)
            
            score = self._calculate_score(result)
            
            param_result = {
                'fast': fast,
                'slow': slow,
                'signal': signal,
                'total_return': result['total_return'],
                'sharpe_ratio': result['sharpe_ratio'],
                'max_drawdown': result['max_drawdown'],
                'trade_count': result['trade_count'],
                'score': score
            }
            
            self.results.append(param_result)
            
            if score > best_score:
                best_score = score
                best_result = param_result
        
        print(f"\n最优参数: 快线EMA={best_result['fast']}, 慢线EMA={best_result['slow']}, 信号={best_result['signal']}")
        print(f"收益率: {best_result['total_return']:.2f}%, 夏普比率: {best_result['sharpe_ratio']:.2f}")
        
        return best_result
    
    def _ma_cross_strategy_wrapper(self, df: pd.DataFrame, fast: int, slow: int) -> int:
        """均线策略包装器"""
        if len(df) < slow + 1:
            return 0
        
        # 动态计算MA
        df[f'MA_{fast}'] = df['close'].rolling(window=fast).mean()
        df[f'MA_{slow}'] = df['close'].rolling(window=slow).mean()
        
        ma_fast = df[f'MA_{fast}'].iloc[-1]
        ma_slow = df[f'MA_{slow}'].iloc[-1]
        ma_fast_prev = df[f'MA_{fast}'].iloc[-2]
        ma_slow_prev = df[f'MA_{slow}'].iloc[-2]
        
        if ma_fast > ma_slow and ma_fast_prev <= ma_slow_prev:
            return 1
        elif ma_fast < ma_slow and ma_fast_prev >= ma_slow_prev:
            return -1
        return 0
    
    def _rsi_strategy_wrapper(self, df: pd.DataFrame, oversold: int, overbought: int) -> int:
        """RSI策略包装器"""
        if len(df) < 15:
            return 0
        
        # 计算RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        rsi_current = rsi.iloc[-1]
        rsi_prev = rsi.iloc[-2]
        
        if rsi_prev < oversold and rsi_current >= oversold:
            return 1
        elif rsi_current > overbought:
            return -1
        return 0
    
    def _macd_strategy_wrapper(self, df: pd.DataFrame, fast: int, slow: int, signal: int) -> int:
        """MACD策略包装器"""
        if len(df) < slow:
            return 0
        
        # 计算MACD
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        
        macd_current = macd.iloc[-1]
        signal_current = macd_signal.iloc[-1]
        macd_prev = macd.iloc[-2]
        signal_prev = macd_signal.iloc[-2]
        
        if macd_current > signal_current and macd_prev <= signal_prev:
            return 1
        elif macd_current < signal_current and macd_prev >= signal_prev:
            return -1
        return 0
    
    def _calculate_score(self, result: Dict) -> float:
        """
        计算参数组合评分
        
        综合考虑：收益率、夏普比率、最大回撤、交易次数
        """
        total_return = result['total_return']
        sharpe_ratio = result['sharpe_ratio']
        max_drawdown = result['max_drawdown']
        trade_count = result['trade_count']
        
        # 过滤掉表现太差的
        if total_return <= 0 or sharpe_ratio <= 0:
            return -np.inf
        
        # 评分公式
        # - 收益权重：40%
        # - 夏普权重：30%
        # - 回撤惩罚：20%
        # - 交易频率：10%（避免过度交易）
        
        return_score = min(total_return / 50, 1.0)  # 假设50%收益为满分
        sharpe_score = min(sharpe_ratio / 2, 1.0)   # 假设夏普2为满分
        drawdown_score = max(0, 1 - max_drawdown / 30)  # 回撤越小越好
        trade_score = min(trade_count / 20, 1.0) if trade_count > 0 else 0
        
        score = (return_score * 0.4 + 
                sharpe_score * 0.3 + 
                drawdown_score * 0.2 +
                trade_score * 0.1)
        
        return score
    
    def get_top_results(self, n: int = 10) -> pd.DataFrame:
        """
        获取评分最高的N组参数
        
        Args:
            n: 返回前N个结果
        
        Returns:
            DataFrame with top results
        """
        if not self.results:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.results)
        df = df.sort_values('score', ascending=False).head(n)
        return df
    
    def generate_optimization_report(self, best_result: Dict, strategy_name: str) -> str:
        """
        生成优化报告
        
        Args:
            best_result: 最优参数结果
            strategy_name: 策略名称
        
        Returns:
            str: 报告文本
        """
        top_results = self.get_top_results(5)
        
        report = f"""
{'='*60}
{strategy_name} 参数优化报告
{'='*60}

【最优参数】
"""
        
        for key, value in best_result.items():
            if key not in ['total_return', 'sharpe_ratio', 'max_drawdown', 'trade_count', 'score']:
                report += f"{key}: {value}\n"
        
        report += f"""
【回测表现】
总收益率: {best_result['total_return']:.2f}%
夏普比率: {best_result['sharpe_ratio']:.2f}
最大回撤: {best_result['max_drawdown']:.2f}%
交易次数: {best_result['trade_count']}
综合评分: {best_result['score']:.4f}

【TOP 5 参数组合】
"""
        
        for idx, row in top_results.iterrows():
            report += f"\n排名 {idx+1}:\n"
            for key, value in row.items():
                if key != 'score':
                    if isinstance(value, float):
                        report += f"  {key}: {value:.4f}\n"
                    else:
                        report += f"  {key}: {value}\n"
            report += f"  评分: {row['score']:.4f}\n"
        
        report += f"\n{'='*60}\n"
        
        return report


def optimize_strategy(df: pd.DataFrame, 
                     strategy_type: str = "ma",
                     initial_capital: float = 100000) -> Dict:
    """
    快捷函数：优化指定策略
    
    Args:
        df: 历史数据
        strategy_type: 策略类型，"ma", "rsi", "macd"
        initial_capital: 初始资金
    
    Returns:
        Dict: 最优参数
    """
    optimizer = StrategyOptimizer(df, initial_capital)
    
    if strategy_type == "ma":
        return optimizer.optimize_ma_cross()
    elif strategy_type == "rsi":
        return optimizer.optimize_rsi()
    elif strategy_type == "macd":
        return optimizer.optimize_macd()
    else:
        raise ValueError(f"不支持策略类型: {strategy_type}")


if __name__ == "__main__":
    print("策略参数优化模块")
    print("\n使用示例:")
    print("  from scripts.strategy_optimizer import StrategyOptimizer, optimize_strategy")
    print("\n  # 创建优化器")
    print("  optimizer = StrategyOptimizer(df)")
    print("\n  # 优化均线策略")
    print("  best = optimizer.optimize_ma_cross(fast_range=range(3,15), slow_range=range(15,40))")
    print("\n  # 快捷函数")
    print("  best_params = optimize_strategy(df, strategy_type='ma')")
    print("\n  # 获取前10名结果")
    print("  top10 = optimizer.get_top_results(10)")
    print("\n  # 生成报告")
    print("  report = optimizer.generate_optimization_report(best, '均线策略')")

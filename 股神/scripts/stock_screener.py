"""
自动化选股模块
根据技术指标和基本面条件筛选股票
"""
import pandas as pd
import numpy as np
import requests
import json
import time
from typing import List, Dict, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_sina_data import fetch_stock_data
from technical_analysis import analyze_all, get_latest_signals


class StockScreener:
    """
    股票筛选器
    
    支持自定义筛选条件，批量扫描A股全市场
    """
    
    def __init__(self):
        self.filters = []
        # A股全市场代码池（简化版，实际使用时需要更完整的列表）
        self.stock_pool = self._get_default_stock_pool()
    
    def _get_default_stock_pool(self) -> List[str]:
        """获取默认股票池 - 常见股票代码"""
        # 这里使用一些常见股票作为示例
        # 实际使用时可以从 AKShare/Tushare 获取全量代码
        return [
            # 金融
            "600036", "601398", "601288", "601939", "601988", "601318", "601628",
            # 白酒
            "600519", "000858", "000568", "002304",
            # 医药
            "600276", "000538", "600436", "300122", "300760", "300238",
            # 科技
            "000725", "002475", "002594", "300750", "002371",
            # 新能源
            "601012", "600438", "300274", "002460",
            # 消费
            "600887", "000333", "000651", "002714",
            # 传媒
            "300413", "002027",
            # 中字头
            "601857", "600028", "601088", "600900", "601668"
        ]
    
    def set_stock_pool(self, stock_codes: List[str]):
        """设置自定义股票池"""
        self.stock_pool = stock_codes
    
    def add_filter(self, filter_func: Callable, **kwargs):
        """
        添加筛选条件
        
        Args:
            filter_func: 筛选函数，接收股票数据，返回True/False
            **kwargs: 传递给筛选函数的参数
        """
        self.filters.append((filter_func, kwargs))
    
    def screen(self, max_workers: int = 5) -> List[Dict]:
        """
        执行选股
        
        Args:
            max_workers: 并发线程数
        
        Returns:
            List[Dict]: 符合条件的股票列表
        """
        results = []
        
        print(f"开始扫描 {len(self.stock_pool)} 只股票...")
        
        # 分批获取数据避免请求过于频繁
        batch_size = 50
        for i in range(0, len(self.stock_pool), batch_size):
            batch = self.stock_pool[i:i+batch_size]
            print(f"  处理第 {i//batch_size + 1} 批 ({len(batch)} 只)...")
            
            try:
                data = fetch_stock_data(batch)
                
                for code, stock_data in data.items():
                    if "error" in stock_data:
                        continue
                    
                    # 执行所有筛选条件
                    passed = True
                    for filter_func, kwargs in self.filters:
                        if not filter_func(stock_data, **kwargs):
                            passed = False
                            break
                    
                    if passed:
                        results.append({
                            'code': code,
                            'name': stock_data.get('name', ''),
                            'price': stock_data.get('price', 0),
                            'change': stock_data.get('change_percent', 0),
                            'volume': stock_data.get('volume', 0),
                            'high': stock_data.get('high', 0),
                            'low': stock_data.get('low', 0)
                        })
                
                time.sleep(0.5)  # 避免请求过快
                
            except Exception as e:
                print(f"  批次处理出错: {e}")
                continue
        
        print(f"\n选股完成，共筛选出 {len(results)} 只股票")
        return results
    
    def clear_filters(self):
        """清除所有筛选条件"""
        self.filters = []


# ==================== 预置筛选条件 ====================

def filter_by_price(stock_data: Dict, min_price: float = 5, max_price: float = 500) -> bool:
    """按价格范围筛选"""
    price = stock_data.get('price', 0)
    return min_price <= price <= max_price

def filter_by_change(stock_data: Dict, min_change: float = -10, max_change: float = 10) -> bool:
    """按涨跌幅筛选"""
    change = stock_data.get('change_percent', 0)
    return min_change <= change <= max_change

def filter_by_volume(stock_data: Dict, min_volume: int = 1000000) -> bool:
    """按成交量筛选"""
    volume = stock_data.get('volume', 0)
    return volume >= min_volume

def filter_rising(stock_data: Dict, min_change: float = 3) -> bool:
    """筛选上涨股票"""
    change = stock_data.get('change_percent', 0)
    return change >= min_change

def filter_falling(stock_data: Dict, max_change: float = -3) -> bool:
    """筛选下跌股票"""
    change = stock_data.get('change_percent', 0)
    return change <= max_change

def filter_breakout_high(stock_data: Dict) -> bool:
    """筛选接近今日新高的股票"""
    price = stock_data.get('price', 0)
    high = stock_data.get('high', 0)
    return high > 0 and price >= high * 0.995

def filter_near_low(stock_data: Dict) -> bool:
    """筛选接近今日新低的股票"""
    price = stock_data.get('price', 0)
    low = stock_data.get('low', 0)
    return low > 0 and price <= low * 1.005


# ==================== 预设选股策略 ====================

def strategy_hot_stocks() -> List[Dict]:
    """
    热点股策略：当日涨幅3%以上且成交量放大
    """
    screener = StockScreener()
    screener.add_filter(filter_rising, min_change=3)
    screener.add_filter(filter_by_volume, min_volume=5000000)
    return screener.screen()

def strategy_oversold_bounce() -> List[Dict]:
    """
    超跌反弹策略：当日跌幅超过3%但价格接近低点
    """
    screener = StockScreener()
    screener.add_filter(filter_falling, max_change=-3)
    screener.add_filter(filter_near_low)
    return screener.screen()

def strategy_breakout() -> List[Dict]:
    """
    突破策略：价格接近当日高点
    """
    screener = StockScreener()
    screener.add_filter(filter_breakout_high)
    screener.add_filter(filter_by_volume, min_volume=3000000)
    return screener.screen()

def strategy_value_stocks() -> List[Dict]:
    """
    价值股策略：价格在10-100元之间，波动较小
    """
    screener = StockScreener()
    screener.add_filter(filter_by_price, min_price=10, max_price=100)
    screener.add_filter(filter_by_change, min_change=-2, max_change=5)
    return screener.screen()

def strategy_penny_stocks() -> List[Dict]:
    """
    低价股策略：价格低于10元，有一定成交量
    """
    screener = StockScreener()
    screener.add_filter(filter_by_price, min_price=2, max_price=10)
    screener.add_filter(filter_by_volume, min_volume=1000000)
    return screener.screen()


def generate_screening_report(results: List[Dict], strategy_name: str = "选股结果") -> str:
    """
    生成选股报告
    
    Args:
        results: 选股结果列表
        strategy_name: 策略名称
    
    Returns:
        str: 报告文本
    """
    if not results:
        return f"【{strategy_name}】\n未筛选出符合条件的股票\n"
    
    report = f"""
{'='*60}
{strategy_name}
{'='*60}
共筛选出 {len(results)} 只股票

【股票列表】
{"代码":<12}{"名称":<10}{"现价":>10}{"涨跌幅":>10}{"成交量":>15}
{"-"*57}
"""
    
    for stock in results:
        code = stock['code']
        name = stock['name'][:8]  # 截断长名称
        price = stock['price']
        change = stock['change']
        volume = stock['volume']
        
        emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        
        report += f"{emoji} {code:<10}{name:<10}{price:>10.2f}{change:>9.2f}%{volume:>15,}\n"
    
    report += "="*60 + "\n"
    
    return report


if __name__ == "__main__":
    print("自动化选股模块")
    print("\n预设策略:")
    print("  1. strategy_hot_stocks() - 热点股")
    print("  2. strategy_oversold_bounce() - 超跌反弹")
    print("  3. strategy_breakout() - 突破")
    print("  4. strategy_value_stocks() - 价值股")
    print("  5. strategy_penny_stocks() - 低价股")
    print("\n自定义选股示例:")
    print("  screener = StockScreener()")
    print("  screener.add_filter(filter_by_price, min_price=5, max_price=50)")
    print("  screener.add_filter(filter_rising, min_change=2)")
    print("  results = screener.screen()")

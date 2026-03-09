"""
AKShare 历史数据获取模块
提供A股历史K线数据获取功能
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List
import time

class AKDataProvider:
    """
    AKShare 数据提供者
    
    提供股票历史数据、实时行情、财务数据等
    """
    
    def __init__(self):
        self.cache = {}
    
    def get_stock_hist(self, 
                       stock_code: str, 
                       period: str = "daily",
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       adjust: str = "qfq") -> pd.DataFrame:
        """
        获取股票历史K线数据
        
        Args:
            stock_code: 股票代码，如 "600519"
            period: 周期，可选 "daily", "weekly", "monthly"
            start_date: 开始日期，格式 "YYYYMMDD"
            end_date: 结束日期，格式 "YYYYMMDD"
            adjust: 复权类型，""不复权, "qfq"前复权, "hfq"后复权
        
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        # 判断交易所
        if stock_code.startswith('6'):
            stock_code = f"sh{stock_code}"
        elif stock_code.startswith(('0', '3')):
            stock_code = f"sz{stock_code}"
        
        # 默认获取最近120天数据
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d')
        
        try:
            # 使用 AKShare 获取历史数据
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 标准化列名
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            
            # 设置日期索引
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # 只保留需要的列
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            df = df[required_cols]
            
            return df
            
        except Exception as e:
            print(f"获取 {stock_code} 历史数据失败: {e}")
            return pd.DataFrame()
    
    def get_realtime_quotes(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        获取实时行情（比新浪财经更全的数据）
        
        Args:
            stock_codes: 股票代码列表
        
        Returns:
            DataFrame with real-time data
        """
        all_data = []
        
        for code in stock_codes:
            try:
                # 使用 AKShare 获取实时行情
                if code.startswith('6'):
                    symbol = f"sh{code}"
                elif code.startswith(('0', '3')):
                    symbol = f"sz{code}"
                else:
                    symbol = code
                
                df = ak.stock_zh_a_spot_em()
                stock_data = df[df['代码'] == code]
                
                if not stock_data.empty:
                    all_data.append({
                        'code': code,
                        'name': stock_data['名称'].values[0],
                        'price': float(stock_data['最新价'].values[0]),
                        'change': float(stock_data['涨跌幅'].values[0]),
                        'volume': int(stock_data['成交量'].values[0]),
                        'amount': float(stock_data['成交额'].values[0]),
                        'high': float(stock_data['最高'].values[0]),
                        'low': float(stock_data['最低'].values[0]),
                        'open': float(stock_data['今开'].values[0]),
                        'pre_close': float(stock_data['昨收'].values[0])
                    })
                
                time.sleep(0.1)  # 避免请求过快
                
            except Exception as e:
                print(f"获取 {code} 实时数据失败: {e}")
                continue
        
        return pd.DataFrame(all_data)
    
    def get_all_stock_codes(self) -> pd.DataFrame:
        """
        获取所有A股代码列表
        
        Returns:
            DataFrame with columns: code, name
        """
        try:
            df = ak.stock_zh_a_spot_em()
            return df[['代码', '名称']].rename(columns={'代码': 'code', '名称': 'name'})
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def get_index_hist(self, 
                       index_code: str = "sh000001",
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取指数历史数据
        
        Args:
            index_code: 指数代码，如 "sh000001"(上证), "sz399001"(深证)
            start_date: 开始日期
            end_date: 结束日期
        
        Returns:
            DataFrame with index data
        """
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d')
        
        try:
            # 上证指数
            if index_code in ['sh000001', '000001']:
                df = ak.index_zh_a_hist(symbol="000001", period="daily", 
                                        start_date=start_date, end_date=end_date)
            # 深证成指
            elif index_code in ['sz399001', '399001']:
                df = ak.index_zh_a_hist(symbol="399001", period="daily",
                                        start_date=start_date, end_date=end_date)
            # 创业板指
            elif index_code in ['sz399006', '399006']:
                df = ak.index_zh_a_hist(symbol="399006", period="daily",
                                        start_date=start_date, end_date=end_date)
            else:
                return pd.DataFrame()
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            print(f"获取指数数据失败: {e}")
            return pd.DataFrame()


def fetch_hist_data(stock_code: str, days: int = 120) -> pd.DataFrame:
    """
    快捷函数：获取股票历史数据
    
    Args:
        stock_code: 股票代码
        days: 获取最近多少天的数据
    
    Returns:
        DataFrame with OHLCV data
    """
    provider = AKDataProvider()
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
    
    return provider.get_stock_hist(stock_code, start_date=start_date, end_date=end_date)


def fetch_index_data(index_code: str = "sh000001", days: int = 120) -> pd.DataFrame:
    """
    快捷函数：获取指数历史数据
    
    Args:
        index_code: 指数代码
        days: 获取最近多少天的数据
    
        Returns:
        DataFrame with index OHLCV data
    """
    provider = AKDataProvider()
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
    
    return provider.get_index_hist(index_code, start_date=start_date, end_date=end_date)


if __name__ == "__main__":
    print("AKShare 数据获取模块")
    print("\n使用示例:")
    print("  from scripts.akshare_data import fetch_hist_data, AKDataProvider")
    print("\n  # 获取单只股票历史数据")
    print("  df = fetch_hist_data('600519', days=120)")
    print("\n  # 获取所有股票代码")
    print("  provider = AKDataProvider()")
    print("  all_stocks = provider.get_all_stock_codes()")
    print("\n  # 获取指数数据")
    print("  index_df = provider.get_index_hist('sh000001')")

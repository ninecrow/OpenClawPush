"""
从新浪财经获取A股实时行情数据
支持：单只股票查询、批量查询、指数查询
"""
import requests
import json
import re
import sys
from typing import Dict, List, Union

# 新浪股票API基础URL
SINA_API_BASE = "https://hq.sinajs.cn"

def get_stock_code(stock_id: str) -> str:
    """
    转换股票代码为新浪格式
    沪市: sh + 代码 (600xxx)
    深市: sz + 代码 (000xxx, 300xxx)
    北交所: bj + 代码
    """
    stock_id = stock_id.strip()
    
    # 如果已经是 sh/sz/bj 开头，直接返回
    if stock_id.startswith(('sh', 'sz', 'bj')):
        return stock_id
    
    # 根据代码规则判断交易所
    if stock_id.startswith('6'):
        return f"sh{stock_id}"
    elif stock_id.startswith(('0', '3')):
        return f"sz{stock_id}"
    elif stock_id.startswith('8'):
        return f"bj{stock_id}"
    else:
        raise ValueError(f"无法识别的股票代码: {stock_id}")

def fetch_stock_data(stock_codes: Union[str, List[str]]) -> Dict:
    """
    从新浪财经获取股票数据
    
    Args:
        stock_codes: 单个股票代码或代码列表
    
    Returns:
        Dict: 股票数据字典
    """
    if isinstance(stock_codes, str):
        stock_codes = [stock_codes]
    
    # 转换所有代码
    sina_codes = [get_stock_code(code) for code in stock_codes]
    codes_str = ",".join(sina_codes)
    
    # 构造请求URL
    url = f"{SINA_API_BASE}/list={codes_str}"
    
    # 设置请求头（模拟浏览器）
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://finance.sina.com.cn'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'gb2312'
        
        result = {}
        lines = response.text.strip().split('\n')
        
        for line in lines:
            match = re.search(r'var hq_str_(\w+)="([^"]*)"', line)
            if match:
                code = match.group(1)
                data_str = match.group(2)
                
                if not data_str:
                    result[code] = {"error": "无数据"}
                    continue
                
                data_parts = data_str.split(',')
                
                # 根据代码类型解析数据
                if code.startswith('sh') or code.startswith('sz'):
                    if len(data_parts) >= 33:  # 个股数据
                        result[code] = {
                            "name": data_parts[0],
                            "open": float(data_parts[1]),
                            "close_yesterday": float(data_parts[2]),
                            "price": float(data_parts[3]),
                            "high": float(data_parts[4]),
                            "low": float(data_parts[5]),
                            "bid": float(data_parts[6]),
                            "ask": float(data_parts[7]),
                            "volume": int(data_parts[8]),
                            "amount": float(data_parts[9]),
                            "bid1_vol": int(data_parts[10]),
                            "bid1": float(data_parts[11]),
                            "bid2_vol": int(data_parts[12]),
                            "bid2": float(data_parts[13]),
                            "bid3_vol": int(data_parts[14]),
                            "bid3": float(data_parts[15]),
                            "bid4_vol": int(data_parts[16]),
                            "bid4": float(data_parts[17]),
                            "bid5_vol": int(data_parts[18]),
                            "bid5": float(data_parts[19]),
                            "ask1_vol": int(data_parts[20]),
                            "ask1": float(data_parts[21]),
                            "ask2_vol": int(data_parts[22]),
                            "ask2": float(data_parts[23]),
                            "ask3_vol": int(data_parts[24]),
                            "ask3": float(data_parts[25]),
                            "ask4_vol": int(data_parts[26]),
                            "ask4": float(data_parts[27]),
                            "ask5_vol": int(data_parts[28]),
                            "ask5": float(data_parts[29]),
                            "date": data_parts[30],
                            "time": data_parts[31]
                        }
                        # 计算涨跌幅
                        result[code]["change"] = result[code]["price"] - result[code]["close_yesterday"]
                        result[code]["change_percent"] = (result[code]["change"] / result[code]["close_yesterday"]) * 100
        
        return result
        
    except Exception as e:
        return {"error": str(e)}

def fetch_index_data(index_code: str) -> Dict:
    """
    获取指数数据
    常用指数: sh000001(上证指数), sz399001(深证成指), sz399006(创业板指)
    """
    return fetch_stock_data(index_code)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python fetch_sina_data.py <股票代码> [股票代码2] ...")
        print("示例: python fetch_sina_data.py 600519 000001 300238")
        sys.exit(1)
    
    codes = sys.argv[1:]
    data = fetch_stock_data(codes)
    print(json.dumps(data, ensure_ascii=False, indent=2))

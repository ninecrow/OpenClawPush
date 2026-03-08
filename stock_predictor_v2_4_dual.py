"""
股票预测系统 v2.4 - 双模型版本（同时预测最高价和最低价）
使用新浪财经/东方财富数据
"""

import pandas as pd
import numpy as np
import datetime
import requests
import json
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

from risk_control import RiskController, TradingSignalGenerator, RiskLevel

# ============== 配置 ==============
CONFIG = {
    'stock_code': '600754',
    'market': 'sh',
    'train_days': 760,
    
    # 风险控制参数
    'max_daily_return': 0.095,
    'max_daily_drop': -0.095,
    'volatility_threshold': 2.5,
    'min_confidence': 0.55,
    'max_position': 0.3,
    'stop_loss_pct': 0.03,
    'take_profit_pct': 0.05,
}


# ============== 数据获取 ==============

def get_secid(stock_code: str, market: str = 'sh') -> str:
    """转换股票代码为东方财富格式"""
    if market == 'sh':
        return f"1.{stock_code}"
    else:
        return f"0.{stock_code}"


def fetch_data_eastmoney(stock_code: str, market: str, start_date: str, end_date: str) -> pd.DataFrame:
    """东方财富API获取K线数据"""
    secid = get_secid(stock_code, market)
    
    url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
    params = {
        'secid': secid,
        'fields1': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70',
        'klt': '101',
        'fqt': '1',
        'beg': start_date,
        'end': end_date,
        '_': str(int(datetime.datetime.now().timestamp() * 1000))
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://quote.eastmoney.com/'
    }
    
    try:
        print(f"正在从东方财富获取数据: {stock_code} ({market})...")
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('data') is None:
            return pd.DataFrame()
        
        klines = data['data'].get('klines', [])
        
        if not klines:
            return pd.DataFrame()
        
        rows = []
        for kline in klines:
            parts = kline.split(',')
            if len(parts) >= 6:
                rows.append({
                    'trade_date': parts[0],
                    'open': float(parts[1]),
                    'close': float(parts[2]),
                    'high': float(parts[3]),
                    'low': float(parts[4]),
                    'vol': float(parts[5]) if len(parts) > 5 else 0,
                    'amount': float(parts[6]) if len(parts) > 6 else 0,
                    'amplitude': float(parts[7]) if len(parts) > 7 else 0,
                    'pct_change': float(parts[8]) if len(parts) > 8 else 0,
                    'change': float(parts[9]) if len(parts) > 9 else 0,
                    'turnover_rate': float(parts[10]) if len(parts) > 10 else 0,
                })
        
        df = pd.DataFrame(rows)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df['ts_code'] = f"{stock_code}.{market.upper()}"
        
        df['volume_ma5'] = df['vol'].rolling(window=5).mean()
        df['volume_ratio'] = df['vol'] / df['volume_ma5']
        
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        print(f"东方财富获取成功: {stock_code}, {len(df)} 条数据")
        return df
        
    except Exception as e:
        print(f"东方财富数据获取失败: {e}")
        return pd.DataFrame()


def fetch_data_sina(stock_code: str, market: str, start_date: str, end_date: str) -> pd.DataFrame:
    """新浪财经数据接口"""
    if market == 'sh':
        sina_code = f"sh{stock_code}"
    else:
        sina_code = f"sz{stock_code}"
    
    url = 'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData'
    params = {
        'symbol': sina_code,
        'scale': 240,
        'ma': 'no',
        'datalen': 800
    }
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        print(f"正在从新浪财经获取数据: {sina_code}...")
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        text = response.text
        if not text or text == 'null':
            return pd.DataFrame()
        
        try:
            data = json.loads(text)
        except:
            text = text.replace('null', 'None')
            data = eval(text)
        
        if not data:
            return pd.DataFrame()
        
        rows = []
        for item in data:
            day = item.get('day', '')
            if len(day) > 10:
                day = day[:10]
            
            rows.append({
                'trade_date': day,
                'open': float(item.get('open', 0)),
                'close': float(item.get('close', 0)),
                'high': float(item.get('high', 0)),
                'low': float(item.get('low', 0)),
                'vol': float(item.get('volume', 0)),
            })
        
        df = pd.DataFrame(rows)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df['ts_code'] = f"{stock_code}.{market.upper()}"
        
        # 添加模拟的换手率（新浪不返回这个数据）
        df['turnover_rate'] = np.random.uniform(0.5, 5.0, len(df))
        df['volume_ma5'] = df['vol'].rolling(window=5).mean()
        df['volume_ratio'] = df['vol'] / df['volume_ma5']
        
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        df = df[(df['trade_date'] >= start_dt) & (df['trade_date'] <= end_dt)]
        
        print(f"新浪财经获取成功: {stock_code}, {len(df)} 条数据")
        return df
        
    except Exception as e:
        print(f"新浪财经数据获取失败: {e}")
        return pd.DataFrame()


def fetch_data(stock_code: str, market: str, start_date: str, end_date: str) -> pd.DataFrame:
    """统一数据获取接口"""
    df = fetch_data_eastmoney(stock_code, market, start_date, end_date)
    if not df.empty:
        return df
    
    print("尝试新浪财经备用接口...")
    df = fetch_data_sina(stock_code, market, start_date, end_date)
    if not df.empty:
        return df
    
    print("\n[注意] 真实数据获取失败，使用模拟数据进行测试...")
    return generate_mock_data(start_date, end_date, stock_code)


def generate_mock_data(start_date: str, end_date: str, stock_code: str) -> pd.DataFrame:
    """生成模拟数据"""
    start_dt = datetime.datetime.strptime(start_date, '%Y%m%d')
    end_dt = datetime.datetime.strptime(end_date, '%Y%m%d')
    
    date_range = pd.date_range(start=start_dt, end=end_dt, freq='B')
    
    np.random.seed(42)
    n_days = len(date_range)
    
    base_price = 25.0
    trend = np.linspace(0, 5, n_days)
    noise = np.random.randn(n_days) * 0.5
    
    closes = base_price + trend + noise.cumsum() * 0.1
    closes = np.maximum(closes, 1.0)
    
    data = {
        'trade_date': date_range,
        'ts_code': stock_code,
        'open': closes * (1 + np.random.randn(n_days) * 0.01),
        'close': closes,
        'high': closes * (1 + np.abs(np.random.randn(n_days)) * 0.02 + 0.005),
        'low': closes * (1 - np.abs(np.random.randn(n_days)) * 0.02 - 0.005),
        'vol': np.random.randint(1000000, 10000000, n_days),
        'turnover_rate': np.random.uniform(0.5, 5.0, n_days),
        'volume_ratio': np.random.uniform(0.8, 1.5, n_days),
    }
    
    df = pd.DataFrame(data)
    df['high'] = df[['high', 'open', 'close']].max(axis=1) * 1.01
    df['low'] = df[['low', 'open', 'close']].min(axis=1) * 0.99
    
    df = df.sort_values('trade_date').reset_index(drop=True)
    
    print(f"[模拟数据] 生成 {len(df)} 条数据")
    return df


# ============== 特征工程 ==============

def create_features(df):
    """特征工程"""
    df = df.copy()
    
    # 价格特征
    df['price_range'] = (df['high'] - df['low']) / df['close']
    df['price_change'] = (df['close'] - df['open']) / df['open']
    df['body_ratio'] = abs(df['close'] - df['open']) / (df['high'] - df['low'] + 1e-8)
    
    # 移动平均线
    for window in [5, 10, 20, 60]:
        df[f'ma_{window}'] = df['close'].rolling(window=window).mean()
        df[f'ma_ratio_{window}'] = df['close'] / df[f'ma_{window}']
    
    # 波动率
    df['volatility_5'] = df['close'].rolling(window=5).std() / df['close']
    df['volatility_20'] = df['close'].rolling(window=20).std() / df['close']
    
    # ATR
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['close'].shift(1))
    df['tr3'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['atr_14'] = df['tr'].rolling(window=14).mean()
    
    # 成交量
    df['volume_ma5'] = df['vol'].rolling(window=5).mean()
    df['volume_ratio'] = df['vol'] / df['volume_ma5']
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-8)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # 价格位置
    df['high_20'] = df['high'].rolling(window=20).max()
    df['low_20'] = df['low'].rolling(window=20).min()
    df['price_position'] = (df['close'] - df['low_20']) / (df['high_20'] - df['low_20'] + 1e-8)
    
    return df


def prepare_data(df, target_col='high'):
    """准备训练数据"""
    df = df.copy()
    df['target'] = df[target_col].shift(-1)
    
    drop_cols = ['ts_code', 'trade_date', 'target', 'tr1', 'tr2', 'tr3', 'tr']
    feature_cols = [c for c in df.columns if c not in drop_cols]
    
    df = df.dropna()
    
    return df[feature_cols], df['target'], df['trade_date'], feature_cols, df


# ============== 双模型训练 ==============

class DualPricePredictor:
    """
    双价格预测器 - 同时预测最高价和最低价
    """
    
    def __init__(self):
        self.high_model = None
        self.low_model = None
        self.feature_cols = None
        self.high_rmse = None
        self.low_rmse = None
    
    def train(self, df, feature_cols, n_splits=5):
        """
        训练两个模型：一个预测最高价，一个预测最低价
        """
        print("\n" + "=" * 60)
        print("训练最高价预测模型...")
        print("=" * 60)
        
        X_high, y_high, dates_high, _, df_high = prepare_data(df, target_col='high')
        self.high_model, self.high_rmse = self._train_single_model(
            X_high, y_high, dates_high, target_name='最高价', n_splits=n_splits
        )
        
        print("\n" + "=" * 60)
        print("训练最低价预测模型...")
        print("=" * 60)
        
        X_low, y_low, dates_low, _, df_low = prepare_data(df, target_col='low')
        self.low_model, self.low_rmse = self._train_single_model(
            X_low, y_low, dates_low, target_name='最低价', n_splits=n_splits
        )
        
        self.feature_cols = feature_cols
        
        return self
    
    def _train_single_model(self, X, y, dates, target_name='price', n_splits=5):
        """训练单个模型"""
        tscv = TimeSeriesSplit(n_splits=n_splits)
        
        results = []
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            model = xgb.XGBRegressor(
                objective='reg:squarederror',
                max_depth=6,
                learning_rate=0.05,
                n_estimators=200,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42
            )
            
            model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
            y_pred = model.predict(X_val)
            
            mse = mean_squared_error(y_val, y_pred)
            rmse = np.sqrt(mse)
            mae = mean_absolute_error(y_val, y_pred)
            
            # 方向准确率（针对价格预测）
            if target_name == '最高价':
                actual_dir = np.sign(y_val.values - X_val['close'].values)
                pred_dir = np.sign(y_pred - X_val['close'].values)
            else:  # 最低价
                actual_dir = np.sign(y_val.values - X_val['close'].values)
                pred_dir = np.sign(y_pred - X_val['close'].values)
            
            direction_acc = np.mean(actual_dir == pred_dir)
            
            print(f"Fold {fold+1}: RMSE={rmse:.4f}, MAE={mae:.4f}, 方向准确率={direction_acc:.2%}")
            results.append({'rmse': rmse, 'mae': mae, 'direction_acc': direction_acc})
        
        # 汇总
        avg_rmse = np.mean([r['rmse'] for r in results])
        avg_mae = np.mean([r['mae'] for r in results])
        avg_dir_acc = np.mean([r['direction_acc'] for r in results])
        
        print(f"\n{target_name}模型平均结果:")
        print(f"  RMSE: {avg_rmse:.4f}")
        print(f"  MAE: {avg_mae:.4f}")
        print(f"  方向准确率: {avg_dir_acc:.2%}")
        
        # 用全部数据训练最终模型
        final_model = xgb.XGBRegressor(
            objective='reg:squarederror',
            max_depth=6,
            learning_rate=0.05,
            n_estimators=200,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        final_model.fit(X, y)
        
        return final_model, avg_rmse
    
    def predict(self, X_latest):
        """
        预测下一个交易日的最高价和最低价
        """
        if self.high_model is None or self.low_model is None:
            raise ValueError("模型尚未训练")
        
        pred_high = self.high_model.predict(X_latest)[0]
        pred_low = self.low_model.predict(X_latest)[0]
        
        # 确保 low <= high
        if pred_low > pred_high:
            pred_low, pred_high = pred_high, pred_low
        
        return {
            'high': pred_high,
            'low': pred_low,
            'range': pred_high - pred_low,
            'high_confidence': 1.0,  # 可扩展为实际置信度
            'low_confidence': 1.0,
        }
    
    def save(self, stock_code, market):
        """保存两个模型"""
        self.high_model.save_model(f"model_{stock_code}_{market}_high.json")
        self.low_model.save_model(f"model_{stock_code}_{market}_low.json")
        print(f"\n模型已保存:")
        print(f"  最高价模型: model_{stock_code}_{market}_high.json")
        print(f"  最低价模型: model_{stock_code}_{market}_low.json")
    
    def load(self, stock_code, market, model_dir='.'):
        """加载两个模型"""
        import os
        self.high_model = xgb.XGBRegressor()
        self.low_model = xgb.XGBRegressor()
        
        high_path = os.path.join(model_dir, f"model_{stock_code}_{market}_high.json")
        low_path = os.path.join(model_dir, f"model_{stock_code}_{market}_low.json")
        
        # 如果指定目录不存在，尝试当前目录
        if not os.path.exists(high_path):
            high_path = f"model_{stock_code}_{market}_high.json"
        if not os.path.exists(low_path):
            low_path = f"model_{stock_code}_{market}_low.json"
        
        self.high_model.load_model(high_path)
        self.low_model.load_model(low_path)
        return self


# ============== 交易信号生成 ==============

def generate_trading_signal(predictor, df, feature_cols, stock_code, market, risk_ctrl, signal_gen):
    """
    基于双价格预测生成交易信号
    """
    latest = df.iloc[-1]
    X_pred = df[feature_cols].iloc[-1:]
    
    # 双价格预测
    predictions = predictor.predict(X_pred)
    pred_high = predictions['high']
    pred_low = predictions['low']
    
    current_price = latest['close']
    last_close = df.iloc[-2]['close'] if len(df) > 1 else current_price
    volatility = latest['volatility_20']
    
    # 风控评估
    risk_result = risk_ctrl.evaluate_trade(
        current_price=current_price,
        predicted_high=pred_high,
        predicted_low=pred_low,
        last_close=last_close,
        current_volatility=volatility
    )
    
    # 生成交易建议
    expected_high_return = (pred_high - current_price) / current_price
    expected_low_return = (pred_low - current_price) / current_price
    
    # 判断交易方向
    if expected_high_return > 0.02 and expected_low_return > -0.01:
        # 预期最高价有盈利空间，且最低价不会亏太多
        action = 'BUY'
        target_price = pred_high * 0.99
        message = f"建议买入，目标价 {target_price:.2f}，预期最高收益 {expected_high_return:.2%}"
    elif expected_low_return < -0.02:
        # 预期会下跌
        action = 'SELL'
        message = f"建议卖出，预测最低价 {pred_low:.2f}，预期下跌 {abs(expected_low_return):.2%}"
    else:
        action = 'HOLD'
        message = f"观望，预测区间 [{pred_low:.2f}, {pred_high:.2f}]"
    
    signal = {
        'stock_code': f"{stock_code}.{market.upper()}",
        'timestamp': datetime.datetime.now(),
        'current_price': current_price,
        'predicted_high': pred_high,
        'predicted_low': pred_low,
        'predicted_range': predictions['range'],
        'action': action,
        'message': message,
        'risk_check': risk_result,
        'expected_returns': {
            'high': expected_high_return,
            'low': expected_low_return,
        }
    }
    
    return signal


def print_signal(signal, predictor):
    """打印交易信号"""
    print("\n" + "=" * 60)
    print("交易信号 (双价格预测)")
    print("=" * 60)
    print(f"股票代码: {signal['stock_code']}")
    print(f"时间: {signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"当前价格: {signal['current_price']:.2f}")
    print("-" * 60)
    print(f"预测最高价: {signal['predicted_high']:.2f}")
    print(f"预测最低价: {signal['predicted_low']:.2f}")
    print(f"预测区间宽度: {signal['predicted_range']:.2f} ({signal['predicted_range']/signal['current_price']*100:.1f}%)")
    print("-" * 60)
    print(f"预期最高收益: {signal['expected_returns']['high']:.2%}")
    print(f"预期最低亏损: {signal['expected_returns']['low']:.2%}")
    print("-" * 60)
    print(f"操作建议: {signal['action']}")
    print(f"说明: {signal['message']}")
    print("-" * 60)
    
    risk = signal['risk_check']
    print(f"风险等级: {risk.risk_level.value}")
    print(f"能否交易: {'是' if risk.can_trade else '否'}")
    print(f"建议仓位: {risk.suggested_position:.0%}")
    
    if risk.stop_loss_price and risk.take_profit_price:
        print(f"止损价: {risk.stop_loss_price:.2f}")
        print(f"止盈价: {risk.take_profit_price:.2f}")
        
        entry = signal['current_price']
        stop = risk.stop_loss_price
        take = risk.take_profit_price
        if entry - stop > 0:
            risk_reward = (take - entry) / (entry - stop)
            print(f"风险收益比: 1:{risk_reward:.1f}")
    
    if predictor.high_rmse and predictor.low_rmse:
        print("-" * 60)
        print(f"模型误差参考:")
        print(f"  最高价预测 RMSE: {predictor.high_rmse:.4f}")
        print(f"  最低价预测 RMSE: {predictor.low_rmse:.4f}")
    
    print("=" * 60)


# ============== 主流程 ==============

def main():
    """主流程"""
    print("=" * 60)
    print("股票预测系统 v2.4 - 双价格预测版")
    print("同时预测最高价和最低价")
    print("=" * 60)
    
    stock_code = CONFIG['stock_code']
    market = CONFIG['market']
    
    # 初始化风控
    risk_ctrl = RiskController(
        max_daily_return=CONFIG['max_daily_return'],
        max_daily_drop=CONFIG['max_daily_drop'],
        volatility_threshold=CONFIG['volatility_threshold'],
        min_confidence=CONFIG['min_confidence'],
        max_position=CONFIG['max_position'],
        stop_loss_pct=CONFIG['stop_loss_pct'],
        take_profit_pct=CONFIG['take_profit_pct']
    )
    signal_gen = TradingSignalGenerator(risk_ctrl)
    
    # 计算日期范围
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=CONFIG['train_days'])
    
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')
    
    print(f"\n股票代码: {stock_code}.{market.upper()}")
    print(f"时间范围: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    # 获取数据
    df = fetch_data(stock_code, market, start_str, end_str)
    
    if df.empty:
        print("数据获取失败")
        return None
    
    # 特征工程
    df = create_features(df)
    print(f"特征工程后: {len(df)} 条数据")
    
    # 准备特征列表
    _, _, _, feature_cols, _ = prepare_data(df, target_col='high')
    print(f"特征数: {len(feature_cols)}")
    
    # 训练双模型
    predictor = DualPricePredictor()
    predictor.train(df, feature_cols, n_splits=5)
    
    # 保存模型
    predictor.save(stock_code, market)
    
    # 生成交易信号
    print("\n" + "=" * 60)
    print("生成实时交易信号...")
    
    signal = generate_trading_signal(
        predictor, df, feature_cols, stock_code, market, risk_ctrl, signal_gen
    )
    
    print_signal(signal, predictor)
    
    return {
        'predictor': predictor,
        'risk_ctrl': risk_ctrl,
        'signal_gen': signal_gen,
        'df': df,
        'feature_cols': feature_cols,
        'last_signal': signal
    }


if __name__ == '__main__':
    result = main()

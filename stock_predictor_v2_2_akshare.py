"""
股票预测系统 v2.2 - AKShare 版本（免费数据源）
使用 AKShare 替代 Tushare，无需付费 token
"""

import pandas as pd
import numpy as np
import akshare as ak
import datetime
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error
import xgboost as xgb
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

from risk_control import RiskController, TradingSignalGenerator, RiskLevel

# ============== 配置 ==============
CONFIG = {
    'stock_code': '600754',  # AKShare 格式：不带 .SH/.SZ 后缀
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


def convert_stock_code_akshare(ts_code: str) -> str:
    """
    将 tushare 格式转换为 akshare 格式
    600754.SH -> 600754
    000001.SZ -> 000001
    """
    if '.' in ts_code:
        return ts_code.split('.')[0]
    return ts_code


def convert_stock_code_tushare(ak_code: str, market: str = 'sh') -> str:
    """
    将 akshare 格式转换为 tushare 格式
    600754 -> 600754.SH
    """
    market_suffix = market.upper() if market else 'SH'
    return f"{ak_code}.{market_suffix}"


# ============== AKShare 数据获取 ==============

def fetch_data_akshare(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    使用 AKShare 获取股票日线数据
    
    Args:
        stock_code: 股票代码 (如 '600754')
        start_date: 开始日期 (格式: 'YYYYMMDD')
        end_date: 结束日期 (格式: 'YYYYMMDD')
    
    Returns:
        DataFrame with columns: trade_date, open, high, low, close, volume, amount, ...
    """
    try:
        # AKShare 日线数据接口
        # 注意：AKShare 的日期格式是 'YYYYMMDD'
        df = ak.stock_zh_a_daily(
            symbol=stock_code,
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"  # 前复权
        )
        
        if df.empty:
            print(f"警告：未获取到 {stock_code} 的数据")
            return pd.DataFrame()
        
        # AKShare 返回的列名映射为统一格式
        # AKShare: date, open, high, low, close, volume, outstanding_share, turnover
        column_mapping = {
            'date': 'trade_date',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'vol',
        }
        
        df = df.rename(columns=column_mapping)
        
        # 确保日期格式正确
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        # 添加股票代码列（兼容 tushare 格式）
        df['ts_code'] = convert_stock_code_tushare(stock_code)
        
        # 按日期排序
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        print(f"AKShare 获取成功: {stock_code}, {len(df)} 条数据")
        return df
        
    except Exception as e:
        print(f"AKShare 获取数据失败: {e}")
        # 尝试备用接口
        return fetch_data_akshare_backup(stock_code, start_date, end_date)


def fetch_data_akshare_backup(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    AKShare 备用数据接口
    """
    try:
        # 使用历史行情数据接口
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq"
        )
        
        if df.empty:
            return pd.DataFrame()
        
        # 列名映射
        column_mapping = {
            '日期': 'trade_date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'vol',
            '成交额': 'amount',
            '振幅': 'amplitude',
            '涨跌幅': 'pct_change',
            '涨跌额': 'change',
            '换手率': 'turnover_rate',
        }
        
        df = df.rename(columns=column_mapping)
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df['ts_code'] = convert_stock_code_tushare(stock_code)
        
        df = df.sort_values('trade_date').reset_index(drop=True)
        
        print(f"AKShare 备用接口获取成功: {stock_code}, {len(df)} 条数据")
        return df
        
    except Exception as e:
        print(f"AKShare 备用接口也失败: {e}")
        return pd.DataFrame()


def fetch_data_akshare_minute(stock_code: str, period: str = '5') -> pd.DataFrame:
    """
    获取分钟级数据（用于更精细的分析）
    
    Args:
        stock_code: 股票代码
        period: 分钟周期 ('1', '5', '15', '30', '60')
    """
    try:
        df = ak.stock_zh_a_minute(
            symbol=convert_stock_code_tushare(stock_code),
            period=period,
            adjust="qfq"
        )
        
        df = df.rename(columns={
            'day': 'trade_time',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'vol',
        })
        
        df['trade_time'] = pd.to_datetime(df['trade_time'])
        df = df.sort_values('trade_time').reset_index(drop=True)
        
        return df
    except Exception as e:
        print(f"分钟数据获取失败: {e}")
        return pd.DataFrame()


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
    
    # ATR (Average True Range)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['close'].shift(1))
    df['tr3'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['atr_14'] = df['tr'].rolling(window=14).mean()
    
    # 成交量特征
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
    
    # 新增特征：价格位置
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


# ============== 模型训练 ==============

def train_model(X_train, y_train, X_val=None, y_val=None):
    """训练 XGBoost 模型"""
    model = xgb.XGBRegressor(
        objective='reg:squarederror',
        max_depth=6,
        learning_rate=0.05,
        n_estimators=200,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    
    if X_val is not None and y_val is not None:
        model.fit(X_train, y_train, 
                  eval_set=[(X_val, y_val)],
                  verbose=False)
    else:
        model.fit(X_train, y_train)
    
    return model


def walk_forward_validation(X, y, dates, df, n_splits=5):
    """Walk-Forward 验证"""
    tscv = TimeSeriesSplit(n_splits=n_splits)
    risk_ctrl = RiskController(
        max_daily_return=CONFIG['max_daily_return'],
        max_daily_drop=CONFIG['max_daily_drop'],
        volatility_threshold=CONFIG['volatility_threshold'],
        min_confidence=CONFIG['min_confidence'],
        max_position=CONFIG['max_position'],
        stop_loss_pct=CONFIG['stop_loss_pct'],
        take_profit_pct=CONFIG['take_profit_pct']
    )
    
    results = []
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        print(f"\n=== Fold {fold + 1}/{n_splits} ===")
        
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        model = train_model(X_train, y_train, X_val, y_val)
        y_pred = model.predict(X_val)
        
        # 评估指标
        mse = mean_squared_error(y_val, y_pred)
        mae = mean_absolute_error(y_val, y_pred)
        rmse = np.sqrt(mse)
        
        # 方向准确率
        actual_direction = np.sign(y_val.values - X_val['close'].values)
        pred_direction = np.sign(y_pred - X_val['close'].values)
        direction_acc = np.mean(actual_direction == pred_direction)
        
        print(f"RMSE: {rmse:.4f}, MAE: {mae:.4f}, 方向准确率: {direction_acc:.2%}")
        
        # 风控评估（取验证集最后一个样本）
        last_idx = val_idx[-1]
        current_price = df.iloc[last_idx]['close']
        last_close = df.iloc[last_idx-1]['close'] if last_idx > 0 else current_price
        volatility = df.iloc[last_idx]['volatility_20']
        
        risk_result = risk_ctrl.evaluate_trade(
            current_price=current_price,
            predicted_high=y_pred[-1],
            predicted_low=y_pred[-1] * 0.98,
            last_close=last_close,
            current_volatility=volatility
        )
        
        print(f"风控检查: {risk_result.risk_level.value}, 能否交易: {risk_result.can_trade}")
        
        results.append({
            'fold': fold + 1,
            'rmse': rmse,
            'mae': mae,
            'direction_acc': direction_acc,
        })
    
    return results


# ============== 实时预测与交易信号 ==============

def predict_and_generate_signal(model, df, feature_cols, stock_code, risk_ctrl, signal_gen):
    """预测并生成交易信号"""
    latest = df.iloc[-1]
    X_pred = df[feature_cols].iloc[-1:]
    
    predicted_high = model.predict(X_pred)[0]
    
    # 计算预测最低价
    high_low_ratio = (df['high'] / df['low']).rolling(20).mean().iloc[-1]
    predicted_low = predicted_high / high_low_ratio
    
    current_price = latest['close']
    last_close = df.iloc[-2]['close'] if len(df) > 1 else current_price
    volatility = latest['volatility_20']
    
    signal = signal_gen.generate_signal(
        stock_code=convert_stock_code_tushare(stock_code),
        current_price=current_price,
        predicted_high=predicted_high,
        predicted_low=predicted_low,
        last_close=last_close,
        current_volatility=volatility
    )
    
    return signal, predicted_high, predicted_low


def print_signal(signal):
    """打印交易信号"""
    print("\n" + "=" * 60)
    print("交易信号")
    print("=" * 60)
    print(f"股票代码: {signal['stock_code']}")
    print(f"时间: {signal['timestamp']}")
    print(f"当前价格: {signal['current_price']:.2f}")
    print(f"预测最高价: {signal['predicted_high']:.2f}")
    print(f"预测最低价: {signal['predicted_low']:.2f}")
    print("-" * 60)
    print(f"操作建议: {signal['action']}")
    print(f"说明: {signal['message']}")
    print("-" * 60)
    
    risk = signal['risk_check']
    print(f"风险等级: {risk.risk_level.value}")
    print(f"能否交易: {'是' if risk.can_trade else '否'}")
    print(f"建议仓位: {risk.suggested_position:.0%}")
    
    if risk.stop_loss_price:
        print(f"止损价: {risk.stop_loss_price:.2f}")
        print(f"止盈价: {risk.take_profit_price:.2f}")
        
        entry = signal['current_price']
        stop = risk.stop_loss_price
        take = risk.take_profit_price
        risk_reward = (take - entry) / (entry - stop) if (entry - stop) > 0 else 0
        print(f"风险收益比: 1:{risk_reward:.1f}")
    
    print("=" * 60)


# ============== 主流程 ==============

def main():
    """主流程"""
    print("=" * 60)
    print("股票预测系统 v2.2 - AKShare 版本（免费数据源）")
    print("=" * 60)
    
    stock_code = CONFIG['stock_code']
    
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
    
    # AKShare 日期格式: 'YYYYMMDD'
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')
    
    print(f"\n获取数据: {stock_code}")
    print(f"时间范围: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    # 使用 AKShare 获取数据
    df = fetch_data_akshare(stock_code, start_str, end_str)
    
    if df.empty:
        print("数据获取失败，请检查股票代码是否正确")
        return None
    
    print(f"获取到 {len(df)} 条数据")
    
    # 特征工程
    df = create_features(df)
    print(f"特征工程后: {len(df)} 条数据")
    
    # 准备数据
    X, y, dates, feature_cols, df_full = prepare_data(df, target_col='high')
    print(f"训练样本: {len(X)}, 特征数: {len(feature_cols)}")
    
    # Walk-Forward 验证
    print("\n" + "=" * 60)
    print("开始 Walk-Forward 验证...")
    results = walk_forward_validation(X, y, dates, df_full, n_splits=5)
    
    # 汇总
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    avg_rmse = np.mean([r['rmse'] for r in results])
    avg_mae = np.mean([r['mae'] for r in results])
    avg_dir_acc = np.mean([r['direction_acc'] for r in results])
    print(f"平均 RMSE: {avg_rmse:.4f}")
    print(f"平均 MAE: {avg_mae:.4f}")
    print(f"平均方向准确率: {avg_dir_acc:.2%}")
    
    # 训练最终模型
    print("\n训练最终模型...")
    final_model = train_model(X, y)
    
    # 保存模型
    model_filename = f"model_{stock_code}_akshare_v2.json"
    final_model.save_model(model_filename)
    print(f"模型已保存: {model_filename}")
    
    # 生成实时交易信号
    print("\n" + "=" * 60)
    print("生成实时交易信号...")
    
    signal, pred_high, pred_low = predict_and_generate_signal(
        final_model, df_full, feature_cols, stock_code, risk_ctrl, signal_gen
    )
    
    print_signal(signal)
    
    return {
        'model': final_model,
        'risk_ctrl': risk_ctrl,
        'signal_gen': signal_gen,
        'df': df_full,
        'feature_cols': feature_cols,
        'last_signal': signal
    }


if __name__ == '__main__':
    result = main()

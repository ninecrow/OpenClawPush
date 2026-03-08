"""
股票预测系统 v2.3 - 演示版本（使用模拟数据）
用于测试代码逻辑，无需网络连接
"""

import pandas as pd
import numpy as np
import datetime
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

from risk_control import RiskController, TradingSignalGenerator

# ============== 配置 ==============
CONFIG = {
    'stock_code': 'DEMO',
    'train_days': 500,
    
    # 风险控制参数
    'max_daily_return': 0.095,
    'max_daily_drop': -0.095,
    'volatility_threshold': 2.5,
    'min_confidence': 0.55,
    'max_position': 0.3,
    'stop_loss_pct': 0.03,
    'take_profit_pct': 0.05,
}


# ============== 生成模拟股票数据 ==============

def generate_mock_stock_data(n_days=500, seed=42):
    """
    生成模拟股票数据，用于测试代码逻辑
    模拟具有趋势和波动性的股价走势
    """
    np.random.seed(seed)
    
    # 生成日期
    end_date = datetime.datetime.now()
    dates = pd.date_range(end=end_date, periods=n_days, freq='B')  # 工作日
    
    # 生成股价走势（随机游走 + 趋势）
    returns = np.random.normal(0.0005, 0.02, n_days)  # 日均收益 0.05%，波动率 2%
    
    # 添加一些趋势周期
    trend = np.sin(np.linspace(0, 4*np.pi, n_days)) * 0.01  # 周期性趋势
    returns += trend
    
    # 计算价格
    initial_price = 25.0
    prices = initial_price * np.exp(np.cumsum(returns))
    
    # 生成 OHLC 数据
    data = []
    for i, date in enumerate(dates):
        close = prices[i]
        # 日内波动
        high = close * (1 + abs(np.random.normal(0, 0.01)))
        low = close * (1 - abs(np.random.normal(0, 0.01)))
        open_price = low + np.random.random() * (high - low)
        volume = int(np.random.normal(1000000, 200000))
        
        data.append({
            'trade_date': date,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'vol': max(volume, 100000),
            'ts_code': 'DEMO'
        })
    
    df = pd.DataFrame(data)
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
        
        # 风控评估
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
        stock_code=stock_code,
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
    print("股票预测系统 v2.3 - 演示版本（使用模拟数据）")
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
    
    print(f"\n生成模拟数据: {stock_code}")
    print("注：这是演示版本，使用随机生成的模拟股票数据")
    
    # 生成模拟数据
    df = generate_mock_stock_data(n_days=500, seed=42)
    
    print(f"生成 {len(df)} 条模拟数据")
    print(f"价格范围: {df['close'].min():.2f} ~ {df['close'].max():.2f}")
    
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
    model_filename = f"model_{stock_code}_demo_v2.json"
    final_model.save_model(model_filename)
    print(f"模型已保存: {model_filename}")
    
    # 生成实时交易信号
    print("\n" + "=" * 60)
    print("生成实时交易信号...")
    
    signal, pred_high, pred_low = predict_and_generate_signal(
        final_model, df_full, feature_cols, stock_code, risk_ctrl, signal_gen
    )
    
    print_signal(signal)
    
    # 特征重要性
    print("\n" + "=" * 60)
    print("特征重要性 (Top 10)")
    print("=" * 60)
    importance = list(zip(feature_cols, final_model.feature_importances_))
    importance.sort(key=lambda x: x[1], reverse=True)
    for feat, imp in importance[:10]:
        print(f"  {feat}: {imp:.4f}")
    
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

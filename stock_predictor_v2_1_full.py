"""
股票预测系统 v2.1 - 完整版（含风险控制）
整合预测模型和风险控制的完整交易决策系统
"""

import pandas as pd
import numpy as np
import tushare as ts
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
    'ts_token': 'your_tushare_token_here',  # 替换为你的 token
    'stock_code': '600754.SH',
    'train_days': 760,
    
    # 风险控制参数
    'max_daily_return': 0.095,      # 涨幅限制
    'max_daily_drop': -0.095,       # 跌幅限制
    'volatility_threshold': 2.5,    # 波动率异常阈值
    'min_confidence': 0.55,         # 最低置信度
    'max_position': 0.3,            # 最大仓位
    'stop_loss_pct': 0.03,          # 止损比例
    'take_profit_pct': 0.05,        # 止盈比例
}


# ============== 数据获取与特征工程 ==============

def fetch_data(ts_code, start_date, end_date, pro):
    """获取股票数据"""
    daily = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    basic = pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date)
    moneyflow = pro.moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
    
    df = pd.merge(daily, basic[['trade_date', 'turnover_rate', 'volume_ratio']], 
                  on='trade_date', how='left')
    
    if not moneyflow.empty:
        df = pd.merge(df, moneyflow[['trade_date', 'net_mf_amount']], 
                      on='trade_date', how='left')
    
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df = df.sort_values('trade_date').reset_index(drop=True)
    
    return df


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
    
    # 波动率 (用于风控)
    df['volatility_5'] = df['close'].rolling(window=5).std() / df['close']
    df['volatility_20'] = df['close'].rolling(window=20).std() / df['close']
    
    # ATR (Average True Range)
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
    """Walk-Forward 验证（带风控评估）"""
    tscv = TimeSeriesSplit(n_splits=n_splits)
    risk_ctrl = RiskController()
    
    results = []
    all_predictions = []
    all_actuals = []
    
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
        
        # 风控评估示例（取验证集最后一个样本）
        last_idx = val_idx[-1]
        current_price = df.iloc[last_idx]['close']
        last_close = df.iloc[last_idx-1]['close'] if last_idx > 0 else current_price
        volatility = df.iloc[last_idx]['volatility_20']
        
        # 模拟风控检查
        risk_result = risk_ctrl.evaluate_trade(
            current_price=current_price,
            predicted_high=y_pred[-1],
            predicted_low=y_pred[-1] * 0.98,  # 简化处理
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
        
        all_predictions.extend(y_pred)
        all_actuals.extend(y_val.values)
    
    return results, all_predictions, all_actuals


# ============== 实时预测与交易信号 ==============

def predict_and_generate_signal(model, df, feature_cols, stock_code, risk_ctrl, signal_gen):
    """
    预测并生成交易信号
    """
    # 获取最新数据
    latest = df.iloc[-1]
    
    # 准备特征
    X_pred = df[feature_cols].iloc[-1:]
    
    # 预测
    predicted_high = model.predict(X_pred)[0]
    
    # 计算预测最低价 (简化：基于历史高低点比例)
    high_low_ratio = (df['high'] / df['low']).rolling(20).mean().iloc[-1]
    predicted_low = predicted_high / high_low_ratio
    
    current_price = latest['close']
    last_close = df.iloc[-2]['close'] if len(df) > 1 else current_price
    volatility = latest['volatility_20']
    
    # 生成交易信号
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
        
        # 计算风险收益比
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
    print("股票预测系统 v2.1 - 带风险控制")
    print("=" * 60)
    
    # 初始化
    pro = ts.pro_api(CONFIG['ts_token'])
    
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
    
    # 获取数据
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=CONFIG['train_days'])
    
    print(f"\n获取数据: {CONFIG['stock_code']}")
    print(f"时间范围: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    df = fetch_data(
        CONFIG['stock_code'],
        start_date.strftime('%Y%m%d'),
        end_date.strftime('%Y%m%d'),
        pro
    )
    
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
    results, all_preds, all_actuals = walk_forward_validation(X, y, dates, df_full, n_splits=5)
    
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
    final_model.save_model(f"model_{CONFIG['stock_code'].replace('.', '_')}_v2.json")
    print(f"模型已保存")
    
    # 生成实时交易信号
    print("\n" + "=" * 60)
    print("生成实时交易信号...")
    
    signal, pred_high, pred_low = predict_and_generate_signal(
        final_model, df_full, feature_cols, CONFIG['stock_code'], risk_ctrl, signal_gen
    )
    
    print_signal(signal)
    
    # 返回关键数据供后续使用
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

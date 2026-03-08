"""
股票预测系统 - 修复版
修复内容：
1. 时间序列划分（去掉 shuffle，防止数据泄露）
2. Ridge -> XGBoost（非线性模型，捕捉复杂模式）
3. 增加 Walk-Forward 验证（更符合实际交易场景）
"""

import pandas as pd
import numpy as np
import tushare as ts
import datetime
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error
import xgboost as xgb
import matplotlib.pyplot as plt
import matplotlib.dates as mdate
import warnings
warnings.filterwarnings('ignore')

# ============== 配置 ==============
TS_TOKEN = 'your_tushare_token_here'  # 替换为你的 tushare token
STOCK_CODE = '600754.SH'  # 示例股票
TRAIN_DAYS = 760  # 训练数据天数
PREDICT_WINDOW = 20  # 预测窗口天数

# ============== 数据获取 ==============

def fetch_stock_data(ts_code, start_date, end_date, pro):
    """获取股票数据，包括日线和基本面"""
    # 日线行情
    daily = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    
    # 每日指标
    basic = pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date)
    
    # 资金流向
    moneyflow = pro.moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
    
    # 合并数据
    df = pd.merge(daily, basic[['trade_date', 'turnover_rate', 'volume_ratio']], 
                  on='trade_date', how='left')
    
    if not moneyflow.empty:
        df = pd.merge(df, moneyflow[['trade_date', 'net_mf_amount']], 
                      on='trade_date', how='left')
    
    # 转换日期格式
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df = df.sort_values('trade_date').reset_index(drop=True)
    
    return df


def create_features(df):
    """创建特征工程"""
    df = df.copy()
    
    # 价格特征
    df['price_range'] = (df['high'] - df['low']) / df['close']
    df['price_change'] = (df['close'] - df['open']) / df['open']
    df['body_ratio'] = abs(df['close'] - df['open']) / (df['high'] - df['low'] + 1e-8)
    
    # 移动平均线
    for window in [5, 10, 20]:
        df[f'ma_{window}'] = df['close'].rolling(window=window).mean()
        df[f'ma_ratio_{window}'] = df['close'] / df[f'ma_{window}']
    
    # 波动率
    df['volatility_5'] = df['close'].rolling(window=5).std()
    df['volatility_20'] = df['close'].rolling(window=20).std()
    
    # 成交量特征
    df['volume_ma5'] = df['vol'].rolling(window=5).mean()
    df['volume_ratio'] = df['vol'] / df['volume_ma5']
    
    # 技术指标 - RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-8)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 技术指标 - MACD
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    
    return df


def prepare_data(df, target_col='high'):
    """
    准备训练数据
    关键修复：用 T 日特征预测 T+1 日的目标值
    """
    df = df.copy()
    
    # 创建目标变量（下一天的最高价/最低价）
    df['target'] = df[target_col].shift(-1)
    
    # 删除不需要的列
    drop_cols = ['ts_code', 'trade_date', 'target']
    feature_cols = [c for c in df.columns if c not in drop_cols]
    
    # 删除 NaN 值（主要是 rolling 特征产生的）
    df = df.dropna()
    
    X = df[feature_cols]
    y = df['target']
    dates = df['trade_date']
    
    return X, y, dates, feature_cols


# ============== 模型训练 ==============

def train_xgboost(X_train, y_train, X_val=None, y_val=None):
    """训练 XGBoost 模型"""
    
    params = {
        'objective': 'reg:squarederror',
        'max_depth': 6,
        'learning_rate': 0.05,
        'n_estimators': 200,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
        'early_stopping_rounds': 20,
        'eval_metric': 'rmse'
    }
    
    model = xgb.XGBRegressor(**{k: v for k, v in params.items() 
                                 if k not in ['early_stopping_rounds', 'eval_metric']})
    
    if X_val is not None and y_val is not None:
        model.fit(X_train, y_train, 
                  eval_set=[(X_val, y_val)],
                  verbose=False)
    else:
        model.fit(X_train, y_train)
    
    return model


def walk_forward_validation(X, y, dates, n_splits=5):
    """
    Walk-Forward 验证
    关键：按时间顺序划分，模拟实际交易场景
    """
    tscv = TimeSeriesSplit(n_splits=n_splits)
    
    results = []
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        print(f"\n=== Fold {fold + 1}/{n_splits} ===")
        print(f"训练集: {dates.iloc[train_idx].min()} ~ {dates.iloc[train_idx].max()}")
        print(f"验证集: {dates.iloc[val_idx].min()} ~ {dates.iloc[val_idx].max()}")
        
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        model = train_xgboost(X_train, y_train, X_val, y_val)
        
        # 预测
        y_pred = model.predict(X_val)
        
        # 评估
        mse = mean_squared_error(y_val, y_pred)
        mae = mean_absolute_error(y_val, y_pred)
        rmse = np.sqrt(mse)
        
        # 计算方向准确率
        direction_actual = np.sign(y_val.values - X_val['close'].values)
        direction_pred = np.sign(y_pred - X_val['close'].values)
        direction_acc = np.mean(direction_actual == direction_pred)
        
        print(f"RMSE: {rmse:.4f}, MAE: {mae:.4f}, 方向准确率: {direction_acc:.2%}")
        
        results.append({
            'fold': fold + 1,
            'rmse': rmse,
            'mae': mae,
            'direction_acc': direction_acc,
            'model': model
        })
    
    return results


def plot_feature_importance(model, feature_cols, top_n=20):
    """绘制特征重要性"""
    importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False).head(top_n)
    
    plt.figure(figsize=(10, 6))
    plt.barh(importance['feature'], importance['importance'])
    plt.xlabel('Importance')
    plt.title(f'Top {top_n} Feature Importance (XGBoost)')
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.show()
    
    return importance


def plot_predictions(dates, actual, predicted, title='Price Prediction'):
    """绘制预测 vs 实际对比图"""
    plt.figure(figsize=(15, 6))
    plt.plot(dates, actual, 'r-', label='Actual', linewidth=1.5)
    plt.plot(dates, predicted, 'b--', label='Predicted', linewidth=1.5)
    
    # 添加误差区间
    error = np.abs(actual - predicted)
    plt.fill_between(dates, predicted - error, predicted + error, 
                     alpha=0.2, color='blue', label='Error Band')
    
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.title(title)
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


# ============== 主流程 ==============

def main():
    """主流程"""
    # 初始化 tushare
    pro = ts.pro_api(TS_TOKEN)
    
    # 计算日期范围
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=TRAIN_DAYS)
    
    print(f"获取数据: {STOCK_CODE}")
    print(f"时间范围: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    
    # 获取数据
    df = fetch_stock_data(
        STOCK_CODE,
        start_date.strftime('%Y%m%d'),
        end_date.strftime('%Y%m%d'),
        pro
    )
    
    print(f"获取到 {len(df)} 条数据")
    
    # 特征工程
    df = create_features(df)
    print(f"特征工程后: {len(df)} 条数据")
    
    # 准备数据 - 预测最高价
    X, y, dates, feature_cols = prepare_data(df, target_col='high')
    print(f"训练样本: {len(X)}, 特征数: {len(feature_cols)}")
    
    # Walk-Forward 验证
    print("\n开始 Walk-Forward 验证...")
    results = walk_forward_validation(X, y, dates, n_splits=5)
    
    # 汇总结果
    print("\n=== 验证结果汇总 ===")
    avg_rmse = np.mean([r['rmse'] for r in results])
    avg_mae = np.mean([r['mae'] for r in results])
    avg_dir_acc = np.mean([r['direction_acc'] for r in results])
    print(f"平均 RMSE: {avg_rmse:.4f}")
    print(f"平均 MAE: {avg_mae:.4f}")
    print(f"平均方向准确率: {avg_dir_acc:.2%}")
    
    # 用全部数据训练最终模型
    print("\n训练最终模型...")
    final_model = train_xgboost(X, y)
    
    # 特征重要性
    print("\n特征重要性分析...")
    importance = plot_feature_importance(final_model, feature_cols)
    print("\nTop 10 重要特征:")
    print(importance.head(10))
    
    # 保存模型
    final_model.save_model(f'model_{STOCK_CODE.replace(".", "_")}_high.json')
    print(f"\n模型已保存: model_{STOCK_CODE.replace('.', '_')}_high.json")
    
    return final_model, feature_cols


if __name__ == '__main__':
    model, features = main()

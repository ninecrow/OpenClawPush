#!/usr/bin/env python3
"""
实时预测脚本 - Real-time Prediction Script
每日运行一次，获取最新数据并生成交易信号

使用方法:
    python realtime_predict.py                    # 使用默认配置
    python realtime_predict.py --code 000001 --market sz  # 指定股票
    python realtime_predict.py --notify           # 发送通知（需配置）
"""

import argparse
import pandas as pd
import numpy as np
import datetime
import json
import os
import sys
from pathlib import Path

# 导入双模型预测系统的模块
from stock_predictor_v2_4_dual import (
    fetch_data, create_features, prepare_data, 
    DualPricePredictor, generate_trading_signal, print_signal,
    RiskController, TradingSignalGenerator
)

# ============== 配置 ==============
DEFAULT_CONFIG = {
    'stock_code': '600754',
    'market': 'sh',
    'model_dir': './models',  # 模型保存目录
    'output_dir': './signals',  # 信号输出目录
    'history_file': './prediction_history.json',  # 预测历史记录
}


def load_config():
    """加载配置文件"""
    config_file = Path('./predict_config.json')
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return DEFAULT_CONFIG


def save_config(config):
    """保存配置文件"""
    with open('./predict_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def check_model_exists(stock_code: str, market: str, model_dir: str = './models') -> bool:
    """检查模型文件是否存在"""
    high_model = Path(model_dir) / f"model_{stock_code}_{market}_high.json"
    low_model = Path(model_dir) / f"model_{stock_code}_{market}_low.json"
    return high_model.exists() and low_model.exists()


def train_and_save_model(stock_code: str, market: str, train_days: int = 760):
    """
    训练新模型并保存
    """
    print(f"\n[模型训练] 为 {stock_code}.{market.upper()} 训练新模型...")
    print("=" * 60)
    
    # 导入主训练流程
    from stock_predictor_v2_4_dual import main as train_main
    
    # 临时修改配置
    import stock_predictor_v2_4_dual as sp
    original_config = sp.CONFIG.copy()
    sp.CONFIG['stock_code'] = stock_code
    sp.CONFIG['market'] = market
    sp.CONFIG['train_days'] = train_days
    
    # 运行训练
    result = train_main()
    
    # 恢复配置
    sp.CONFIG = original_config
    
    return result is not None


def load_models(stock_code: str, market: str, model_dir: str = './models'):
    """
    加载训练好的模型
    """
    predictor = DualPricePredictor()
    
    high_model_path = Path(model_dir) / f"model_{stock_code}_{market}_high.json"
    low_model_path = Path(model_dir) / f"model_{stock_code}_{market}_low.json"
    
    if not high_model_path.exists() or not low_model_path.exists():
        return None
    
    predictor.load(stock_code, market)
    
    # 加载历史 RMSE（如果有）
    history_file = Path(model_dir) / f"model_{stock_code}_{market}_metrics.json"
    if history_file.exists():
        with open(history_file, 'r') as f:
            metrics = json.load(f)
            predictor.high_rmse = metrics.get('high_rmse')
            predictor.low_rmse = metrics.get('low_rmse')
    
    return predictor


def save_prediction_history(signal: dict, history_file: str):
    """
    保存预测历史，用于后续评估模型准确性
    """
    history_path = Path(history_file)
    
    # 加载现有历史
    history = []
    if history_path.exists():
        with open(history_path, 'r', encoding='utf-8') as f:
            history = json.load(f)
    
    # 添加新记录
    record = {
        'timestamp': signal['timestamp'].isoformat() if hasattr(signal['timestamp'], 'isoformat') else str(signal['timestamp']),
        'stock_code': signal['stock_code'],
        'current_price': float(signal['current_price']),
        'predicted_high': float(signal['predicted_high']),
        'predicted_low': float(signal['predicted_low']),
        'action': signal['action'],
        'risk_level': signal['risk_check'].risk_level.value if hasattr(signal['risk_check'], 'risk_level') else str(signal['risk_check'].get('risk_level', '')),
    }
    
    history.append(record)
    
    # 只保留最近 100 条
    history = history[-100:]
    
    # 保存
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print(f"[历史记录] 已保存到 {history_file}")


def save_signal_to_file(signal: dict, output_dir: str = './signals'):
    """
    将信号保存到文件
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # 文件名: signals/YYYYMMDD_600754_SH.json
    today = datetime.datetime.now().strftime('%Y%m%d')
    stock_code = signal['stock_code'].replace('.', '_')
    filename = output_path / f"{today}_{stock_code}.json"
    
    # 转换信号为可序列化格式
    signal_data = {
        'timestamp': signal['timestamp'].isoformat() if hasattr(signal['timestamp'], 'isoformat') else str(signal['timestamp']),
        'stock_code': signal['stock_code'],
        'current_price': float(signal['current_price']),
        'predicted_high': float(signal['predicted_high']),
        'predicted_low': float(signal['predicted_low']),
        'predicted_range': float(signal.get('predicted_range', 0)),
        'action': signal['action'],
        'message': signal['message'],
        'expected_returns': {
            'high': float(signal['expected_returns']['high']),
            'low': float(signal['expected_returns']['low']),
        },
        'risk_check': {
            'can_trade': signal['risk_check'].can_trade if hasattr(signal['risk_check'], 'can_trade') else signal['risk_check'].get('can_trade'),
            'risk_level': signal['risk_check'].risk_level.value if hasattr(signal['risk_check'], 'risk_level') else signal['risk_check'].get('risk_level', ''),
            'suggested_position': float(signal['risk_check'].suggested_position if hasattr(signal['risk_check'], 'suggested_position') else signal['risk_check'].get('suggested_position', 0)),
            'stop_loss_price': float(signal['risk_check'].stop_loss_price if hasattr(signal['risk_check'], 'stop_loss_price') else signal['risk_check'].get('stop_loss_price', 0)) if signal['risk_check'].stop_loss_price if hasattr(signal['risk_check'], 'stop_loss_price') else signal['risk_check'].get('stop_loss_price') else None,
            'take_profit_price': float(signal['risk_check'].take_profit_price if hasattr(signal['risk_check'], 'take_profit_price') else signal['risk_check'].get('take_profit_price', 0)) if signal['risk_check'].take_profit_price if hasattr(signal['risk_check'], 'take_profit_price') else signal['risk_check'].get('take_profit_price') else None,
        }
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(signal_data, f, ensure_ascii=False, indent=2)
    
    print(f"[文件保存] 信号已保存到 {filename}")
    return filename


def send_notification(signal: dict, method: str = 'print'):
    """
    发送通知（可扩展为飞书/钉钉/邮件等）
    
    Args:
        signal: 交易信号
        method: 通知方式 ('print', 'feishu', 'dingtalk', 'email')
    """
    if method == 'print':
        # 默认只打印到控制台
        return
    
    elif method == 'feishu':
        # 飞书 webhook 通知（需要配置 webhook url）
        import requests
        
        webhook_url = os.getenv('FEISHU_WEBHOOK_URL')
        if not webhook_url:
            print("[通知] 未配置 FEISHU_WEBHOOK_URL 环境变量")
            return
        
        message = {
            "msg_type": "text",
            "content": {
                "text": f"""股票交易信号
股票: {signal['stock_code']}
当前价: {signal['current_price']:.2f}
预测区间: [{signal['predicted_low']:.2f}, {signal['predicted_high']:.2f}]
操作建议: {signal['action']}
说明: {signal['message']}"""
            }
        }
        
        try:
            requests.post(webhook_url, json=message, timeout=10)
            print("[通知] 飞书消息已发送")
        except Exception as e:
            print(f"[通知] 飞书发送失败: {e}")
    
    # 可扩展更多通知方式...


def update_actual_prices(history_file: str, stock_code: str, actual_high: float = None, actual_low: float = None):
    """
    更新预测历史中的实际价格（用于后续评估）
    每天收盘后运行此函数更新
    """
    history_path = Path(history_file)
    if not history_path.exists():
        return
    
    with open(history_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    # 找到最近一条该股票的预测记录
    for record in reversed(history):
        if record['stock_code'] == stock_code and 'actual_high' not in record:
            if actual_high is not None:
                record['actual_high'] = float(actual_high)
            if actual_low is not None:
                record['actual_low'] = float(actual_low)
            break
    
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print(f"[历史更新] 已更新实际价格")


def evaluate_recent_predictions(history_file: str, days: int = 10):
    """
    评估最近几天的预测准确性
    """
    history_path = Path(history_file)
    if not history_path.exists():
        print("[评估] 无历史记录")
        return
    
    with open(history_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    # 筛选有实际价格的记录
    evaluated = [h for h in history if 'actual_high' in h and 'actual_low' in h]
    
    if len(evaluated) < days:
        print(f"[评估] 历史记录不足（{len(evaluated)} 条，需要 {days} 条）")
        return
    
    recent = evaluated[-days:]
    
    # 计算误差
    high_errors = [abs(r['predicted_high'] - r['actual_high']) / r['actual_high'] for r in recent]
    low_errors = [abs(r['predicted_low'] - r['actual_low']) / r['actual_low'] for r in recent]
    
    print("\n" + "=" * 60)
    print(f"最近 {days} 天预测评估")
    print("=" * 60)
    print(f"最高价预测平均误差: {np.mean(high_errors):.2%}")
    print(f"最低价预测平均误差: {np.mean(low_errors):.2%}")
    print(f"最高价预测方向准确率: {np.mean([r['predicted_high'] > r['current_price'] and r['actual_high'] > r['current_price'] for r in recent]):.1%}")
    print(f"最低价预测方向准确率: {np.mean([r['predicted_low'] < r['current_price'] and r['actual_low'] < r['current_price'] for r in recent]):.1%}")
    print("=" * 60)


def realtime_predict(stock_code: str = None, market: str = None, 
                     force_retrain: bool = False, notify: bool = False,
                     config: dict = None) -> dict:
    """
    实时预测主函数
    
    Args:
        stock_code: 股票代码（默认使用配置）
        market: 市场（sh/sz）
        force_retrain: 强制重新训练模型
        notify: 是否发送通知
        config: 配置字典
    
    Returns:
        交易信号字典
    """
    if config is None:
        config = load_config()
    
    stock_code = stock_code or config['stock_code']
    market = market or config['market']
    model_dir = config.get('model_dir', './models')
    output_dir = config.get('output_dir', './signals')
    history_file = config.get('history_file', './prediction_history.json')
    
    print("=" * 60)
    print("实时预测脚本")
    print("=" * 60)
    print(f"股票: {stock_code}.{market.upper()}")
    print(f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 检查模型是否存在
    model_exists = check_model_exists(stock_code, market, model_dir)
    
    if not model_exists or force_retrain:
        print("\n[状态] 模型不存在或需要重新训练")
        success = train_and_save_model(stock_code, market)
        if not success:
            print("[错误] 模型训练失败")
            return None
    else:
        print("\n[状态] 已加载现有模型")
    
    # 加载模型
    predictor = load_models(stock_code, market, model_dir)
    if predictor is None:
        print("[错误] 无法加载模型")
        return None
    
    print(f"[模型] 最高价预测模型 + 最低价预测模型")
    
    # 获取最新数据
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=60)  # 只需要最近60天用于特征计算
    
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')
    
    print(f"\n[数据] 获取最新行情数据...")
    df = fetch_data(stock_code, market, start_str, end_str)
    
    if df.empty:
        print("[错误] 数据获取失败")
        return None
    
    # 特征工程
    df = create_features(df)
    
    # 准备特征
    _, _, _, feature_cols, _ = prepare_data(df, target_col='high')
    
    # 初始化风控
    risk_ctrl = RiskController(
        max_daily_return=0.095,
        max_daily_drop=-0.095,
        volatility_threshold=2.5,
        min_confidence=0.55,
        max_position=0.3,
        stop_loss_pct=0.03,
        take_profit_pct=0.05
    )
    signal_gen = TradingSignalGenerator(risk_ctrl)
    
    # 生成信号
    print("\n[预测] 生成交易信号...")
    signal = generate_trading_signal(
        predictor, df, feature_cols, stock_code, market, risk_ctrl, signal_gen
    )
    
    # 打印信号
    print_signal(signal, predictor)
    
    # 保存到文件
    signal_file = save_signal_to_file(signal, output_dir)
    
    # 保存历史
    save_prediction_history(signal, history_file)
    
    # 发送通知
    if notify:
        send_notification(signal, method='feishu')
    
    # 评估最近预测
    evaluate_recent_predictions(history_file, days=5)
    
    print("\n[完成] 实时预测完成")
    print(f"[文件] 信号已保存: {signal_file}")
    
    return signal


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='股票实时预测脚本')
    parser.add_argument('--code', type=str, help='股票代码（如 600754）')
    parser.add_argument('--market', type=str, choices=['sh', 'sz'], help='市场（sh 或 sz）')
    parser.add_argument('--retrain', action='store_true', help='强制重新训练模型')
    parser.add_argument('--notify', action='store_true', help='发送通知')
    parser.add_argument('--evaluate', action='store_true', help='只评估最近预测，不生成新信号')
    parser.add_argument('--update-actual', nargs=3, metavar=('CODE', 'HIGH', 'LOW'), 
                        help='更新实际价格（收盘后使用）')
    
    args = parser.parse_args()
    
    config = load_config()
    
    # 更新配置
    if args.code:
        config['stock_code'] = args.code
    if args.market:
        config['market'] = args.market
    
    # 保存配置
    save_config(config)
    
    # 执行命令
    if args.evaluate:
        # 只评估
        history_file = config.get('history_file', './prediction_history.json')
        evaluate_recent_predictions(history_file, days=10)
    elif args.update_actual:
        # 更新实际价格
        code, high, low = args.update_actual
        history_file = config.get('history_file', './prediction_history.json')
        update_actual_prices(history_file, f"{code}.{config['market'].upper()}", 
                            float(high), float(low))
        evaluate_recent_predictions(history_file, days=10)
    else:
        # 正常预测
        signal = realtime_predict(
            stock_code=config['stock_code'],
            market=config['market'],
            force_retrain=args.retrain,
            notify=args.notify,
            config=config
        )
        
        if signal:
            # 返回码：0=正常，1=建议交易，2=禁止交易
            if signal['risk_check'].can_trade:
                return 1
            else:
                return 2
        return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
实时预测脚本 v2.5 - 多股票监控 + 飞书推送
监控股票: 601166(兴业银行), 300238(冠昊生物)

使用方法:
    python realtime_predict_v2_5.py                    # 默认监控所有配置的股票
    python realtime_predict_v2_5.py --code 601166      # 只监控指定股票
    python realtime_predict_v2_5.py --notify           # 推送结果到飞书
    python realtime_predict_v2_5.py --retrain          # 重新训练所有模型
"""

import argparse
import pandas as pd
import numpy as np
import datetime
import json
import os
import sys
from pathlib import Path
from typing import List, Dict

# 导入模块
from stock_predictor_v2_4_dual import (
    fetch_data, create_features, prepare_data, 
    DualPricePredictor, generate_trading_signal,
    RiskController, TradingSignalGenerator
)
from feishu_notifier import FeishuNotifier

# ============== 配置 ==============
DEFAULT_CONFIG = {
    # 监控的股票列表
    'watchlist': [
        {'code': '601166', 'market': 'sh', 'name': '兴业银行'},  # 上海主板
        {'code': '300238', 'market': 'sz', 'name': '冠昊生物'},  # 深圳创业板
    ],
    
    # 路径配置
    'model_dir': './models',
    'output_dir': './signals',
    'history_file': './prediction_history.json',
    
    # 训练配置
    'train_days': 760,
    
    # 风控参数
    'risk_control': {
        'max_daily_return': 0.095,
        'max_daily_drop': -0.095,
        'volatility_threshold': 2.5,
        'min_confidence': 0.55,
        'max_position': 0.3,
        'stop_loss_pct': 0.03,
        'take_profit_pct': 0.05,
    }
}


def load_config():
    """加载配置文件"""
    config_file = Path('./predict_config.json')
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            saved_config = json.load(f)
            # 合并配置，保留默认股票列表
            result = DEFAULT_CONFIG.copy()
            result.update({k: v for k, v in saved_config.items() if k != 'watchlist'})
            if 'watchlist' in saved_config:
                result['watchlist'] = saved_config['watchlist']
            return result
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """保存配置文件"""
    with open('./predict_config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def check_model_exists(stock_code: str, market: str, model_dir: str = './models') -> bool:
    """检查模型文件是否存在"""
    # 检查指定目录
    high_model = Path(model_dir) / f"model_{stock_code}_{market}_high.json"
    low_model = Path(model_dir) / f"model_{stock_code}_{market}_low.json"
    if high_model.exists() and low_model.exists():
        return True
    
    # 检查当前目录（因为默认保存到当前目录）
    high_model = Path(f"model_{stock_code}_{market}_high.json")
    low_model = Path(f"model_{stock_code}_{market}_low.json")
    return high_model.exists() and low_model.exists()


def train_model_for_stock(stock_info: Dict, train_days: int = 760) -> bool:
    """
    为指定股票训练模型
    """
    stock_code = stock_info['code']
    market = stock_info['market']
    name = stock_info.get('name', '')
    
    print(f"\n{'='*60}")
    print(f"[训练] {name} ({stock_code}.{market.upper()})")
    print(f"{'='*60}")
    
    try:
        # 导入并修改配置
        import stock_predictor_v2_4_dual as sp
        original_config = sp.CONFIG.copy()
        
        sp.CONFIG['stock_code'] = stock_code
        sp.CONFIG['market'] = market
        sp.CONFIG['train_days'] = train_days
        
        # 运行训练主流程
        result = sp.main()
        
        # 恢复配置
        sp.CONFIG = original_config
        
        return result is not None
        
    except Exception as e:
        print(f"[错误] 训练失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_models(stock_code: str, market: str, model_dir: str = './models'):
    """加载训练好的模型"""
    predictor = DualPricePredictor()
    
    # 尝试从指定目录加载
    high_model_path = Path(model_dir) / f"model_{stock_code}_{market}_high.json"
    low_model_path = Path(model_dir) / f"model_{stock_code}_{market}_low.json"
    
    # 如果不存在，尝试当前目录
    if not high_model_path.exists():
        high_model_path = Path(f"model_{stock_code}_{market}_high.json")
    if not low_model_path.exists():
        low_model_path = Path(f"model_{stock_code}_{market}_low.json")
    
    if not high_model_path.exists() or not low_model_path.exists():
        return None
    
    try:
        # 使用文件所在目录
        load_dir = str(high_model_path.parent)
        predictor.load(stock_code, market, load_dir)
        print(f"[状态] 模型加载成功")
        
        return predictor
    except Exception as e:
        print(f"[错误] 加载模型失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def predict_single_stock(stock_info: Dict, config: Dict, notifier: FeishuNotifier = None) -> Dict:
    """
    为单只股票生成预测
    
    Returns:
        交易信号字典，如果失败则返回 None
    """
    stock_code = stock_info['code']
    market = stock_info['market']
    name = stock_info.get('name', '')
    
    print(f"\n{'='*60}")
    print(f"[预测] {name} ({stock_code}.{market.upper()})")
    print(f"{'='*60}")
    
    # 检查模型
    if not check_model_exists(stock_code, market, config['model_dir']):
        print(f"[状态] 模型不存在，开始训练...")
        if not train_model_for_stock(stock_info, config['train_days']):
            error_msg = f"{name}({stock_code}) 模型训练失败"
            print(f"[错误] {error_msg}")
            if notifier:
                notifier.send_error(error_msg)
            return None
    
    # 加载模型
    predictor = load_models(stock_code, market, config['model_dir'])
    if predictor is None:
        error_msg = f"{name}({stock_code}) 模型加载失败"
        print(f"[错误] {error_msg}")
        if notifier:
            notifier.send_error(error_msg)
        return None
    
    print(f"[状态] 模型加载成功")
    
    # 获取最新数据
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=60)
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')
    
    print(f"[数据] 获取行情数据...")
    df = fetch_data(stock_code, market, start_str, end_str)
    
    if df.empty:
        error_msg = f"{name}({stock_code}) 数据获取失败"
        print(f"[错误] {error_msg}")
        if notifier:
            notifier.send_error(error_msg)
        return None
    
    # 特征工程
    df = create_features(df)
    _, _, _, feature_cols, _ = prepare_data(df, target_col='high')
    
    # 初始化风控
    risk_cfg = config['risk_control']
    risk_ctrl = RiskController(**risk_cfg)
    signal_gen = TradingSignalGenerator(risk_ctrl)
    
    # 生成信号
    signal = generate_trading_signal(
        predictor, df, feature_cols, stock_code, market, risk_ctrl, signal_gen
    )
    
    # 添加股票名称
    signal['stock_name'] = name
    
    # 打印信号
    print(f"\n[信号]")
    print(f"  操作建议: {signal['action']}")
    print(f"  预测区间: [{signal['predicted_low']:.2f}, {signal['predicted_high']:.2f}]")
    print(f"  风险等级: {signal['risk_check'].risk_level.value}")
    print(f"  能否交易: {'是' if signal['risk_check'].can_trade else '否'}")
    
    return signal


def predict_all_stocks(config: Dict, target_code: str = None, force_retrain: bool = False, notify: bool = False) -> List[Dict]:
    """
    预测所有配置的股票
    
    Args:
        config: 配置字典
        target_code: 如果指定，只预测这只股票
        force_retrain: 强制重新训练
        notify: 是否发送飞书通知
    
    Returns:
        交易信号列表
    """
    # 初始化飞书通知
    notifier = FeishuNotifier() if notify else None
    
    # 获取要监控的股票列表
    watchlist = config['watchlist']
    if target_code:
        watchlist = [s for s in watchlist if s['code'] == target_code]
        if not watchlist:
            print(f"[错误] 未找到股票 {target_code}")
            return []
    
    print(f"\n{'='*60}")
    print(f"实时预测脚本 v2.5")
    print(f"监控股票: {len(watchlist)} 只")
    print(f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # 如果需要重新训练
    if force_retrain:
        print(f"\n[模式] 强制重新训练模型")
        for stock_info in watchlist:
            train_model_for_stock(stock_info, config['train_days'])
    
    # 逐个预测
    all_signals = []
    for stock_info in watchlist:
        signal = predict_single_stock(stock_info, config, notifier)
        if signal:
            all_signals.append(signal)
    
    # 汇总
    print(f"\n{'='*60}")
    print(f"预测汇总")
    print(f"{'='*60}")
    print(f"成功: {len(all_signals)}/{len(watchlist)} 只股票")
    
    for signal in all_signals:
        emoji = "🟢" if signal['action'] == 'BUY' else "🔴" if signal['action'] == 'SELL' else "⚪"
        print(f"  {emoji} {signal['stock_name']}({signal['stock_code']}): {signal['action']} | "
              f"区间[{signal['predicted_low']:.2f}, {signal['predicted_high']:.2f}]")
    
    # 发送飞书通知
    if notifier and all_signals:
        print(f"\n[飞书] 发送通知...")
        # 发送汇总
        notifier.send_daily_summary(all_signals)
        # 发送每个股票的详细信号
        for signal in all_signals:
            # 查找对应的 predictor
            stock_code = signal['stock_code'].split('.')[0]
            market = signal['stock_code'].split('.')[1].lower()
            predictor = load_models(stock_code, market, config['model_dir'])
            notifier.send_signal(signal, predictor)
    
    return all_signals


def save_signals_to_file(signals: List[Dict], output_dir: str = './signals'):
    """保存所有信号到文件"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    today = datetime.datetime.now().strftime('%Y%m%d')
    
    for signal in signals:
        stock_code = signal['stock_code'].replace('.', '_')
        filename = output_path / f"{today}_{stock_code}.json"
        
        # 转换信号为可序列化格式
        signal_data = {
            'timestamp': signal['timestamp'].isoformat() if hasattr(signal['timestamp'], 'isoformat') else str(signal['timestamp']),
            'stock_code': signal['stock_code'],
            'stock_name': signal.get('stock_name', ''),
            'current_price': float(signal['current_price']),
            'predicted_high': float(signal['predicted_high']),
            'predicted_low': float(signal['predicted_low']),
            'action': signal['action'],
            'message': signal['message'],
            'expected_returns': {
                'high': float(signal['expected_returns']['high']),
                'low': float(signal['expected_returns']['low']),
            },
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(signal_data, f, ensure_ascii=False, indent=2)
        
        print(f"[保存] {signal['stock_code']} -> {filename}")


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description='实时预测脚本 v2.5 - 多股票监控')
    parser.add_argument('--code', type=str, help='指定股票代码（如 601166）')
    parser.add_argument('--retrain', action='store_true', help='强制重新训练模型')
    parser.add_argument('--notify', action='store_true', help='发送飞书通知')
    parser.add_argument('--add-stock', nargs=3, metavar=('CODE', 'MARKET', 'NAME'),
                        help='添加新股票到监控列表')
    parser.add_argument('--list-stocks', action='store_true', help='显示监控列表')
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config()
    
    # 添加新股票
    if args.add_stock:
        code, market, name = args.add_stock
        new_stock = {'code': code, 'market': market, 'name': name}
        config['watchlist'].append(new_stock)
        save_config(config)
        print(f"[配置] 已添加 {name}({code}) 到监控列表")
        return
    
    # 显示监控列表
    if args.list_stocks:
        print("\n当前监控的股票列表:")
        for i, stock in enumerate(config['watchlist'], 1):
            print(f"  {i}. {stock['name']} ({stock['code']}.{stock['market'].upper()})")
        return
    
    # 执行预测
    signals = predict_all_stocks(
        config=config,
        target_code=args.code,
        force_retrain=args.retrain,
        notify=args.notify
    )
    
    # 保存信号
    if signals:
        save_signals_to_file(signals, config['output_dir'])
        print(f"\n[完成] 共生成 {len(signals)} 个交易信号")
        return 0
    else:
        print(f"\n[警告] 未生成任何信号")
        return 1


if __name__ == '__main__':
    sys.exit(main())

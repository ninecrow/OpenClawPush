#!/usr/bin/env python3
"""
每日定时任务脚本
自动运行选股并将结果推送到飞书
"""
import sys
import os
from datetime import datetime

# 添加脚本目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stock_screener import (
    strategy_hot_stocks,
    strategy_oversold_bounce, 
    strategy_breakout,
    strategy_value_stocks,
    generate_screening_report
)
from message_pusher import load_webhooks_from_env


def run_daily_screening():
    """
    运行每日选股任务
    """
    print(f"\n{'='*60}")
    print(f"每日选股任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # 加载消息推送配置
    try:
        pusher = load_webhooks_from_env()
    except Exception as e:
        print(f"加载推送配置失败: {e}")
        print("请设置环境变量 FEISHU_WEBHOOK 或 DINGTALK_WEBHOOK")
        return
    
    # 1. 热点股策略
    print("[1/4] 运行热点股策略...")
    try:
        hot_stocks = strategy_hot_stocks()
        if hot_stocks:
            report = generate_screening_report(hot_stocks, "🔥 今日热点股")
            print(report)
            pusher.send_screening_result(hot_stocks, "🔥 今日热点股")
        else:
            msg = "📊 今日无热点股"
            print(msg)
            pusher.send(msg)
    except Exception as e:
        print(f"热点股策略失败: {e}")
    
    # 2. 超跌反弹策略
    print("[2/4] 运行超跌反弹策略...")
    try:
        oversold = strategy_oversold_bounce()
        if oversold:
            report = generate_screening_report(oversold, "📉 超跌反弹机会")
            print(report)
            pusher.send_screening_result(oversold, "📉 超跌反弹机会")
        else:
            print("暂无超跌反弹标的")
    except Exception as e:
        print(f"超跌反弹策略失败: {e}")
    
    # 3. 突破策略
    print("[3/4] 运行突破策略...")
    try:
        breakout = strategy_breakout()
        if breakout:
            report = generate_screening_report(breakout, "🚀 突破新高")
            print(report)
            pusher.send_screening_result(breakout, "🚀 突破新高")
        else:
            print("暂无突破标的")
    except Exception as e:
        print(f"突破策略失败: {e}")
    
    # 4. 价值股策略
    print("[4/4] 运行价值股策略...")
    try:
        value = strategy_value_stocks()
        if value:
            report = generate_screening_report(value, "💎 价值股")
            print(report)
            pusher.send_screening_result(value, "💎 价值股")
        else:
            print("暂无价值股标的")
    except Exception as e:
        print(f"价值股策略失败: {e}")
    
    print(f"\n{'='*60}")
    print("选股任务完成")
    print(f"{'='*60}\n")


def run_market_summary():
    """
    推送市场 summary
    """
    from fetch_sina_data import fetch_stock_data
    
    print("获取市场概况...")
    
    # 获取主要指数
    indices = ["sh000001", "sz399001", "sz399006"]
    data = fetch_stock_data(indices)
    
    message = f"📊 市场概况 ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n"
    
    for code, info in data.items():
        if "error" not in info:
            emoji = "📈" if info['change_percent'] > 0 else "📉"
            name = info['name']
            price = info['price']
            change = info['change_percent']
            message += f"{emoji} {name}: {price:.2f} ({change:+.2f}%)\n"
    
    pusher = load_webhooks_from_env()
    pusher.send(message)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='每日股票定时任务')
    parser.add_argument('--task', choices=['screening', 'market', 'all'], 
                       default='all', help='任务类型')
    
    args = parser.parse_args()
    
    if args.task in ['screening', 'all']:
        run_daily_screening()
    
    if args.task in ['market', 'all']:
        run_market_summary()

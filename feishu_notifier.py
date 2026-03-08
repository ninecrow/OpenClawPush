#!/usr/bin/env python3
"""
飞书推送模块 - Feishu Notification Module
支持群机器人 webhook 推送交易信号
"""

import json
import requests
from datetime import datetime
from typing import Dict, Optional
import os


class FeishuNotifier:
    """
    飞书群机器人推送器
    
    使用方法：
        1. 在飞书群中添加自定义机器人
        2. 复制 webhook URL
        3. 设置环境变量 FEISHU_WEBHOOK_URL
        4. 调用 send_signal() 推送消息
    """
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        初始化
        
        Args:
            webhook_url: 飞书机器人 webhook 地址，如果不传则从环境变量获取
        """
        self.webhook_url = webhook_url or os.getenv('FEISHU_WEBHOOK_URL')
        self.enabled = self.webhook_url is not None and self.webhook_url.startswith('https://')
        
        if not self.enabled:
            print("[飞书推送] 未配置 webhook，请设置 FEISHU_WEBHOOK_URL 环境变量")
    
    def _send_request(self, payload: Dict) -> bool:
        """发送请求到飞书"""
        if not self.enabled:
            return False
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') == 0:
                print("[飞书推送] 消息发送成功")
                return True
            else:
                print(f"[飞书推送] 发送失败: {result.get('msg')}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"[飞书推送] 请求失败: {e}")
            return False
        except Exception as e:
            print(f"[飞书推送] 错误: {e}")
            return False
    
    def send_text(self, text: str) -> bool:
        """发送纯文本消息"""
        payload = {
            "msg_type": "text",
            "content": {
                "text": text
            }
        }
        return self._send_request(payload)
    
    def send_rich_text(self, title: str, content: list) -> bool:
        """发送富文本消息（支持颜色、链接等）"""
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": content
                    }
                }
            }
        }
        return self._send_request(payload)
    
    def send_signal(self, signal: Dict, predictor=None) -> bool:
        """
        发送交易信号通知
        
        Args:
            signal: 交易信号字典
            predictor: 预测器对象（可选，用于显示模型误差）
        """
        if not self.enabled:
            print("[飞书推送] 未启用，跳过发送")
            return False
        
        # 确定颜色
        action = signal.get('action', 'HOLD')
        if action == 'BUY':
            title = "🟢 买入信号"
        elif action == 'SELL':
            title = "🔴 卖出信号"
        else:
            title = "⚪ 观望信号"
        
        # 构建富文本内容
        content = [
            # 股票信息
            [
                {"tag": "text", "text": f"股票代码: "},
                {"tag": "text", "text": signal['stock_code'], "style": {"bold": True}}
            ],
            [
                {"tag": "text", "text": f"当前价格: "},
                {"tag": "text", "text": f"{signal['current_price']:.2f}", "style": {"bold": True}}
            ],
            # 预测区间
            [
                {"tag": "text", "text": f"预测最高价: {signal['predicted_high']:.2f}\n"},
                {"tag": "text", "text": f"预测最低价: {signal['predicted_low']:.2f}\n"},
                {"tag": "text", "text": f"预测区间: [{signal['predicted_low']:.2f}, {signal['predicted_high']:.2f}]"}
            ],
            # 预期收益
            [
                {"tag": "text", "text": f"预期最高收益: "},
                {"tag": "text", "text": f"{signal['expected_returns']['high']:.2%}", 
                 "style": {"color": "green" if signal['expected_returns']['high'] > 0 else "red"}}
            ],
            [
                {"tag": "text", "text": f"预期最低亏损: "},
                {"tag": "text", "text": f"{signal['expected_returns']['low']:.2%}",
                 "style": {"color": "red" if signal['expected_returns']['low'] < 0 else "green"}}
            ],
            # 操作建议
            [
                {"tag": "text", "text": f"操作建议: "},
                {"tag": "text", "text": signal['action'], "style": {"bold": True, "color": self._get_action_color(action)}}
            ],
            [
                {"tag": "text", "text": signal['message']}
            ],
            # 风控信息
            [
                {"tag": "text", "text": f"\n风险等级: {signal['risk_check'].risk_level.value if hasattr(signal['risk_check'], 'risk_level') else signal['risk_check'].get('risk_level', '未知')}"},
            ],
            [
                {"tag": "text", "text": f"能否交易: {'✅ 是' if (signal['risk_check'].can_trade if hasattr(signal['risk_check'], 'can_trade') else signal['risk_check'].get('can_trade')) else '❌ 否'}"}
            ],
            [
                {"tag": "text", "text": f"建议仓位: "},
                {"tag": "text", "text": f"{(signal['risk_check'].suggested_position if hasattr(signal['risk_check'], 'suggested_position') else signal['risk_check'].get('suggested_position', 0)):.0%}", "style": {"bold": True}}
            ],
            # 止损止盈
            [
                {"tag": "text", "text": f"止损价: {signal['risk_check'].stop_loss_price if hasattr(signal['risk_check'], 'stop_loss_price') else signal['risk_check'].get('stop_loss_price', 0):.2f}"}
            ],
            [
                {"tag": "text", "text": f"止盈价: {signal['risk_check'].take_profit_price if hasattr(signal['risk_check'], 'take_profit_price') else signal['risk_check'].get('take_profit_price', 0):.2f}"}
            ],
        ]
        
        # 添加模型误差信息（如果有）
        if predictor and predictor.high_rmse and predictor.low_rmse:
            content.append([
                {"tag": "text", "text": f"\n📊 模型误差参考:\n"}
            ])
            content.append([
                {"tag": "text", "text": f"最高价预测 RMSE: {predictor.high_rmse:.4f}\n"}
            ])
            content.append([
                {"tag": "text", "text": f"最低价预测 RMSE: {predictor.low_rmse:.4f}"}
            ])
        
        # 添加时间戳
        content.append([
            {"tag": "text", "text": f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "style": {"italic": True, "color": "gray"}}
        ])
        
        return self.send_rich_text(title, content)
    
    def _get_action_color(self, action: str) -> str:
        """获取操作对应的颜色"""
        colors = {
            'BUY': 'green',
            'SELL': 'red',
            'HOLD': 'gray',
            'BLOCKED': 'orange'
        }
        return colors.get(action, 'black')
    
    def send_daily_summary(self, signals: list) -> bool:
        """
        发送每日汇总消息
        
        Args:
            signals: 多只股票的交易信号列表
        """
        if not self.enabled or not signals:
            return False
        
        title = f"📈 每日交易信号汇总 ({datetime.now().strftime('%Y-%m-%d')})"
        
        content = []
        
        for signal in signals:
            action = signal.get('action', 'HOLD')
            emoji = "🟢" if action == 'BUY' else "🔴" if action == 'SELL' else "⚪"
            
            content.append([
                {"tag": "text", "text": f"{emoji} "},
                {"tag": "text", "text": signal['stock_code'], "style": {"bold": True}},
                {"tag": "text", "text": f" | 当前: {signal['current_price']:.2f} | "},
                {"tag": "text", "text": f"预测: [{signal['predicted_low']:.2f}, {signal['predicted_high']:.2f}] | "},
                {"tag": "text", "text": action, "style": {"bold": True, "color": self._get_action_color(action)}}
            ])
        
        return self.send_rich_text(title, content)
    
    def send_error(self, error_message: str) -> bool:
        """发送错误通知"""
        title = "❌ 预测脚本错误"
        content = [
            [{"tag": "text", "text": error_message, "style": {"color": "red"}}],
            [{"tag": "text", "text": f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "style": {"italic": True, "color": "gray"}}]
        ]
        return self.send_rich_text(title, content)


# ============== 测试代码 ==============

def test():
    """测试飞书推送"""
    
    # 检查环境变量
    webhook = os.getenv('FEISHU_WEBHOOK_URL')
    
    if not webhook:
        print("请设置 FEISHU_WEBHOOK_URL 环境变量")
        print("示例: export FEISHU_WEBHOOK_URL='https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx'")
        return
    
    notifier = FeishuNotifier(webhook)
    
    # 测试文本消息
    print("\n[测试1] 发送文本消息...")
    notifier.send_text("测试消息：股票预测系统已启动")
    
    # 测试交易信号
    print("\n[测试2] 发送交易信号...")
    test_signal = {
        'stock_code': '601166.SH',
        'current_price': 18.50,
        'predicted_high': 19.20,
        'predicted_low': 18.30,
        'action': 'BUY',
        'message': '建议买入，预期收益 3.78%',
        'expected_returns': {
            'high': 0.0378,
            'low': -0.0108
        },
        'risk_check': type('obj', (object,), {
            'risk_level': type('obj', (object,), {'value': '安全'})(),
            'can_trade': True,
            'suggested_position': 0.25,
            'stop_loss_price': 17.95,
            'take_profit_price': 19.01
        })
    }
    notifier.send_signal(test_signal)
    
    print("\n测试完成")


if __name__ == '__main__':
    test()

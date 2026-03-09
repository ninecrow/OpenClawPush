"""
消息推送模块
支持飞书、钉钉、企业微信消息推送
"""
import requests
import json
from datetime import datetime
from typing import Optional, Dict, List
import os

class MessagePusher:
    """
    消息推送器
    
    支持多平台消息推送，可推送文本、Markdown、卡片消息
    """
    
    def __init__(self):
        self.webhooks = {}
    
    def set_feishu_webhook(self, webhook_url: str, secret: Optional[str] = None):
        """
        设置飞书 webhook
        
        Args:
            webhook_url: 飞书机器人 webhook 地址
            secret: 签名密钥（可选）
        """
        self.webhooks['feishu'] = {
            'url': webhook_url,
            'secret': secret
        }
    
    def set_dingtalk_webhook(self, webhook_url: str, secret: Optional[str] = None):
        """
        设置钉钉 webhook
        
        Args:
            webhook_url: 钉钉机器人 webhook 地址
            secret: 签名密钥（可选）
        """
        self.webhooks['dingtalk'] = {
            'url': webhook_url,
            'secret': secret
        }
    
    def set_wecom_webhook(self, webhook_url: str):
        """
        设置企业微信 webhook
        
        Args:
            webhook_url: 企业微信机器人 webhook 地址
        """
        self.webhooks['wecom'] = {
            'url': webhook_url
        }
    
    def _send_feishu(self, message: str, msg_type: str = "text") -> bool:
        """发送飞书消息"""
        if 'feishu' not in self.webhooks:
            print("错误: 未设置飞书 webhook")
            return False
        
        webhook = self.webhooks['feishu']
        url = webhook['url']
        
        # 构造消息体
        if msg_type == "text":
            payload = {
                "msg_type": "text",
                "content": {
                    "text": message
                }
            }
        elif msg_type == "markdown":
            payload = {
                "msg_type": "interactive",
                "card": {
                    "config": {"wide_screen_mode": True},
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": "📊 股票分析推送"
                        },
                        "template": "blue"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": message
                            }
                        }
                    ]
                }
            }
        else:
            payload = {"msg_type": "text", "content": {"text": message}}
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            if result.get('code') == 0:
                print(f"✓ 飞书消息发送成功")
                return True
            else:
                print(f"✗ 飞书消息发送失败: {result.get('msg')}")
                return False
        except Exception as e:
            print(f"✗ 飞书消息发送异常: {e}")
            return False
    
    def _send_dingtalk(self, message: str, msg_type: str = "text") -> bool:
        """发送钉钉消息"""
        if 'dingtalk' not in self.webhooks:
            print("错误: 未设置钉钉 webhook")
            return False
        
        webhook = self.webhooks['dingtalk']
        url = webhook['url']
        secret = webhook.get('secret')
        
        # 如果需要签名
        if secret:
            import time
            import hmac
            import hashlib
            import base64
            import urllib.parse
            
            timestamp = str(round(time.time() * 1000))
            string_to_sign = f"{timestamp}\n{secret}"
            hmac_code = hmac.new(secret.encode('utf-8'), string_to_sign.encode('utf-8'), digestmod=hashlib.sha256).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
            url = f"{url}&timestamp={timestamp}&sign={sign}"
        
        # 构造消息体
        if msg_type == "markdown":
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "股票分析推送",
                    "text": message
                }
            }
        else:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            if result.get('errcode') == 0:
                print(f"✓ 钉钉消息发送成功")
                return True
            else:
                print(f"✗ 钉钉消息发送失败: {result.get('errmsg')}")
                return False
        except Exception as e:
            print(f"✗ 钉钉消息发送异常: {e}")
            return False
    
    def _send_wecom(self, message: str, msg_type: str = "text") -> bool:
        """发送企业微信消息"""
        if 'wecom' not in self.webhooks:
            print("错误: 未设置企业微信 webhook")
            return False
        
        webhook = self.webhooks['wecom']
        url = webhook['url']
        
        if msg_type == "markdown":
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": message
                }
            }
        else:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": message
                }
            }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            if result.get('errcode') == 0:
                print(f"✓ 企业微信消息发送成功")
                return True
            else:
                print(f"✗ 企业微信消息发送失败: {result.get('errmsg')}")
                return False
        except Exception as e:
            print(f"✗ 企业微信消息发送异常: {e}")
            return False
    
    def send(self, message: str, platform: Optional[str] = None, msg_type: str = "text") -> Dict[str, bool]:
        """
        发送消息
        
        Args:
            message: 消息内容
            platform: 指定平台 ('feishu', 'dingtalk', 'wecom')，None表示发送到所有已配置平台
            msg_type: 消息类型 ('text', 'markdown')
        
        Returns:
            Dict: 各平台发送结果
        """
        results = {}
        
        platforms = [platform] if platform else list(self.webhooks.keys())
        
        for p in platforms:
            if p == 'feishu':
                results[p] = self._send_feishu(message, msg_type)
            elif p == 'dingtalk':
                results[p] = self._send_dingtalk(message, msg_type)
            elif p == 'wecom':
                results[p] = self._send_wecom(message, msg_type)
        
        return results
    
    def send_stock_analysis(self, stock_code: str, stock_name: str, 
                           price: float, change: float, 
                           signals: Dict, platform: Optional[str] = None):
        """
        发送股票分析消息（格式化）
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            price: 当前价格
            change: 涨跌幅
            signals: 技术信号字典
            platform: 指定平台
        """
        emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        change_str = f"+{change:.2f}%" if change > 0 else f"{change:.2f}%"
        
        # 获取MACD和RSI信号
        macd_signal = signals.get('MACD', {}).get('信号', '维持')
        rsi_status = signals.get('RSI', {}).get('状态', '正常')
        rsi_value = signals.get('RSI', {}).get('RSI(14)', 50)
        
        message = f"""{emoji} {stock_name} ({stock_code}) 技术分析

💰 当前价格: {price:.2f} ({change_str})

📊 技术指标:
• MACD: {macd_signal}
• RSI(14): {rsi_value:.1f} ({rsi_status})
• MA趋势: {signals.get('移动平均线', {}).get('MA5', 0):.2f} / {signals.get('移动平均线', {}).get('MA20', 0):.2f}

⚠️ 免责声明: 本分析仅供参考，不构成投资建议

发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        return self.send(message, platform, msg_type="text")
    
    def send_screening_result(self, results: List[Dict], strategy_name: str, 
                             platform: Optional[str] = None):
        """
        发送选股结果
        
        Args:
            results: 选股结果列表
            strategy_name: 策略名称
            platform: 指定平台
        """
        if not results:
            message = f"📋 {strategy_name}\n\n未筛选出符合条件的股票"
        else:
            message = f"📋 {strategy_name}\n共筛选出 {len(results)} 只股票\n\n"
            
            for i, stock in enumerate(results[:10], 1):  # 只显示前10只
                emoji = "📈" if stock['change'] > 0 else "📉"
                message += f"{i}. {emoji} {stock['name']} ({stock['code']}): {stock['price']:.2f} ({stock['change']:+.2f}%)\n"
            
            if len(results) > 10:
                message += f"\n... 等共 {len(results)} 只股票"
        
        message += f"\n\n发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return self.send(message, platform, msg_type="text")
    
    def send_backtest_report(self, result: Dict, strategy_name: str,
                            platform: Optional[str] = None):
        """
        发送回测报告摘要
        
        Args:
            result: 回测结果
            strategy_name: 策略名称
            platform: 指定平台
        """
        total_return = result.get('total_return', 0)
        emoji = "🟢" if total_return > 0 else "🔴"
        
        message = f"""{emoji} {strategy_name} 回测报告

💰 初始资金: {result.get('initial_capital', 0):,.0f} 元
📈 最终资产: {result.get('final_value', 0):,.0f} 元
📊 总收益率: {total_return:.2f}%
📉 最大回撤: {result.get('max_drawdown', 0):.2f}%
⚖️ 夏普比率: {result.get('sharpe_ratio', 0):.2f}
🎯 胜率: {result.get('win_rate', 0):.1f}%

📋 交易统计:
总交易次数: {result.get('trade_count', 0)} 次

发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        return self.send(message, platform, msg_type="text")


def load_webhooks_from_env() -> MessagePusher:
    """
    从环境变量加载 webhook 配置
    
    环境变量:
    - FEISHU_WEBHOOK: 飞书 webhook URL
    - FEISHU_SECRET: 飞书签名密钥（可选）
    - DINGTALK_WEBHOOK: 钉钉 webhook URL
    - DINGTALK_SECRET: 钉钉签名密钥（可选）
    - WECOM_WEBHOOK: 企业微信 webhook URL
    """
    pusher = MessagePusher()
    
    # 飞书
    feishu_url = os.getenv('FEISHU_WEBHOOK')
    if feishu_url:
        feishu_secret = os.getenv('FEISHU_SECRET')
        pusher.set_feishu_webhook(feishu_url, feishu_secret)
        print(f"已加载飞书 webhook")
    
    # 钉钉
    dingtalk_url = os.getenv('DINGTALK_WEBHOOK')
    if dingtalk_url:
        dingtalk_secret = os.getenv('DINGTALK_SECRET')
        pusher.set_dingtalk_webhook(dingtalk_url, dingtalk_secret)
        print(f"已加载钉钉 webhook")
    
    # 企业微信
    wecom_url = os.getenv('WECOM_WEBHOOK')
    if wecom_url:
        pusher.set_wecom_webhook(wecom_url)
        print(f"已加载企业微信 webhook")
    
    return pusher


if __name__ == "__main__":
    print("消息推送模块")
    print("\n使用示例:")
    print("""
    # 方式1: 手动配置
    pusher = MessagePusher()
    pusher.set_feishu_webhook("https://open.feishu.cn/xxx")
    pusher.send("测试消息")
    
    # 方式2: 从环境变量加载
    pusher = load_webhooks_from_env()
    pusher.send("测试消息")
    
    # 发送股票分析
    pusher.send_stock_analysis("600519", "贵州茅台", 1500.0, 2.5, signals)
    
    # 发送选股结果
    pusher.send_screening_result(results, "热点股策略")
    """)
    
    print("\n环境变量配置:")
    print("  export FEISHU_WEBHOOK='https://open.feishu.cn/...'")
    print("  export DINGTALK_WEBHOOK='https://oapi.dingtalk.com/...'")
    print("  export WECOM_WEBHOOK='https://qyapi.weixin.qq.com/...'")

"""
风险控制模块 - Risk Control Module
解决涨停崩盘问题，提供完整的交易决策过滤系统
"""

import numpy as np
import pandas as pd
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict
import warnings
warnings.filterwarnings('ignore')


class RiskLevel(Enum):
    """风险等级"""
    SAFE = "安全"           # 可以正常交易
    CAUTION = "谨慎"        # 可以交易但需小心
    WARNING = "警告"        # 建议观望
    DANGER = "危险"         # 禁止交易


@dataclass
class RiskCheckResult:
    """风险检查结果"""
    can_trade: bool                    # 是否允许交易
    risk_level: RiskLevel              # 风险等级
    reason: str                        # 原因说明
    details: Dict                      # 详细数据
    suggested_position: float          # 建议仓位 (0-1)
    stop_loss_price: Optional[float]   # 建议止损价
    take_profit_price: Optional[float] # 建议止盈价


class RiskController:
    """
    交易风险控制器
    
    核心功能：
    1. 涨停/跌停检测 - 避免无法成交的情况
    2. 波动率监控 - 识别异常波动
    3. 模型置信度评估 - 预测可靠性判断
    4. 仓位管理 - 根据风险动态调整
    5. 止损止盈建议 - 保护性价位计算
    """
    
    def __init__(self, 
                 max_daily_return: float = 0.095,      # 单日最大涨幅限制 (9.5%, 接近涨停)
                 max_daily_drop: float = -0.095,       # 单日最大跌幅限制 (-9.5%)
                 volatility_threshold: float = 2.0,    # 波动率异常阈值 (倍数)
                 min_confidence: float = 0.6,          # 最低模型置信度
                 max_position: float = 0.3,            # 最大仓位 (30%)
                 stop_loss_pct: float = 0.03,          # 止损比例 (3%)
                 take_profit_pct: float = 0.05):       # 止盈比例 (5%)
        
        self.max_daily_return = max_daily_return
        self.max_daily_drop = max_daily_drop
        self.volatility_threshold = volatility_threshold
        self.min_confidence = min_confidence
        self.max_position = max_position
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        # 历史波动率记录 (用于计算平均波动率)
        self.volatility_history: List[float] = []
        self.max_history_size = 60  # 保存60天历史
    
    def update_volatility_history(self, volatility: float):
        """更新历史波动率记录"""
        self.volatility_history.append(volatility)
        if len(self.volatility_history) > self.max_history_size:
            self.volatility_history.pop(0)
    
    def get_avg_volatility(self) -> float:
        """获取平均波动率"""
        if len(self.volatility_history) < 20:
            return np.mean(self.volatility_history) if self.volatility_history else 0.02
        return np.mean(self.volatility_history[-20:])
    
    def check_limit_up_down(self, 
                           current_price: float, 
                           predicted_high: float,
                           predicted_low: float,
                           last_close: float) -> Tuple[bool, str, Dict]:
        """
        检查涨停/跌停风险
        
        Returns:
            (是否安全, 原因, 详细数据)
        """
        # 计算预期涨跌幅
        expected_high_return = (predicted_high - last_close) / last_close
        expected_low_return = (predicted_low - last_close) / last_close
        
        details = {
            'expected_high_return': expected_high_return,
            'expected_low_return': expected_low_return,
            'last_close': last_close
        }
        
        # 检查是否接近涨停 (预期最高价涨幅过大)
        if expected_high_return > self.max_daily_return:
            return False, f"预测最高价涨幅 {expected_high_return:.2%} 接近涨停，可能无法买入", details
        
        # 检查是否接近跌停 (预期最低价跌幅过大)
        if expected_low_return < self.max_daily_drop:
            return False, f"预测最低价跌幅 {expected_low_return:.2%} 接近跌停，风险过高", details
        
        # 检查当前价格是否已涨停 (无法买入)
        current_return = (current_price - last_close) / last_close
        if current_return > 0.095:  # 已涨停
            return False, f"当前已涨停 ({current_return:.2%})，无法买入", details
        
        return True, "涨跌停检查通过", details
    
    def check_volatility(self, 
                        current_volatility: float,
                        atr: Optional[float] = None) -> Tuple[bool, str, Dict]:
        """
        检查波动率是否异常
        
        Args:
            current_volatility: 当前波动率
            atr: 平均真实波幅 (Average True Range)
        """
        avg_vol = self.get_avg_volatility()
        vol_ratio = current_volatility / (avg_vol + 1e-8)
        
        details = {
            'current_volatility': current_volatility,
            'avg_volatility': avg_vol,
            'volatility_ratio': vol_ratio,
            'atr': atr
        }
        
        # 波动率异常高
        if vol_ratio > self.volatility_threshold:
            return False, f"波动率异常 ({vol_ratio:.1f}倍于平均)，市场不稳定", details
        
        # 波动率异常低 (可能即将变盘)
        if vol_ratio < 0.3 and len(self.volatility_history) > 20:
            return True, f"波动率极低 ({vol_ratio:.1f}倍于平均)，注意变盘风险", details
        
        return True, "波动率正常", details
    
    def check_model_confidence(self,
                              prediction: float,
                              historical_predictions: List[float],
                              historical_actuals: List[float]) -> Tuple[bool, str, float, Dict]:
        """
        评估模型预测置信度
        
        基于最近预测准确率来评估当前预测的可靠性
        """
        details = {
            'prediction': prediction,
            'historical_count': len(historical_predictions)
        }
        
        if len(historical_predictions) < 10 or len(historical_actuals) < 10:
            return True, "历史数据不足，默认允许交易", 0.5, details
        
        # 计算最近10次预测的方向准确率
        recent_pred = historical_predictions[-10:]
        recent_actual = historical_actuals[-10:]
        
        direction_correct = 0
        for i in range(1, len(recent_pred)):
            pred_direction = np.sign(recent_pred[i] - recent_actual[i-1])
            actual_direction = np.sign(recent_actual[i] - recent_actual[i-1])
            if pred_direction == actual_direction:
                direction_correct += 1
        
        direction_accuracy = direction_correct / (len(recent_pred) - 1)
        
        # 计算最近预测误差
        errors = [abs(p - a) / a for p, a in zip(recent_pred, recent_actual)]
        avg_error = np.mean(errors)
        
        details['direction_accuracy'] = direction_accuracy
        details['avg_error'] = avg_error
        
        # 置信度 = 方向准确率 * (1 - 归一化误差)
        confidence = direction_accuracy * max(0, 1 - avg_error * 10)
        
        if confidence < self.min_confidence:
            return False, f"模型置信度 {confidence:.2%} 低于阈值 {self.min_confidence:.0%}", confidence, details
        
        return True, f"模型置信度 {confidence:.2%}", confidence, details
    
    def calculate_position_size(self,
                               risk_level: RiskLevel,
                               confidence: float,
                               volatility: float) -> float:
        """
        计算建议仓位大小
        
        Returns:
            仓位比例 (0-1)
        """
        base_position = {
            RiskLevel.SAFE: 1.0,
            RiskLevel.CAUTION: 0.6,
            RiskLevel.WARNING: 0.3,
            RiskLevel.DANGER: 0.0
        }
        
        # 基础仓位
        position = base_position.get(risk_level, 0.0)
        
        # 根据置信度调整
        position *= confidence
        
        # 根据波动率调整 (波动率越高，仓位越低)
        vol_factor = 1 / (1 + volatility * 10)
        position *= vol_factor
        
        # 限制最大仓位
        position = min(position, self.max_position)
        
        return round(position, 2)
    
    def calculate_protection_prices(self,
                                   entry_price: float,
                                   predicted_high: float,
                                   predicted_low: float) -> Tuple[float, float]:
        """
        计算止损价和止盈价
        
        Returns:
            (止损价, 止盈价)
        """
        # 止损价：买入价向下 3%，或预测最低价减去缓冲
        stop_loss = max(
            entry_price * (1 - self.stop_loss_pct),
            predicted_low * 0.98  # 预测最低价留 2% 缓冲
        )
        
        # 止盈价：买入价向上 5%，或预测最高价减去缓冲
        take_profit = min(
            entry_price * (1 + self.take_profit_pct),
            predicted_high * 0.98  # 预测最高价留 2% 缓冲
        )
        
        return round(stop_loss, 2), round(take_profit, 2)
    
    def evaluate_trade(self,
                      current_price: float,
                      predicted_high: float,
                      predicted_low: float,
                      last_close: float,
                      current_volatility: float,
                      historical_predictions: Optional[List[float]] = None,
                      historical_actuals: Optional[List[float]] = None) -> RiskCheckResult:
        """
        完整交易风险评估
        
        这是主要入口函数，整合所有风险检查
        """
        # 更新波动率历史
        self.update_volatility_history(current_volatility)
        
        details = {
            'current_price': current_price,
            'predicted_high': predicted_high,
            'predicted_low': predicted_low,
            'checks': {}
        }
        
        # 1. 检查涨停/跌停
        safe, reason, limit_details = self.check_limit_up_down(
            current_price, predicted_high, predicted_low, last_close
        )
        details['checks']['limit_up_down'] = {'safe': safe, 'reason': reason, **limit_details}
        
        if not safe:
            return RiskCheckResult(
                can_trade=False,
                risk_level=RiskLevel.DANGER,
                reason=reason,
                details=details,
                suggested_position=0.0,
                stop_loss_price=None,
                take_profit_price=None
            )
        
        # 2. 检查波动率
        safe, reason, vol_details = self.check_volatility(current_volatility)
        details['checks']['volatility'] = {'safe': safe, 'reason': reason, **vol_details}
        
        if not safe:
            return RiskCheckResult(
                can_trade=False,
                risk_level=RiskLevel.WARNING,
                reason=reason,
                details=details,
                suggested_position=0.0,
                stop_loss_price=None,
                take_profit_price=None
            )
        
        # 3. 检查模型置信度
        historical_predictions = historical_predictions or []
        historical_actuals = historical_actuals or []
        
        safe, reason, confidence, conf_details = self.check_model_confidence(
            predicted_high, historical_predictions, historical_actuals
        )
        details['checks']['confidence'] = {'safe': safe, 'reason': reason, **conf_details}
        
        # 4. 确定风险等级
        risk_level = RiskLevel.SAFE if safe else RiskLevel.CAUTION
        
        # 如果波动率偏低，提升风险等级
        if vol_details.get('volatility_ratio', 1) < 0.5:
            risk_level = RiskLevel.CAUTION
        
        # 5. 计算建议仓位
        position = self.calculate_position_size(risk_level, confidence, current_volatility)
        
        # 6. 计算保护价位
        stop_loss, take_profit = self.calculate_protection_prices(
            current_price, predicted_high, predicted_low
        )
        
        # 综合判断
        can_trade = position > 0.05  # 仓位大于5%才允许交易
        
        final_reason = f"风险等级: {risk_level.value}, 置信度: {confidence:.1%}, 建议仓位: {position:.0%}"
        
        return RiskCheckResult(
            can_trade=can_trade,
            risk_level=risk_level,
            reason=final_reason,
            details=details,
            suggested_position=position,
            stop_loss_price=stop_loss,
            take_profit_price=take_profit
        )


class TradingSignalGenerator:
    """
    交易信号生成器
    整合预测结果和风险控制，生成最终交易建议
    """
    
    def __init__(self, risk_controller: RiskController):
        self.risk_controller = risk_controller
        self.prediction_history: List[Dict] = []
    
    def generate_signal(self,
                       stock_code: str,
                       current_price: float,
                       predicted_high: float,
                       predicted_low: float,
                       last_close: float,
                       current_volatility: float,
                       features: Optional[Dict] = None) -> Dict:
        """
        生成完整交易信号
        """
        # 提取历史预测和实际值
        historical_preds = [p['predicted'] for p in self.prediction_history[-20:]]
        historical_actuals = [p['actual'] for p in self.prediction_history[-20:]]
        
        # 风险评估
        risk_result = self.risk_controller.evaluate_trade(
            current_price=current_price,
            predicted_high=predicted_high,
            predicted_low=predicted_low,
            last_close=last_close,
            current_volatility=current_volatility,
            historical_predictions=historical_preds,
            historical_actuals=historical_actuals
        )
        
        # 计算交易信号
        signal = {
            'stock_code': stock_code,
            'timestamp': pd.Timestamp.now(),
            'current_price': current_price,
            'predicted_high': predicted_high,
            'predicted_low': predicted_low,
            'risk_check': risk_result,
            'action': 'HOLD'  # 默认持仓不动
        }
        
        if not risk_result.can_trade:
            signal['action'] = 'BLOCKED'
            signal['message'] = f"交易被阻止: {risk_result.reason}"
        else:
            # 计算潜在收益率
            expected_return_high = (predicted_high - current_price) / current_price
            expected_return_low = (predicted_low - current_price) / current_price
            
            # T+0 策略：如果预期最高价有足够利润空间
            if expected_return_high > 0.02:  # 预期盈利 > 2%
                signal['action'] = 'BUY'
                signal['target_price'] = predicted_high * 0.99  # 目标卖出价
                signal['message'] = f"建议买入，目标价 {signal['target_price']:.2f}，预期收益 {expected_return_high:.2%}"
            elif expected_return_low < -0.02:  # 预期大跌
                signal['action'] = 'SELL'
                signal['message'] = f"建议卖出，预测最低价 {predicted_low:.2f}"
            else:
                signal['message'] = f"观望，预期波动区间 [{predicted_low:.2f}, {predicted_high:.2f}]"
        
        return signal
    
    def update_actual(self, actual_high: float, actual_low: float):
        """
        更新实际价格，用于后续评估模型准确性
        """
        if self.prediction_history:
            self.prediction_history[-1]['actual_high'] = actual_high
            self.prediction_history[-1]['actual_low'] = actual_low
    
    def record_prediction(self, predicted_high: float, predicted_low: float):
        """记录预测值"""
        self.prediction_history.append({
            'timestamp': pd.Timestamp.now(),
            'predicted_high': predicted_high,
            'predicted_low': predicted_low,
            'actual_high': None,
            'actual_low': None
        })


# ============== 使用示例 ==============

def demo():
    """风险控制模块使用示例"""
    
    # 初始化风险控制器
    risk_ctrl = RiskController(
        max_daily_return=0.095,    # 9.5% 涨幅限制
        max_daily_drop=-0.095,     # -9.5% 跌幅限制
        volatility_threshold=2.5,  # 波动率异常阈值
        min_confidence=0.55,       # 最低置信度 55%
        max_position=0.3,          # 最大仓位 30%
        stop_loss_pct=0.03,        # 止损 3%
        take_profit_pct=0.05       # 止盈 5%
    )
    
    # 场景 1：正常情况
    print("=" * 50)
    print("场景 1：正常交易")
    result = risk_ctrl.evaluate_trade(
        current_price=25.50,
        predicted_high=26.20,      # 预期涨 2.7%
        predicted_low=25.30,
        last_close=25.50,
        current_volatility=0.015,   # 1.5% 波动率
    )
    print(f"能否交易: {result.can_trade}")
    print(f"风险等级: {result.risk_level.value}")
    print(f"原因: {result.reason}")
    print(f"建议仓位: {result.suggested_position:.0%}")
    print(f"止损价: {result.stop_loss_price}")
    print(f"止盈价: {result.take_profit_price}")
    
    # 场景 2：涨停风险
    print("\n" + "=" * 50)
    print("场景 2：预测接近涨停")
    result = risk_ctrl.evaluate_trade(
        current_price=25.50,
        predicted_high=28.00,      # 预期涨 9.8%，接近涨停
        predicted_low=25.30,
        last_close=25.50,
        current_volatility=0.015,
    )
    print(f"能否交易: {result.can_trade}")
    print(f"风险等级: {result.risk_level.value}")
    print(f"原因: {result.reason}")
    
    # 场景 3：波动率异常
    print("\n" + "=" * 50)
    print("场景 3：波动率异常")
    # 先设置历史波动率
    for _ in range(20):
        risk_ctrl.update_volatility_history(0.01)  # 正常 1% 波动率
    
    result = risk_ctrl.evaluate_trade(
        current_price=25.50,
        predicted_high=26.20,
        predicted_low=25.30,
        last_close=25.50,
        current_volatility=0.035,   # 3.5% 波动率，是平均的 3.5 倍
    )
    print(f"能否交易: {result.can_trade}")
    print(f"原因: {result.reason}")
    print(f"当前波动率: {result.details['checks']['volatility']['current_volatility']:.2%}")
    print(f"平均波动率: {result.details['checks']['volatility']['avg_volatility']:.2%}")
    print(f"波动率比值: {result.details['checks']['volatility']['volatility_ratio']:.1f}x")
    
    # 场景 4：交易信号生成
    print("\n" + "=" * 50)
    print("场景 4：完整交易信号")
    
    signal_gen = TradingSignalGenerator(risk_ctrl)
    
    signal = signal_gen.generate_signal(
        stock_code='600754.SH',
        current_price=25.50,
        predicted_high=26.50,      # 预期涨 3.9%
        predicted_low=25.20,
        last_close=25.50,
        current_volatility=0.015,
    )
    
    print(f"股票: {signal['stock_code']}")
    print(f"当前价: {signal['current_price']}")
    print(f"操作建议: {signal['action']}")
    print(f"说明: {signal['message']}")
    print(f"建议仓位: {signal['risk_check'].suggested_position:.0%}")
    if signal['risk_check'].stop_loss_price:
        print(f"止损价: {signal['risk_check'].stop_loss_price}")
        print(f"止盈价: {signal['risk_check'].take_profit_price}")


if __name__ == '__main__':
    demo()

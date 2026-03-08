# 飞书推送配置说明

## 配置步骤

### 1. 创建飞书群机器人

1. 打开飞书，进入你想要接收通知的群聊
2. 点击群设置 → 群机器人 → 添加机器人
3. 选择 "自定义机器人"
4. 设置机器人名称（如"股票预警"）和描述
5. 复制 **Webhook 地址**

### 2. 设置环境变量

**Linux/Mac:**
```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxx"
```

**Windows PowerShell:**
```powershell
$env:FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxx"
```

**永久配置（推荐）:**

添加到 `~/.bashrc` 或 `~/.zshrc`:
```bash
echo 'export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxx"' >> ~/.bashrc
source ~/.bashrc
```

### 3. 测试飞书推送

```bash
python3 feishu_notifier.py
```

如果配置正确，你会在飞书群收到测试消息。

### 4. 运行带通知的预测

```bash
python3 realtime_predict_v2_5.py --notify
```

---

## 推送消息示例

**买入信号：**
```
🟢 买入信号
股票代码: 601166.SH
当前价格: 18.52
预测最高价: 19.20
预测最低价: 18.30
预测区间: [18.30, 19.20]
预期最高收益: 3.78%
预期最低亏损: -1.19%
操作建议: BUY
说明: 建议买入，预期收益 3.78%

风险等级: 安全
能否交易: ✅ 是
建议仓位: 25%
止损价: 17.95
止盈价: 19.01

模型误差参考:
  最高价预测 RMSE: 0.7626
  最低价预测 RMSE: 0.4799

⏰ 2026-03-08 09:30:00
```

---

## 设置定时推送

### Linux/Mac - Crontab

```bash
# 编辑 crontab
crontab -e

# 每天 9:00 开盘前推送
0 9 * * 1-5 cd /path/to/workspace && export FEISHU_WEBHOOK_URL="https://..." && python3 realtime_predict_v2_5.py --notify >> predict.log 2>&1

# 每天 14:30 盘中提醒
30 14 * * 1-5 cd /path/to/workspace && export FEISHU_WEBHOOK_URL="https://..." && python3 realtime_predict_v2_5.py --notify >> predict.log 2>&1
```

### Windows - 任务计划程序

1. 打开任务计划程序
2. 创建基本任务 → 名称"股票早盘提醒"
3. 触发器：每天 9:00，周一至周五
4. 操作：启动程序
5. 程序：`python.exe`
6. 参数：`realtime_predict_v2_5.py --notify`
7. 起始目录：`workspace` 目录
8. 在"条件"选项卡中设置环境变量 `FEISHU_WEBHOOK_URL`

---

## 项目文件说明

| 文件 | 功能 |
|------|------|
| `realtime_predict_v2_5.py` | 主程序（多股票 + 飞书推送） |
| `feishu_notifier.py` | 飞书推送模块 |
| `stock_predictor_v2_4_dual.py` | 双模型预测系统 |
| `risk_control.py` | 风险控制模块 |

---

## 监控股票配置

默认监控 2 只股票：
- **601166.SH** 兴业银行
- **300238.SZ** 冠昊生物

### 添加新股票

```bash
python3 realtime_predict_v2_5.py --add-stock 000001 sz 平安银行
```

### 查看监控列表

```bash
python3 realtime_predict_v2_5.py --list-stocks
```

---

## 常见问题

### Q: 飞书推送失败怎么办？
**A:** 
1. 检查 `FEISHU_WEBHOOK_URL` 环境变量是否设置
2. 检查 webhook URL 是否完整（以 `https://` 开头）
3. 检查网络是否能访问飞书服务器
4. 查看日志中的错误信息

### Q: 只想推送特定股票？
**A:**
```bash
python3 realtime_predict_v2_5.py --code 601166 --notify
```

### Q: 如何关闭推送？
**A:** 去掉 `--notify` 参数即可：
```bash
python3 realtime_predict_v2_5.py
```

### Q: 推送消息太长被截断？
**A:** 飞书单条消息有长度限制。如果信息过多，可以考虑：
1. 修改 `feishu_notifier.py` 精简消息内容
2. 分多条消息推送
3. 只推送关键信息（操作、价格、风控）

---

## 安全提示

⚠️ **Webhook URL 相当于群密钥，请妥善保管：**
- 不要上传到 GitHub
- 不要分享给他人
- 如果泄露，立即在飞书群中删除并重新创建机器人

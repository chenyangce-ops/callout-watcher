# Callout Watcher

Callout Watcher 会定时监控指定 X/Twitter 博主的新帖子，判断内容是否像交易喊单，命中后推送到 Telegram、Discord，或直接打印到控制台。

> 这个项目只做信息过滤和提醒，不构成投资建议。

## 功能

- 监控多个 X/Twitter 账号的新帖子
- 本地记录已处理帖子，重启后不重复提醒
- 支持规则判断，也支持 OpenAI 语义分类
- 支持 Telegram、Discord、控制台三种通知方式
- 可过滤回复和转推

## 环境要求

- Python 3.11 或更新版本
- X API Bearer Token，且账号权限支持读取用户时间线
- 可选：OpenAI API Key，用于更准确地判断“是否喊单”
- 可选：Telegram Bot 或 Discord Webhook，用于推送提醒

## 安装

1. 克隆项目并进入目录：

```powershell
git clone https://github.com/your-name/callout-watcher.git
cd callout-watcher
```

2. 创建虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. 安装依赖：

```powershell
pip install -r requirements.txt pytest
```

## 配置

复制配置模板：

```powershell
Copy-Item .env.example .env
Copy-Item config.example.yaml config.yaml
```

编辑 `.env`：

```env
X_BEARER_TOKEN=你的_X_API_Bearer_Token
OPENAI_API_KEY=可选，用于更准的语义判断
TELEGRAM_BOT_TOKEN=可选
TELEGRAM_CHAT_ID=可选
DISCORD_WEBHOOK_URL=可选
```

编辑 `config.yaml`，把 `accounts` 换成你要跟踪的博主：

```yaml
accounts:
  - username: example_blogger
    display_name: Example Blogger
  - username: another_blogger
    display_name: Another Blogger
```

## 通知方式

默认会打印到控制台：

```yaml
notifications:
  channel: console
```

发送到 Telegram：

```yaml
notifications:
  channel: telegram
```

发送到 Discord：

```yaml
notifications:
  channel: discord
```

## 使用

只跑一次：

```powershell
python -m callout_watcher.app --once
```

持续监控：

```powershell
python -m callout_watcher.app
```

指定配置文件：

```powershell
python -m callout_watcher.app --config config.yaml --state .data/state.json
```

## 只监控股票相关推文

如果不想读取某个账号的全部新推文，可以打开 `stock_search` 模式。程序会使用 X 搜索接口，只搜索该账号里命中股票关键词的公开推文：

```yaml
stock_search:
  enabled: true
  max_results: 10
  exclude_replies: true
  exclude_retweets: true
  keywords:
    - 股票
    - 美股
    - 财报
    - NVDA
    - TSLA
    - AAPL
    - MSFT
    - QQQ
```

这个模式会生成类似这样的 X 查询：

```text
from:WallStreet0Name (股票 OR 美股 OR 财报 OR NVDA OR TSLA OR AAPL OR MSFT OR QQQ) -is:reply -is:retweet
```

注意：这会减少无关推文读取，但仍然会调用 X API 并消耗 credits。X recent search 能搜索的历史范围取决于你的 API 权限。

## 历史推文分析

分析某个账号历史推文，并输出 Markdown 报告：

```powershell
python -m callout_watcher.analyze_history --username WallStreet0Name --output .data/WallStreet0Name-report.md --max-pages 10
```

同时输出 JSON 明细：

```powershell
python -m callout_watcher.analyze_history --username WallStreet0Name --output .data/WallStreet0Name-report.md --json-output .data/WallStreet0Name-report.json --max-pages 10
```

`--max-pages` 每页最多 100 条。X API 是否能返回完整历史取决于你的账号权限和接口限制；如果你要“全部历史”，可以把 `--max-pages` 调大，但最终以 X API 实际返回为准。

## 判断逻辑

有 `OPENAI_API_KEY` 时，程序优先让模型判断是否属于喊单；没有 key 或模型调用失败时，会退回到关键词规则。

规则会综合以下特征打分：

- 交易动作词，比如 `buy`、`long`、`开多`、`买入`、`止盈`
- 资产或币种词，比如 `BTC`、`ETH`、`SOL`
- 价格、百分比、目标位等数字表达
- 命令式表达，比如 `上车`、`entry`、`target`

阈值可以在 `config.yaml` 里调整：

```yaml
classification:
  confidence_threshold: 0.72
```

## 测试

```powershell
python -m pytest -q
```

## 数据文件

程序会把每个账号最后处理过的帖子 ID 存到 `.data/state.json`。这个目录已经被 `.gitignore` 忽略，不会提交到 GitHub。

## 常见问题

### 为什么没有推送？

先确认：

- `.env` 里有 `X_BEARER_TOKEN`
- `config.yaml` 里账号 username 没有写错
- X API 权限支持读取用户时间线
- `notifications.channel` 和对应的 token/webhook 配置正确

### 没有 OpenAI API Key 能用吗？

可以。没有 `OPENAI_API_KEY` 时会自动使用本地规则判断，只是语义判断会没那么细。

### 会重复提醒吗？

正常不会。程序会记录每个账号最后处理到的帖子 ID。删除 `.data/state.json` 后会重新扫描最近的帖子。

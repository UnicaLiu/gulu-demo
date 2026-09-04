# 沽渌农业自动化管理总控台（Gulu Agri Command Center）

一个连接本机 **Hermes Bot** 的网页总控看板 demo：页面展示各部门 Bot 的工作状态卡，点击卡片即可与对应 Bot 实时对话（走 Bot 真正的常驻 Bot Chat，记忆连续）。

```
┌─────────────────────────────────────────────┐
│  沽渌农业自动化管理总控台          [时钟]     │
│  ┌──────────────┐  ┌──────────────┐         │
│  │ 农业销售部   │  │ 农业生产部   │  ← 信息卡  │
│  │ 状态/任务/进度│  │ 状态/任务/进度│   (可配置)  │
│  └──────────────┘  └──────────────┘         │
│        点卡片 → 侧滑对话框 → 与 Bot 对话       │
└─────────────────────────────────────────────┘
```

## 文件结构

```
├── bridge.py        # Python 后端：调用 hermes CLI 桥接各 Bot（HTTP :8790）
├── bots.json        # ★ 核心配置：公司抬头 + 要连接的 Bot 列表（增删改都在这）
├── index.html       # 前端总控台页面（数据驱动，自动读取 /api/bots）
├── assets/          # AI 生成的背景图与 Bot 头像
└── README.md
```

## 快速开始（本机已有 Hermes + 已建好 Bot）

```bash
# 1. 按需编辑 bots.json：company 抬头、bots 数组（id 必须等于 Hermes profile 名）
# 2. 启动后端
cd 本目录
python3 bridge.py            # 默认 http://127.0.0.1:8790

# 3. 浏览器打开
open http://127.0.0.1:8790
```

点任一 Bot 卡片 → 输入消息 → 发送 → 等待回复（Bot 真实思考，通常几秒～几十秒）。

## ★ 换一台设备部署（关键：指定要连接哪几个 Bot）

1. **目标设备安装 Hermes 并创建好 Bot**：每个要接入的 Bot 就是一个 profile。
   ```bash
   hermes profile list               # 查看本机已有 profile（即 Bot）
   hermes profile create <名字>      # 如没有则新建（用桌面端 Bots 面板建也行）
   # 记得先各自 Chat 过一次，让 'Bot Chat' 会话生成（bridge 会自动 --create-if-missing，不聊也行）
   ```

2. **拷贝本项目**到目标设备任意目录（git clone 或直接拷文件）。

3. **编辑 `bots.json`**——这就是"指定连接哪几个 Bot"的地方：
   - `bots[].id` 填目标设备上**真实的 profile 名**（如 `agri-xiaoshou`、`lina`、`iron-man`）
   - `name/dept` 卡片显示名；`task/progress/kpi1/kpi2/...` 卡片展示信息
   - `image` 头像路径（可留 `""`，前端自动显示名称首字圆标）
   - `welcome` 打开对话框时的欢迎语
   - `company/hero_title` 页面抬头与标语，随设备/公司改

4. **启动并访问**（同上）。前端会自动从 `/api/bots` 拉取配置渲染，**不用改任何 HTML**。

> 后端的桥接命令等价于：
> `hermes -p <bots[].id> chat -Q -q "<你的消息>" -c 'Bot Chat' --create-if-missing`
> 因此目标设备的 Hermes 需在 PATH 中，且对应用户能执行 hermes。

## 配置示例（bots.json）

```json
{
  "company": "沽渌农业自动化管理总控台",
  "company_en": "GULU AGRI · AUTOMATION COMMAND",
  "hero_title": "让每一寸农田，被看见、被理解、被调度。",
  "bots": [
    {
      "id": "agri-xiaoshou",
      "name": "农业销售部",
      "state": "在线",
      "task": "梳理本周高意向客户，生成首轮回访建议",
      "progress": 72,
      "kpi1": "今日跟进客户", "value1": "12 位",
      "kpi2": "订单转化",    "value2": "3 单",
      "image": "assets/agri-sales-bot.png",
      "welcome": "您好，我是农业销售部智能助手。"
    }
  ]
}
```

## 端口 / 局域网访问

- 默认 `127.0.0.1:8790`（仅本机）。手机或别的电脑访问：
  ```bash
  python3 bridge.py --host 0.0.0.0        # 局域网可访问（注意防火墙/安全）
  # 然后浏览器打开 http://<本机IP>:8790
  ```

## 已知说明

- 每次对话是"一问一答"（同步等待），非流式；Bot 长任务可能需数十秒，页面有 60s 超时与"仍在处理"提示。
- 对话历史存于各 Bot 的常驻 Bot Chat（Hermes 侧），刷新网页后重新拉取欢迎语；页面内存仅保存本次会话气泡。
- 图片资源默认来自 assets/，上传时建议一并提交（头像/背景）。

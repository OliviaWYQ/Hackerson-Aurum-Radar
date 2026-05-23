# Sunzi Strategy Skill

基于《孙子兵法》的 Codex skill，用来分析生活、商业、组织、谈判、经济与军事理论中的复杂局势。

这个 skill 的核心目标不是复述名句，而是把问题拆成：

- 这是什么局
- 谁掌握主动权
- 哪些是虚，哪些是实
- 该进、该守、该退，还是该换战场
- 哪条路径最省成本、最有胜算

## 仓库内容

```text
.
├─ README.md
├─ .gitignore
├─ .gitattributes
└─ sunzi-strategy/
   ├─ SKILL.md
   ├─ agents/
   │  └─ openai.yaml
   └─ references/
      ├─ principles.md
      ├─ life.md
      ├─ business.md
      ├─ organization.md
      ├─ economics.md
      ├─ military-theory.md
      ├─ examples.md
      └─ anti-patterns.md
```

## Skill 定位

`sunzi-strategy` 把《孙子兵法》翻译成现代策略分析框架，适合这些场景：

- 生活决策与人际边界
- 职场推进与组织协同
- 商业竞争与谈判
- 项目推进与资源争夺
- 宏观、行业与经济判断
- 军事史、兵学与战略理论分析

它强调：

- 先胜后战
- 知彼知己
- 避实击虚
- 以正合，以奇胜
- 致人而不致于人
- 低成本取胜，而不是高情绪硬冲

## 安装方式

### 1. Codex / OpenAI Skills

把 `sunzi-strategy/` 目录复制到 Codex 的 skills 目录即可。

常见位置：

- Windows: `%CODEX_HOME%\\skills`
- 如果没有设置 `CODEX_HOME`，通常放到用户目录下的 `.codex\\skills`

安装后目录结构应类似：

```text
$CODEX_HOME/skills/
└─ sunzi-strategy/
   ├─ SKILL.md
   ├─ agents/
   └─ references/
```

### 2. OpenClaw

OpenClaw 原生支持 `SKILL.md` 目录式 skills，这个仓库可以直接复用。

快速安装 OpenClaw：

1. 先按官方文档安装 OpenClaw：
   [OpenClaw Install](https://docs.openclaw.ai/install/index)
2. 完成引导：
   `openclaw onboard --install-daemon`
3. 把 `sunzi-strategy/` 放到以下任一位置：
   - 当前 OpenClaw workspace 下的 `skills/sunzi-strategy/`
   - 共享目录 `~/.openclaw/skills/sunzi-strategy/`
4. 重新开始一个 OpenClaw 会话，让 skill 被加载

补充说明：

- OpenClaw 官方安装页：
  [Install](https://docs.openclaw.ai/install/index)
- OpenClaw skills 说明：
  [Skills](https://docs.openclaw.ai/tools/skills)
- ClawHub 安装与发布：
  [ClawHub](https://docs.openclaw.ai/tools/clawhub)

### 3. 常见 Agent IDE

下面这些工具和 Codex / OpenClaw 的 skill 机制不完全相同。最稳的用法是：

- 把本仓库作为工作区打开
- 让 agent 读取 `sunzi-strategy/SKILL.md`
- 按需读取 `references/` 里的场景文件

#### Cursor

- 下载页：
  [cursor.com/downloads](https://cursor.com/downloads/)
- 文档首页：
  [cursor.com/docs](https://cursor.com/docs)
- 推荐接入方式：
  打开本仓库后，把 `sunzi-strategy/SKILL.md` 当作项目规则或长期参考文档使用

#### Windsurf

- 官方入门与安装：
  [Windsurf Getting Started](https://docs.windsurf.com/windsurf/getting-started)
- 如果你用的是 JetBrains / VS Code 插件路线：
  [Windsurf Plugins](https://docs.windsurf.com/plugins/getting-started)
- 推荐接入方式：
  直接打开本仓库，在对话里显式要求 agent 参考 `sunzi-strategy/` 目录

#### Cline

- 官方安装文档：
  [Installing Cline](https://docs.cline.bot/getting-started/installing-cline)
- 快速开始：
  [Cline Quick Start](https://docs.cline.bot/getting-started/quick-start)
- 推荐接入方式：
  在 VS Code / Cursor / Windsurf / JetBrains 中安装 Cline 后，打开本仓库，把 `sunzi-strategy/SKILL.md` 作为工作区提示文档使用

## 跨工具使用建议

如果你不是在原生支持 skills 的环境里使用本项目，建议这样调用：

```text
请先阅读 sunzi-strategy/SKILL.md，再按场景阅读对应的 references 文件，用《孙子兵法》的框架分析这个问题。
```

这样在 Cursor、Windsurf、Cline、OpenClaw 里都比较稳定。

## 使用方式

你可以直接在请求中显式调用：

```text
使用 $sunzi-strategy 分析这个局，拆出敌我、虚实、势和最合适的低成本动作。
```

也可以自然描述需求，例如：

- “用孙子兵法帮我看下这次谈判怎么打。”
- “这个项目老卡在跨部门协作，怎么破局？”
- “我们是小团队，面对大公司竞争该怎么避实击虚？”
- “从《孙子兵法》看，这段关系到底该争还是该退？”

## 回答结构

这个 skill 默认会把问题拆成六段：

1. 战场定义
2. 敌我态势
3. 孙子判断
4. 可选战法
5. 推荐动作
6. 风险警报

同时根据问题自动切换为：

- `quick`
- `standard`
- `deep`
- `classical`

## 参考文件

- [sunzi-strategy/SKILL.md](./sunzi-strategy/SKILL.md)：主说明与调用规则
- [sunzi-strategy/references/principles.md](./sunzi-strategy/references/principles.md)：13 条原则库
- [sunzi-strategy/references/life.md](./sunzi-strategy/references/life.md)：生活与人际
- [sunzi-strategy/references/business.md](./sunzi-strategy/references/business.md)：商业与谈判
- [sunzi-strategy/references/organization.md](./sunzi-strategy/references/organization.md)：组织与协同
- [sunzi-strategy/references/economics.md](./sunzi-strategy/references/economics.md)：经济与周期
- [sunzi-strategy/references/military-theory.md](./sunzi-strategy/references/military-theory.md)：军事理论
- [sunzi-strategy/references/examples.md](./sunzi-strategy/references/examples.md)：示例库
- [sunzi-strategy/references/anti-patterns.md](./sunzi-strategy/references/anti-patterns.md)：反模式检查

## 设计原则

这个 skill 刻意避免几种常见问题：

- 只会背名句，不会分析
- 把所有问题都写成“打仗”
- 把谋略写成操控和伤害
- 把一时热血误当成战略

它更关心：

- 局势判断
- 位置选择
- 节奏控制
- 低成本动作
- 退出与转场时机

## 开发与维护

如果你要继续扩展这个 skill，优先从这几个方向继续迭代：

- 补充十三篇逐篇解释索引
- 增加更多中文示例
- 增强特定领域的映射文件
- 做一次真实调用下的 forward test

## 仓库地址

[https://github.com/calmlim/sunzi-strategy-skill](https://github.com/calmlim/sunzi-strategy-skill)

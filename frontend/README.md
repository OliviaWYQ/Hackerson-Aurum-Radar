# Aurum Radar — Frontend

全球市场战略情报看板 · Jewelry Overseas Market Intelligence Dashboard

## 技术栈

- **Vite** — 构建工具，支持热更新
- **React 18** + **TypeScript**
- **Tailwind CSS** — 布局工具类
- **CSS Variables** — 设计系统 Token（香槟金、珍珠白、柔和阴影）

## 目录结构

```
frontend/
├── src/
│   ├── api/
│   │   ├── types.ts        # TypeScript 类型定义
│   │   ├── mockData.ts     # Mock 数据（对应真实 API 字段）
│   │   └── index.ts        # API 函数封装，backend 就绪后在此替换 fetch
│   ├── components/
│   │   ├── ui/             # Icon、DiamondMark 基础组件
│   │   ├── shell/          # TopBar、Sidebar 全局导航
│   │   ├── overview/       # 概览页 — 全球地图 + 国家摘要
│   │   ├── map/            # 地图洞察页 — 新加坡商圈
│   │   ├── intel/          # 情报中心页 — 事件流 + 详情
│   │   └── actions/        # 行动建议页 — 部门行动清单
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css           # Design Tokens + Tailwind
└── package.json
```

## 启动开发服务器

```bash
cd frontend
npm install
npm run dev
```

浏览器将自动打开 http://localhost:5173

## 对接后端

所有 API 调用统一在 `src/api/index.ts`，当前返回 `mockData.ts` 中的静态数据。

后端就绪后，将每个函数的 `return` 替换为 `fetch` 即可：

```ts
// src/api/index.ts — 替换示例
export async function fetchEvents(category?: string) {
  const url = category && category !== '全部'
    ? `/api/events?category=${category}`
    : '/api/events'
  const res = await fetch(url)
  return res.json()
}
```

数据字段定义见 `src/api/types.ts`，与后端数据结构一一对应。

## 构建生产版本

```bash
npm run build
npm run preview   # 本地预览产物
```

# ChatAgent 前端项目

基于 React + TypeScript + Tailwind CSS 的现代化聊天界面

## 功能特性

- 👤 用户注册和登录
- 💬 实时聊天功能（支持流式响应）
- 🗂️ 多会话管理
- 🧹 清除聊天历史
- 📱 响应式设计
- 🔐 JWT 身份认证

## 项目结构

```
src/
├── pages/           # 页面组件
│   ├── LoginPage.tsx        # 登录页面
│   ├── RegisterPage.tsx      # 注册页面
│   └── ChatPage.tsx          # 聊天页面
├── components/      # 公共组件
│   ├── MessageBubble.tsx      # 消息气泡
│   ├── SessionList.tsx        # 会话列表
│   └── ProtectedRoute.tsx      # 受保护路由
├── services/        # API 服务
│   └── api.ts               # API 请求封装
├── types/           # TypeScript 类型定义
│   └── index.ts             # 类型导出
├── App.tsx          # 应用根组件
├── main.tsx         # 入口文件
└── index.css        # 全局样式
```

## 环境要求

- Node.js >= 16
- npm 或 yarn

## 快速开始

1. 安装依赖

```bash
npm install
```

2. 开发环境运行

```bash
npm run dev
```

3. 生产构建

```bash
npm run build
```

## API 接口

前端与后端通过 RESTful API 通信：

### 认证接口
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `PATCH /api/v1/auth/passwd/change` - 修改密码

### 会话接口
- `POST /api/v1/auth/session` - 创建会话
- `GET /api/v1/auth/sessions` - 获取所有会话
- `PATCH /api/v1/auth/session/name` - 更新会话名称
- `DELETE /api/v1/auth/session` - 删除会话

### 聊天接口
- `POST /api/v1/chat/chat` - 发送聊天消息
- `POST /api/v1/chat/chat/stream` - 流式聊天
- `GET /api/v1/chat/messages` - 获取聊天历史
- `DELETE /api/v1/chat/messages` - 清除聊天历史

## 配置

### Vite 代理配置

在 `vite.config.ts` 中配置后端 API 代理：

```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true
  }
}
```

修改 `target` 为您的后端服务器地址。

## 开发指南

### 添加新页面

1. 在 `src/pages` 中创建新的 `.tsx` 文件
2. 在 `App.tsx` 中添加路由

### 添加新组件

1. 在 `src/components` 中创建新的 `.tsx` 文件
2. 导出组件供其他文件使用

### API 调用

使用 `apiService` 进行 API 调用：

```typescript
import { apiService } from '../services/api';

// 登录
await apiService.login(email, password);

// 获取会话列表
const sessions = await apiService.getSessions();

// 发送消息
await apiService.sendChat(messages, sessionId);
```

## 样式

项目使用 Tailwind CSS 进行样式管理，配置文件为 `tailwind.config.js`。

## 错误处理

- API 请求自动处理 401 未授权错误，重定向到登录页面
- 表单验证在客户端进行，提供友好的错误提示
- 网络错误会显示在 UI 中供用户确认

## 部署

1. 构建项目

```bash
npm run build
```

2. 部署 `dist` 目录到静态文件服务器

3. 配置反向代理以指向后端 API

## 许可证

MIT

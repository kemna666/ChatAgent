# 快速开始指南

## 项目概述

这是 ChatAgent 的前端项目，一个基于 React + TypeScript + Tailwind CSS 构建的现代化 AI 聊天助手 Web 应用。

## 快速启动

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 配置后端 API 地址

编辑 `vite.config.ts`，修改 proxy target：

```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8000',  // 改为您的后端服务地址
    changeOrigin: true
  }
}
```

### 3. 启动开发服务器

```bash
npm run dev
```

访问 `http://localhost:5173`

### 4. 生产构建

```bash
npm run build
```

## 页面说明

### 登录页面 (`/login`)
- 用户邮箱登录
- 错误处理和验证
- 链接到注册页面

### 注册页面 (`/register`)
- 新用户注册
- 密码强度验证（至少10个字符，包含字母和数字）
- 密码确认检查
- 链接到登录页面

### 聊天页面 (`/chat`)
- **左侧边栏**：会话列表，可创建、删除会话
- **主区域**：聊天消息显示和输入
- **功能**：
  - 实时聊天（支持流式响应）
  - 多会话管理
  - 清除聊天历史
  - 用户登出

## 核心功能

### API 服务 (`src/services/api.ts`)

```typescript
// 认证
apiService.register(userData)      // 注册
apiService.login(email, password)  // 登录
apiService.changePassword(...)     // 修改密码

// 会话管理
apiService.createSession(name)     // 创建会话
apiService.getSessions()           // 获取所有会话
apiService.updateSessionName(...)  // 更新会话名称
apiService.deleteSession(id)       // 删除会话

// 聊天
apiService.sendChat(messages, id)        // 发送聊天
apiService.streamChat(messages, id)      // 流式聊天
apiService.getMessages(id)               // 获取历史消息
apiService.clearHistory(id)              // 清除历史
```

### 组件结构

```
App.tsx
├── 路由管理
├── 认证状态
└── 页面切换

LoginPage / RegisterPage
└── 用户认证

ChatPage
├── 侧边栏
│   └── SessionList：会话列表管理
└── 主聊天区域
    ├── 消息显示
    │   └── MessageBubble：单条消息
    └── 消息输入
```

## 身份认证流程

1. **注册/登录** → 获取 JWT token
2. **保存 token** 到 localStorage
3. **API 请求** 自动在 Authorization header 中添加 token
4. **Token 过期** → 自动重定向到登录页
5. **登出** → 清除 token 和本地数据

## 样式框架

- **Tailwind CSS**：工具类样式
- **响应式设计**：移动端和桌面端适配
- **深色模式支持**：可在 tailwind.config.js 中配置

## 常见问题

### Q: CORS 错误？
A: 确保 vite.config.ts 中的 proxy target 正确指向后端服务器

### Q: 无法上传文件？
A: 当前版本支持文本聊天，多模态功能在开发中

### Q: 消息未保存？
A: 刷新页面后会从后端重新加载历史消息

## 开发工具

```bash
npm run dev          # 启动开发服务器
npm run build        # 生产构建
npm run preview      # 预览构建结果
npm run lint         # ESLint 检查（暂未配置）
npm run type-check   # TypeScript 类型检查
```

## 浏览器支持

- Chrome/Edge (最新版)
- Firefox (最新版)
- Safari 14+

## 项目依赖

- **react**: UI 库
- **react-router-dom**: 路由管理
- **axios**: HTTP 客户端
- **react-icons**: 图标库
- **tailwindcss**: CSS 工具框架

## 下一步

1. 启动后端服务（FastAPI）
2. 运行 `npm install && npm run dev`
3. 在浏览器中注册/登录
4. 开始聊天！

## 支持

遇到问题？检查：
- 后端服务是否运行在 8000 端口
- 浏览器控制台是否有错误信息
- 网络连接是否正常

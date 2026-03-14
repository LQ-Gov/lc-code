# 客服AI机器人 UI

## 项目结构
- `index.html` - 主页面（基于Alpine.js的现代化版本）
- `styles.css` - 样式文件  

## 运行说明

### 开发环境运行
1. **启动后端服务**：
   ```bash
   python main.py
   ```
   后端服务将运行在 `http://localhost:8000`

2. **访问UI界面**：
   - 直接在浏览器中打开 `ui/index.html` 文件
   - 或者使用简单的HTTP服务器（推荐）：
     ```bash
     # 在项目根目录下
     python -m http.server 8080
     ```
     然后访问 `http://localhost:8080/ui/index.html`

### 生产环境部署建议
对于生产环境，建议将UI文件作为静态资源集成到FastAPI应用中：

1. 在 `web/api.py` 中添加静态文件服务：
   ```python
   from fastapi.staticfiles import StaticFiles
   
   # 在 app 初始化后添加
   app.mount("/ui", StaticFiles(directory="ui"), name="ui")
   ```

2. 访问地址：`http://your-server:8000/ui/index.html`

## API 集成
UI通过以下API端点与后端agent通信：

- **客服咨询**：`POST /api/robot/consult`
  - 请求体包含：`user_id`, `question`, `session_id`(可选)
  - 返回：机器人回复、会话ID等信息

- **健康检查**：`GET /api/health`

## 功能特性
- ✅ 实时对话交互
- ✅ 会话状态管理
- ✅ 加载动画指示
- ✅ 响应式设计（支持移动端）
- ✅ 常见问题快捷按钮
- ✅ 与后端agent无缝集成

## 依赖要求
- 现代浏览器（Chrome, Firefox, Safari, Edge）
- 后端FastAPI服务正常运行
- 网络连接（用于API调用）

## 故障排除
如果遇到CORS错误，请确保后端服务已正确配置CORS中间件。

如果API调用失败，请检查：
1. 后端服务是否正在运行 (`http://localhost:8000/api/health`)
2. 网络连接是否正常
3. 浏览器控制台是否有错误信息
# QAuto

# A股K线图片AI分析工具 v1.0
基于React+TypeScript+Python+ChatGPT/Gemini的A股K线图片智能分析工具，支持上传K线截图并通过AI分析趋势、支撑位、压力位等关键信息。

## 核心功能
✅ 支持JPG/PNG/WEBP格式K线图片上传  
✅ 图片实时预览  
✅ AI智能分析（ChatGPT-4V/Gemini Pro Vision）  
✅ 结构化分析结果展示  
✅ 前后端分离架构，易扩展  

## 环境要求
### 前端
- Node.js ≥ 16.0.0
- npm ≥ 8.0.0 或 yarn ≥ 1.22.0

### 后端
- Python ≥ 3.8 & < 3.13 (recommand to use 3.12.7)
- OpenAI/Gemini API密钥（二选一）

## 快速部署步骤
<li><b>克隆/下载项目</b></li>

``` bash
cd QAuto
```
<li><b>后端部署</b></li>

``` bash
# 进入后端目录
cd backend

# 安装依赖（建议用虚拟环境）
python -m venv qauto
# 激活虚拟环境
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt

# 配置API密钥
cp .env.example .env
# 编辑.env文件，填入OpenAI/Gemini API密钥

# 启动后端服务
python main.py
# 服务地址： http://127.0.0.1:8000
```
<li><b>前端部署</b></li>

``` bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务
npm run dev
# 访问地址：http://127.0.0.1:5173
```

<img src='./assets/k1_example.png'>


import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from config import HOST, PORT, MAX_FILE_SIZE, USE_MODEL
from utils import save_uploaded_file, analyze_kline_image, clean_temp_file

# 创建FastAPI应用
app = FastAPI(
    title="A股K线图片AI分析API",
    description="基于ChatGPT/Gemini的A股K线图片智能分析接口",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境请替换为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 文件大小限制中间件
@app.middleware("http")
async def limit_file_size(request: Request, call_next):
    """
    限制请求体大小
    """
    if request.method == "POST":
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_FILE_SIZE:
            return JSONResponse(
                status_code=413,
                content={
                    "success": False,
                    "error": f"文件大小超过限制（最大{MAX_FILE_SIZE/1024/1024}MB）"
                }
            )
    response = await call_next(request)
    return response

@app.get("/health")
async def health_check():
    """
    健康检查接口
    """
    return {
        "status": "healthy",
        "model": USE_MODEL,
        "version": "1.0.0"
    }
@app.get("/")
async def root():
    """根路径返回服务状态"""
    return {
        "status": "success",
        "message": "A股K线分析服务运行中",
        "version": "1.0.0",
        "docs_url": "http://127.0.0.1:8000/docs",
        "api_endpoint": "/analyze-kline"
    }

@app.post("/analyze-kline")
async def analyze_kline(kline_image: UploadFile = File(...)):
    """
    上传K线图片并返回AI分析结果
    """
    try:
        # 1. 校验文件类型
        allowed_extensions = ["jpg", "jpeg", "png", "webp"]
        file_ext = kline_image.filename.split(".")[-1].lower() if "." in kline_image.filename else ""
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式：{file_ext}，仅支持{','.join(allowed_extensions)}"
            )
        
        # 2. 读取并保存文件
        file_content = await kline_image.read()
        file_path = save_uploaded_file(file_content, file_ext)
        
        try:
            # 3. AI分析
            analysis_result = await analyze_kline_image(file_path)
            
            # 4. 返回结果
            return {
                "success": True,
                "data": analysis_result
            }
        finally:
            # 5. 清理临时文件
            clean_temp_file(file_path)
    
    except HTTPException as e:
        logger.error(f"请求错误：{e.detail}")
        raise
    except Exception as e:
        logger.error(f"分析失败：{str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"分析失败：{str(e)}"
            }
        )

if __name__ == "__main__":
    import uvicorn
    logger.info(f"启动K线分析服务，模型：{USE_MODEL}，端口：{PORT}")
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=True,  # 开发模式开启热重载
        log_level="info"
    )
from datetime import datetime
import json
import os
import io
import base64
from typing import Dict, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import chromadb
from chromadb.utils import embedding_functions
import numpy as np
import openai
import google.generativeai as genai
import pandas as pd
from fastapi.responses import JSONResponse
from loguru import logger
from config import HOST, PORT, MAX_FILE_SIZE, USE_MODEL
from utils.utils import analyze_uploaded_kline_image, save_uploaded_file, analyze_kline_image, clean_temp_file

# 导入自定义模块
from cache.redis_client import CustomJSONEncoder, redis_client
from stock.stock_selector import stock_selector
from stock.kline_generator import kline_generator
from utils.image_utils import extract_image_embedding

# 加载环境变量
load_dotenv()

app = FastAPI(
    title="A股K线图片AI分析API",
    description="基于ChatGPT/Gemini的A股K线图片智能分析接口",
    version="2.0.0"
)

# 跨域配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ====================== 初始化组件 ======================
# 1. 向量数据库
chroma_client = chromadb.PersistentClient(
    path=os.getenv("CHROMA_PATH", os.getenv("CHROMA_PATH")),  # 向量数据存储路径
    tenant="default_tenant" # 1.3.5新增多租户特性（默认即可）
)

# 初始化默认嵌入函数（用于文本/特征向量转换）
default_ef = embedding_functions.DefaultEmbeddingFunction()

# 创建/获取股票特征向量集合（1.3.5自动创建不存在的集合）
stock_collection = chroma_client.get_or_create_collection(
    name="stock_macd_features",
    embedding_function=default_ef,  # 绑定嵌入函数
    metadata={"description": "存储股票MACD特征向量及分析结果"}
)

# ===================== 工具函数（辅助逻辑） =====================
def generate_stock_embedding(stock_data: Dict) -> List[float]:
    """
    生成股票特征向量（基于MACD指标+价格特征）
    :param stock_data: 包含MACD/价格的股票数据
    :return: 归一化后的特征向量（长度512，适配ChromaDB默认嵌入）
    """
    try:
        # 提取核心特征：dif/dea/macd/最新价/涨跌幅（简化版）
        core_features = [
            stock_data.get("dif", 0.0),
            stock_data.get("dea", 0.0),
            stock_data.get("macd", 0.0),
            stock_data.get("latest_price", 0.0) / 100,  # 价格归一化
            (stock_data.get("latest_price", 0.0) - stock_data.get("open", 0.0)) / stock_data.get("latest_price", 0.0)  # 涨跌幅
        ]
        # 补全到512维（适配默认嵌入函数输出维度）
        embedding = np.pad(core_features, (0, 512 - len(core_features)), mode='constant').tolist()
        return embedding
    except Exception as e:
        raise RuntimeError(f"生成股票特征向量失败: {str(e)}")

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

@app.middleware("http")
async def custom_json_encoder(request, call_next):
    response = await call_next(request)
    return response

# 全局配置：让FastAPI使用自定义编码器序列化JSON
def custom_json_serializer(obj):
    return json.dumps(obj, cls=CustomJSONEncoder)

app.json_encoder = CustomJSONEncoder  # 关键：配置全局编码器

@app.get("/health-old", summary="v1.0服务健康检查")
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
            analysis_result = await analyze_uploaded_kline_image(file_path)
            
            # 4. 返回结果
            return { "data": {
                "success": True,
                "data": analysis_result
                }
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

# ====================== API接口 ======================
@app.get("/health", summary="服务健康检查")
async def health_check():
    """检查服务状态（Redis/数据库/大模型）"""
    redis_status = redis_client.ping()
    logger.info(f"Redis连接状态-----------: {redis_status}")
    chroma_count = stock_collection.count()
    
    return {
        "status": "healthy" if redis_status else "unhealthy",
        "redis_connected": redis_status,
        "chroma_count": chroma_count,
        "llm_type": USE_MODEL,
        "timestamp": str(pd.Timestamp.now())
    }

@app.get("/select-stocks", summary="MACD金叉选股")
async def select_stocks(
    fast: Optional[int] = Query(None, description="MACD快速周期"),
    slow: Optional[int] = Query(None, description="MACD慢速周期"),
    signal: Optional[int] = Query(None, description="MACD信号周期"),
    limit: Optional[int] = Query(50, description="选股数量上限")
) -> Dict:
    """执行MACD金叉选股，并将结果存入ChromaDB向量库"""
    try:
        if not stock_selector:
            raise HTTPException(status_code=500, detail="选股器初始化失败")
        
        logger.info(f"开始执行MACD金叉选股，参数fast={fast}, slow={slow}, signal={signal}, limit={limit}")
        # 执行选股
        selected_stocks = stock_selector.select_stocks(fast=fast, slow=slow, signal=signal)
        selected_stocks = selected_stocks[:limit]
        logger.info(f"选出{len(selected_stocks)}只符合MACD金叉条件的股票")
        
        # 批量存入ChromaDB（1.3.5支持批量操作）
        stock_ids = []
        stock_embeddings = []
        stock_metadatas = []
        stock_documents = []
        
        for stock in selected_stocks:
            stock_id = stock["ts_code"]  # 用股票代码作为唯一ID
            # 生成特征向量
            embedding = generate_stock_embedding(stock)
            logger.info(f"生成特征向量，长度：{len(embedding)}")
            # 构造元数据和文档
            metadata = {
                "symbol": stock["symbol"],
                "name": stock["name"],
                "industry": stock.get("industry", "未知"),
                "dif": stock.get("dif", 0.0),
                "dea": stock.get("dea", 0.0),
                "macd": stock.get("macd", 0.0),
                "latest_price": stock.get("latest_price", 0.0)
            }
            document = f"股票{stock['name']}({stock['ts_code']})，行业{stock.get('industry', '未知')}，MACD金叉，DIF={stock.get('dif', 0.0)}，DEA={stock.get('dea', 0.0)}，MACD={stock.get('macd', 0.0)}，最新价={stock.get('latest_price', 0.0)}"
            
            stock_ids.append(stock_id)
            stock_embeddings.append(embedding)
            stock_metadatas.append(metadata)
            stock_documents.append(document)
        
        # 批量添加到ChromaDB（存在则更新）
        if stock_ids:
            stock_collection.upsert(
                ids=stock_ids,
                embeddings=stock_embeddings,
                metadatas=stock_metadatas,
                documents=stock_documents
            )
        
        return {
            "code": 200,
            "msg": "选股成功",
            "data": {
                "status": "success",
                "count": len(selected_stocks),
                "data": selected_stocks,
                "timestamp": str(pd.Timestamp.now())
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"选股失败: {str(e)}")
    
@app.get("/stock/{ts_code}", summary="获取单只股票详情+分析")
async def get_stock_detail(ts_code: str) -> Dict:
    """获取股票详情，并从ChromaDB查询相似股票"""
    try:
        # 1. 获取股票基础数据
        stock_list = stock_selector.get_stock_list()
        stock_info = next((s for s in stock_list if s["ts_code"] == ts_code), None)
        if not stock_info:
            raise HTTPException(status_code=404, detail=f"股票{ts_code}不存在")
        
        # 2. 获取日线数据和MACD
        daily_df = stock_selector.get_daily_data(ts_code)
        daily_df = stock_selector.calculate_macd(daily_df)
        latest_row = daily_df.tail(1).iloc[0]
        
        stock_detail = {
            "ts_code": ts_code,
            "name": stock_info["name"],
            "industry": stock_info.get("industry", "未知"),
            "latest_price": float(latest_row["close"]),
            "dif": float(latest_row["dif"]),
            "dea": float(latest_row["dea"]),
            "macd": float(latest_row["macd"]),
            "is_gold_cross": stock_selector.is_macd_gold_cross(daily_df)
        }
        
        # 3. 从ChromaDB查询相似股票（基于特征向量）
        query_embedding = generate_stock_embedding(stock_detail)
        similar_stocks = stock_collection.query(
            query_embeddings=[query_embedding],
            n_results=5,  # 返回Top5相似股票
            where={"industry": stock_info.get("industry", "未知")}  # 按行业过滤
        )
        
        # 格式化相似股票结果
        similar_list = []
        for i, (stock_id, metadata, distance) in enumerate(
            zip(similar_stocks["ids"][0], similar_stocks["metadatas"][0], similar_stocks["distances"][0])
        ):
            similar_list.append({
                "rank": i + 1,
                "ts_code": stock_id,
                "name": metadata["name"],
                "industry": metadata["industry"],
                "similarity": 1 - distance,  # 距离越小相似度越高
                "latest_price": metadata["latest_price"]
            })
        
        return {
            "code": 200,
            "msg": "获取成功",
            "data": {
                "stock_detail": stock_detail,
                "similar_stocks": similar_list
            }
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取股票详情失败: {str(e)}")

@app.get("/clear_chroma", summary="清空ChromaDB股票向量数据")
async def clear_chroma_collection():
    """清空股票特征向量集合（谨慎使用）"""
    try:
        # 方式1：清空集合（保留集合）
        stock_collection.delete(ids=stock_collection.get()["ids"])
        # 方式2：删除集合（需重新创建）
        # chroma_client.delete_collection(name="stock_macd_features")
        
        return {"code": 200, "msg": "ChromaDB向量数据已清空"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空失败: {str(e)}")

@app.get("/generate-kline", summary="生成K线图")
async def generate_kline(ts_code: str = Query(..., description="股票代码（如600519.SH）")):
    """生成指定股票的K线图"""
    try:
        # 获取日线数据
        df = stock_selector.get_daily_data(ts_code)
        if df.empty:
            raise HTTPException(status_code=400, detail="股票数据为空")
        
        # 生成K线图
        img_bytes = kline_generator.generate_kline(ts_code, df)
        
        # 返回Base64编码的图片
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        return {
            "status": "success",
            "ts_code": ts_code,
            "image_base64": img_base64,
            "timestamp": str(pd.Timestamp.now())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成K线图失败: {str(e)}")

@app.post("/analyze-stock", summary="分析指定股票")
async def analyze_stock(
    ts_code: str = Body(..., embed=True, description="股票代码"),
    user_question: str = Body(default=None, embed=True, description="自定义分析问题")
):
    """分析指定股票（自动生成K线图并调用大模型）"""
    try:
        # 1. 获取日线数据
        df = stock_selector.get_daily_data(ts_code)
        if df.empty:
            raise HTTPException(status_code=400, detail="股票数据为空")
        
        # 2. 生成K线图
        img_bytes = kline_generator.generate_kline(ts_code, df)
        file_path = save_uploaded_file(img_bytes, "png")
        
        # 3. 分析K线图
        analysis_result = await analyze_kline_image(file_path, ts_code, stock_collection, redis_client, user_question)
        
        # 4. 返回结果（包含Base64图片）
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        return {
            "data": {
                "status": "success",
                "ts_code": ts_code,
                "stock_name": next((s['name'] for s in (stock_selector.get_stock_list()) if s['ts_code'] == ts_code), "未知"),
                "image_base64": img_base64,
                "analysis_result": analysis_result,
                "timestamp": str(pd.Timestamp.now()),
                "llm_type": USE_MODEL
            }   
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析股票失败: {str(e)}")

@app.post("/batch-analyze", summary="批量分析选股结果")
async def batch_analyze(
    fast: int = Body(default=None, embed=True, description="MACD快速周期"),
    slow: int = Body(default=None, embed=True, description="MACD慢速周期"),
    signal: int = Body(default=None, embed=True, description="MACD信号周期")
):
    """批量分析MACD金叉选股结果"""
    try:
        # 1. 选股
        selected_stocks = stock_selector.select_stocks(fast, slow, signal)
        if not selected_stocks:
            # 返回标准化可序列化响应
            return JSONResponse(
                content={
                    "status": "success",
                    "count": 0,
                    "data": [],
                    "message": "未筛选出符合MACD金叉条件的股票",
                    "timestamp": datetime.now().isoformat()  # 标准化时间（替代pd.Timestamp）
                },
                status_code=200
            )
        
        # 2. 批量分析
        batch_result = []
        for stock in selected_stocks[:10]:  # 限制批量分析数量
            ts_code = stock['ts_code']
            if not ts_code:
                continue  # 跳过无代码的股票
            try:
                # 获取日线数据
                df = stock_selector.get_daily_data(ts_code)
                if df.empty:
                    continue
                
                # 生成K线图
                img_bytes = kline_generator.generate_kline(ts_code, df)
                file_path = save_uploaded_file(img_bytes, "png")
                
                # 分析K线图
                analysis_result = await analyze_kline_image(file_path, ts_code, stock_collection, redis_client)
                
                # 标准化分析结果（处理numpy/自定义类型）
                analysis_result = json.loads(json.dumps(analysis_result, cls=CustomJSONEncoder))
                
                # 构建结果
                 # 构建单条结果：逐字段类型转换，确保可序列化
                single_result = {
                    "ts_code": str(ts_code),  # 确保是字符串
                    "stock_name": str(stock.get('name', '')),  # 兜底空字符串
                    "industry": str(stock.get('industry', '')),
                    # 修复：numpy数值转Python原生类型（如np.float64 → float）
                    "latest_price": float(stock.get('latest_price', 0.0)) if stock.get('latest_price') is not None else 0.0,
                    "macd": float(stock.get('macd', 0.0)) if stock.get('macd') is not None else 0.0,
                    "analysis_result": analysis_result,  # 已标准化的分析结果
                    # base64编码后的字符串是JSON可序列化的
                    "image_base64": base64.b64encode(img_bytes).decode("utf-8") if img_bytes else ""
                }
                batch_result.append(single_result)

            except Exception as e:
                print(f"批量分析{ts_code}失败: {str(e)}")
                continue
        
        # ========== 构建最终响应：全字段可序列化 ==========
        final_response = { "data": {
                "status": "success",
                "count": int(len(batch_result)),  # 确保是int
                "total_selected": int(len(selected_stocks)),  # 确保是int
                "data": batch_result,  # list[dict]，全字段可序列化
                "timestamp": datetime.now().isoformat()  # 标准化时间字符串（替代pd.Timestamp）
            }
        }
        
        # 使用JSONResponse + 自定义编码器，兜底处理遗漏的不可序列化类型
        return JSONResponse(
            content=final_response,
            status_code=200,
            media_type="application/json"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量分析失败: {str(e)}")

@app.post("/clear-cache", summary="清理缓存")
async def clear_cache(
    cache_type: str = Body(default="all", embed=True, description="缓存类型：all/stock/kline/analysis")
):
    """清理指定类型的缓存"""
    try:
        if cache_type == "all":
            success = redis_client.clear_all_cache()
        else:
            # 按前缀删除
            keys = redis_client.client.keys(f"{cache_type}:*")
            if keys:
                redis_client.client.delete(*keys)
            success = True
        
        return {
            "status": "success" if success else "failed",
            "message": f"已清理{cache_type}类型缓存",
            "timestamp": str(pd.Timestamp.now())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理缓存失败: {str(e)}")

# ====================== 启动服务 ======================
if __name__ == "__main__":
    import uvicorn
    logger.info(f"启动K线分析服务，模型：{USE_MODEL}，端口：{PORT}")
    uvicorn.run(
        app="main:app",
        host=os.getenv("HOST"),
        port=int(os.getenv("PORT")),
        reload=True,  # 开发模式开启热重载
        log_level="info",
        workers=1
    )
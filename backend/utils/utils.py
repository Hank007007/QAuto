import base64
import http
import json
import os
import uuid
from loguru import logger
import google.generativeai as genai
from openai import OpenAI
import pandas as pd
from cache.redis_client import RedisClient
from utils.image_utils import extract_image_embedding
from config import (
    OPENAI_API_KEY, OPENAI_MODEL,
    GEMINI_API_KEY, GEMINI_MODEL,
    USE_MODEL, TEMP_DIR,USE_PROXY,
    ANALYSIS_PROMPT, LLM_TYPE, API_KEY
)

# 初始化AI客户端
clients = {}
if USE_MODEL == "chatgpt" and USE_PROXY == "false" and OPENAI_API_KEY:
    clients["openai"] = OpenAI(api_key=OPENAI_API_KEY)
    clients["proxy"] = False
elif USE_MODEL == "gemini" and USE_PROXY == "false" and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    clients["gemini"] = genai.GenerativeModel(GEMINI_MODEL)
    clients["proxy"] = False
elif USE_PROXY == "true":
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        'Accept': 'application/json',
    }
    clients["baseUrl"] = "https://poloai.top/v1/"
    clients["headers"] = headers
    clients["modelType"] = LLM_TYPE
    clients["proxy"] = True

def generate_unique_filename(extension: str) -> str:
    """
    生成唯一的文件名
    :param extension: 文件扩展名
    :return: 唯一文件名
    """
    return f"{uuid.uuid4()}.{extension.lstrip('.')}"

def save_uploaded_file(file_content: bytes, extension: str) -> str:
    """
    保存上传的文件到临时目录
    :param file_content: 文件二进制内容
    :param extension: 文件扩展名
    :return: 文件保存路径
    """
    filename = generate_unique_filename(extension)
    file_path = os.path.join(TEMP_DIR, filename)
    
    try:
        with open(file_path, "wb") as f:
            f.write(file_content)
        logger.info(f"文件保存成功：{file_path}")
        return file_path
    except Exception as e:
        logger.error(f"保存文件失败：{str(e)}")
        raise

def image_to_base64(image_path: str) -> str:
    """
    将图片转换为Base64编码
    :param image_path: 图片路径
    :return: Base64编码字符串
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"图片转Base64失败：{str(e)}")
        raise

def analyze_with_chatgpt(image_path: str) -> str:
    """
    使用ChatGPT-4V分析K线图片
    :param image_path: 图片路径
    :return: 分析结果
    """
    if "openai" not in clients:
        raise ValueError("ChatGPT客户端未初始化，请检查API密钥")
    
    try:
        # 图片转Base64
        base64_image = image_to_base64(image_path)
        
        # 调用OpenAI API
        response = clients["openai"].chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ANALYSIS_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1500,
            temperature=0.3,  # 低随机性，保证分析结果稳定
        )
        
        result = response.choices[0].message.content.strip()
        logger.info("ChatGPT分析完成")
        return result
    except Exception as e:
        logger.error(f"ChatGPT分析失败：{str(e)}")
        raise

def analyze_with_gemini(image_path: str) -> str:
    """
    使用Gemini Pro Vision分析K线图片
    :param image_path: 图片路径
    :return: 分析结果
    """
    if "gemini" not in clients:
        raise ValueError("Gemini客户端未初始化，请检查API密钥")
    
    try:
        # 读取图片
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
        
        # 调用Gemini API
        response = clients["gemini"].generate_content([
            ANALYSIS_PROMPT,
            {"mime_type": "image/jpeg", "data": image_data}
        ])
        response.resolve()
        
        result = response.text.strip()
        logger.info("Gemini分析完成")
        return result
    except Exception as e:
        logger.error(f"Gemini分析失败：{str(e)}")
        raise

async def analyze_with_Proxy(image_path: str) -> str:
    """
    使用Gemini Pro Vision分析K线图片
    :param image_path: 图片路径
    :return: 分析结果
    """      
    
    if "gpt" in clients["modelType"]:
        base64_image = image_to_base64(image_path)
        content = [
                        {"type": "text", "text": ANALYSIS_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
    elif "gemini" in clients["modelType"]:
        with open(image_path, "rb") as image_file:
                image_data = image_file.read()
        content = [ANALYSIS_PROMPT,
                        {"mime_type": "image/jpeg", "data": image_data}
                    ]
    
    
    try:
        conn = http.client.HTTPSConnection("poloai.top")
        payload = json.dumps({
            "model": "gpt-4o",
            "max_tokens": 4000,
            "temperature": 1,
            # "frequency_penalty": 0.05,
            # "presence_penalty": 0.0,
            # "top_p": 1,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ]
        })
        
        conn.request("POST", "/v1/chat/completions", payload, headers)
        res = conn.getresponse()
        data = res.read()
        result = data.decode("utf-8")
        resultjson = json.loads(result)
    
        if hasattr(data, "error"):
            
            print(f"请求失败，状态码: {resultjson.error}")
            return resultjson.error.message
        else:
            resultjson = json.loads(result)
            return resultjson["choices"][0]["message"]["content"].strip()
            
    except Exception as e:
        logger.error(f"${clients["modelType"]}分析失败：{str(e)}")
        raise

async def analyze_uploaded_kline_image(image_path: str) -> str:
    """
    统一的K线图片分析入口
    :param image_path: 图片路径
    :return: 分析结果
    """
    if USE_MODEL == "chatgpt" and USE_PROXY == "false":
        return analyze_with_chatgpt(image_path)
    elif USE_MODEL == "gemini" and USE_PROXY == "false":
        return analyze_with_gemini(image_path)
    elif USE_PROXY == "true":
        return await analyze_with_Proxy(image_path)
    else:
        raise ValueError(f"不支持的模型类型：{USE_MODEL}")

# ====================== 核心分析函数 ======================
async def analyze_kline_image(image_path: str, ts_code: str, kline_collection:any, redis_client: RedisClient, user_question: str = None) -> str:
    """
    分析K线图
    :param image_bytes: K线图二进制数据
    :param ts_code: 股票代码
    :param user_question: 分析问题（默认使用通用问题）
    :return: 分析结论
    """
    # 默认分析问题
    if not user_question:
        user_question = """分析这张A股日K线图的走势：
1. 识别K线形态和关键技术指标；
2. 结合MACD金叉信号，判断短期走势；
3. 指出支撑位、压力位；
4. 给出操作建议（注明仅为技术分析参考）。"""
    
    # 缓存分析结果
    cache_key = f"analysis:{USE_MODEL}:{ts_code}"
    cached_analysis = redis_client.get_cache(cache_key, "str")
    if cached_analysis:
        return cached_analysis
    
    try:
        with open(image_path, "rb") as image_file:
            image_bytes = image_file.read()

        # 提取图片特征
        embedding = extract_image_embedding(image_bytes)
        
        # 检索相似K线
        similar_klines = []
        if kline_collection.count() > 0:
            results = kline_collection.query(
                query_embeddings=[embedding],
                n_results=3,
                include=["metadatas", "documents", "distances"]
            )
            for idx, distance in enumerate(results["distances"][0]):
                if distance < 1.0:
                    similar_klines.append({
                        "股票代码": results["metadatas"][0][idx].get("ts_code"),
                        "相似度": round(float(distance), 4),
                        "分析": results["documents"][0][idx]
                    })
        
        # 构建提示词
        prompt = f"""
### 角色
资深A股技术分析专家，专注于MACD金叉信号的K线分析。

### 分析对象
股票代码：{ts_code}
分析问题：{user_question}

### 相似K线参考
{similar_klines if similar_klines else "无相似K线参考"}

### 分析要求
1. 基于MACD金叉信号，结合K线形态、成交量等分析短期走势；
2. 明确给出支撑位、压力位（具体数值）；
3. 操作建议需具体且注明"仅为技术分析参考，不构成投资建议"；
4. 语言简洁，逻辑清晰，使用中文作答。
        """
        
        # 调用大模型
        if USE_MODEL == "chatgpt" and USE_PROXY == "false":
            analysis_result = analyze_with_chatgpt(image_path)
        elif USE_MODEL == "gemini" and USE_PROXY == "false":
            analysis_result = analyze_with_gemini(image_path)
        elif USE_PROXY == "true":
            analysis_result = await analyze_with_Proxy(image_path)
        else:
            raise ValueError(f"不支持的模型类型：{USE_MODEL}")
        
        # 缓存分析结果
        redis_client.set_cache(cache_key, analysis_result)
        
        # 存入向量库
        kline_collection.add(
            embeddings=[embedding],
            metadatas=[{"ts_code": ts_code, "analysis_time": str(pd.Timestamp.now())}],
            documents=[analysis_result],
            ids=[f"{ts_code}_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"]
        )
        
        return analysis_result
    except Exception as e:
        raise RuntimeError(f"分析K线图失败: {str(e)}")
    
def clean_temp_file(file_path: str):
    """
    清理临时文件
    :param file_path: 文件路径
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"临时文件已删除：{file_path}")
    except Exception as e:
        logger.error(f"删除临时文件失败：{str(e)}")
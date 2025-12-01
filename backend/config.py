import os
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# 加载环境变量
load_dotenv()

# ==================== 路径配置 ====================
BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)  # 自动创建临时目录

# ==================== 日志配置 ====================
logger.add(
    BASE_DIR / "logs" / "kline_analysis.log",
    rotation="100MB",
    retention="7 days",
    compression="zip",
    level="INFO"
)

# ==================== AI模型配置 ====================
# OpenAI ChatGPT
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-vision-preview")

# Google Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro-vision")

# 选择使用的模型 (chatgpt / gemini)
USE_MODEL = os.getenv("USE_MODEL", "").lower()

# 校验模型配置
if USE_MODEL not in ["chatgpt", "gemini"]:
    logger.error(f"无效的模型配置：{USE_MODEL}，默认使用chatgpt")
    USE_MODEL = "chatgpt"

if USE_MODEL == "chatgpt" and not OPENAI_API_KEY:
    logger.error("使用ChatGPT但未配置OPENAI_API_KEY！")
elif USE_MODEL == "gemini" and not GEMINI_API_KEY:
    logger.error("使用Gemini但未配置GEMINI_API_KEY！")

USE_PROXY = os.getenv("USE_PROXY", "").lower()
LLM_TYPE = os.getenv("LLM_TYPE", "gpt-4o")
API_KEY = os.getenv("API_KEY", "")

# ==================== 服务器配置 ====================
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
MAX_FILE_SIZE = 5 * 1024 * 1024  # 最大文件大小：5MB

# ==================== 分析提示词配置 ====================
ANALYSIS_PROMPT = """
请专业分析这张A股K线图片，按照以下维度给出详细结论：
1. 趋势判断：明确说明当前股价趋势（上涨/下跌/横盘）及趋势强度；
2. 关键价位：指出明显的支撑位、压力位（如有具体数值请标注）；
3. 成交量分析：分析成交量变化与价格趋势的关联性；
4. 技术指标：解读可见的技术指标（MA/MACD/RSI/KDJ等）信号；
5. 操作建议：基于技术分析给出中立的操作参考（注明不构成投资建议）。

要求：
- 语言简洁、专业、客观；
- 仅基于图片可见信息分析，不编造数据；
- 分点清晰，逻辑连贯。
"""
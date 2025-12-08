import mplfinance as mpf
import matplotlib.pyplot as plt
import pandas as pd
import io
import os
from PIL import Image
from cache.redis_client import redis_client
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置中文字体（跨系统兼容，解决中文乱码）
plt.rcParams['font.sans-serif'] = [
    'SimHei',  # Windows默认黑体
    'WenQuanYi Micro Hei',  # Linux
    'Hiragino Sans GB',  # macOS
    'DejaVu Sans'  # 兜底
]
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

class KlineGenerator:
    """A股K线图生成器（修复dpi参数问题）"""
    def __init__(self):
        self.img_size = (10, 6)  # 图片尺寸 (宽, 高)
        self.dpi = 100  # 图片分辨率（移到savefig时指定）
        self.style = 'yahoo'  # K线样式

    def generate_kline(self, ts_code: str, df: pd.DataFrame) -> bytes:
        """
        生成日K线图
        :param ts_code: 股票代码
        :param df: 日线数据（需包含open/high/low/close/vol/trade_date）
        :return: 图片二进制数据
        """
        # 优先读取缓存（有效期2小时）
        cache_key = f"kline:image:{ts_code}"
        cached_img = redis_client.get_cache(cache_key, "bytes")
        if cached_img:
            return cached_img
        
        try:
            # ===================== 数据预处理（原有逻辑保留） =====================
            df_kline = df.copy()
            # 转换日期格式并设置为索引（适配mplfinance）
            df_kline['trade_date'] = pd.to_datetime(df_kline['trade_date'])
            df_kline = df_kline.set_index('trade_date')
            # 重命名列（mplfinance要求英文列名）
            df_kline.rename(
                columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'vol': 'Volume'},
                inplace=True
            )
            # 只保留最近30天数据
            df_kline = df_kline.tail(30)

            # ===================== 修复核心：移除mpf.plot的dpi参数，改在savefig指定 =====================
            # 1. 生成K线图（移除dpi参数，returnfig=True返回画布对象）
            fig, axes = mpf.plot(
                df_kline,
                type='candle',  # 蜡烛图类型
                style=self.style,
                volume=True,    # 显示成交量子图
                title=f'{ts_code} 日K线图（近30天）',
                ylabel='价格 (¥)',
                ylabel_lower='成交量',
                figsize=self.img_size,  # 仅保留figsize，移除dpi
                returnfig=True  # 必须返回fig对象，才能后续保存
            )

            # 2. 将图片转为二进制（在savefig时指定dpi，这是mplfinance的正确用法）
            img_buffer = io.BytesIO()
            fig.savefig(
                img_buffer,
                format='PNG',
                dpi=self.dpi,  # 在这里指定分辨率，而非mpf.plot中
                bbox_inches='tight',  # 去除白边
                pad_inches=0.1  # 轻微内边距
            )
            img_buffer.seek(0)  # 重置缓冲区指针到开头

            # ===================== 图片压缩（原有逻辑保留） =====================
            img = Image.open(img_buffer)
            img = img.convert('RGB')  # 转为RGB格式（避免透明通道问题）
            # 保存为压缩后的二进制
            img_byte_arr = io.BytesIO()
            img.save(
                img_byte_arr,
                format='PNG',
                quality=90,  # 压缩质量（1-100）
                optimize=True  # 开启优化
            )
            img_bytes = img_byte_arr.getvalue()

            # ===================== 缓存+资源清理（原有逻辑保留） =====================
            # 缓存图片到Redis（7200秒=2小时）
            redis_client.set_cache(cache_key, img_bytes, 7200)
            # 强制关闭画布，释放内存（避免matplotlib内存泄漏）
            plt.close(fig)
            return img_bytes
        except Exception as e:
            # 异常时确保画布关闭，避免资源泄漏
            try:
                plt.close('all')
            except:
                pass
            raise RuntimeError(f"生成K线图失败: {str(e)}")

# 初始化K线生成器实例（保持原有调用方式）
kline_generator = KlineGenerator()
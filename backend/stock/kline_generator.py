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

# 设置中文字体（解决中文乱码）
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class KlineGenerator:
    """A股K线图生成器"""
    def __init__(self):
        self.img_size = (10, 6)  # 图片尺寸
        self.dpi = 100  # 分辨率
        self.style = 'yahoo'  # K线样式

    def generate_kline(self, ts_code: str, df: pd.DataFrame) -> bytes:
        """
        生成日K线图
        :param ts_code: 股票代码
        :param df: 日线数据（需包含open/high/low/close/vol/trade_date）
        :return: 图片二进制数据
        """
        # 缓存K线图（有效期2小时）
        cache_key = f"kline:image:{ts_code}"
        cached_img = redis_client.get_cache(cache_key, "bytes")
        if cached_img:
            return cached_img
        
        try:
            # 数据预处理
            df_kline = df.copy()
            # 转换日期格式
            df_kline['trade_date'] = pd.to_datetime(df_kline['trade_date'])
            # 设置索引
            df_kline = df_kline.set_index('trade_date')
            # 重命名列（适配mplfinance）
            df_kline.rename(
                columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'vol': 'Volume'},
                inplace=True
            )
            # 只保留最近30天数据
            df_kline = df_kline.tail(30)
            
            # 生成K线图
            fig, axes = mpf.plot(
                df_kline,
                type='candle',  # 蜡烛图
                style=self.style,
                volume=True,    # 显示成交量
                title=f'{ts_code} 日K线图（近30天）',
                ylabel='价格 (¥)',
                ylabel_lower='成交量',
                figsize=self.img_size,
                dpi=self.dpi,
                returnfig=True
            )
            
            # 将图片转为二进制
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='PNG', bbox_inches='tight', pad_inches=0.1)
            img_buffer.seek(0)
            
            # 压缩图片（可选）
            img = Image.open(img_buffer)
            img = img.convert('RGB')
            # 保存为二进制
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG', quality=90)
            img_bytes = img_byte_arr.getvalue()
            
            # 缓存图片
            redis_client.set_cache(cache_key, img_bytes, 7200)
            
            # 清理资源
            plt.close(fig)
            return img_bytes
        except Exception as e:
            raise RuntimeError(f"生成K线图失败: {str(e)}")

# 初始化K线生成器
kline_generator = KlineGenerator()
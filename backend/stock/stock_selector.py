import baostock as bs
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os
from cache.redis_client import redis_client

# 加载环境变量
load_dotenv()

class MACDStockSelector:
    """基于MACD金叉的A股选股器（Baostock版）"""
    def __init__(self):
        # MACD参数（从.env读取，带默认值）
        self.fast_period = int(os.getenv("MACD_FAST", 12))
        self.slow_period = int(os.getenv("MACD_SLOW", 26))
        self.signal_period = int(os.getenv("MACD_SIGNAL", 9))
        self.max_stocks = int(os.getenv("STOCK_LIMIT", 50))  # 替换TUSHARE_LIMIT为STOCK_LIMIT

    def calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算MACD指标（逻辑不变）"""
        ema_fast = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        
        df['dif'] = ema_fast - ema_slow
        df['dea'] = df['dif'].ewm(span=self.signal_period, adjust=False).mean()
        df['macd'] = 2 * (df['dif'] - df['dea'])
        
        return df

    def get_stock_list(self) -> list:
        """获取A股基础列表（Baostock版）"""
        try:
            # 缓存A股列表（有效期1天）
            cache_key = "stock:basic_list"
            cached_list = redis_client.get_cache(cache_key, "list")
            if cached_list:
                return cached_list
            
            # 初始化Baostock连接
            lg = bs.login()
            if lg.error_code != '0':
                raise RuntimeError(f"Baostock登录失败: {lg.error_msg}")
            
            # 获取沪深A股列表
            stock_rs = bs.query_stock_basic(code_name="", exchange="", field="code,code_name,industry,list_date")
            stock_list = []
            while (stock_rs.error_code == '0') & stock_rs.next():
                row = stock_rs.get_row_data()
                # 格式适配（对齐原有Tushare字段）
                stock_list.append({
                    "ts_code": row[0],  # 股票代码（如600519.SH）
                    "symbol": row[0].split('.')[0],  # 纯数字代码
                    "name": row[1],  # 股票名称
                    "industry": row[2],  # 行业
                    "list_date": row[3]  # 上市日期
                })
            
            # 登出Baostock
            bs.logout()
            
            # 筛选沪深A股（排除创业板/科创板可自定义）
            stock_list = [s for s in stock_list if s['ts_code'].endswith(('SH', 'SZ'))]
            
            # 缓存结果
            redis_client.set_cache(cache_key, stock_list, 86400)
            return stock_list
        except Exception as e:
            raise RuntimeError(f"获取股票列表失败: {str(e)}")

    def get_daily_data(self, ts_code: str) -> pd.DataFrame:
        """获取股票日线数据（Baostock版）"""
        try:
            # 缓存日线数据（有效期4小时）
            cache_key = f"stock:daily:{ts_code}"
            cached_data = redis_client.get_cache(cache_key, "dict")
            if cached_data:
                df = pd.DataFrame(cached_data)
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                df = df.sort_values('trade_date').reset_index(drop=True)
                return df
            
            # 初始化Baostock连接
            lg = bs.login()
            if lg.error_code != '0':
                raise RuntimeError(f"Baostock登录失败: {lg.error_msg}")
            
            # 获取最近60天日线数据
            # Baostock代码格式：600519.SH → sh.600519
            bs_code = f"{ts_code.split('.')[1].lower()}.{ts_code.split('.')[0]}"
            daily_rs = bs.query_history_k_data_plus(
                code=bs_code,
                fields="date,open,high,low,close,volume",
                start_date="", end_date="",
                frequency="d", adjustflag="3"  # 3=不复权
            )
            
            # 转换为DataFrame
            daily_list = []
            while (daily_rs.error_code == '0') & daily_rs.next():
                row = daily_rs.get_row_data()
                daily_list.append({
                    "ts_code": ts_code,
                    "trade_date": row[0],
                    "open": float(row[1]) if row[1] else 0.0,
                    "high": float(row[2]) if row[2] else 0.0,
                    "low": float(row[3]) if row[3] else 0.0,
                    "close": float(row[4]) if row[4] else 0.0,
                    "vol": float(row[5]) if row[5] else 0.0
                })
            
            # 登出Baostock
            bs.logout()
            
            # 转换为DataFrame并排序
            df = pd.DataFrame(daily_list)
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.sort_values('trade_date').reset_index(drop=True)
            
            # 缓存结果
            redis_client.set_cache(cache_key, df.to_dict('records'), 14400)
            return df
        except Exception as e:
            raise RuntimeError(f"获取{ts_code}日线数据失败: {str(e)}")

    def is_macd_gold_cross(self, df: pd.DataFrame) -> bool:
        """判断MACD金叉（逻辑不变）"""
        if len(df) < self.slow_period + self.signal_period:
            return False
        
        last_two = df.tail(2)
        if len(last_two) < 2:
            return False
        
        prev = last_two.iloc[0]
        curr = last_two.iloc[1]
        
        gold_cross = (
            (prev['dif'] < prev['dea']) and
            (curr['dif'] > curr['dea']) and
            (prev['macd'] < 0) and
            (curr['macd'] > 0)
        )
        return gold_cross

    def select_stocks(self, fast: int = None, slow: int = None, signal: int = None) -> list:
        """执行MACD金叉选股（逻辑不变）"""
        if fast:
            self.fast_period = fast
        if slow:
            self.slow_period = slow
        if signal:
            self.signal_period = signal
        
        # 缓存选股结果（按参数缓存）
        cache_key = f"stock:macd_select:{self.fast_period}:{self.slow_period}:{self.signal_period}"
        cached_result = redis_client.get_cache(cache_key, "list")
        if cached_result:
            return cached_result
        
        try:
            stock_list = self.get_stock_list()[:self.max_stocks]
            selected_stocks = []
            
            for stock in stock_list:
                ts_code = stock['ts_code']
                try:
                    df = self.get_daily_data(ts_code)
                    if len(df) < 60:
                        continue
                    
                    df = self.calculate_macd(df)
                    if self.is_macd_gold_cross(df):
                        latest = df.tail(1).iloc[0]
                        stock['dif'] = float(latest['dif'])
                        stock['dea'] = float(latest['dea'])
                        stock['macd'] = float(latest['macd'])
                        stock['latest_price'] = float(latest['close'])
                        selected_stocks.append(stock)
                    
                    if len(selected_stocks) >= self.max_stocks:
                        break
                except Exception as e:
                    print(f"处理{ts_code}失败: {str(e)}")
                    continue
            
            redis_client.set_cache(cache_key, selected_stocks, int(os.getenv("CACHE_EXPIRE", 3600)))
            return selected_stocks
        except Exception as e:
            raise RuntimeError(f"选股失败: {str(e)}")

# 初始化选股器
try:
    stock_selector = MACDStockSelector()
except Exception as e:
    print(f"选股器初始化警告: {str(e)}")
    stock_selector = None
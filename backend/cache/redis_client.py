import datetime
from loguru import logger
import numpy as np
import pandas as pd
import redis  # 仅保留同步redis库
import json
import base64
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

# 自定义JSON编码器（处理Timestamp/numpy类型）
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # 处理numpy数值类型（如np.float64/np.int64）
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        # 处理pandas Timestamp（转为ISO标准时间字符串）
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        # 处理datetime对象
        elif isinstance(obj, datetime):
            return obj.isoformat()
        # 处理其他自定义对象（若有）：转为字典或字符串
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        # 兜底：转为字符串
        return str(obj)

class RedisClient:
    """Redis缓存客户端，封装常用缓存操作（全同步版本）"""
    def __init__(self):
        # 环境变量容错：所有配置加默认值
        self.host = os.getenv("REDIS_HOST", "127.0.0.1")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.db = int(os.getenv("REDIS_DB", 0))
        self.password = os.getenv("REDIS_PASSWORD") or None
        # 缓存过期时间：加默认值（3600秒=1小时），避免int(None)报错
        self.expire = int(os.getenv("CACHE_EXPIRE", 3600))

        # 初始化同步Redis客户端
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=False,  # 图片二进制需关闭解码
                socket_connect_timeout=10,
                socket_timeout=10
            )
            # 初始化时检查连接
            self.ping()
            logger.info("Redis客户端初始化成功")
        except Exception as e:
            logger.error(f"Redis客户端初始化失败: {str(e)}")
            raise RuntimeError(f"Redis连接失败: {str(e)}")

    def ping(self) -> bool:
        """检查Redis连接（同步）"""
        logger.info("检查Redis连接----------")
        try:
            result = self.client.ping()
            logger.info("Redis连接正常----------")
            return result
        except Exception as e:
            logger.error(f"Redis连接失败----------: {str(e)}")
            print(f"Redis连接失败: {str(e)}")
            return False

    def set_cache(self, key: str, value: any, expire: int = None) -> bool:
        """
        设置缓存（同步）
        :param key: 缓存键
        :param value: 缓存值（支持str/dict/list/bytes）
        :param expire: 过期时间（默认使用全局配置）
        """
        try:
            expire = expire or self.expire
            logger.info(f"设置缓存----------: {key}，过期时间: {expire}s")

            # 处理不同类型的值
            if isinstance(value, dict) or isinstance(value, list):
                logger.info(f"缓存内容（前100字节）: {str(value)[:100]}")
                # 序列化后转字节，避免乱码
                value = json.dumps(value, ensure_ascii=False, cls=CustomJSONEncoder).encode("utf-8")
                self.client.setex(key, expire, value)
            elif isinstance(value, bytes):
                logger.info(f"缓存内容为二进制数据，长度: {len(value)}字节")
                self.client.setex(key, expire, value)
            else:
                logger.info(f"缓存内容（前100字节）: {str(value)[:100]}")
                # 字符串转字节存储，统一编码
                self.client.setex(key, expire, str(value).encode("utf-8"))
            logger.info(f"缓存{key}设置成功")
            return True
        except Exception as e:
            logger.error(f"设置缓存失败----------: {key} -> {str(e)}")
            print(f"设置缓存失败: {str(e)}")
            return False

    def get_cache(self, key: str, data_type: str = "str") -> any:
        """
        获取缓存（同步）
        :param key: 缓存键
        :param data_type: 数据类型（str/dict/list/bytes）
        """
        try:
            value = self.client.get(key)
            if value is None:
                logger.info(f"缓存{key}不存在")
                return None
            
            # 按类型解析
            if data_type == "dict" or data_type == "list":
                result = json.loads(value.decode("utf-8"))
            elif data_type == "bytes":
                result = value
            else:
                result = value.decode("utf-8")
            logger.info(f"获取缓存{key}成功，数据类型: {data_type}")
            return result
        except Exception as e:
            logger.error(f"获取缓存失败----------: {key} -> {str(e)}")
            print(f"获取缓存失败: {str(e)}")
            return None

    def delete_cache(self, key: str) -> bool:
        """删除指定缓存（同步）"""
        try:
            self.client.delete(key)
            logger.info(f"删除缓存{key}成功")
            return True
        except Exception as e:
            logger.error(f"删除缓存失败----------: {key} -> {str(e)}")
            print(f"删除缓存失败: {str(e)}")
            return False

    def clear_all_cache(self) -> bool:
        """清空当前数据库所有缓存（谨慎使用）"""
        try:
            self.client.flushdb()
            logger.warning("清空当前Redis数据库所有缓存！")
            return True
        except Exception as e:
            logger.error(f"清空缓存失败----------: {str(e)}")
            print(f"清空缓存失败: {str(e)}")
            return False

# 初始化Redis客户端单例
redis_client = RedisClient()
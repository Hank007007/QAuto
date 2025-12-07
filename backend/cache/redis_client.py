import redis
import json
import base64
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

class RedisClient:
    """Redis缓存客户端，封装常用缓存操作"""
    def __init__(self):
        self.client = redis.Redis(
            host=os.getenv("REDIS_HOST", "127.0.0.1"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            password=os.getenv("REDIS_PASSWORD") or None,
            decode_responses=False,  # 图片二进制需关闭解码
            socket_connect_timeout=10,
            socket_timeout=10
        )
        # 缓存过期时间（秒）
        self.expire = int(os.getenv("CACHE_EXPIRE"))

    def ping(self) -> bool:
        """检查Redis连接"""
        try:
            return self.client.ping()
        except Exception as e:
            print(f"Redis连接失败: {str(e)}")
            return False

    def set_cache(self, key: str, value: any, expire: int = None) -> bool:
        """
        设置缓存
        :param key: 缓存键
        :param value: 缓存值（支持str/dict/list/bytes）
        :param expire: 过期时间（默认使用全局配置）
        """
        try:
            expire = expire or self.expire
            # 处理不同类型的值
            if isinstance(value, dict) or isinstance(value, list):
                value = json.dumps(value, ensure_ascii=False)
                self.client.setex(key, expire, value)
            elif isinstance(value, bytes):
                self.client.setex(key, expire, value)
            else:
                self.client.setex(key, expire, str(value))
            return True
        except Exception as e:
            print(f"设置缓存失败: {str(e)}")
            return False

    def get_cache(self, key: str, data_type: str = "str") -> any:
        """
        获取缓存
        :param key: 缓存键
        :param data_type: 数据类型（str/dict/list/bytes）
        """
        try:
            value = self.client.get(key)
            if value is None:
                return None
            
            # 按类型解析
            if data_type == "dict" or data_type == "list":
                return json.loads(value.decode("utf-8"))
            elif data_type == "bytes":
                return value
            else:
                return value.decode("utf-8")
        except Exception as e:
            print(f"获取缓存失败: {str(e)}")
            return None

    def delete_cache(self, key: str) -> bool:
        """删除指定缓存"""
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            print(f"删除缓存失败: {str(e)}")
            return False

    def clear_all_cache(self) -> bool:
        """清空当前数据库所有缓存（谨慎使用）"""
        try:
            self.client.flushdb()
            return True
        except Exception as e:
            print(f"清空缓存失败: {str(e)}")
            return False

# 初始化Redis客户端单例
redis_client = RedisClient()
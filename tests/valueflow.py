import akshare as ak
import pandas as pd

# 获取A股实时行情（含成交额、外盘）
df_spot = ak.stock_zh_a_spot()  # 东方财富数据源，可能包含外盘字段

# 筛选成交额前100名个股
active_stocks = df_spot.sort_values(by="成交额", ascending=False).head(100)

# 计算外盘总和与总成交量
total_vol = active_stocks["成交量"].sum()
total_outside = active_stocks["外盘"].sum()

# 外盘占比（%）
outside_ratio = (total_outside / total_vol) * 100
print(f"活跃个股外盘占比：{outside_ratio:.2f}%")
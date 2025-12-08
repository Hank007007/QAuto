import axios from 'axios';
import { message } from 'antd';
import {
  UploadResponse,
  HealthCheckResponse,
  SelectStocksResponse,
  GenerateKlineResponse,
  AnalyzeStockResponse,
  BatchAnalyzeResponse,
  ClearCacheResponse
} from '../types/APITypes';

// 创建axios实例
const apiClient = axios.create({
  timeout: 120000, // 批量分析超时2分钟（AI分析可能耗时较长）
  headers: {
    'Content-Type': 'application/json;charset=utf-8',
  },
});

/**
 * 上传K线图片并获取AI分析结果
 * @param file 选中的图片文件
 * @returns 分析结果
 */
export const uploadKlineImage = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('kline_image', file);

  try {
    const response = await apiClient.post<UploadResponse>('/api/analyze-kline', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error: any) {
    console.error('K线图片分析失败:', error);
    return {
      success: false,
      error: error.response?.data?.error || '分析失败，请检查网络或API配置',
    };
  }
};

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => config,
  (error) => {
    message.error(`请求错误: ${error.message}`);
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const errMsg = error.response?.data?.detail || error.message || '请求失败';
    message.error(errMsg);
    return Promise.reject(error);
  }
);

// 健康检查
export const healthCheck = async (): Promise<HealthCheckResponse> => {
  const response = await apiClient.get<HealthCheckResponse>('/api/health');
  return response.data;
};

// MACD选股
export const selectStocks = async (
  fast?: number,
  slow?: number,
  signal?: number
): Promise<SelectStocksResponse> => {
  const response = await apiClient.get<SelectStocksResponse>('/api/select-stocks', {
    params: { fast, slow, signal }
  });
  return response.data;
};

// 生成K线图
export const generateKline = async (ts_code: string): Promise<GenerateKlineResponse> => {
  const response = await apiClient.get<GenerateKlineResponse>('/api/generate-kline', {
    params: { ts_code }
  });
  return response.data;
};

// 分析单只股票
export const analyzeStock = async (
  ts_code: string,
  user_question?: string
): Promise<AnalyzeStockResponse> => {
  const response = await apiClient.post<AnalyzeStockResponse>('/api/analyze-stock', {
    ts_code,
    user_question
  });
  return response.data;
};

// 批量分析
export const batchAnalyze = async (
  fast?: number,
  slow?: number,
  signal?: number
): Promise<BatchAnalyzeResponse> => {
  const response = await apiClient.post<BatchAnalyzeResponse>('/api/batch-analyze', {
    fast,
    slow,
    signal
  });
  return response.data;
};

// 清理缓存
export const clearCache = async (cache_type: string = "all"): Promise<ClearCacheResponse> => {
  const response = await apiClient.post<ClearCacheResponse>('/api/clear-cache', {
    cache_type
  });
  return response.data;
};

export default apiClient;
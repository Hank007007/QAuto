import axios from 'axios';
import { UploadResponse } from '../types';

// 创建axios实例
const api = axios.create({
  timeout: 60000, // 超时时间60秒（AI分析可能耗时较长）
  headers: {
    'Content-Type': 'application/json',
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
    const response = await api.post<UploadResponse>('/api/analyze-kline', formData, {
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
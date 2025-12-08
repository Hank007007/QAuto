/**
 * 分析结果类型定义
 */
export interface AnalysisResult {
    success: boolean;
    data?: string;
    error?: string;
  }
  
/**
 * 上传响应类型
 */
export interface UploadResponse extends AnalysisResult {}

/**
 * 文件上传状态
 */
export type UploadStatus = 'idle' | 'loading' | 'success' | 'error';

  // 健康检查响应
export interface HealthCheckResponse {
  status: string;
  redis_connected: boolean;
  chroma_count: number;
  llm_type: string;
  timestamp: string;
}

// 股票基础信息
export interface StockBasic {
  ts_code: string;
  symbol: string;
  name: string;
  industry: string;
  list_date: string;
  dif?: number;
  dea?: number;
  macd?: number;
  latest_price?: number;
}

// 选股响应
export interface SelectStocksResponse {
  status: string;
  count: number;
  data: StockBasic[];
  timestamp: string;
}

// K线图响应
export interface GenerateKlineResponse {
  status: string;
  ts_code: string;
  image_base64: string;
  timestamp: string;
}

// 单股票分析响应
export interface AnalyzeStockResponse {
  status: string;
  ts_code: string;
  stock_name: string;
  image_base64: string;
  analysis_result: string;
  timestamp: string;
  llm_type: string;
}

// 批量分析结果项
export interface BatchAnalysisItem {
  ts_code: string;
  stock_name: string;
  industry: string;
  latest_price?: number;
  macd?: number;
  image_base64: string;
  analysis_result: string;
}

// 批量分析响应
export interface BatchAnalyzeResponse {
  status: string;
  count: number;
  total_selected: number;
  data: BatchAnalysisItem[];
  timestamp: string;
}

// 清理缓存响应
export interface ClearCacheResponse {
  status: string;
  message: string;
  timestamp: string;
}
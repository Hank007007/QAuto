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
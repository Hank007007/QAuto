import React from 'react';
import { useState, useRef, useEffect } from 'react';
import { uploadKlineImage } from '../services/api';
import { AnalysisResult, UploadStatus } from '../types/APITypes';
import AnalysisResultView from './AnalysisResult';

const KlineUploader = () => {
  // 状态管理
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 清理预览URL
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  /**
   * 处理文件选择
   */
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 校验文件类型
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      alert('仅支持JPG/PNG/WEBP格式的图片文件！');
      return;
    }

    // 校验文件大小（最大5MB）
    const maxSize = 5 * 1024 * 1024; // 5MB
    if (file.size > maxSize) {
      alert('图片大小不能超过5MB！');
      return;
    }

    // 更新状态
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setAnalysisResult(null);
    setUploadStatus('idle');
  };

  /**
   * 处理文件上传
   */
  const handleUpload = async () => {
    if (!selectedFile) {
      alert('请先选择要分析的K线图片！');
      return;
    }

    setUploadStatus('loading');
    try {
      const result = await uploadKlineImage(selectedFile);
      setAnalysisResult(result);
      setUploadStatus(result.success ? 'success' : 'error');
    } catch (error) {
      setUploadStatus('error');
      setAnalysisResult({
        success: false,
        error: '上传失败，请重试！',
      });
    }
  };

  /**
   * 清空选择
   */
  const handleClear = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setAnalysisResult(null);
    setUploadStatus('idle');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // 样式定义
  const styles = {
    container: {
      backgroundColor: '#fff',
      borderRadius: '12px',
      padding: '30px',
      boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
    },
    title: {
      fontSize: '24px',
      color: '#1f2937',
      textAlign: 'center',
      marginBottom: '30px',
      fontWeight: '600',
    },
    uploadArea: {
      display: 'flex',
      gap: '12px',
      marginBottom: '20px',
      flexWrap: 'wrap',
      alignItems: 'center',
    },
    fileInput: {
      display: 'none',
    },
    button: {
      padding: '10px 20px',
      borderRadius: '8px',
      border: 'none',
      cursor: 'pointer',
      fontSize: '14px',
      fontWeight: '500',
      transition: 'all 0.2s',
    },
    selectButton: {
      ...{ backgroundColor: '#4285f4', color: '#fff' },
      ':hover': { backgroundColor: '#3367d6' },
    },
    uploadButton: {
      ...{ backgroundColor: '#0f9d58', color: '#fff' },
      ':hover': { backgroundColor: '#0d884e' },
      ':disabled': { backgroundColor: '#9be3c3', cursor: 'not-allowed' },
    },
    clearButton: {
      ...{ backgroundColor: '#f87171', color: '#fff' },
      ':hover': { backgroundColor: '#dc2626' },
    },
    previewArea: {
      marginBottom: '20px',
      padding: '15px',
      border: '1px dashed #d1d5db',
      borderRadius: '8px',
      textAlign: 'center',
    },
    previewImage: {
      maxWidth: '100%',
      maxHeight: '400px',
      borderRadius: '8px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    },
    previewText: {
      color: '#6b7280',
      fontSize: '14px',
    },
  } as const;

  return (
    <div style={styles.container}>
      <h2 style={styles.title}>A股K线图片AI分析工具 v1.0</h2>

      {/* 文件上传区域 */}
      <div style={styles.uploadArea}>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="image/jpeg,image/png,image/webp"
          style={styles.fileInput}
          id="kline-file-input"
        />
        <label htmlFor="kline-file-input" style={{ ...styles.button, ...styles.selectButton, cursor: 'pointer' }}>
          选择K线图片
        </label>

        <button
          onClick={handleUpload}
          disabled={uploadStatus === 'loading' || !selectedFile}
          style={{
            ...styles.button,
            ...styles.uploadButton,
            opacity: uploadStatus === 'loading' || !selectedFile ? 0.7 : 1,
          }}
        >
          {uploadStatus === 'loading' ? 'AI分析中...' : '上传并分析'}
        </button>

        <button
          onClick={handleClear}
          disabled={uploadStatus === 'loading'}
          style={{
            ...styles.button,
            ...styles.clearButton,
            opacity: uploadStatus === 'loading' ? 0.7 : 1,
          }}
        >
          清空
        </button>
      </div>

      {/* 图片预览区域 */}
      <div style={styles.previewArea}>
        {previewUrl ? (
          <img src={previewUrl} alt="K线图片预览" style={styles.previewImage} />
        ) : (
          <p style={styles.previewText}>未选择图片，支持JPG/PNG/WEBP格式（最大5MB）</p>
        )}
      </div>

      {/* 分析结果展示 */}
      {analysisResult && <AnalysisResultView result={analysisResult} />}
    </div>
  );
};

export default KlineUploader;
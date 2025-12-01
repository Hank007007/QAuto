import { AnalysisResult } from '../types';

interface AnalysisResultProps {
  result: AnalysisResult;
}

const AnalysisResultView = ({ result }: AnalysisResultProps) => {
  // 样式定义
  const styles = {
    container: {
      marginTop: '20px',
      padding: '20px',
      borderRadius: '8px',
      border: '1px solid #e5e7eb',
      backgroundColor: '#fff',
    },
    title: {
      fontSize: '18px',
      fontWeight: '600',
      marginBottom: '15px',
      color: '#1f2937',
    },
    successContainer: {
      color: '#1f2937',
      lineHeight: '1.8',
      fontSize: '14px',
    },
    errorContainer: {
      color: '#dc2626',
      fontSize: '14px',
      fontWeight: '500',
    },
    line: {
      margin: '8px 0',
      whiteSpace: 'pre-wrap',
    },
    successIcon: {
      color: '#10b981',
      marginRight: '8px',
    },
    errorIcon: {
      color: '#dc2626',
      marginRight: '8px',
    },
  } as const;

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>
        {result.success ? (
          <span>
            <span style={styles.successIcon}>✅</span> AI分析结果
          </span>
        ) : (
          <span>
            <span style={styles.errorIcon}>❌</span> 分析失败
          </span>
        )}
      </h3>

      {result.success ? (
        <div style={styles.successContainer}>
          {result.data?.split('\n').map((line, index) => (
            <p key={index} style={styles.line}>{line}</p>
          ))}
          <p style={{ marginTop: '20px', color: '#6b7280', fontSize: '12px' }}>
            ⚠️ 分析结果仅作参考，不构成任何投资建议
          </p>
        </div>
      ) : (
        <div style={styles.errorContainer}>
          {result.error || '未知错误'}
        </div>
      )}
    </div>
  );
};

export default AnalysisResultView;
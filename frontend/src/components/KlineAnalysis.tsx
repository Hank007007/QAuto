import React, { useState, useEffect } from 'react';
import { Card, Collapse, Image, Typography, Button, Space, message, Tag } from 'antd';
import { BatchAnalysisItem, AnalyzeStockResponse } from '../types/APITypes';
import { batchAnalyze, clearCache } from '../services/api';

const { Panel } = Collapse;
const { Title, Text } = Typography;

interface KlineAnalysisProps {
  fast?: number;
  slow?: number;
  signal?: number;
}

const KlineAnalysis: React.FC<KlineAnalysisProps> = ({ fast, slow, signal }) => {
  const [loading, setLoading] = useState<boolean>(false);
  const [singleResult, setSingleResult] = useState<AnalyzeStockResponse | null>(null);
  const [batchResult, setBatchResult] = useState<BatchAnalysisItem[]>([]);
  const [batchCount, setBatchCount] = useState<number>(0);

  // 监听单股票分析完成事件
  useEffect(() => {
    const handleStockAnalyzed = (e: CustomEvent) => {
      setSingleResult(e.detail);
      setBatchResult([]); // 清空批量结果
    };

    window.addEventListener('stockAnalyzed', handleStockAnalyzed as EventListener);
    return () => {
      window.removeEventListener('stockAnalyzed', handleStockAnalyzed as EventListener);
    };
  }, []);

  // 批量分析
  const handleBatchAnalyze = async () => {
    try {
      setLoading(true);
      const result = await batchAnalyze(fast, slow, signal);
      setBatchResult(result.data);
      setBatchCount(result.count);
      setSingleResult(null); // 清空单股票结果
      message.success(`批量分析完成，共分析${result.count}只股票`);
    } catch (error) {
      console.error('批量分析失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 清理缓存
  const handleClearCache = async () => {
    try {
      await clearCache();
      message.success('缓存清理完成');
    } catch (error) {
      console.error('清理缓存失败:', error);
    }
  };

  // 渲染单股票分析结果
  const renderSingleResult = () => {
    if (!singleResult) return null;

    return (
      <Card
        title={`${singleResult.stock_name} (${singleResult.ts_code}) 分析结果`}
        style={{ marginBottom: 20 }}
        extra={
          <Space>
            <Text type="secondary">{singleResult.timestamp}</Text>
            <Tag>{singleResult.llm_type.includes('gpt') ? 'GPT-4V' : 'Gemini'}</Tag>
          </Space>
        }
      >
        <Collapse defaultActiveKey={['1', '2']}>
          <Panel header="K线图" key="1">
            <Image
              src={`data:image/png;base64,${singleResult.image_base64}`}
              alt={`${singleResult.ts_code} K线图`}
              style={{ maxWidth: '100%' }}
            />
          </Panel>
          <Panel header="分析结论" key="2">
            <div style={{
              padding: 16,
              lineHeight: 1.8,
              fontSize: 14,
              whiteSpace: 'pre-line',
              backgroundColor: '#f9f9f9',
              borderRadius: 6
            }}>
              {singleResult.analysis_result}
            </div>
          </Panel>
        </Collapse>
      </Card>
    );
  };

  // 渲染批量分析结果
  const renderBatchResult = () => {
    if (batchResult.length === 0) return null;

    return (
      <div style={{ marginBottom: 20 }}>
        <Title level={5} style={{ marginBottom: 10 }}>
          批量分析结果（共{batchCount}只）
        </Title>
        {batchResult.map((item) => (
          <Card
            key={item.ts_code}
            title={`${item.stock_name} (${item.ts_code}) - ${item.industry}`}
            style={{ marginBottom: 10 }}
          >
            <Collapse defaultActiveKey={['2']}>
              <Panel header="K线图" key="1">
                <Image
                  src={`data:image/png;base64,${item.image_base64}`}
                  alt={`${item.ts_code} K线图`}
                  style={{ maxWidth: '100%' }}
                />
              </Panel>
              <Panel header="分析结论" key="2">
                <div style={{
                  padding: 16,
                  lineHeight: 1.8,
                  fontSize: 14,
                  whiteSpace: 'pre-line',
                  backgroundColor: '#f9f9f9',
                  borderRadius: 6
                }}>
                  {item.analysis_result}
                </div>
              </Panel>
            </Collapse>
          </Card>
        ))}
      </div>
    );
  };

  return (
    <div>
      <Space style={{ marginBottom: 20 }}>
        <Button
          type="primary"
          loading={loading}
          onClick={handleBatchAnalyze}
        >
          批量分析选股结果
        </Button>
        <Button
          danger
          onClick={handleClearCache}
        >
          清理缓存
        </Button>
      </Space>

      {renderSingleResult()}
      {renderBatchResult()}
    </div>
  );
};

export default KlineAnalysis;
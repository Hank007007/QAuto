import React, { useState, useEffect } from 'react';
import { Layout, Typography, Space, Tag, message } from 'antd';
import { HealthCheckResponse, SelectStocksResponse } from './types/APITypes';
import { healthCheck } from './services/api';
import StockSelector from './components/StockSelector';
import StockList from './components/StockList';
import KlineAnalysis from './components/KlineAnalysis';
import KlineUploader from './components/KlineUploader';

const { Header, Content, Footer } = Layout;
const { Title, Text } = Typography;

const App: React.FC = () => {
  const [healthStatus, setHealthStatus] = useState<HealthCheckResponse | null>(null);
  const [selectedStocks, setSelectedStocks] = useState<SelectStocksResponse | null>(null);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [macdParams, setMacdParams] = useState<{
    fast?: number;
    slow?: number;
    signal?: number;
  }>({});

  // 健康检查
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await healthCheck();
        setHealthStatus(res);
        if (!res.redis_connected) {
          message.warning('Redis连接失败，缓存功能不可用');
        }
      } catch (error) {
        message.error('服务健康检查失败，请检查后端服务');
        console.error('健康检查失败:', error);
      }
    };
    checkHealth();
  }, []);

  // 选股完成回调
  const handleSelectComplete = (data: SelectStocksResponse) => {
    setSelectedStocks(data);
    // 保存选股参数
    setMacdParams({
      fast: data.data.length > 0 ? macdParams.fast : undefined,
      slow: data.data.length > 0 ? macdParams.slow : undefined,
      signal: data.data.length > 0 ? macdParams.signal : undefined
    });
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 头部 */}
      <Header style={{
        backgroundColor: 'white',
        boxShadow: '0 2px 12px 0 rgba(0,0,0,0.05)',
        padding: '0 24px'
      }}>
        <Space align="center" style={{ width: '100%', display: 'flex', justifyContent: 'space-between' }}>
          <Title level={2} style={{ margin: 0, color: '#1890ff' }}>
            A股K线图AI分析工具 v2.0
          </Title>
          {healthStatus && (
            <Space>
              <Tag color={healthStatus.redis_connected ? 'success' : 'error'}>
                Redis: {healthStatus.redis_connected ? '已连接' : '未连接'}
              </Tag>
              <Tag>{healthStatus.llm_type === 'gpt-4v' ? 'GPT-4V' : 'Gemini'}</Tag>
            </Space>
          )}
        </Space>
      </Header>

      {/* 内容区 */}
      <Content style={{
        padding: '24px',
        maxWidth: 1400,
        margin: '0 auto',
        width: '100%'
      }}>
        {/* 服务状态提示 */}
        {healthStatus && (
          <Text
            type={healthStatus.status === 'healthy' ? 'success' : 'danger'}
            style={{ marginBottom: 20, display: 'block' }}
          >
            服务状态: {healthStatus.status} | 向量库数据量: {healthStatus.chroma_count} | 更新时间: {healthStatus.timestamp}
          </Text>
        )}

        {/* 选股组件 */}
        <StockSelector onSelectComplete={handleSelectComplete} />

        {/* 选股结果 */}
        {selectedStocks && (
          <StockList
            data={selectedStocks}
            onAnalyzeStart={() => setAnalyzing(true)}
          />
        )}

        {/* 分析结果 */}
        <KlineAnalysis {...macdParams} />
        
        <KlineUploader />

      </Content>

      {/* 底部 */}
      <Footer style={{
        textAlign: 'center',
        backgroundColor: 'white',
        boxShadow: '0 -2px 12px 0 rgba(0,0,0,0.05)'
      }}>
        <Text type="secondary">
          免责声明：本工具仅提供技术分析参考，不构成任何投资建议，投资有风险，入市需谨慎
        </Text>
      </Footer>
    </Layout>
  );
};

export default App;
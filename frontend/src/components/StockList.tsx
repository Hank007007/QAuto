import React from 'react';
import { Table, Button, Space, Typography, Tag } from 'antd';
import { StockBasic, SelectStocksResponse } from '../types/APITypes';
import { analyzeStock } from '../services/api';

const { Title, Text } = Typography;

interface StockListProps {
  data: SelectStocksResponse;
  onAnalyzeStart: () => void;
}

const StockList: React.FC<StockListProps> = ({ data, onAnalyzeStart }) => {
  // 表格列配置
  const columns = [
    {
      title: '股票代码',
      dataIndex: 'ts_code',
      key: 'ts_code',
      width: 120,
    },
    {
      title: '股票名称',
      dataIndex: 'name',
      key: 'name',
      width: 120,
    },
    {
      title: '行业',
      dataIndex: 'industry',
      key: 'industry',
      width: 150,
    },
    {
      title: '最新价格',
      dataIndex: 'latest_price',
      key: 'latest_price',
      width: 100,
      render: (price?: number) => price ? `${price.toFixed(2)}` : '-',
    },
    {
      title: 'MACD值',
      dataIndex: 'macd',
      key: 'macd',
      width: 100,
      render: (macd?: number) => (
        <Tag color={macd && macd > 0 ? 'success' : 'default'}>
          {macd ? macd.toFixed(4) : '-'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: StockBasic) => (
        <Space size="small">
          <Button
            type="primary"
            size="small"
            onClick={() => handleAnalyze(record.ts_code)}
          >
            分析
          </Button>
        </Space>
      ),
    },
  ];

  // 分析单只股票
  const handleAnalyze = async (ts_code: string) => {
    try {
      onAnalyzeStart();
      const result = await analyzeStock(ts_code);
      // 触发父组件更新分析结果
      window.dispatchEvent(new CustomEvent('stockAnalyzed', { detail: result }));
    } catch (error) {
      console.error('分析股票失败:', error);
    }
  };

  if (data.count === 0) {
    return (
      <div style={{ textAlign: 'center', padding: 20, backgroundColor: 'white', borderRadius: 8 }}>
        <Text type="warning">暂无符合MACD金叉条件的股票</Text>
      </div>
    );
  }

  return (
    <div style={{ marginBottom: 20 }}>
      <Title level={5} style={{ marginBottom: 10 }}>
        选股结果（共{data.count}只）
      </Title>
      <Table
        dataSource={data.data}
        columns={columns}
        bordered
        rowKey="ts_code"
        pagination={{ pageSize: 10 }}
        scroll={{ x: 'max-content' }}
      />
    </div>
  );
};

export default StockList;
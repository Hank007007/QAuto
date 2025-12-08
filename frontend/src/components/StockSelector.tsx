import React, { useState } from 'react';
import { Form, InputNumber, Button, Card, Typography, Space, message } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { selectStocks } from '../services/api';
import { SelectStocksResponse } from '../types/APITypes';

const { Title, Text } = Typography;

interface StockSelectorProps {
  onSelectComplete: (data: SelectStocksResponse) => void;
}

const StockSelector: React.FC<StockSelectorProps> = ({ onSelectComplete }) => {
  const [loading, setLoading] = useState<boolean>(false);
  const [form] = Form.useForm();

  // 选股参数默认值
  const defaultValues = {
    fast: 12,
    slow: 26,
    signal: 9
  };

  // 执行选股
  const handleSelect = async () => {
    try {
      setLoading(true);
      const values = form.getFieldsValue();
      const result = await selectStocks(values.fast, values.slow, values.signal);
      message.success(`选股完成，共筛选出${result.count}只符合MACD金叉条件的股票`);
      onSelectComplete(result);
    } catch (error) {
      console.error('选股失败:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      title="MACD金叉选股参数 V2.0"
      style={{ marginBottom: 20, boxShadow: '0 2px 12px 0 rgba(0,0,0,0.05)' }}
    >
      <Form
        form={form}
        layout="inline"
        initialValues={defaultValues}
        style={{ marginBottom: 20 }}
      >
        <Form.Item label="快速周期" name="fast">
          <InputNumber min= {1} max={30} style={{ width: 100 }} />
        </Form.Item>
        <Form.Item label="慢速周期" name="slow">
          <InputNumber min={10} max={50} style={{ width: 100 }} />
        </Form.Item>
        <Form.Item label="信号周期" name="signal">
          <InputNumber min={1} max={20} style={{ width: 100 }} />
        </Form.Item>
        <Form.Item>
          <Button
            type="primary"
            icon={<SearchOutlined />}
            loading={loading}
            onClick={handleSelect}
          >
            开始选股
          </Button>
        </Form.Item>
      </Form>
      
      <Text type="secondary">
        选股逻辑：DIF上穿DEA，且MACD由负转正（金叉），默认参数：快速周期12，慢速周期26，信号周期9
      </Text>
    </Card>
  );
};

export default StockSelector;
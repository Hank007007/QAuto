import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import App from './App';

// 全局样式
const globalStyle = {
  margin: 0,
  padding: 0,
  boxSizing: 'border-box',
  fontFamily: 'Arial, Helvetica, sans-serif',
  backgroundColor: '#f5f7fa',
};

Object.assign(document.body.style, globalStyle);

// 渲染根组件
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN}>
      <App />
    </ConfigProvider>
  </React.StrictMode>,
);
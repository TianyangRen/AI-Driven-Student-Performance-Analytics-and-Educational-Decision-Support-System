import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import enUS from 'antd/locale/en_US';
import App from './App.jsx';
import { AuthProvider } from './contexts/AuthContext.jsx';
import { cockpitTheme } from './theme/antdTheme';
import 'antd/dist/reset.css';
import './styles/global.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider locale={enUS} theme={cockpitTheme}>
      <AntApp>
        <BrowserRouter>
          <AuthProvider>
            <App />
          </AuthProvider>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>
);

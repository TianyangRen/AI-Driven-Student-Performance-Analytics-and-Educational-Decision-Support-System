import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import enUS from 'antd/locale/en_US';
import zhCN from 'antd/locale/zh_CN';
import App from './App.jsx';
import { AuthProvider } from './contexts/AuthContext.jsx';
import { PreferencesProvider, useI18n } from './contexts/PreferencesContext.jsx';
import { buildTheme } from './theme/antdTheme';
import 'antd/dist/reset.css';
import './styles/global.css';

function ThemedApp() {
  const { mode, lang } = useI18n();
  return (
    <ConfigProvider locale={lang === 'zh' ? zhCN : enUS} theme={buildTheme(mode)}>
      <AntApp>
        <BrowserRouter>
          <AuthProvider>
            {/* Remount routed content on theme change so inline styles and
                ECharts options rebuild with the active palette. */}
            <App key={mode} />
          </AuthProvider>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <PreferencesProvider>
      <ThemedApp />
    </PreferencesProvider>
  </React.StrictMode>
);

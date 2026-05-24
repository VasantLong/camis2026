import { Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, App as AntApp } from "antd";
import zhCN from "antd/locale/zh_CN";

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <AntApp>
        <Routes>
          <Route path="/" element={<Navigate to="/activities" replace />} />
          <Route path="*" element={<div>404 - Page Not Found</div>} />
        </Routes>
      </AntApp>
    </ConfigProvider>
  );
}

export default App;

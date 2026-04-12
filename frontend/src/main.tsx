import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { SelectedProfileProvider } from './context/SelectedProfileContext'
import './index.css'
import { themeConfig } from './theme/config'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <SelectedProfileProvider>
          <ConfigProvider theme={themeConfig}>
            <App />
          </ConfigProvider>
        </SelectedProfileProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)

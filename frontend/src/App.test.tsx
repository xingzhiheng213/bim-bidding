import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import type { ReactNode } from 'react'
import App from './App'
import { themeConfig } from './theme/config'

function TestProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter initialEntries={['/']}>
        <ConfigProvider theme={themeConfig}>{children}</ConfigProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('App', () => {
  it('renders shell with app title', async () => {
    render(<App />, { wrapper: TestProviders })
    expect(await screen.findByText('BIM 标书生成')).toBeInTheDocument()
  })
})

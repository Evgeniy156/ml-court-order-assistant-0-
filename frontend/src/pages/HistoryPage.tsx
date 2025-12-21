import { useEffect, useState } from 'react'
import { Card, Table, Tag, Pagination, Spin, message } from 'antd'
import { webService } from '../services/api'
import type { ColumnsType } from 'antd/es/table'

interface HistoryItem {
  id: number
  amount: number
  type: string
  description: string | null
  created_at: string
}

interface HistoryResponse {
  items: HistoryItem[]
  total: number
  page: number
  limit: number
  total_pages: number
}

const HistoryPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<HistoryResponse | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 20

  useEffect(() => {
    loadHistory(currentPage)
  }, [currentPage])

  const loadHistory = async (page: number) => {
    try {
      setLoading(true)
      const historyData = await webService.getHistory(page, pageSize)
      setData(historyData)
    } catch (error: any) {
      message.error('Ошибка загрузки истории транзакций')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const columns: ColumnsType<HistoryItem> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: 'Сумма',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount: number) => (
        <span style={{ color: amount >= 0 ? '#52c41a' : '#ff4d4f', fontWeight: 'bold' }}>
          {amount >= 0 ? '+' : ''}{amount.toFixed(2)} кредитов
        </span>
      ),
    },
    {
      title: 'Тип',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const colorMap: Record<string, string> = {
          deposit: 'green',
          withdraw: 'red',
        }
        return (
          <Tag color={colorMap[type] || 'default'}>
            {type === 'deposit' ? 'Пополнение' : type === 'withdraw' ? 'Списание' : type}
          </Tag>
        )
      },
    },
    {
      title: 'Описание',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'Дата и время',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString('ru-RU'),
      width: 200,
    },
  ]

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>История транзакций</h1>
      <Card>
        <Spin spinning={loading}>
          <Table
            columns={columns}
            dataSource={data?.items || []}
            rowKey="id"
            pagination={false}
            loading={loading}
          />
          {data && data.total_pages > 1 && (
            <div style={{ marginTop: 16, textAlign: 'right' }}>
              <Pagination
                current={currentPage}
                total={data.total}
                pageSize={pageSize}
                showTotal={(total) => `Всего ${total} транзакций`}
                onChange={(page) => setCurrentPage(page)}
                showSizeChanger={false}
              />
            </div>
          )}
        </Spin>
      </Card>
    </div>
  )
}

export default HistoryPage


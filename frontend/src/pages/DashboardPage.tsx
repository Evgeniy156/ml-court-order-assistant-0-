import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Table, Tag, Spin, message } from 'antd'
import { DollarOutlined, TransactionOutlined, ExperimentOutlined } from '@ant-design/icons'
import { webService } from '../services/api'
import type { ColumnsType } from 'antd/es/table'

interface DashboardData {
  user_id: number
  email: string
  balance: number
  total_transactions: number
  total_predictions: number
  recent_transactions: Array<{
    id: number
    amount: number
    type: string
    description: string | null
    created_at: string
  }>
  recent_predictions: Array<{
    id: number
    prediction: number
    credits_charged: number
    created_at: string
  }>
}

const DashboardPage: React.FC = () => {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<DashboardData | null>(null)

  useEffect(() => {
    loadDashboard()
  }, [])

  const loadDashboard = async () => {
    try {
      setLoading(true)
      const dashboardData = await webService.getDashboard()
      setData(dashboardData)
    } catch (error: any) {
      message.error('Ошибка загрузки данных дашборда')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  const transactionColumns: ColumnsType<DashboardData['recent_transactions'][0]> = [
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
        <span style={{ color: amount >= 0 ? '#52c41a' : '#ff4d4f' }}>
          {amount >= 0 ? '+' : ''}{amount.toFixed(2)} кредитов
        </span>
      ),
    },
    {
      title: 'Тип',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => (
        <Tag color={type === 'deposit' ? 'green' : 'red'}>{type}</Tag>
      ),
    },
    {
      title: 'Описание',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: 'Дата',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString('ru-RU'),
    },
  ]

  const predictionColumns: ColumnsType<DashboardData['recent_predictions'][0]> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: 'Предсказание',
      dataIndex: 'prediction',
      key: 'prediction',
      render: (prediction: number) => (prediction * 100).toFixed(2) + '%',
    },
    {
      title: 'Списано кредитов',
      dataIndex: 'credits_charged',
      key: 'credits_charged',
    },
    {
      title: 'Дата',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString('ru-RU'),
    },
  ]

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!data) {
    return <div>Нет данных</div>
  }

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>Дашборд</h1>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="Баланс"
              value={data.balance}
              precision={2}
              prefix={<DollarOutlined />}
              suffix="кредитов"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="Всего транзакций"
              value={data.total_transactions}
              prefix={<TransactionOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8}>
          <Card>
            <Statistic
              title="Всего предсказаний"
              value={data.total_predictions}
              prefix={<ExperimentOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Последние транзакции" style={{ marginBottom: 16 }}>
            <Table
              columns={transactionColumns}
              dataSource={data.recent_transactions}
              rowKey="id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Последние предсказания" style={{ marginBottom: 16 }}>
            <Table
              columns={predictionColumns}
              dataSource={data.recent_predictions}
              rowKey="id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default DashboardPage


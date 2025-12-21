import { useState } from 'react'
import { Card, Form, InputNumber, Button, message, Alert } from 'antd'
import { CreditCardOutlined } from '@ant-design/icons'
import { billingService } from '../services/api'

const PaymentPage: React.FC = () => {
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const onFinish = async (values: { amount: number }) => {
    try {
      setLoading(true)
      await billingService.deposit(values.amount)
      message.success(`Баланс пополнен на ${values.amount} кредитов`)
      form.resetFields()
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Ошибка пополнения баланса')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>Пополнение баланса</h1>
      <Card style={{ maxWidth: 500 }}>
        <Alert
          message="Эмуляция платежа"
          description="В демо-версии пополнение баланса происходит без реальной оплаты"
          type="info"
          showIcon
          style={{ marginBottom: 24 }}
        />
        <Form form={form} onFinish={onFinish} layout="vertical">
          <Form.Item
            name="amount"
            label="Сумма пополнения"
            rules={[
              { required: true, message: 'Введите сумму' },
              { type: 'number', min: 0.01, message: 'Сумма должна быть больше 0' },
            ]}
          >
            <InputNumber
              prefix={<CreditCardOutlined />}
              placeholder="Введите сумму"
              style={{ width: '100%' }}
              min={0.01}
              step={1}
              precision={2}
              size="large"
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block size="large" loading={loading}>
              Пополнить баланс
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default PaymentPage


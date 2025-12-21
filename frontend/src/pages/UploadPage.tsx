import { useState } from 'react'
import { Card, Upload, Button, message, Alert, Table, Tag } from 'antd'
import { UploadOutlined, FileTextOutlined } from '@ant-design/icons'
import type { UploadFile, UploadProps } from 'antd'
import { webService } from '../services/api'

interface TaskStatus {
  task_id: number
  status: string
  prediction: number | null
  error_message: string | null
  credits_charged: number
  created_at: string | null
  updated_at: string | null
}

const UploadPage: React.FC = () => {
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [uploading, setUploading] = useState(false)
  const [tasks] = useState<TaskStatus[]>([])

  const handleUpload: UploadProps['customRequest'] = async (options) => {
    const { file, onSuccess, onError } = options

    // Валидация файла
    if (!(file instanceof File)) {
      onError?.(new Error('Неверный тип файла'))
      return
    }

    if (!file.name.endsWith('.csv')) {
      onError?.(new Error('Поддерживаются только CSV файлы'))
      return
    }

    const maxSize = 10 * 1024 * 1024 // 10MB
    if (file.size > maxSize) {
      onError?.(new Error('Размер файла не должен превышать 10MB'))
      return
    }

    try {
      setUploading(true)
      const response = await webService.uploadFile(file)
      message.success(`Файл загружен. Обработано записей: ${response.records_processed}`)

      // Если это массовая загрузка, создаем задачи для отслеживания
      // В реальном сценарии нужно получать список созданных task_id
      // Для демо просто показываем сообщение
      if (response.records_processed > 0) {
        message.info(
          `Создано ${response.records_processed} задач. Они обрабатываются в фоновом режиме.`
        )
      }

      onSuccess?.(response, file)
      setFileList([])
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.detail || 'Ошибка загрузки файла'
      message.error(errorMessage)
      onError?.(new Error(errorMessage))
    } finally {
      setUploading(false)
    }
  }

  const taskColumns = [
    {
      title: 'ID задачи',
      dataIndex: 'task_id',
      key: 'task_id',
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          pending: 'orange',
          running: 'blue',
          done: 'green',
          failed: 'red',
        }
        return <Tag color={colorMap[status] || 'default'}>{status}</Tag>
      },
    },
    {
      title: 'Предсказание',
      dataIndex: 'prediction',
      key: 'prediction',
      render: (prediction: number | null) =>
        prediction !== null ? `${(prediction * 100).toFixed(2)}%` : '-',
    },
    {
      title: 'Списано кредитов',
      dataIndex: 'credits_charged',
      key: 'credits_charged',
    },
    {
      title: 'Ошибка',
      dataIndex: 'error_message',
      key: 'error_message',
      render: (error: string | null) => error || '-',
    },
    {
      title: 'Обновлено',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (date: string | null) =>
        date ? new Date(date).toLocaleString('ru-RU') : '-',
    },
  ]

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>Загрузка данных для ML-предсказаний</h1>

      <Card style={{ marginBottom: 24 }}>
        <Alert
          message="Формат CSV файла"
          description={
            <div>
              <p>CSV файл должен содержать следующие колонки:</p>
              <ul>
                <li>
                  <code>total_debt</code> - общая задолженность (число)
                </li>
                <li>
                  <code>penalty_amount</code> - сумма пеней (число)
                </li>
                <li>
                  <code>days_overdue</code> - количество дней просрочки (целое число)
                </li>
                <li>
                  <code>payments_ratio</code> - коэффициент платежей (число от 0 до 1)
                </li>
                <li>
                  <code>is_physical_person</code> - физическое лицо (true/false)
                </li>
              </ul>
            </div>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Upload
          fileList={fileList}
          onChange={({ fileList }) => setFileList(fileList)}
          customRequest={handleUpload}
          accept=".csv"
          maxCount={1}
          beforeUpload={() => false} // Предотвращаем автоматическую загрузку
        >
          <Button icon={<UploadOutlined />} size="large" loading={uploading} disabled={uploading}>
            {uploading ? 'Загрузка...' : 'Выбрать CSV файл'}
          </Button>
        </Upload>
      </Card>

      {tasks.length > 0 && (
        <Card
          title={
            <span>
              <FileTextOutlined style={{ marginRight: 8 }} />
              Отслеживание задач
            </span>
          }
        >
          <Table
            columns={taskColumns}
            dataSource={tasks}
            rowKey="task_id"
            pagination={false}
          />
        </Card>
      )}
    </div>
  )
}

export default UploadPage


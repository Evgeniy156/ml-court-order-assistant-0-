import { useState } from 'react'
import { Form, Input, Button, Card, Tabs, message } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'

const AuthPage: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false)
  const { login, register } = useAuth()
  const navigate = useNavigate()
  const [loginForm] = Form.useForm()
  const [registerForm] = Form.useForm()

  const onLogin = async (values: { email: string; password: string }) => {
    setIsLoading(true)
    try {
      await login(values.email, values.password)
      navigate('/dashboard')
    } catch (error) {
      // Ошибка уже обработана в AuthContext
    } finally {
      setIsLoading(false)
    }
  }

  const onRegister = async (values: { email: string; password: string }) => {
    setIsLoading(true)
    try {
      await register(values.email, values.password)
      // После регистрации предлагаем войти
      loginForm.setFieldsValue({ email: values.email })
      message.info('Теперь войдите в систему')
    } catch (error) {
      // Ошибка уже обработана в AuthContext
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Card style={{ width: 400 }}>
        <h1 style={{ textAlign: 'center', marginBottom: 24 }}>ML Court Order Assistant</h1>
        <Tabs
          defaultActiveKey="login"
          items={[
            {
              key: 'login',
              label: 'Вход',
              children: (
                <Form form={loginForm} onFinish={onLogin} layout="vertical">
                  <Form.Item
                    name="email"
                    rules={[
                      { required: true, message: 'Введите email' },
                      { type: 'email', message: 'Некорректный email' },
                    ]}
                  >
                    <Input prefix={<UserOutlined />} placeholder="Email" size="large" />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    rules={[{ required: true, message: 'Введите пароль' }]}
                  >
                    <Input.Password prefix={<LockOutlined />} placeholder="Пароль" size="large" />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" htmlType="submit" block size="large" loading={isLoading}>
                      Войти
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'register',
              label: 'Регистрация',
              children: (
                <Form form={registerForm} onFinish={onRegister} layout="vertical">
                  <Form.Item
                    name="email"
                    rules={[
                      { required: true, message: 'Введите email' },
                      { type: 'email', message: 'Некорректный email' },
                    ]}
                  >
                    <Input prefix={<UserOutlined />} placeholder="Email" size="large" />
                  </Form.Item>
                  <Form.Item
                    name="password"
                    rules={[
                      { required: true, message: 'Введите пароль' },
                      { min: 4, message: 'Пароль должен быть не менее 4 символов' },
                    ]}
                  >
                    <Input.Password prefix={<LockOutlined />} placeholder="Пароль" size="large" />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" htmlType="submit" block size="large" loading={isLoading}>
                      Зарегистрироваться
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}

export default AuthPage


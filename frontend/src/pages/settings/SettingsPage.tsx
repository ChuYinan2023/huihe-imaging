import { useState } from 'react';
import { Card, Form, Input, Button, Upload, App, Space, Image } from 'antd';
import { UploadOutlined, LockOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload';
import api from '../../services/api';

export default function SettingsPage() {
  const { message } = App.useApp();

  // Password change
  const [pwForm] = Form.useForm();
  const [pwSubmitting, setPwSubmitting] = useState(false);

  // Signature
  const [sigFileList, setSigFileList] = useState<UploadFile[]>([]);
  const [sigPreview, setSigPreview] = useState<string | null>(null);

  const handleChangePassword = async () => {
    try {
      const values = await pwForm.validateFields();
      if (values.new_password !== values.confirm_password) {
        message.error('两次输入的新密码不一致');
        return;
      }
      setPwSubmitting(true);
      await api.put('/users/me/password', {
        old_password: values.old_password,
        new_password: values.new_password,
      });
      message.success('密码修改成功');
      pwForm.resetFields();
    } catch (err: any) {
      if (err?.errorFields) return;
      message.error(err?.response?.data?.detail ?? '密码修改失败');
    } finally {
      setPwSubmitting(false);
    }
  };

  const handleSigChange = (info: { fileList: UploadFile[] }) => {
    const list = info.fileList.slice(-1);
    setSigFileList(list);
    if (list.length > 0 && list[0].originFileObj) {
      const reader = new FileReader();
      reader.onload = (e) => setSigPreview(e.target?.result as string);
      reader.readAsDataURL(list[0].originFileObj);
    } else {
      setSigPreview(null);
    }
  };

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>个人设置</h2>

      <Space direction="vertical" size="large" style={{ width: '100%', maxWidth: 600 }}>
        <Card title={<span><LockOutlined style={{ marginRight: 8 }} />修改密码</span>}>
          <Form form={pwForm} layout="vertical">
            <Form.Item
              name="old_password"
              label="当前密码"
              rules={[{ required: true, message: '请输入当前密码' }]}
            >
              <Input.Password placeholder="请输入当前密码" />
            </Form.Item>
            <Form.Item
              name="new_password"
              label="新密码"
              rules={[
                { required: true, message: '请输入新密码' },
                { min: 6, message: '密码至少6位' },
              ]}
            >
              <Input.Password placeholder="请输入新密码" />
            </Form.Item>
            <Form.Item
              name="confirm_password"
              label="确认新密码"
              rules={[
                { required: true, message: '请再次输入新密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('new_password') === value) {
                      return Promise.resolve();
                    }
                    return Promise.reject(new Error('两次输入的密码不一致'));
                  },
                }),
              ]}
            >
              <Input.Password placeholder="请再次输入新密码" />
            </Form.Item>
            <Form.Item>
              <Button type="primary" loading={pwSubmitting} onClick={handleChangePassword}>
                修改密码
              </Button>
            </Form.Item>
          </Form>
        </Card>

        <Card title="电子签名">
          <p style={{ color: '#666', marginBottom: 16 }}>
            上传您的电子签名图片，用于报告签名。支持 PNG、JPG 格式。
          </p>
          {sigPreview && (
            <div style={{ marginBottom: 16 }}>
              <Image src={sigPreview} alt="签名预览" style={{ maxWidth: 300, maxHeight: 150 }} />
            </div>
          )}
          <Upload
            beforeUpload={() => false}
            fileList={sigFileList}
            onChange={handleSigChange}
            maxCount={1}
            accept=".png,.jpg,.jpeg"
          >
            <Button icon={<UploadOutlined />}>选择签名图片</Button>
          </Upload>
          <p style={{ color: '#999', marginTop: 8, fontSize: 12 }}>
            签名上传功能即将上线，当前仅供预览。
          </p>
        </Card>
      </Space>
    </div>
  );
}

import { Form, Input, DatePicker, Button } from "antd";
import type { ActivityCreate } from "@/types/activity";

interface Props {
  onSubmit: (values: ActivityCreate) => void;
  loading: boolean;
  initialValues?: Partial<ActivityCreate>;
}

export default function ActivityForm({ onSubmit, loading, initialValues }: Props) {
  return (
    <Form
      layout="vertical"
      onFinish={onSubmit}
      initialValues={initialValues}
      size="large"
    >
      <Form.Item
        name="name"
        label="活动名称"
        rules={[{ required: true, message: "请输入活动名称" }]}
      >
        <Input placeholder="如：2026年春节文旅嘉年华" maxLength={255} />
      </Form.Item>
      <Form.Item
        name="type"
        label="活动类型"
        rules={[{ required: true, message: "请输入活动类型" }]}
      >
        <Input placeholder="如：大型户外活动" maxLength={128} />
      </Form.Item>
      <Form.Item
        name="estimated_time"
        label="预计举办时间"
        rules={[{ required: true, message: "请选择预计时间" }]}
      >
        <DatePicker showTime style={{ width: "100%" }} />
      </Form.Item>
      <Form.Item
        name="location"
        label="活动地点"
        rules={[{ required: true, message: "请输入活动地点" }]}
      >
        <Input placeholder="如：市民广场" maxLength={512} />
      </Form.Item>
      <Form.Item
        name="sponsor"
        label="主办方"
        rules={[{ required: true, message: "请输入主办方" }]}
      >
        <Input placeholder="如：市文旅局" maxLength={255} />
      </Form.Item>
      <Form.Item
        name="deadline"
        label="截止日期"
        rules={[{ required: true, message: "请选择截止日期" }]}
      >
        <DatePicker showTime style={{ width: "100%" }} />
      </Form.Item>
      <Form.Item>
        <Button type="primary" htmlType="submit" loading={loading} block>
          提交
        </Button>
      </Form.Item>
    </Form>
  );
}

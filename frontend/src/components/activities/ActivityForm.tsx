import { Form, Input, DatePicker, Select, Button, Row, Col } from "antd";
import dayjs from "dayjs";
import type { ActivityCreate } from "@/types/activity";

const ACTIVITY_TYPES = ["文艺汇演", "民俗活动", "体育赛事", "商贸活动", "民族宗教活动", "其他"];
const LOCATION_TYPES = ["中心广场", "商业区域", "娱乐场所", "寺观教堂", "旅游景区", "其他"];

interface Props {
  onSubmit: (values: ActivityCreate) => void;
  loading: boolean;
  initialValues?: Partial<ActivityCreate>;
}

export default function ActivityForm({ onSubmit, loading, initialValues }: Props) {
  const [form] = Form.useForm();

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={onSubmit}
      initialValues={initialValues}
      size="large"
    >
      <Row gutter={16}>
        <Col span={24}>
          <Form.Item
            name="name"
            label="活动名称"
            rules={[
              { required: true, message: "请输入活动名称" },
              { min: 1, max: 255, message: "1-255 个字符" },
            ]}
          >
            <Input placeholder="如：2026年春节文旅嘉年华" maxLength={255} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            name="type"
            label="活动类型"
            rules={[{ required: true, message: "请选择活动类型" }]}
          >
            <Select placeholder="选择活动类型" options={ACTIVITY_TYPES.map((t) => ({ value: t, label: t }))} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            name="estimated_time"
            label="预计举办时间"
            rules={[{ required: true, message: "请选择预计举办时间" }]}
            help="精确到半小时"
          >
            <DatePicker
              showTime={{ minuteStep: 30, format: "HH:mm" }}
              format="YYYY-MM-DD HH:mm"
              placeholder="YYYY-MM-DD HH:mm"
              style={{ width: "100%" }}
              disabledDate={(d) => d && d.isBefore(dayjs().startOf("day"))}
            />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            name="location"
            label="活动地点"
            rules={[{ required: true, message: "请选择活动地点" }]}
          >
            <Select placeholder="选择地点类型" options={LOCATION_TYPES.map((t) => ({ value: t, label: t }))} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            name="sponsor"
            label="主办方"
            rules={[
              { required: true, message: "请输入主办方名称" },
              { min: 1, max: 255, message: "1-255 个字符" },
            ]}
          >
            <Input placeholder="如：市文旅局" maxLength={255} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            name="sponsor_contact"
            label="主办方联系人"
            rules={[
              { required: true, message: "请输入联系人姓名" },
              { min: 1, max: 128, message: "1-128 个字符" },
            ]}
          >
            <Input placeholder="如：张三" maxLength={128} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            name="sponsor_phone"
            label="主办方联系方式"
            rules={[
              { required: true, message: "请输入联系方式" },
              { min: 1, max: 64, message: "1-64 个字符" },
            ]}
          >
            <Input placeholder="如：13800138000" maxLength={64} />
          </Form.Item>
        </Col>
        <Col span={8}>
          <Form.Item
            name="deadline"
            label="截止日期"
            rules={[
              { required: true, message: "请选择截止日期" },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value) return Promise.resolve();
                  if (dayjs(value).isBefore(dayjs())) {
                    return Promise.reject(new Error("截止日期必须晚于当前时间"));
                  }
                  const est = getFieldValue("estimated_time");
                  if (est && !dayjs(value).isBefore(dayjs(est))) {
                    return Promise.reject(new Error("截止日期必须早于预计举办时间"));
                  }
                  return Promise.resolve();
                },
              }),
            ]}
            help="精确到半小时，须早于举办时间"
          >
            <DatePicker
              showTime={{ minuteStep: 30, format: "HH:mm" }}
              format="YYYY-MM-DD HH:mm"
              placeholder="YYYY-MM-DD HH:mm"
              style={{ width: "100%" }}
              disabledDate={(d) => d && d.isBefore(dayjs().startOf("day"))}
            />
          </Form.Item>
        </Col>
      </Row>

      <Form.Item>
        <Button type="primary" htmlType="submit" loading={loading} block>
          提交
        </Button>
      </Form.Item>
    </Form>
  );
}

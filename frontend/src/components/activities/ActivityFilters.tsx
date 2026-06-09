import { Form, Select, Input, DatePicker, Button, Space } from "antd";
import { SearchOutlined, ClearOutlined } from "@ant-design/icons";
import { useSearchParams } from "react-router-dom";
import { ACTIVITY_STATUSES } from "@/utils/constants";
import dayjs from "dayjs";

export default function ActivityFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const status = searchParams.get("status") || undefined;
  const keyword = searchParams.get("keyword") || undefined;
  const dateFrom = searchParams.get("date_from") || undefined;
  const dateTo = searchParams.get("date_to") || undefined;
  const sort = searchParams.get("sort") || "created";

  const updateParam = (key: string, value: string | undefined) => {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    next.set("page", "1");
    setSearchParams(next);
  };

  const clearAll = () => {
    setSearchParams({});
  };

  return (
    <Form layout="inline" style={{ marginBottom: 16 }}>
      <Form.Item label="状态">
        <Select
          allowClear
          placeholder="选择状态"
          style={{ width: 160 }}
          value={status}
          onChange={(v) => updateParam("status", v)}
          options={ACTIVITY_STATUSES.map((s) => ({ label: s, value: s }))}
        />
      </Form.Item>
      <Form.Item label="关键词">
        <Input
          allowClear
          placeholder="搜索名称/主办方"
          prefix={<SearchOutlined />}
          style={{ width: 200 }}
          value={keyword}
          onChange={(e) => {
            if (!e.target.value) updateParam("keyword", undefined);
          }}
          onPressEnter={(e) =>
            updateParam("keyword", (e.target as HTMLInputElement).value)
          }
          onBlur={(e) => updateParam("keyword", e.target.value || undefined)}
        />
      </Form.Item>
      <Form.Item label="排序">
        <Select
          style={{ width: 160 }}
          value={sort}
          onChange={(v) => updateParam("sort", v)}
          options={[
            { label: "创建时间", value: "created" },
            { label: "最近操作", value: "latest_operation" },
          ]}
        />
      </Form.Item>
      <Form.Item label="日期范围">
        <DatePicker.RangePicker
          value={dateFrom && dateTo ? [dayjs(dateFrom), dayjs(dateTo)] : undefined}
          onChange={(_, dateStrings) => {
            if (dateStrings[0] && dateStrings[1]) {
              const next = new URLSearchParams(searchParams);
              next.set("date_from", dateStrings[0]);
              next.set("date_to", dateStrings[1]);
              next.set("page", "1");
              setSearchParams(next);
            } else {
              const next = new URLSearchParams(searchParams);
              next.delete("date_from");
              next.delete("date_to");
              next.set("page", "1");
              setSearchParams(next);
            }
          }}
        />
      </Form.Item>
      <Form.Item>
        <Space>
          <Button icon={<ClearOutlined />} onClick={clearAll}>
            重置
          </Button>
        </Space>
      </Form.Item>
    </Form>
  );
}

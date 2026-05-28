import { Timeline, Typography, Tag } from "antd";
import dayjs from "dayjs";
import { STATUS_COLOR_MAP } from "@/utils/constants";
import type { StatusLogEntry } from "@/types/activity";

interface Props {
  history: StatusLogEntry[];
}

export default function StatusTimeline({ history }: Props) {
  if (history.length === 0) {
    return <Typography.Text type="secondary">暂无状态变更记录</Typography.Text>;
  }

  return (
    <Timeline
      items={[...history].reverse().map((entry) => ({
        color: STATUS_COLOR_MAP[entry.to_status] || "blue",
        content: (
          <div>
            <div>
              {entry.from_status ? (
                <>
                  <Tag>{entry.from_status}</Tag> →{" "}
                </>
              ) : (
                <Typography.Text type="secondary">创建 </Typography.Text>
              )}
              <Tag color={STATUS_COLOR_MAP[entry.to_status] || "blue"}>
                {entry.to_status}
              </Tag>
            </div>
            {entry.comment && (
              <Typography.Text type="secondary">
                {entry.comment}
              </Typography.Text>
            )}
            <div>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                {dayjs(entry.created_at).format("YYYY-MM-DD HH:mm:ss")}
              </Typography.Text>
            </div>
          </div>
        ),
      }))}
    />
  );
}

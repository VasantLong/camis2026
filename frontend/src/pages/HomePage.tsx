import { Alert, Card, Statistic, Table, Tag, Typography, Button, Space, Spin } from "antd";
import {
  PlusOutlined,
  SearchOutlined,
  DashboardOutlined,
  SettingOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import dayjs from "dayjs";
import { useAuthStore } from "@/stores/authStore";
import { useActivityCounts, useActivities } from "@/hooks/useActivityQueries";
import { ROLE_LABEL_MAP, STATUS_COLOR_MAP } from "@/utils/constants";
import type { ActivityResponse } from "@/types/activity";

const { Title, Text } = Typography;

const RED = "#cf1322";

export default function HomePage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const { data: counts, isLoading } = useActivityCounts();

  if (!user) return null;

  const roles: string[] = user.roles ?? [];
  const displayName = user.display_name || user.email;

  // Multi-role fallback: keep old HomeRedirect behavior for devtest
  if (roles.length > 1) {
    const perms = user.permissions ?? [];
    const target = perms.includes("administer_users")
      ? "/admin/users"
      : perms.includes("manage_users")
        ? "/admin/role-requests"
        : perms.includes("view_dashboard")
          ? "/dashboard"
          : perms.includes("view_owned_activity")
            ? "/activities"
            : "/profile";
    navigate(target, { replace: true });
    return null;
  }

  // No role — prompt user to apply
  if (roles.length === 0) {
    return (
      <div style={{ padding: 24, textAlign: "center" }}>
        <Title level={3} style={{ marginBottom: 8 }}>欢迎使用 CAMIS</Title>
        <Text type="secondary" style={{ display: "block", marginBottom: 24 }}>
          你还没有分配角色，请先申请角色以使用系统功能
        </Text>
        <Button type="primary" icon={<UserOutlined />} onClick={() => navigate("/profile")}>
          前往个人中心申请角色
        </Button>
      </div>
    );
  }

  const role = roles[0];
  const roleLabel = ROLE_LABEL_MAP[role] ?? role;

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  const contactPhone = useAuthStore((s) => s.user?.contact_phone);
  const showRecentActivities = ["Promoter", "SecurityOfficer", "SecurityManager", "GovLiaison"].includes(role);

  return (
    <div style={{ padding: 24 }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={3} style={{ marginBottom: 4 }}>
          工作台
        </Title>
        <Text type="secondary">{displayName} · {roleLabel}</Text>
      </div>

      {!contactPhone && (
        <Alert
          type="warning"
          message="请补充联系方式"
          description="您的联系方式尚未填写，请前往个人中心补充联系方式，以便后续活动流转。"
          action={<Button size="small" onClick={() => navigate("/profile")}>前往个人中心</Button>}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {counts && <CardGrid role={role} counts={counts} onNavigate={navigate} />}

      <div style={{ marginTop: 24 }}>{renderQuickActions(role, navigate)}</div>

      {showRecentActivities && <RecentActivities />}
    </div>
  );
}

function CardGrid({
  role,
  counts,
  onNavigate,
}: {
  role: string;
  counts: Record<string, number>;
  onNavigate: (path: string) => void;
}) {
  const activeStyle = (val: number | undefined) =>
    val ? { color: RED } : undefined;

  if (role === "SuperAdmin") {
    return (
      <div style={{ display: "flex", gap: 16 }}>
        <Card style={{ flex: 1 }}>
          <Statistic title="用户总数" value={counts.total_users ?? 0} />
        </Card>
        <Card
          style={{ flex: 1, cursor: "pointer" }}
          onClick={() => onNavigate("/admin/role-requests")}
        >
          <Statistic
            title="待审批申请"
            value={counts.pending_role_requests ?? 0}
            styles={{ content: activeStyle(counts.pending_role_requests) }}
          />
        </Card>
        <Card style={{ flex: 1 }}>
          <Statistic title="总活动数" value={counts.total_activities ?? 0} />
        </Card>
      </div>
    );
  }

  if (role === "AdminStaff" || role === "AdminManager") {
    return (
      <div style={{ display: "flex", gap: 16 }}>
        <Card style={{ flex: 1 }}>
          <Statistic title="总活动数" value={counts.total ?? 0} />
        </Card>
        <Card style={{ flex: 1 }}>
          <Statistic
            title="审批通过率"
            value={counts.approval_rate != null ? counts.approval_rate * 100 : 0}
            suffix="%"
            precision={1}
          />
        </Card>
        <Card style={{ flex: 1 }}>
          <Statistic title="本月新增" value={counts.new_this_month ?? 0} />
        </Card>
        <Card style={{ flex: 1 }}>
          <Statistic
            title="待确认变更"
            value={counts.pending_force_confirm ?? 0}
            styles={{ content: activeStyle(counts.pending_force_confirm) }}
          />
        </Card>
      </div>
    );
  }

  // GovLiaison, SecurityManager, SecurityOfficer, Promoter — all 2-card layouts
  const config: Record<string, Array<{ title: string; key: string; link?: string }>> = {
    GovLiaison: [
      { title: "待审查材料", key: "pending_review", link: "/activities?status=备案材料已交接" },
      { title: "今日已登记", key: "registered_today" },
    ],
    SecurityManager: [
      { title: "待签署确认", key: "pending_sign_confirm", link: "/activities?status=待安保方案设计" },
      { title: "待打包备案", key: "pending_pack", link: "/activities?status=待备案申请" },
    ],
    SecurityOfficer: [
      { title: "待编制安保方案", key: "pending_draft", link: "/activities?status=待安保方案设计" },
      { title: "待打包备案", key: "pending_pack", link: "/activities?status=待备案申请" },
    ],
    Promoter: [
      { title: "待设计方案", key: "pending_plan", link: "/activities?status=待设计方案" },
      { title: "我的活动", key: "my_activities", link: "/activities" },
    ],
  };

  const cards = config[role];
  if (!cards) return null;

  return (
    <div style={{ display: "flex", gap: 16 }}>
      {cards.map((c) => (
        <Card
          key={c.key}
          style={{ flex: 1, ...(c.link ? { cursor: "pointer" } : {}) }}
          onClick={c.link ? () => onNavigate(c.link!) : undefined}
        >
          <Statistic
            title={c.title}
            value={counts[c.key] ?? 0}
            styles={{ content: activeStyle(counts[c.key]) }}
          />
        </Card>
      ))}
    </div>
  );
}

function renderQuickActions(role: string, navigate: (path: string) => void) {
  if (role === "Promoter") {
    return (
      <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/activities/new")}>
        新建立项
      </Button>
    );
  }
  if (role === "GovLiaison") {
    return (
      <Button type="primary" icon={<SearchOutlined />} onClick={() => navigate("/activities?status=备案材料已交接")}>
        进入审查
      </Button>
    );
  }
  if (role === "AdminStaff" || role === "AdminManager") {
    return (
      <Button type="primary" icon={<DashboardOutlined />} onClick={() => navigate("/dashboard")}>
        进入仪表盘
      </Button>
    );
  }
  if (role === "SuperAdmin") {
    return (
      <Space>
        <Button type="primary" icon={<SettingOutlined />} onClick={() => navigate("/admin/users")}>
          用户管理
        </Button>
        <Button icon={<DashboardOutlined />} onClick={() => navigate("/activities")}>
          全部活动
        </Button>
      </Space>
    );
  }
  return null;
}

function RecentActivities() {
  const navigate = useNavigate();
  const { data } = useActivities({ page: 1, size: 5 });

  const columns = [
    {
      title: "活动名称",
      dataIndex: "name",
      key: "name",
      ellipsis: true,
      render: (text: string, record: ActivityResponse) => (
        <a onClick={() => navigate(`/activities/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: "类型",
      dataIndex: "type",
      key: "type",
      width: 120,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 150,
      render: (status: string) => (
        <Tag color={STATUS_COLOR_MAP[status] || "default"}>{status}</Tag>
      ),
    },
    {
      title: "预计时间",
      dataIndex: "estimated_time",
      key: "estimated_time",
      width: 170,
      render: (t: string) => dayjs(t).format("YYYY-MM-DD HH:mm"),
    },
  ];

  return (
    <Card
      title="最近活动"
      style={{ marginTop: 24 }}
      extra={
        <Button type="link" onClick={() => navigate("/activities")}>
          查看全部
        </Button>
      }
    >
      <Table<ActivityResponse>
        columns={columns}
        dataSource={data?.items ?? []}
        rowKey="id"
        pagination={false}
        size="small"
      />
    </Card>
  );
}

import { useState } from "react";
import { Button, Space } from "antd";
import {
  CheckOutlined,
  CloseOutlined,
  StopOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { getAvailableTransitions, type TransitionDef } from "@/utils/constants";
import StatusTransitionModal from "./StatusTransitionModal";
import RejectModal from "./RejectModal";
import ForceChangeModal from "./ForceChangeModal";

interface Props {
  activityId: string;
  currentStatus: string;
}

export default function WorkflowActions({ activityId, currentStatus }: Props) {
  const [modal, setModal] = useState<{
    type: TransitionDef["mode"];
    def: TransitionDef;
  } | null>(null);
  const userPermissions = useAuthStore((s) => s.user?.permissions);
  const permissions = userPermissions ?? [];
  const qc = useQueryClient();

  console.log("[WorkflowActions] status:", currentStatus, "permissions:", permissions, "actions:", getAvailableTransitions(currentStatus, permissions));
  const actions = getAvailableTransitions(currentStatus, permissions);
  if (actions.length === 0) return null;

  const onSuccess = () => {
    qc.invalidateQueries({ queryKey: ["activities", activityId] });
  };

  const iconFor = (mode: TransitionDef["mode"]) => {
    switch (mode) {
      case "reject":
        return <CloseOutlined />;
      case "forceCancel":
        return <StopOutlined />;
      case "forcePostpone":
        return <ClockCircleOutlined />;
      default:
        return <CheckOutlined />;
    }
  };

  return (
    <>
      <Space wrap style={{ marginTop: 16 }}>
        {actions.map((a) => (
          <Button
            key={a.label}
            danger={a.mode === "forceCancel" || a.mode === "reject"}
            icon={iconFor(a.mode)}
            onClick={() => setModal({ type: a.mode, def: a })}
          >
            {a.label}
          </Button>
        ))}
      </Space>
      <StatusTransitionModal
        open={modal?.type === "transition"}
        activityId={activityId}
        toStatus={modal?.def.toStatus || ""}
        onClose={() => setModal(null)}
        onSuccess={onSuccess}
      />
      <RejectModal
        open={modal?.type === "reject"}
        activityId={activityId}
        isReverseFlow={currentStatus === "审批通过"}
        onClose={() => setModal(null)}
        onSuccess={onSuccess}
      />
      <ForceChangeModal
        open={modal?.type === "forceCancel" || modal?.type === "forcePostpone"}
        mode={modal?.type === "forcePostpone" ? "postpone" : "cancel"}
        activityId={activityId}
        onClose={() => setModal(null)}
        onSuccess={onSuccess}
      />
    </>
  );
}

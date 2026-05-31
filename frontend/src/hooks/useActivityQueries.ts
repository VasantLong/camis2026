import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { activitiesApi } from "@/api/activities";
import type { ActivityCreate, ActivityListParams } from "@/types/activity";

export function useActivities(params: ActivityListParams) {
  return useQuery({
    queryKey: ["activities", params],
    queryFn: () => activitiesApi.list(params).then((r) => r.data),
    staleTime: 0,
  });
}

export function useActivity(id: string) {
  return useQuery({
    queryKey: ["activities", id],
    queryFn: () => activitiesApi.get(id).then((r) => r.data),
    enabled: !!id,
  });
}

export function useCreateActivity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ActivityCreate) =>
      activitiesApi.create(data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["activities"] });
    },
  });
}

export function useActivityHistory(id: string) {
  return useQuery({
    queryKey: ["activities", id, "history"],
    queryFn: () => activitiesApi.getHistory(id).then((r) => r.data),
    enabled: !!id,
  });
}

export function useActivityDocuments(id: string) {
  return useQuery({
    queryKey: ["activities", id, "documents"],
    queryFn: () => activitiesApi.getDocuments(id).then((r) => r.data),
    enabled: !!id,
  });
}

export function useActivityCounts() {
  return useQuery({
    queryKey: ["activities", "counts"],
    queryFn: () => activitiesApi.fetchCounts().then((r) => r.data),
    refetchInterval: 30_000,
    staleTime: 0,
  });
}

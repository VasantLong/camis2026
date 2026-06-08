import { useQuery } from "@tanstack/react-query";
import { templatesApi } from "@/api/templates";

export function useMaterialSchema(
  activityId: string,
  materialType: string,
  enabled: boolean,
) {
  const materialQuery = useQuery({
    queryKey: ["activities", activityId, "material", materialType],
    queryFn: () => templatesApi.createMaterial(activityId, materialType),
    enabled,
    staleTime: Infinity,
  });
  const materialId = materialQuery.data?.data?.material_id as string | undefined;

  const schemaQuery = useQuery({
    queryKey: ["activities", activityId, "material", materialType, "schema"],
    queryFn: () => templatesApi.getMaterialSchema(activityId, materialId!),
    enabled: !!materialId,
  });

  return {
    materialId,
    schema: schemaQuery.data?.data,
    isLoading: materialQuery.isLoading || schemaQuery.isLoading,
    refetch: schemaQuery.refetch,
  };
}

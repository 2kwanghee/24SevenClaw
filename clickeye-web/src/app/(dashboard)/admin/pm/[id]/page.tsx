import { use } from "react";
import { PMEditForm } from "@/components/admin/pm/pm-edit-form";

export default function AdminPMDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <PMEditForm profileId={id} />;
}

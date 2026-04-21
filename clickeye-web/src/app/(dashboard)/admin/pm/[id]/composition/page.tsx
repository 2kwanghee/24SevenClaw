import { redirect } from "next/navigation";
import { use } from "react";

export default function AdminPMCompositionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  redirect(`/admin/pm/${id}`);
}

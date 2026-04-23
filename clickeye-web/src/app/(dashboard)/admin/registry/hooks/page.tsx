import { RoleGuard } from "@/components/common/role-guard";
import { RegistryListTable } from "@/components/admin/registry/registry-list-table";

export default function AdminRegistryHooksPage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-white">Hook 레지스트리</h1>
            <p className="mt-1 text-xs text-slate-500">훅 카탈로그 항목 관리</p>
          </div>
        </div>
        <RegistryListTable type="hooks" />
      </div>
    </RoleGuard>
  );
}

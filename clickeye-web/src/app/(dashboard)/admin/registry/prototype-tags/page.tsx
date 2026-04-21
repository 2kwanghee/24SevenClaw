import { RoleGuard } from "@/components/common/role-guard";
import { PrototypeTagsTable } from "@/components/admin/prototype-catalog/prototype-tags-table";

export default function AdminPrototypeTagsPage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <div className="space-y-6">
        <div>
          <h1 className="text-lg font-semibold text-white">프로토타입 태그</h1>
          <p className="mt-1 text-xs text-slate-500">
            카탈로그 분류에 사용되는 태그를 관리합니다 (고정 enum 없이 자유 추가 가능)
          </p>
        </div>
        <PrototypeTagsTable />
      </div>
    </RoleGuard>
  );
}

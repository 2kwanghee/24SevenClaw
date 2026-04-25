import { RoleGuard } from "@/components/common/role-guard";
import { PrototypeCatalogTable } from "@/components/admin/prototype-catalog/prototype-catalog-table";

export default function AdminPrototypeCatalogPage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <div className="space-y-6">
        <div>
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">프로토타입 카탈로그</h1>
          <p className="mt-1 text-xs text-[var(--text-muted)]">
            위저드 AI 제안 및 ZIP 생성 시 참조되는 카탈로그 엔트리를 관리합니다
          </p>
        </div>
        <PrototypeCatalogTable />
      </div>
    </RoleGuard>
  );
}

import { RoleGuard } from "@/components/common/role-guard";
import { AppSettingsPanel } from "@/components/admin/app-settings-panel";

export default function AdminSettingsPage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <div className="space-y-6">
        <div>
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">전역 설정</h1>
          <p className="mt-1 text-xs text-[var(--text-muted)]">
            위저드 동작에 영향을 주는 전역 설정을 관리합니다
          </p>
        </div>
        <AppSettingsPanel />
      </div>
    </RoleGuard>
  );
}

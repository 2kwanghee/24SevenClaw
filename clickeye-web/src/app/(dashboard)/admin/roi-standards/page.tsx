"use client";

import { useState } from "react";
import { RoleGuard } from "@/components/common/role-guard";
import { RoiStandardsTable } from "@/components/admin/roi/roi-standards-table";

type Tab = "role_rate" | "solution_effort" | "complexity_multiplier";

const TABS: { id: Tab; label: string; desc: string }[] = [
  { id: "role_rate", label: "직군 단가", desc: "직군별 일급 (KRW/day)" },
  { id: "solution_effort", label: "솔루션 공수", desc: "솔루션 타입별 직군별 baseline 작업일수" },
  { id: "complexity_multiplier", label: "복잡도 계수", desc: "복잡도별 공수 배율" },
];

export default function AdminRoiStandardsPage() {
  const [tab, setTab] = useState<Tab>("role_rate");

  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <div className="space-y-6">
        <div>
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">ROI 단가/공수 표준</h1>
          <p className="mt-1 text-xs text-[var(--text-muted)]">
            위저드 ROI 비교 산출에 사용되는 표준 파라미터 관리. 변경 사항은 새 세션에 즉시 반영됩니다.
          </p>
        </div>

        <div className="flex gap-1 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-hover)] p-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex-1 rounded-lg px-3 py-2 text-xs font-medium transition-all ${
                tab === t.id
                  ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-sm"
                  : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div>
          <p className="mb-3 text-xs text-[var(--text-muted)]">
            {TABS.find((t) => t.id === tab)?.desc}
          </p>
          <RoiStandardsTable key={tab} category={tab} />
        </div>
      </div>
    </RoleGuard>
  );
}

"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  Check,
  Copy,
  ExternalLink,
  Inbox,
  Info,
  KeyRound,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { BaseModal } from "@/components/common/base-modal";
import { ConfirmByTypingDialog } from "@/components/common/confirm-by-typing-dialog";
import { RoleGuard } from "@/components/common/role-guard";
import {
  useAcceptIntake,
  useCreateIntakeServiceKey,
  useDeactivateIntakeServiceKey,
  useIntakeList,
  useIntakeServiceKeys,
  useRejectIntake,
} from "@/hooks/use-intake";
import {
  ApiClientError,
  type IntakeResponse,
  type IntakeServiceKeyResponse,
  type IntakeStatus,
} from "@/lib/api-client";
import { useRBACStore } from "@/stores/rbac-store";

/** FEATURE_INTAKE off → 백엔드가 404(존재 은닉)를 반환한다. 에러가 아닌 안내로 처리 */
function isFeatureDisabled(error: unknown): boolean {
  return error instanceof ApiClientError && error.status === 404;
}

const INPUT_TYPE_COLORS: Record<string, string> = {
  structured: "border-blue-200 bg-blue-50 text-blue-700",
  document: "border-violet-200 bg-violet-50 text-violet-700",
  url: "border-emerald-200 bg-emerald-50 text-emerald-700",
};

// A3-full: 정제 상태 뱃지 — 정제 대기 amber / 정제됨 green / 건너뜀 gray.
const REFINE_STATUS_COLORS: Record<string, string> = {
  pending: "border-amber-200 bg-amber-50 text-amber-700",
  refined: "border-emerald-200 bg-emerald-50 text-emerald-700",
  skipped:
    "border-[var(--border-subtle)] bg-[var(--bg-hover)] text-[var(--text-muted)]",
};

function RefineStatusBadge({ status }: { status: string }) {
  const t = useTranslations("intake.refine");
  const known = status === "refined" || status === "skipped" ? status : "pending";
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-xs font-medium ${REFINE_STATUS_COLORS[known]}`}
    >
      {t(`status.${known}`)}
    </span>
  );
}

// CE-311: 콜백 발송 상태 뱃지 — sent green / pending amber / failed red, none 은 비표시.
const CALLBACK_STATUS_COLORS: Record<string, string> = {
  sent: "border-emerald-200 bg-emerald-50 text-emerald-700",
  pending: "border-amber-200 bg-amber-50 text-amber-700",
  failed: "border-red-200 bg-red-50 text-red-700",
};

function CallbackStatusBadge({ status }: { status: string }) {
  const t = useTranslations("intake.callback");
  if (status !== "sent" && status !== "pending" && status !== "failed") return null;
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-xs font-medium ${CALLBACK_STATUS_COLORS[status]}`}
    >
      {t(`status.${status}`)}
    </span>
  );
}

function InputTypeBadge({ inputType }: { inputType: string }) {
  const color =
    INPUT_TYPE_COLORS[inputType] ??
    "border-[var(--border-subtle)] bg-[var(--bg-hover)] text-[var(--text-secondary)]";
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${color}`}>
      {inputType}
    </span>
  );
}

function FeatureDisabledBanner() {
  const t = useTranslations("intake");
  return (
    <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
      <Info className="mt-0.5 h-4 w-4 shrink-0" />
      {t("featureDisabled")}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 인테이크 목록
// ---------------------------------------------------------------------------

interface IntakeRowProps {
  item: IntakeResponse;
  onAccept: (item: IntakeResponse) => void;
  onReject: (item: IntakeResponse) => void;
}

function IntakeRow({ item, onAccept, onReject }: IntakeRowProps) {
  const t = useTranslations("intake");
  const [expanded, setExpanded] = useState(false);

  const createdAt = item.created_at
    ? new Date(item.created_at).toLocaleString("ko-KR")
    : "—";

  return (
    <>
      <tr
        className="cursor-pointer border-b border-[var(--border-subtle)] transition-colors hover:bg-[var(--bg-hover)]"
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-4 py-3">
          <p className="text-sm font-medium text-[var(--text-primary)]">{item.title}</p>
        </td>
        <td className="px-4 py-3">
          <InputTypeBadge inputType={item.input_type} />
        </td>
        <td className="px-4 py-3 text-xs text-[var(--text-secondary)]">
          {item.priority ?? "—"}
        </td>
        <td className="px-4 py-3 text-xs text-[var(--text-secondary)]">{createdAt}</td>
        <td className="px-4 py-3 text-right">
          {item.status === "pending_review" && (
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onAccept(item);
                }}
                className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-emerald-500"
              >
                {t("actions.accept")}
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onReject(item);
                }}
                className="rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 transition-colors hover:bg-red-100"
              >
                {t("actions.reject")}
              </button>
            </div>
          )}
          {item.status === "accepted" && item.project_id && (
            <Link
              href={`/projects/${item.project_id}`}
              onClick={(e) => e.stopPropagation()}
              className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 hover:underline"
            >
              {t("detail.openProject")}
              <ExternalLink className="h-3 w-3" />
            </Link>
          )}
        </td>
      </tr>

      {expanded && (
        <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
          <td colSpan={5} className="px-4 py-4">
            <div className="space-y-3">
              {/* 정제 스펙 (A3-full) — refined_text 있으면 원문과 나란히 비교 표시 */}
              <div>
                <div className="mb-1 flex items-center gap-2">
                  <p className="text-xs font-medium text-[var(--text-muted)]">
                    {t("refine.title")}
                  </p>
                  <RefineStatusBadge status={item.refine_status} />
                </div>
                {item.refined_text ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <p className="mb-1 text-xs text-[var(--text-muted)]">
                        {t("detail.normalizedText")}
                      </p>
                      <pre className="max-h-64 overflow-y-auto whitespace-pre-wrap rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] p-3 text-xs leading-relaxed text-[var(--text-secondary)]">
                        {item.normalized_text ?? t("detail.noNormalizedText")}
                      </pre>
                    </div>
                    <div>
                      <p className="mb-1 text-xs text-[var(--text-muted)]">
                        {t("refine.refinedText")}
                      </p>
                      <pre className="max-h-64 overflow-y-auto whitespace-pre-wrap rounded-lg border border-emerald-200 bg-emerald-50/40 p-3 text-xs leading-relaxed text-[var(--text-secondary)]">
                        {item.refined_text}
                      </pre>
                    </div>
                  </div>
                ) : item.normalized_text ? (
                  <div>
                    <p className="mb-1 text-xs text-[var(--text-muted)]">
                      {t("detail.normalizedText")}
                    </p>
                    <pre className="max-h-64 overflow-y-auto whitespace-pre-wrap rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] p-3 text-xs leading-relaxed text-[var(--text-secondary)]">
                      {item.normalized_text}
                    </pre>
                  </div>
                ) : (
                  <p className="text-xs text-[var(--text-muted)]">
                    {t("detail.noNormalizedText")}
                  </p>
                )}
              </div>

              {/* CE-311: 콜백 발송 상태 — callback_url 이 있는 건만 표시(none 비표시) */}
              {item.callback_status !== "none" && (
                <div className="flex items-center gap-2">
                  <p className="text-xs font-medium text-[var(--text-muted)]">
                    {t("callback.title")}
                  </p>
                  <CallbackStatusBadge status={item.callback_status} />
                </div>
              )}

              {/* 원본 URL */}
              {item.source_url && (
                <div>
                  <p className="mb-1 text-xs font-medium text-[var(--text-muted)]">
                    {t("detail.sourceUrl")}
                  </p>
                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="inline-flex items-center gap-1 break-all text-xs text-blue-700 hover:underline"
                  >
                    {item.source_url}
                    <ExternalLink className="h-3 w-3 shrink-0" />
                  </a>
                </div>
              )}

              {/* 타깃 요약 */}
              {item.target && Object.keys(item.target).length > 0 && (
                <div>
                  <p className="mb-1 text-xs font-medium text-[var(--text-muted)]">
                    {t("detail.target")}
                  </p>
                  <pre className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] p-3 text-xs text-[var(--text-secondary)]">
                    {JSON.stringify(item.target, null, 2)}
                  </pre>
                </div>
              )}

              {/* 생성된 프로젝트 링크 */}
              {item.project_id && (
                <div>
                  <p className="mb-1 text-xs font-medium text-[var(--text-muted)]">
                    {t("detail.project")}
                  </p>
                  <Link
                    href={`/projects/${item.project_id}`}
                    onClick={(e) => e.stopPropagation()}
                    className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 hover:underline"
                  >
                    {t("detail.openProject")}
                    <ExternalLink className="h-3 w-3" />
                  </Link>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function IntakeListSection({ status }: { status: IntakeStatus }) {
  const t = useTranslations("intake");
  const tT = useTranslations("toast.intake");
  const router = useRouter();

  const { data, isLoading, error } = useIntakeList(status);
  const acceptMutation = useAcceptIntake();
  const rejectMutation = useRejectIntake();

  const [acceptTarget, setAcceptTarget] = useState<IntakeResponse | null>(null);
  const [rejectTarget, setRejectTarget] = useState<IntakeResponse | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const handleAccept = () => {
    if (!acceptTarget) return;
    acceptMutation.mutate(acceptTarget.id, {
      onSuccess: (res) => {
        setAcceptTarget(null);
        toast.success(tT("acceptSuccess"), {
          action: res.project_id
            ? {
                label: t("detail.openProject"),
                onClick: () => router.push(`/projects/${res.project_id}`),
              }
            : undefined,
        });
      },
      onError: (err) => {
        toast.error(err.message || tT("acceptFail"));
      },
    });
  };

  const handleReject = () => {
    if (!rejectTarget) return;
    rejectMutation.mutate(
      { intakeId: rejectTarget.id, reason: rejectReason.trim() || undefined },
      {
        onSuccess: () => {
          setRejectTarget(null);
          setRejectReason("");
          toast.success(tT("rejectSuccess"));
        },
        onError: (err) => {
          toast.error(err.message || tT("rejectFail"));
        },
      },
    );
  };

  if (isLoading) {
    return (
      <div className="py-12 text-center text-sm text-[var(--text-muted)]">
        {t("loading")}
      </div>
    );
  }

  if (error) {
    if (isFeatureDisabled(error)) return <FeatureDisabledBanner />;
    return (
      <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        <AlertCircle className="h-4 w-4 shrink-0" />
        {(error as Error).message || t("error")}
      </div>
    );
  }

  return (
    <>
      <div className="overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-hover)]">
              <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">
                {t("col.title")}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">
                {t("col.inputType")}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">
                {t("col.priority")}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">
                {t("col.receivedAt")}
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-muted)]">
                {t("col.actions")}
              </th>
            </tr>
          </thead>
          <tbody>
            {(data ?? []).map((item) => (
              <IntakeRow
                key={item.id}
                item={item}
                onAccept={setAcceptTarget}
                onReject={setRejectTarget}
              />
            ))}
            {data && data.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-12 text-center text-sm text-[var(--text-muted)]"
                >
                  {t("empty")}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 승인 확인 다이얼로그 */}
      <BaseModal
        open={!!acceptTarget}
        onClose={() => setAcceptTarget(null)}
        title={t("acceptDialog.title")}
        titleId="intake-accept-title"
      >
        <div className="p-6">
          <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
            {t("acceptDialog.description", { title: acceptTarget?.title ?? "" })}
          </p>
          {acceptTarget?.refined_text && (
            <div className="mt-3 flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-xs leading-relaxed text-emerald-800">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {t("refine.acceptNotice")}
            </div>
          )}
          <div className="mt-5 flex gap-3">
            <button
              type="button"
              onClick={() => setAcceptTarget(null)}
              className="flex-1 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-2.5 text-sm font-medium text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-hover)]"
            >
              {t("acceptDialog.cancel")}
            </button>
            <button
              type="button"
              onClick={handleAccept}
              disabled={acceptMutation.isPending}
              className="flex-1 rounded-xl bg-emerald-600 py-2.5 text-sm font-medium text-white transition-all hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {acceptMutation.isPending
                ? t("acceptDialog.pending")
                : t("acceptDialog.confirm")}
            </button>
          </div>
        </div>
      </BaseModal>

      {/* 반려 사유 다이얼로그 */}
      <BaseModal
        open={!!rejectTarget}
        onClose={() => {
          setRejectTarget(null);
          setRejectReason("");
        }}
        title={t("rejectDialog.title")}
        titleId="intake-reject-title"
      >
        <div className="p-6">
          <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
            {t("rejectDialog.description", { title: rejectTarget?.title ?? "" })}
          </p>
          <label
            htmlFor="intake-reject-reason"
            className="mt-4 block text-xs text-[var(--text-muted)]"
          >
            {t("rejectDialog.reasonLabel")}
          </label>
          <textarea
            id="intake-reject-reason"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder={t("rejectDialog.reasonPlaceholder")}
            rows={3}
            className="mt-1.5 w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-red-300 focus:ring-1 focus:ring-red-200"
          />
          <div className="mt-4 flex gap-3">
            <button
              type="button"
              onClick={() => {
                setRejectTarget(null);
                setRejectReason("");
              }}
              className="flex-1 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] py-2.5 text-sm font-medium text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-hover)]"
            >
              {t("rejectDialog.cancel")}
            </button>
            <button
              type="button"
              onClick={handleReject}
              disabled={rejectMutation.isPending}
              className="flex-1 rounded-xl bg-red-600 py-2.5 text-sm font-medium text-white transition-all hover:bg-red-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {rejectMutation.isPending
                ? t("rejectDialog.pending")
                : t("rejectDialog.confirm")}
            </button>
          </div>
        </div>
      </BaseModal>
    </>
  );
}

// ---------------------------------------------------------------------------
// 서비스 키 관리 (superadmin 전용 탭)
// ---------------------------------------------------------------------------

function ServiceKeysSection() {
  const t = useTranslations("intake.keys");
  const tT = useTranslations("toast.intake");

  const { data, isLoading, error } = useIntakeServiceKeys();
  const createMutation = useCreateIntakeServiceKey();
  const deactivateMutation = useDeactivateIntakeServiceKey();

  const [name, setName] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [deactivateTarget, setDeactivateTarget] =
    useState<IntakeServiceKeyResponse | null>(null);

  const handleCreate = () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    createMutation.mutate(
      { name: trimmed },
      {
        onSuccess: (res) => {
          setName("");
          setCopied(false);
          setCreatedKey(res.key);
        },
        onError: (err) => {
          toast.error(err.message || tT("keyCreateFail"));
        },
      },
    );
  };

  const handleCopy = async () => {
    if (!createdKey) return;
    try {
      await navigator.clipboard.writeText(createdKey);
      setCopied(true);
      toast.success(tT("copySuccess"));
    } catch {
      toast.error(tT("copyFail"));
    }
  };

  const handleDeactivate = () => {
    if (!deactivateTarget) return;
    deactivateMutation.mutate(deactivateTarget.id, {
      onSuccess: () => {
        setDeactivateTarget(null);
        toast.success(tT("keyDeactivateSuccess"));
      },
      onError: (err) => {
        toast.error(err.message || tT("keyDeactivateFail"));
      },
    });
  };

  if (error && isFeatureDisabled(error)) return <FeatureDisabledBanner />;

  return (
    <div className="space-y-4">
      <p className="text-xs text-[var(--text-muted)]">{t("description")}</p>

      {/* 발급 폼 */}
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <label
            htmlFor="intake-key-name"
            className="mb-1.5 block text-xs text-[var(--text-muted)]"
          >
            {t("nameLabel")}
          </label>
          <input
            id="intake-key-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            placeholder={t("namePlaceholder")}
            maxLength={100}
            className="w-full rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-[var(--border-medium)]"
          />
        </div>
        <button
          type="button"
          onClick={handleCreate}
          disabled={!name.trim() || createMutation.isPending}
          className="rounded-lg bg-[var(--text-primary)] px-4 py-2 text-sm font-medium text-[var(--bg-surface)] transition-all hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {createMutation.isPending ? t("issuing") : t("issue")}
        </button>
      </div>

      {isLoading && (
        <div className="py-8 text-center text-sm text-[var(--text-muted)]">
          {t("loading")}
        </div>
      )}

      {error && !isFeatureDisabled(error) && (
        <div className="flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {(error as Error).message}
        </div>
      )}

      {/* 키 목록 */}
      {data && (
        <div className="overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--border-subtle)] bg-[var(--bg-hover)]">
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">
                  {t("col.name")}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">
                  {t("col.organization")}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">
                  {t("col.active")}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--text-muted)]">
                  {t("col.createdAt")}
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--text-muted)]">
                  {t("col.actions")}
                </th>
              </tr>
            </thead>
            <tbody>
              {data.map((key) => (
                <tr
                  key={key.id}
                  className="border-b border-[var(--border-subtle)] last:border-b-0"
                >
                  <td className="px-4 py-3 text-sm font-medium text-[var(--text-primary)]">
                    {key.name}
                  </td>
                  <td className="px-4 py-3 text-xs font-mono text-[var(--text-muted)]">
                    {key.organization_id ? `${key.organization_id.slice(0, 8)}…` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        key.is_active
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-[var(--bg-base)] text-[var(--text-muted)]"
                      }`}
                    >
                      {key.is_active ? t("active") : t("inactive")}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-[var(--text-muted)]">
                    {key.created_at
                      ? new Date(key.created_at).toLocaleDateString("ko-KR")
                      : "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {key.is_active && (
                      <button
                        type="button"
                        onClick={() => setDeactivateTarget(key)}
                        className="rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 transition-colors hover:bg-red-100"
                      >
                        {t("deactivate")}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {data.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-12 text-center text-sm text-[var(--text-muted)]"
                  >
                    {t("empty")}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* 발급된 평문 키 1회 표시 모달 — 명시적 확인으로만 닫힘 */}
      <BaseModal
        open={!!createdKey}
        title={t("createdTitle")}
        titleId="intake-key-created-title"
      >
        <div className="p-6">
          <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs leading-relaxed text-amber-800">
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            {t("createdWarning")}
          </div>
          <div className="mt-4 flex items-center gap-2">
            <code className="flex-1 break-all rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)] px-3 py-2.5 font-mono text-xs text-[var(--text-primary)]">
              {createdKey}
            </code>
            <button
              type="button"
              onClick={handleCopy}
              className="flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] px-3 py-2.5 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-hover)]"
            >
              {copied ? (
                <Check className="h-3.5 w-3.5 text-emerald-600" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
              {copied ? t("copied") : t("copy")}
            </button>
          </div>
          <button
            type="button"
            onClick={() => {
              setCreatedKey(null);
              setCopied(false);
            }}
            className="mt-5 w-full rounded-xl bg-[var(--text-primary)] py-2.5 text-sm font-medium text-[var(--bg-surface)] transition-all hover:opacity-90"
          >
            {t("done")}
          </button>
        </div>
      </BaseModal>

      {/* 비활성화 확인 다이얼로그 (type-to-confirm) */}
      <ConfirmByTypingDialog
        open={!!deactivateTarget}
        title={t("deactivateTitle")}
        description={t("deactivateDescription")}
        confirmPhrase={deactivateTarget?.name ?? ""}
        confirmLabel={t("deactivate")}
        isPending={deactivateMutation.isPending}
        onConfirm={handleDeactivate}
        onCancel={() => setDeactivateTarget(null)}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// 페이지
// ---------------------------------------------------------------------------

type TabId = IntakeStatus | "service-keys";

function IntakeContent() {
  const t = useTranslations("intake");
  const isSuperadmin = useRBACStore((s) => s.isSuperadmin());
  const [tab, setTab] = useState<TabId>("pending_review");

  const statusTabs: { id: IntakeStatus; label: string }[] = [
    { id: "pending_review", label: t("tabs.pendingReview") },
    { id: "accepted", label: t("tabs.accepted") },
    { id: "rejected", label: t("tabs.rejected") },
  ];

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--bg-hover)]">
          <Inbox className="h-5 w-5 text-[var(--text-secondary)]" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            {t("pageTitle")}
          </h1>
          <p className="mt-0.5 text-sm text-[var(--text-muted)]">
            {t("pageDescription")}
          </p>
        </div>
      </div>

      {/* 탭 */}
      <div className="flex gap-2 border-b border-[var(--border-subtle)]">
        {statusTabs.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setTab(s.id)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
              tab === s.id
                ? "border-[var(--text-primary)] text-[var(--text-primary)]"
                : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
            }`}
          >
            {s.label}
          </button>
        ))}
        {isSuperadmin && (
          <button
            type="button"
            onClick={() => setTab("service-keys")}
            className={`-mb-px ml-auto flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
              tab === "service-keys"
                ? "border-[var(--text-primary)] text-[var(--text-primary)]"
                : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
            }`}
          >
            <KeyRound className="h-3.5 w-3.5" />
            {t("tabs.serviceKeys")}
          </button>
        )}
      </div>

      {tab === "service-keys" ? (
        isSuperadmin && <ServiceKeysSection />
      ) : (
        <IntakeListSection status={tab} />
      )}
    </div>
  );
}

export default function AdminIntakePage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <IntakeContent />
    </RoleGuard>
  );
}

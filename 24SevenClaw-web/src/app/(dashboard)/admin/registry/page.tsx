"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { Plus, Trash2, Edit2, AlertCircle, X, Check } from "lucide-react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { RoleGuard } from "@/components/common/role-guard";
import {
  registryAgents,
  registrySkills,
  registryMcpServers,
  type RegistryItemResponse,
  type RegistryItemCreateRequest,
  type RegistryItemUpdateRequest,
} from "@/lib/api-client";

type ResourceKey = "agents" | "skills" | "mcp-servers";

const RESOURCE_LABELS: Record<ResourceKey, string> = {
  agents: "에이전트",
  skills: "스킬",
  "mcp-servers": "MCP 서버",
};

const resourceClient = {
  agents: registryAgents,
  skills: registrySkills,
  "mcp-servers": registryMcpServers,
};

const INITIAL_FORM: RegistryItemCreateRequest = {
  name: "",
  slug: "",
  description: "",
  body_md: "",
  version: "0.1.0",
  category: "",
  is_public: true,
  config_schema: {},
};

function RegistryTable({ resource, token }: { resource: ResourceKey; token: string }) {
  const qc = useQueryClient();
  const client = resourceClient[resource];

  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState<RegistryItemCreateRequest>(INITIAL_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<RegistryItemUpdateRequest>({});
  const [editBodyMd, setEditBodyMd] = useState("");
  const [showBodyMd, setShowBodyMd] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["registry", resource],
    queryFn: () => client.list(token, { limit: 100 }),
    enabled: !!token,
  });

  const createMutation = useMutation({
    mutationFn: (req: RegistryItemCreateRequest) => client.create(token, req),
    onSuccess: () => {
      toast.success("항목이 추가되었습니다.");
      qc.invalidateQueries({ queryKey: ["registry", resource] });
      setShowAdd(false);
      setForm(INITIAL_FORM);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: RegistryItemUpdateRequest }) =>
      client.update(token, id, data),
    onSuccess: () => {
      toast.success("항목이 업데이트되었습니다.");
      qc.invalidateQueries({ queryKey: ["registry", resource] });
      setEditingId(null);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => client.delete(token, id),
    onSuccess: () => {
      toast.success("항목이 삭제되었습니다.");
      qc.invalidateQueries({ queryKey: ["registry", resource] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const startEdit = (item: RegistryItemResponse) => {
    setEditingId(item.id);
    setEditForm({
      name: item.name,
      description: item.description ?? "",
      body_md: item.body_md ?? "",
      version: item.version,
      category: item.category ?? "",
      is_public: item.is_public,
    });
    setEditBodyMd(item.body_md ?? "");
  };

  if (isLoading) return <div className="py-8 text-center text-sm text-slate-500">불러오는 중...</div>;
  if (error) return (
    <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
      <AlertCircle className="h-4 w-4 shrink-0" />
      {(error as Error).message}
    </div>
  );

  const items = data?.items ?? [];

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-500"
        >
          <Plus className="h-4 w-4" />
          {RESOURCE_LABELS[resource]} 추가
        </button>
      </div>

      {showAdd && (
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5 space-y-4">
          <h3 className="text-sm font-semibold text-white">{RESOURCE_LABELS[resource]} 추가</h3>
          <div className="grid grid-cols-2 gap-3">
            {(["name", "slug", "version", "category"] as const).map((field) => (
              <div key={field}>
                <label className="block text-xs text-slate-400 mb-1">{field}</label>
                <input
                  className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
                  value={(form[field] as string) ?? ""}
                  onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                />
              </div>
            ))}
            <div className="col-span-2">
              <label className="block text-xs text-slate-400 mb-1">description</label>
              <input
                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white focus:border-violet-500/50 focus:outline-none"
                value={form.description ?? ""}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-xs text-slate-400 mb-1">body_md (Markdown 상세)</label>
              <textarea
                rows={6}
                className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-mono text-sm text-slate-300 focus:border-violet-500/50 focus:outline-none"
                value={form.body_md ?? ""}
                onChange={(e) => setForm({ ...form, body_md: e.target.value })}
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                id="add_is_public"
                type="checkbox"
                checked={form.is_public ?? true}
                onChange={(e) => setForm({ ...form, is_public: e.target.checked })}
                className="h-4 w-4 rounded border-white/20"
              />
              <label htmlFor="add_is_public" className="text-sm text-slate-300">공개</label>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => createMutation.mutate(form)}
              disabled={createMutation.isPending || !form.name || !form.slug}
              className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-500 disabled:opacity-50"
            >
              {createMutation.isPending ? "추가 중..." : "추가"}
            </button>
            <button
              type="button"
              onClick={() => { setShowAdd(false); setForm(INITIAL_FORM); }}
              className="rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-400 transition-colors hover:bg-white/5"
            >
              취소
            </button>
          </div>
        </div>
      )}

      {/* body_md 전체보기 모달 */}
      {showBodyMd !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="relative w-full max-w-2xl rounded-xl border border-white/10 bg-[#1a1a2e] p-6">
            <button
              type="button"
              onClick={() => setShowBodyMd(null)}
              className="absolute right-4 top-4 text-slate-500 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
            <h3 className="mb-3 text-sm font-semibold text-white">body_md 전체보기</h3>
            <pre className="max-h-[60vh] overflow-auto rounded-lg bg-black/40 p-4 font-mono text-xs text-slate-300 whitespace-pre-wrap">
              {showBodyMd || "(비어 있음)"}
            </pre>
          </div>
        </div>
      )}

      {items.length === 0 ? (
        <div className="py-12 text-center text-sm text-slate-600">항목이 없습니다.</div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-white/10">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/10 bg-white/[0.02]">
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">이름</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Slug</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">카테고리</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">버전</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">공개</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-400">액션</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                editingId === item.id ? (
                  <tr key={item.id} className="border-b border-white/5 bg-white/[0.03]">
                    <td className="px-4 py-3" colSpan={6}>
                      <div className="space-y-3">
                        <div className="grid grid-cols-3 gap-3">
                          {(["name", "version", "category"] as const).map((field) => (
                            <div key={field}>
                              <label className="block text-xs text-slate-400 mb-1">{field}</label>
                              <input
                                className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-white focus:border-violet-500/50 focus:outline-none"
                                value={(editForm[field] as string) ?? ""}
                                onChange={(e) => setEditForm({ ...editForm, [field]: e.target.value })}
                              />
                            </div>
                          ))}
                        </div>
                        <div>
                          <label className="block text-xs text-slate-400 mb-1">description</label>
                          <input
                            className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-white focus:border-violet-500/50 focus:outline-none"
                            value={editForm.description ?? ""}
                            onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-slate-400 mb-1">body_md</label>
                          <textarea
                            rows={6}
                            className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-mono text-sm text-slate-300 focus:border-violet-500/50 focus:outline-none"
                            value={editForm.body_md ?? ""}
                            onChange={(e) => setEditForm({ ...editForm, body_md: e.target.value })}
                          />
                        </div>
                        <div className="flex items-center gap-2">
                          <input
                            id={`edit_is_public_${item.id}`}
                            type="checkbox"
                            checked={editForm.is_public ?? true}
                            onChange={(e) => setEditForm({ ...editForm, is_public: e.target.checked })}
                            className="h-4 w-4 rounded border-white/20"
                          />
                          <label htmlFor={`edit_is_public_${item.id}`} className="text-sm text-slate-300">공개</label>
                        </div>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => updateMutation.mutate({ id: item.id, data: editForm })}
                            disabled={updateMutation.isPending}
                            className="flex items-center gap-1 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-500 disabled:opacity-50"
                          >
                            <Check className="h-3 w-3" />
                            저장
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingId(null)}
                            className="flex items-center gap-1 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-400 hover:bg-white/5"
                          >
                            <X className="h-3 w-3" />
                            취소
                          </button>
                        </div>
                      </div>
                    </td>
                  </tr>
                ) : (
                  <tr key={item.id} className="border-b border-white/5 hover:bg-white/[0.02]">
                    <td className="px-4 py-3">
                      <div className="text-sm text-white">{item.name}</div>
                      {item.description && (
                        <div className="text-xs text-slate-500 truncate max-w-[200px]">{item.description}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-sm text-slate-400">{item.slug}</td>
                    <td className="px-4 py-3 text-sm text-slate-400">{item.category ?? "—"}</td>
                    <td className="px-4 py-3 text-sm text-slate-400">{item.version}</td>
                    <td className="px-4 py-3 text-xs text-slate-400">{item.is_public ? "✓" : "—"}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-1">
                        {item.body_md && (
                          <button
                            type="button"
                            onClick={() => setShowBodyMd(item.body_md)}
                            className="rounded-lg border border-white/10 px-2 py-1 text-xs text-slate-400 hover:bg-white/5"
                          >
                            MD
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => startEdit(item)}
                          className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-2.5 py-1 text-xs text-slate-400 hover:bg-white/5"
                        >
                          <Edit2 className="h-3 w-3" />
                          편집
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            if (!confirm(`"${item.name}" 항목을 삭제하시겠습니까?`)) return;
                            deleteMutation.mutate(item.id);
                          }}
                          disabled={deleteMutation.isPending}
                          className="inline-flex items-center gap-1 rounded-lg border border-red-500/20 px-2.5 py-1 text-xs text-red-400 hover:bg-red-500/10 disabled:opacity-50"
                        >
                          <Trash2 className="h-3 w-3" />
                          삭제
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function RegistryAdminPage() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";
  const [activeTab, setActiveTab] = useState<ResourceKey>("agents");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-white">Registry 관리</h1>
        <p className="text-xs text-slate-500">Agent / Skill / MCP 서버 CRUD</p>
      </div>

      {/* 탭 */}
      <div className="flex gap-1 rounded-xl border border-white/10 bg-white/[0.02] p-1 w-fit">
        {(["agents", "skills", "mcp-servers"] as const).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setActiveTab(key)}
            className={`rounded-lg px-4 py-1.5 text-xs font-medium transition-colors ${
              activeTab === key
                ? "bg-violet-600 text-white"
                : "text-slate-400 hover:text-slate-300"
            }`}
          >
            {RESOURCE_LABELS[key]}
          </button>
        ))}
      </div>

      <RegistryTable resource={activeTab} token={token} />
    </div>
  );
}

export default function AdminRegistryPage() {
  return (
    <RoleGuard roles={["superadmin", "admin"]}>
      <RegistryAdminPage />
    </RoleGuard>
  );
}

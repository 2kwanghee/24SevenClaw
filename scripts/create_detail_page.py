"""프로젝트 상세 페이지 생성 스크립트"""
import os

dir_path = os.path.join(
    "/mnt/c/workspace/24SevenClaw/clickeye-web/src/app/(dashboard)/projects/[id]"
)
os.makedirs(dir_path, exist_ok=True)

content = r'''"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { ProjectForm } from "@/components/projects/project-form";
import { useDeleteProject, useProject, useUpdateProject } from "@/hooks/use-projects";
import { ApiClientError } from "@/lib/api-client";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: project, isLoading, error } = useProject(id);
  const updateProject = useUpdateProject(id);
  const deleteProject = useDeleteProject();
  const [isEditing, setIsEditing] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  if (isLoading) {
    return <div className="py-12 text-center text-gray-500">불러오는 중...</div>;
  }

  if (error || !project) {
    return (
      <div className="py-12 text-center">
        <p className="text-red-600">프로젝트를 찾을 수 없습니다.</p>
        <Link href="/projects" className="mt-4 inline-block text-sm text-blue-600 hover:underline">
          목록으로 돌아가기
        </Link>
      </div>
    );
  }

  const handleDelete = () => {
    if (!confirm("정말 이 프로젝트를 삭제하시겠습니까?")) return;
    deleteProject.mutate(id, {
      onSuccess: () => router.push("/projects"),
    });
  };

  const createdAt = new Date(project.created_at).toLocaleString("ko-KR");
  const updatedAt = new Date(project.updated_at).toLocaleString("ko-KR");

  return (
    <div>
      <div className="mb-6">
        <Link href="/projects" className="text-sm text-gray-500 hover:text-gray-700">
          &larr; 프로젝트 목록
        </Link>
      </div>

      {isEditing ? (
        <div className="mx-auto max-w-lg rounded-lg border bg-white p-8 shadow-sm">
          <h1 className="mb-6 text-xl font-bold">프로젝트 수정</h1>

          {formError && (
            <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{formError}</div>
          )}

          <ProjectForm
            defaultValues={{ name: project.name, description: project.description ?? "" }}
            isSubmitting={updateProject.isPending}
            submitLabel="저장"
            onSubmit={(data) => {
              setFormError(null);
              updateProject.mutate(data, {
                onSuccess: () => setIsEditing(false),
                onError: (err) => {
                  if (err instanceof ApiClientError) {
                    setFormError(err.detail);
                  } else {
                    setFormError("수정에 실패했습니다.");
                  }
                },
              });
            }}
          />

          <button
            type="button"
            onClick={() => setIsEditing(false)}
            className="mt-3 w-full rounded-md px-4 py-2 text-sm text-gray-600 hover:bg-gray-100"
          >
            취소
          </button>
        </div>
      ) : (
        <div>
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold">{project.name}</h1>
              <p className="mt-1 text-sm text-gray-400">{project.slug}</p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="rounded-md border px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                수정
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleteProject.isPending}
                className="rounded-md border border-red-200 px-4 py-2 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                {deleteProject.isPending ? "삭제 중..." : "삭제"}
              </button>
            </div>
          </div>

          <div className="mt-2">
            <span
              className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                project.status === "active"
                  ? "bg-green-100 text-green-700"
                  : "bg-gray-100 text-gray-600"
              }`}
            >
              {project.status === "active" ? "활성" : "보관됨"}
            </span>
          </div>

          {project.description && (
            <p className="mt-4 text-gray-700">{project.description}</p>
          )}

          <div className="mt-8 rounded-lg border bg-gray-50 p-4">
            <h2 className="mb-3 text-sm font-semibold text-gray-600">프로젝트 정보</h2>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-gray-400">생성일</dt>
                <dd className="text-gray-700">{createdAt}</dd>
              </div>
              <div>
                <dt className="text-gray-400">수정일</dt>
                <dd className="text-gray-700">{updatedAt}</dd>
              </div>
            </dl>
          </div>
        </div>
      )}
    </div>
  );
}
'''

file_path = os.path.join(dir_path, "page.tsx")
with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Created: {file_path}")

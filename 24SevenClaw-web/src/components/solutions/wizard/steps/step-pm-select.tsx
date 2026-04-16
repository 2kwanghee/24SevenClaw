"use client";

import { Loader2, UserCircle2, Star, CheckCircle2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";

import { useSolutionWizardStore } from "@/stores/solution-wizard-store";
import { pmProfiles, type PMProfileResponse } from "@/lib/api-client";
import { cn } from "@/lib/utils";

export function StepPMSelect() {
  const { data: session } = useSession();
  const token = session?.accessToken ?? "";

  const selectedPrototypeId = useSolutionWizardStore(
    (s) => s.data.prototypes.selectedPrototypeId,
  );
  const selectedPmProfileId = useSolutionWizardStore(
    (s) => s.data.pm.selectedPmProfileId,
  );
  const setPM = useSolutionWizardStore((s) => s.setPM);

  const [profiles, setProfiles] = useState<PMProfileResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!token) return;

    const fetchProfiles = async () => {
      setIsLoading(true);
      try {
        if (selectedPrototypeId) {
          const result = await pmProfiles.recommend(token, {
            prototype_id: selectedPrototypeId,
          });
          setProfiles(result.items.map((r) => r.pm_profile));
        } else {
          const result = await pmProfiles.list(token, {
            is_active: true,
            limit: 10,
          });
          setProfiles(result.items);
        }
      } catch {
        setProfiles([]);
      } finally {
        setIsLoading(false);
      }
    };

    void fetchProfiles();
  }, [token, selectedPrototypeId]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
        <p className="mt-3 text-sm text-slate-400">
          적합한 PM을 찾고 있습니다...
        </p>
      </div>
    );
  }

  if (profiles.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <UserCircle2 className="h-10 w-10 text-slate-600" />
        <p className="mt-4 text-sm text-slate-400">
          추천 가능한 PM 프로필이 없습니다
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-400">
        프로젝트를 함께 이끌어갈 AI PM을 선택하세요.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {profiles.map((profile) => {
          const isSelected = selectedPmProfileId === profile.id;
          return (
            <button
              key={profile.id}
              type="button"
              onClick={() =>
                setPM({ selectedPmProfileId: profile.id })
              }
              aria-pressed={isSelected}
              className={cn(
                "relative rounded-xl border p-4 text-left transition-all duration-200",
                isSelected
                  ? "border-emerald-500/50 bg-emerald-500/10 ring-2 ring-emerald-500/20"
                  : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/[0.07]",
              )}
            >
              {isSelected && (
                <CheckCircle2 className="absolute right-3 top-3 h-4 w-4 text-emerald-400" />
              )}
              <div className="mb-2 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/10">
                  <UserCircle2 className="h-6 w-6 text-emerald-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">
                    {profile.name}
                  </p>
                  <p className="text-xs text-emerald-400">{profile.specialty}</p>
                </div>
              </div>
              {profile.description && (
                <p className="text-xs leading-relaxed text-slate-400">
                  {profile.description}
                </p>
              )}
              {profile.skills.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1">
                  {profile.skills.slice(0, 4).map((skill) => (
                    <span
                      key={skill}
                      className="rounded-md bg-white/5 px-2 py-0.5 text-xs text-slate-500"
                    >
                      {skill}
                    </span>
                  ))}
                  {profile.skills.length > 4 && (
                    <span className="rounded-md bg-white/5 px-2 py-0.5 text-xs text-slate-600">
                      +{profile.skills.length - 4}
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>
      <p className="flex items-center gap-1.5 text-xs text-slate-500">
        <Star className="h-3 w-3 text-yellow-500" />
        PM 선택은 나중에 변경할 수 있습니다
      </p>
    </div>
  );
}

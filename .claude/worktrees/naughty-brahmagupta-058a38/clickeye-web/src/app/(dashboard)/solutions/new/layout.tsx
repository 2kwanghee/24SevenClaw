import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "새 솔루션 | ClickEye",
  description: "7단계 위저드로 AI 솔루션을 자동 설계합니다",
};

export default function NewSolutionLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}

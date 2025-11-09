import { useQuery } from "@tanstack/react-query";

export type Category =
  | "Public"
  | "Confidential"
  | "Highly Sensitive"
  | "Unsafe"
  | "Unclassified";

export type DashboardDocument = {
  docId: string;
  filename: string;
  uploadedAt: string | null;
  status: string | null;
  pageCount: number | null;
  imageCount: number | null;
  legibilityScore: number | null;
  finalCategory: Category;
  requiresReview: boolean;
  confidence: number | null;
  contentSafety: string | null;
  classifiedAt: string | null;
  unsafe: boolean;
};

export type DashboardCounts = {
  total: number;
  public: number;
  confidential: number;
  highlySensitive: number;
  unsafe: number;
  needsReview: number;
  averageConfidence: number;
};

export type DashboardResponse = {
  documents: DashboardDocument[];
  counts: DashboardCounts;
  summary: Record<string, unknown>;
  generatedAt: string;
  limit: number;
};

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

async function fetchDashboard(limit: number): Promise<DashboardResponse> {
  const url = new URL(`${API_BASE_URL}/dashboard`);
  url.searchParams.set("limit", String(limit));
  const response = await fetch(url.toString());

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(
      `Dashboard request failed (${response.status}): ${detail || "Unknown error"}`,
    );
  }

  return (await response.json()) as DashboardResponse;
}

export const DASHBOARD_QUERY_KEY = "dashboard";

export function useDashboardData(limit = 50) {
  return useQuery({
    queryKey: [DASHBOARD_QUERY_KEY, limit],
    queryFn: () => fetchDashboard(limit),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
  });
}

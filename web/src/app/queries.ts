import { useQuery } from "@tanstack/react-query";
import { ApiError, fetchResearch, fetchReview, shouldRetry } from "../lib/api";
import { useMode } from "./Mode";
export function useReview(id: string) {
  const { preview } = useMode();
  return useQuery({
    queryKey: [preview ? "research" : "review", id],
    queryFn: async ({ signal }) => {
      if (preview) {
        const r = await fetchResearch(signal);
        if (r.id !== id)
          throw new ApiError(
            "This experiment is not in the committed research preview.",
            404,
          );
        return r;
      }
      return fetchReview(id, signal);
    },
    retry: shouldRetry,
    staleTime: 60_000,
  });
}

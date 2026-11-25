import { useMutation, useQueryClient } from '@tanstack/react-query';
import { saved } from '@/api/endpoints';

/**
 * Save / unsave a word. WordSummary exposes `saved` but not the saved-word id,
 * so unsaving first POSTs (idempotent: returns the existing SavedItem) to learn
 * the id, then DELETEs it. See docs/DECISIONS.md.
 */
export function useSaveToggle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ wordId, save }: { wordId: number; save: boolean }) => {
      const item = await saved.save(wordId);
      if (!save) await saved.remove(item.id);
      return save;
    },
    onSuccess: () => {
      for (const key of ['word', 'search', 'saved', 'saved-stats', 'history', 'season-word'])
        void qc.invalidateQueries({ queryKey: [key] });
    },
  });
}

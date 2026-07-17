import { getAllQuestions } from '@/lib/questions';
import HomeClient from '@/components/HomeClient';
import type { Question } from '@/lib/types';

export default function Page() {
  // Pass lightweight summaries to the homepage (no full answer text).
  // Answers are lazy-loaded from per-category JSON chunks when a modal
  // or study/review mode is opened. This keeps the homepage HTML ~2MB
  // instead of ~24MB, critical for iPad performance.
  const all = getAllQuestions();
  const questions: Question[] = all.map((q) => ({
    ...q,
    // Truncate answer to 300 chars for search indexing; full answer
    // is loaded on demand via useAnswer hook.
    answer: q.answer.slice(0, 300),
  }));
  return <HomeClient questions={questions} />;
}

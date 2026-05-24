import { useEffect, useState } from 'react';
import { getRepoState, type RepoState } from './api';

// Banner that surfaces the current ranked/experimental phase so the
// operator knows whether the next batch will update the official ELO
// record. Polls every few seconds so a branch switch / commit / stash
// is reflected quickly without needing a page reload.
//
// See knowledge-base/decisions/2026-05-24-ranked-vs-experimental.md.

const POLL_MS = 5000;

export function RepoStateBanner() {
  const [state, setState] = useState<RepoState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function tick() {
      try {
        const next = await getRepoState();
        if (!cancelled) {
          setState(next);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) timer = setTimeout(tick, POLL_MS);
      }
    }
    tick();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  if (error) {
    return (
      <div className="repo-banner repo-banner-error">
        repo state unavailable: {error}
      </div>
    );
  }
  if (!state) {
    return <div className="repo-banner repo-banner-loading">checking repo state…</div>;
  }

  const isRanked = state.phase === 'ranked';
  return (
    <div className={`repo-banner repo-banner-${state.phase}`}>
      <span className="repo-banner-label">
        {isRanked ? 'RANKED' : 'EXPERIMENTAL'}
      </span>
      <span className="repo-banner-detail">
        {isRanked
          ? 'batches will write to ranked.csv and update ELO'
          : `batches will write to experimental.csv · ${state.reason}`}
      </span>
      <span className="repo-banner-git">
        <code>{state.branch || '(no repo)'}</code>
        {state.short_sha && <code>@{state.short_sha}</code>}
        {state.dirty && <span className="repo-banner-dirty">dirty</span>}
      </span>
    </div>
  );
}

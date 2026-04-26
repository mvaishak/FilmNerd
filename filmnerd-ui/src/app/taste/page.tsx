'use client'

import useSWR from 'swr'
import { useState } from 'react'
import { ArrowDown, ArrowUp } from 'lucide-react'
import { api } from '@/lib/api'
import type { TasteProfile } from '@/lib/types'
import { LoadingSkeleton } from '@/components/shared/loading-skeleton'
import { formatDimension } from '@/lib/utils'

export default function TastePage() {
  const { data: profile, error, isLoading, mutate } = useSWR<TasteProfile>(
    'taste-profile',
    api.getTasteProfile
  )
  const [retrainState, setRetrainState] = useState<'idle' | 'training' | 'done'>('idle')

  async function handleRetrain() {
    setRetrainState('training')
    await api.retrainTasteModel()
    await mutate()
    setRetrainState('done')
    setTimeout(() => setRetrainState('idle'), 3000)
  }

  if (isLoading) {
    return (
      <div className="px-8 py-12 space-y-16">
        <LoadingSkeleton className="h-6 w-24" />
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <LoadingSkeleton key={i} className="h-8 w-32" />
          ))}
        </div>
      </div>
    )
  }

  if (error || !profile) {
    return (
      <div className="px-8 py-12">
        <p className="text-xs text-[#71717a] font-mono">
          failed to load taste profile —{' '}
          <button onClick={() => mutate()} className="underline">retry</button>
        </p>
      </div>
    )
  }

  const topDims = profile.interpretable_dimensions || []
  const dimWeights = profile.ridge_dimension_weights || {}
  const maxWeight = Math.max(...Object.values(dimWeights), 0.001)

  const divergence = profile.divergence_profile || {}
  const divergenceRows: { dim: string; val: string; score: number }[] = []
  for (const [dim, vals] of Object.entries(divergence)) {
    for (const [val, score] of Object.entries(vals as Record<string, number>)) {
      divergenceRows.push({ dim, val, score })
    }
  }
  divergenceRows.sort((a, b) => Math.abs(b.score) - Math.abs(a.score))
  const topDivergence = divergenceRows.slice(0, 10)

  const modelComparison = profile.model_comparison || {}
  const bestModel = profile.best_model

  return (
    <div className="px-8 py-12 space-y-16">
      <h1 className="text-2xl font-light lowercase tracking-[-0.05em]">taste</h1>

      {/* Section 1 — Summary stats */}
      <div className="border-b border-[#27272a] pb-12">
        <div className="flex gap-16">
          <StatBlock value={String(profile.trained_on_n_films)} label="films" />
          <StatBlock value={(profile.mean_user_rating ?? 0).toFixed(2)} label="mean rating" />
          <StatBlock value={(profile.prediction_mae ?? 0).toFixed(3)} label="pred. mae" />
          <StatBlock
            value={((profile.variance_explained ?? 0) * 100).toFixed(1) + '%'}
            label="variance expl."
          />
        </div>
      </div>

      {/* Section 2 — Dimensions + Divergence */}
      <div className="grid grid-cols-2 gap-16">
        {/* Left: predictive dimensions */}
        <div className="space-y-6">
          <p className="text-xs uppercase tracking-[0.12em] text-[#71717a]">
            predictive dimensions
          </p>
          <div className="space-y-4">
            {topDims.slice(0, 10).map((dim) => {
              const weight = dimWeights[dim] ?? 0
              const pct = (weight / maxWeight) * 100
              return (
                <div key={dim} className="space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-mono text-white">{dim}</span>
                    <span className="text-xs font-mono text-[#71717a]">
                      {weight.toFixed(4)}
                    </span>
                  </div>
                  <div className="flex gap-0 h-px">
                    <div className="bg-white" style={{ width: `${pct}%` }} />
                    <div className="bg-[#27272a] flex-1" />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Right: divergence from consensus */}
        <div className="space-y-6">
          <p className="text-xs uppercase tracking-[0.12em] text-[#71717a]">
            divergence from consensus
          </p>
          <div className="space-y-3">
            {topDivergence.map(({ dim, val, score }) => (
              <div key={`${dim}-${val}`} className="flex items-center gap-3">
                {score < 0 ? (
                  <ArrowDown size={10} className="text-[#71717a] flex-shrink-0" />
                ) : (
                  <ArrowUp size={10} className="text-[#71717a] flex-shrink-0" />
                )}
                <span className="text-sm font-mono flex-1">
                  {dim} · {formatDimension(val)}
                </span>
                <span className={`text-sm font-mono tabular-nums ${score < 0 ? 'text-[#71717a]' : 'text-white'}`}>
                  {score > 0 ? '+' : ''}{score.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Section 3 — Model comparison */}
      <div className="grid grid-cols-2 gap-16">
        <div className="space-y-6">
          <p className="text-xs uppercase tracking-[0.12em] text-[#71717a]">model comparison</p>
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="text-left text-xs uppercase tracking-[0.12em] text-[#71717a] pb-3 font-normal">
                  model
                </th>
                <th className="text-right text-xs uppercase tracking-[0.12em] text-[#71717a] pb-3 font-normal">
                  r²
                </th>
                <th className="text-right text-xs uppercase tracking-[0.12em] text-[#71717a] pb-3 font-normal">
                  mae
                </th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(modelComparison)
                .sort((a, b) => a[1].mae_mean - b[1].mae_mean)
                .map(([name, stats]) => {
                  const active = name === bestModel
                  return (
                    <tr key={name}>
                      <td className={`font-mono py-1 ${active ? 'text-white' : 'text-[#71717a]'}`}>
                        {name} {active && '←'}
                      </td>
                      <td className={`font-mono py-1 text-right tabular-nums ${active ? 'text-white' : 'text-[#71717a]'}`}>
                        {stats.r2_mean.toFixed(3)}
                      </td>
                      <td className={`font-mono py-1 text-right tabular-nums ${active ? 'text-white' : 'text-[#71717a]'}`}>
                        {stats.mae_mean.toFixed(3)}
                      </td>
                    </tr>
                  )
                })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Retrain button */}
      <div>
        <button
          onClick={handleRetrain}
          disabled={retrainState === 'training'}
          className="border border-[#27272a] px-4 py-2 text-xs font-mono text-[#71717a] hover:text-white hover:border-white disabled:opacity-50"
        >
          {retrainState === 'idle' && 'retrain taste model'}
          {retrainState === 'training' && 'retraining...'}
          {retrainState === 'done' && `retrained · ${profile.trained_on_n_films} films`}
        </button>
      </div>
    </div>
  )
}

function StatBlock({ value, label }: { value: string; label: string }) {
  return (
    <div className="space-y-2">
      <p className="text-3xl font-mono tabular-nums">{value}</p>
      <p className="text-xs uppercase tracking-widest text-[#71717a]">{label}</p>
    </div>
  )
}

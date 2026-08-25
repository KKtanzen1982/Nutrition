<script setup lang="ts">
import { computed } from 'vue'

interface TrendPoint {
  label: string
  value: number | null
}

const props = withDefaults(
  defineProps<{
    points: TrendPoint[]
    mode?: 'line' | 'bar'
    variant?: 'primary' | 'secondary'
    height?: number
    unit?: string
    decimals?: number
    referenceValue?: number | null
    referenceLabel?: string
    filled?: boolean
    compact?: boolean
  }>(),
  {
    mode: 'line',
    variant: 'primary',
    height: 160,
    unit: '',
    decimals: 1,
    referenceValue: null,
    referenceLabel: '',
    filled: false,
    compact: false,
  },
)

const WIDTH = 600
const PAD_R = 12
const PAD_T = 12

const PAD_L = computed(() => (props.compact ? 4 : 44))
const PAD_B = computed(() => (props.compact ? 4 : 22))

const plotW = computed(() => WIDTH - PAD_L.value - PAD_R)
const plotH = computed(() => props.height - PAD_T - PAD_B.value)

const yDomain = computed(() => {
  const values = props.points.map((p) => p.value).filter((v): v is number => v !== null)
  if (props.referenceValue !== null) values.push(props.referenceValue)

  if (props.mode === 'bar') {
    const max = values.length ? Math.max(...values, 0) : 1
    return { min: 0, max: max === 0 ? 1 : max * 1.15 }
  }

  if (!values.length) return { min: 0, max: 1 }
  const min = Math.min(...values)
  const max = Math.max(...values)
  if (min === max) return { min: min - 1, max: max + 1 }
  const pad = (max - min) * 0.15
  return { min: min - pad, max: max + pad }
})

function xFor(i: number): number {
  const n = props.points.length
  if (n <= 1) return PAD_L.value + plotW.value / 2
  return PAD_L.value + (i / (n - 1)) * plotW.value
}

function yFor(v: number): number {
  const { min, max } = yDomain.value
  const ratio = (v - min) / (max - min || 1)
  return PAD_T + plotH.value - ratio * plotH.value
}

const barWidth = computed(() => Math.min(24, (plotW.value / Math.max(props.points.length, 1)) * 0.6))

const segments = computed(() => {
  const result: { x: number; y: number }[][] = []
  let current: { x: number; y: number }[] = []
  props.points.forEach((p, i) => {
    if (p.value === null) {
      if (current.length) {
        result.push(current)
        current = []
      }
      return
    }
    current.push({ x: xFor(i), y: yFor(p.value) })
  })
  if (current.length) result.push(current)
  return result
})

const labelIndices = computed(() => {
  const count = props.points.length
  if (count === 0) return []
  const maxLabels = Math.min(6, count)
  if (count <= maxLabels) return props.points.map((_, i) => i)
  const idxs = new Set<number>()
  for (let k = 0; k < maxLabels; k++) {
    idxs.add(Math.round((k / (maxLabels - 1)) * (count - 1)))
  }
  return [...idxs].sort((a, b) => a - b)
})

function formatY(v: number): string {
  return `${v.toFixed(props.decimals)}${props.unit}`
}

const baselineY = computed(() => PAD_T + plotH.value)

const areaPaths = computed(() =>
  segments.value
    .filter((seg) => seg.length > 0)
    .map((seg) => {
      const first = seg[0]
      const last = seg[seg.length - 1]
      const line = seg.map((pt) => `${pt.x},${pt.y}`).join(' L ')
      return `M ${first.x},${baselineY.value} L ${line} L ${last.x},${baselineY.value} Z`
    }),
)
</script>

<template>
  <svg :viewBox="`0 0 ${WIDTH} ${height}`" class="w-full" :style="{ height: `${height}px` }" preserveAspectRatio="none">
    <line :x1="PAD_L" :x2="WIDTH - PAD_R" :y1="height - PAD_B" :y2="height - PAD_B" class="stroke-ink/10" stroke-width="1" />

    <template v-if="!compact">
      <text :x="PAD_L - 6" :y="PAD_T + 4" text-anchor="end" class="fill-tea text-[10px]">{{ formatY(yDomain.max) }}</text>
      <text :x="PAD_L - 6" :y="height - PAD_B" text-anchor="end" class="fill-tea text-[10px]">{{ formatY(yDomain.min) }}</text>
    </template>

    <g v-if="referenceValue !== null">
      <line
        :x1="PAD_L"
        :x2="WIDTH - PAD_R"
        :y1="yFor(referenceValue)"
        :y2="yFor(referenceValue)"
        class="stroke-tea"
        stroke-width="1"
        stroke-dasharray="4 3"
      />
      <text :x="WIDTH - PAD_R" :y="yFor(referenceValue) - 4" text-anchor="end" class="fill-tea text-[10px]">
        {{ referenceLabel }}
      </text>
    </g>

    <g v-if="mode === 'bar'">
      <rect
        v-for="(p, i) in points"
        v-show="p.value !== null"
        :key="i"
        :x="xFor(i) - barWidth / 2"
        :y="yFor(p.value ?? 0)"
        :width="barWidth"
        :height="height - PAD_B - yFor(p.value ?? 0)"
        rx="2"
        :class="variant === 'primary' ? 'fill-accent' : 'fill-tea'"
      >
        <title>{{ p.label }}：{{ p.value ?? '—' }}{{ unit }}</title>
      </rect>
    </g>

    <g v-else>
      <template v-if="filled">
        <path
          v-for="(d, si) in areaPaths"
          :key="`a-${si}`"
          :d="d"
          stroke="none"
          :class="variant === 'primary' ? 'fill-accent/15' : 'fill-tea/10'"
        />
      </template>
      <polyline
        v-for="(seg, si) in segments"
        :key="si"
        :points="seg.map((pt) => `${pt.x},${pt.y}`).join(' ')"
        fill="none"
        :class="variant === 'primary' ? 'stroke-accent' : 'stroke-tea'"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <circle
        v-for="(p, i) in points"
        v-show="p.value !== null"
        :key="`c-${i}`"
        :cx="xFor(i)"
        :cy="yFor(p.value ?? 0)"
        r="2.5"
        :class="variant === 'primary' ? 'fill-accent' : 'fill-tea'"
      >
        <title>{{ p.label }}：{{ p.value ?? '—' }}{{ unit }}</title>
      </circle>
    </g>

    <template v-if="!compact">
      <text
        v-for="i in labelIndices"
        :key="`x-${i}`"
        :x="xFor(i)"
        :y="height - 6"
        text-anchor="middle"
        class="fill-tea text-[10px]"
      >
        {{ points[i]?.label }}
      </text>
    </template>
  </svg>
</template>

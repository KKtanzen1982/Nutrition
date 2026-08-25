export function toISODate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function today(): Date {
  return new Date()
}

export function daysAgo(n: number, from: Date = new Date()): Date {
  const d = new Date(from)
  d.setDate(d.getDate() - n)
  return d
}

export function startOfWeekMonday(d: Date): Date {
  const date = new Date(d)
  const day = date.getDay() // 0 = Sun ... 6 = Sat
  const diff = (day === 0 ? -6 : 1) - day
  date.setDate(date.getDate() + diff)
  date.setHours(0, 0, 0, 0)
  return date
}

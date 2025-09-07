export const formatDateShort = (isoDateString: string): string => {
  return new Date(isoDateString).toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
} 
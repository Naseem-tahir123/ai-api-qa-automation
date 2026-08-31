export const methodClasses = {
  GET: 'method-get', POST: 'method-post', PUT: 'method-put', PATCH: 'method-patch', DELETE: 'method-delete',
}

export function formatDate(value) {
  if (!value) return 'Today'
  return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value))
}

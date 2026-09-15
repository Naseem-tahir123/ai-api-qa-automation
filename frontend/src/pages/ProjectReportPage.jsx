import { Navigate, useParams } from 'react-router-dom'

// Evidence is specification-scoped and is displayed after a pipeline run.
export default function ProjectReportPage() {
  const { projectId } = useParams()
  return <Navigate to={`/projects/${projectId}`} replace />
}

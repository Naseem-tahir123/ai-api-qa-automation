import { useCallback, useEffect, useState } from 'react'
import { projectService } from '../services/api'
import { useToast } from '../context/ToastContext'

export function useProjects() {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const { notify } = useToast()
  const refresh = useCallback(async () => {
    setLoading(true)
    try { setProjects(await projectService.list()) }
    catch (error) { notify(error.message, 'error') }
    finally { setLoading(false) }
  }, [notify])
  useEffect(() => { refresh() }, [refresh])
  const createProject = useCallback(async (input) => {
    const project = await projectService.create(input)
    setProjects((current) => [project, ...current])
    return project
  }, [])
  return { projects, loading, refresh, createProject }
}

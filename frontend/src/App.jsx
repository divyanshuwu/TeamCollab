import { apiRequest } from './api/client'
import { useState, useEffect } from 'react'
import { supabase } from './utils/supabase'
import './App.css'
import Auth from './Auth'

function App() {
  const [authLoading, setAuthLoading] = useState(true)
  const [user, setUser] = useState(null)
  const [projects, setProjects] = useState([])
  const [teamMembers, setTeamMembers] = useState([])
  const [membersLoading, setMembersLoading] = useState(false)
  const [showMemberForm, setShowMemberForm] = useState(false)
  const [memberProjectId, setMemberProjectId] = useState('')
  const [memberUserId, setMemberUserId] = useState('')
  const [memberError, setMemberError] = useState('')
  const [memberSaving, setMemberSaving] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [projectName, setProjectName] = useState('')
  const [projectDescription, setProjectDescription] = useState('')
  const [activePage, setActivePage] = useState('Dashboard')
  const [tasks, setTasks] = useState([])
  const [tasksLoading, setTasksLoading] = useState(false)
  const [showTaskForm, setShowTaskForm] = useState(false)
  const [editingTaskId, setEditingTaskId] = useState(null)
  const [editTaskTitle, setEditTaskTitle] = useState('')
  const [editTaskDescription, setEditTaskDescription] = useState('')
  const [editTaskPriority, setEditTaskPriority] = useState('medium')
  const [taskTitle, setTaskTitle] = useState('')
  const [taskDescription, setTaskDescription] = useState('')
  const [taskPriority, setTaskPriority] = useState('medium')
  const [taskProjectId, setTaskProjectId] = useState('')
  const [taskSaving, setTaskSaving] = useState(false)
  const [taskError, setTaskError] = useState('')

  const [taskStats, setTaskStats] = useState({
    total: 0,
    todo: 0,
    in_progress: 0,
    done: 0,
  })

  async function loadTasks(projectList) {
    setTasksLoading(true)

    try {
      const taskLists = await Promise.all(
        projectList.map(async (project) => {
          const projectTasks = await apiRequest(
            `/projects/${project.id}/tasks/`
          )

          return projectTasks.map((task) => ({
            ...task,
            project_name: project.name,
          }))
        })
      )

      setTasks(taskLists.flat())
    } catch (error) {
      console.error('Failed to load tasks:', error)
    } finally {
      setTasksLoading(false)
    }
  }


async function loadTeamMembers(projectList) {
  setMembersLoading(true)

  try {
    const memberLists = await Promise.all(
      projectList.map(async (project) => {
        const members = await apiRequest(
          `/projects/${project.id}/members`
        )

        return members.map((member) => ({
          ...member,
          project_id: project.id,
          project_name: project.name,
        }))
      })
    )

    setTeamMembers(memberLists.flat())
  } catch (error) {
    console.error('Failed to load team members:', error)
    setTeamMembers([])
  } finally {
    setMembersLoading(false)
  }
}



async function addTeamMember(e) {
  e.preventDefault()
  setMemberError('')

  if (!memberProjectId || !memberUserId.trim()) {
    setMemberError('Please select a project and enter a user ID.')
    return
  }

  const userId = Number(memberUserId)

  if (!Number.isInteger(userId) || userId <= 0) {
    setMemberError('User ID must be a positive integer.')
    return
  }

  setMemberSaving(true)

  try {
    await apiRequest(`/projects/${memberProjectId}/members`, {
      method: 'POST',
      body: JSON.stringify({
        user_id: userId,
        role: 'member',
      }),
    })

    setMemberUserId('')
    setMemberProjectId('')
    setShowMemberForm(false)

    await loadTeamMembers(projects)
  } catch (error) {
    setMemberError(error.message)
  } finally {
    setMemberSaving(false)
  }
}

  async function updateTaskStatus(task, newStatus) {
    try {
      await apiRequest(
        `/projects/${task.project_id}/tasks/${task.id}/status`,
        {
          method: 'PATCH',
          body: JSON.stringify({
            status: newStatus,
          }),
        }
      )

      setTasks((currentTasks) =>
        currentTasks.map((currentTask) =>
          currentTask.id === task.id
            ? { ...currentTask, status: newStatus }
            : currentTask
        )
      )
    } catch (error) {
      alert(`Failed to update task status: ${error.message}`)
      await loadTasks(projects)
    }
  }


  async function deleteTask(task) {
    const confirmed = window.confirm(
      `Are you sure you want to delete "${task.title}"?`
    )

    if (!confirmed) return

    try {
      await apiRequest(
        `/projects/${task.project_id}/tasks/${task.id}`,
        { method: 'DELETE' }
      )

      setTasks((currentTasks) =>
        currentTasks.filter(
          (currentTask) => currentTask.id !== task.id
        )
      )

      await loadTaskStats()
    } catch (error) {
      alert(`Failed to delete task: ${error.message}`)
    }
  }


  async function saveTaskEdit(task) {
    try {
      await apiRequest(
        `/projects/${task.project_id}/tasks/${task.id}`,
        {
          method: 'PUT',
          body: JSON.stringify({
            title: editTaskTitle.trim(),
            description: editTaskDescription.trim(),
            priority: editTaskPriority,
            assigned_to: task.assigned_to ?? null,
            due_date: task.due_date ?? null,
          }),
        }
      )

      setTasks((currentTasks) =>
        currentTasks.map((currentTask) =>
          currentTask.id === task.id
            ? {
                ...currentTask,
                title: editTaskTitle.trim(),
                description: editTaskDescription.trim(),
                priority: editTaskPriority,
              }
            : currentTask
        )
      )

      setEditingTaskId(null)
    } catch (error) {
      alert(`Failed to update task: ${error.message}`)
    }
  }

  async function loadTaskStats() {
    try {
      const summary = await apiRequest('/projects/summary')
      setTaskStats({
        total: summary.total_tasks,
        todo: summary.todo,
        in_progress: summary.in_progress,
        done: summary.done,
      })
    } catch (error) {
      console.error('Failed to load task statistics:', error)
    }
  }

  useEffect(() => {
    if (!user) return undefined
    let cancelled = false

    async function fetchDashboard() {
      try {
        const [projectData, summary] = await Promise.all([
          apiRequest('/projects/'),
          apiRequest('/projects/summary'),
        ])
        if (cancelled) return
        setProjects(projectData)
        setTaskStats({
          total: summary.total_tasks,
          todo: summary.todo,
          in_progress: summary.in_progress,
          done: summary.done,
        })
      } catch (error) {
        if (!cancelled) console.error('Failed to load dashboard:', error)
      }
    }

    void fetchDashboard()
    return () => { cancelled = true }
  }, [user])

  useEffect(() => {
    async function restoreSession() {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        const legacyToken = localStorage.getItem('access_token')
        if (!session && !legacyToken) return

        const currentUser = await apiRequest('/auth/me')
        setUser(currentUser)
      } catch {
        localStorage.removeItem('access_token')
        await supabase.auth.signOut()
        setUser(null)
      } finally {
        setAuthLoading(false)
      }
    }

    restoreSession()
  }, [])

  useEffect(() => {
    if (!user || activePage !== 'My Tasks') return undefined
    let cancelled = false

    async function fetchTasks() {
      try {
        const taskLists = await Promise.all(
          projects.map(async (project) => {
            const projectTasks = await apiRequest(`/projects/${project.id}/tasks/`)
            return projectTasks.map((task) => ({ ...task, project_name: project.name }))
          })
        )
        if (!cancelled) setTasks(taskLists.flat())
      } catch (error) {
        if (!cancelled) console.error('Failed to load tasks:', error)
      } finally {
        if (!cancelled) setTasksLoading(false)
      }
    }

    void fetchTasks()
    return () => { cancelled = true }
  }, [user, activePage, projects])

  useEffect(() => {
    if (!user || activePage !== 'Team Members') return undefined
    let cancelled = false

    async function fetchMembers() {
      try {
        const memberLists = await Promise.all(
          projects.map(async (project) => {
            const members = await apiRequest(`/projects/${project.id}/members`)
            return members.map((member) => ({
              ...member,
              project_id: project.id,
              project_name: project.name,
            }))
          })
        )
        if (!cancelled) setTeamMembers(memberLists.flat())
      } catch (error) {
        if (!cancelled) {
          console.error('Failed to load team members:', error)
          setTeamMembers([])
        }
      } finally {
        if (!cancelled) setMembersLoading(false)
      }
    }

    void fetchMembers()
    return () => { cancelled = true }
  }, [user, activePage, projects])

  if (authLoading) {
    return <div className="auth-page">Loading TeamCollab...</div>
  }

  if (!user) {
    return <Auth onLogin={setUser} />
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <h2 className="logo">TeamCollab</h2>


        <nav>
          <a
            href="#"
            className={`nav-item ${activePage === 'Dashboard' ? 'active' : ''}`}
            onClick={(e) => {
              e.preventDefault()
              setActivePage('Dashboard')
            }}
          >
            Dashboard
          </a>

          <a
            href="#"
            className={`nav-item ${activePage === 'My Projects' ? 'active' : ''}`}
            onClick={(e) => {
              e.preventDefault()
              setActivePage('My Projects')
            }}
          >
            My Projects
          </a>

          <a
            href="#"
            className={`nav-item ${activePage === 'My Tasks' ? 'active' : ''}`}
            onClick={(e) => {
              e.preventDefault()
              setTasksLoading(true)
              setActivePage('My Tasks')
            }}
          >
            My Tasks
          </a>

          <a
            href="#"
            className={`nav-item ${activePage === 'Team Members' ? 'active' : ''}`}
            onClick={(e) => {
              e.preventDefault()
              setMembersLoading(true)
              setActivePage('Team Members')
            }}
          >
            Team Members
          </a>
        </nav>

        <div className="sidebar-bottom">
          <p>TeamCollab Workspace</p>
          <small>Work better together.</small>
        </div>
      </aside>

      <main className="main-content">
        {activePage === 'Dashboard' && (
          <>
          <header className="topbar">
            <div>
              <h1>Dashboard</h1>
              <p>Welcome back! Here's what's happening with your team.</p>
            </div>

            <button
              className="profile-button"
              onClick={async () => {
                await supabase.auth.signOut()
                localStorage.removeItem('access_token')
                setUser(null)
              }}
            >
              Sign out
            </button>
          </header>
          {showForm && (
            <form
              className="project-form"
              onSubmit={async(e) => {
                e.preventDefault()

                if (!projectName.trim()) return

                const createdProject = await apiRequest('/projects/', {
                  method: 'POST',
                  body: JSON.stringify({
                    name: projectName.trim(),
                    description: projectDescription.trim(),
                  }),
                })

                setProjects((currentProjects) => [
                  ...currentProjects,
                  createdProject,
                ])

                setProjectName('')
                setProjectDescription('')
                setShowForm(false)
              }}
            >
              <h2>Create a project</h2>

              <label htmlFor="projectName">Project name</label>
              <input
                id="projectName"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="e.g. College Management System"
                required
              />

              <label htmlFor="projectDescription">Description</label>
              <textarea
                id="projectDescription"
                value={projectDescription}
                onChange={(e) => setProjectDescription(e.target.value)}
                placeholder="What is this project about?"
                rows="3"
              />

              <div className="form-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setShowForm(false)}
                >
                  Cancel
                </button>

                <button type="submit" className="form-submit">
                  Create Project
                </button>
              </div>
            </form>
          )}

          <section className="welcome-card">
            <div>
              <p className="eyebrow">YOUR WORKSPACE</p>
              <h2>Let's get things done.</h2>
              <p>Organize projects, manage tasks, and collaborate with your team.</p>
            </div>

            <button className="primary-button" onClick={() => setShowForm(true)}>+ Create Project</button>
          </section>

          <section className="stats-grid">
            <div className="stat-card">
              <p>Total Projects</p>
              <h2>{projects.length}</h2>
              <small>Your workspace projects</small>
            </div>

            <div className="stat-card">
              <p>Total Tasks</p>
              <h2>{taskStats.total}</h2>
              <small>Tasks across projects</small>
            </div>

            <div className="stat-card">
              <p>In Progress</p>
              <h2>{taskStats.in_progress}</h2>
              <small>Tasks being worked on</small>
            </div>

            <div className="stat-card">
              <p>Completed Tasks</p>
              <h2>{taskStats.done}</h2>
              <small>Successfully completed</small>
            </div>
          </section>

          <section className="projects-section">
            <div className="section-heading">
              <div>
                <h2>Your Projects</h2>
                <p>Keep track of your team's work.</p>
              </div>

              <button className="secondary-button">View All</button>
            </div>

            {projects.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">ðŸ“</div>
                <h3>No projects yet</h3>
                <p>Create your first project to get started with TeamCollab.</p>
                <button
                  className="primary-button"
                  onClick={() => setShowForm(true)}
                >
                  + Create Your First Project
                </button>
              </div>
            ) : (
              <div className="project-list">
                {projects.map((project) => (
                  <article className="project-card" key={project.id}>
                    <h3>{project.name}</h3>
                    <p>{project.description || 'No description added.'}</p>
                    <span>Active project</span>
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
        )}
        {activePage === 'My Projects' && (
          <section className="projects-section">
            <div className="section-heading">
              <div>
                <h2>My Projects</h2>
                <p>All your workspace projects.</p>
              </div>

      <button
        className="primary-button"
        onClick={() => {
          setActivePage('Dashboard')
          setShowForm(true)
        }}
      >
        + Create Project
      </button>
    </div>

    {projects.length === 0 ? (
      <p>No projects yet. Create your first project!</p>
    ) : (
      <div className="project-list">
        {projects.map((project) => (
          <article className="project-card" key={project.id}>
            <h3>{project.name}</h3>
            <p>{project.description || 'No description added.'}</p>
            <span>Active project</span>
          </article>
        ))}
      </div>
    )}
  </section>
)}

{activePage === 'My Tasks' && (
  <section className="projects-section">
    <div className="section-heading">
      <div>
        <h2>My Tasks</h2>
        <p>Tasks across all your projects.</p>
      </div>
      <button
        className="primary-button"
        onClick={() => {
          setTaskError('')
          setShowTaskForm(true)
        }}
      >
        + Create Task
      </button>
    </div>

    {showTaskForm && (
      <form
        className="project-form"
        onSubmit={async (e) => {
          e.preventDefault()
          setTaskError('')

          if (!taskProjectId) {
            setTaskError('Please select a project.')
            return
          }

          setTaskSaving(true)

          try {
            await apiRequest(`/projects/${taskProjectId}/tasks/`, {
              method: 'POST',
              body: JSON.stringify({
                title: taskTitle.trim(),
                description: taskDescription.trim(),
                priority: taskPriority,
              }),
            })

            setTaskTitle('')
            setTaskDescription('')
            setTaskPriority('medium')
            setTaskProjectId('')
            setShowTaskForm(false)

            await loadTasks(projects)
          } catch (error) {
            setTaskError(error.message)
          } finally {
            setTaskSaving(false)
          }
        }}
      >
        <h2>Create a Task</h2>

        <label htmlFor="taskProject">Project</label>
        <select
          id="taskProject"
          value={taskProjectId}
          onChange={(e) => setTaskProjectId(e.target.value)}
          required
        >
          <option value="">Select a project</option>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>

        <label htmlFor="taskTitle">Task title</label>
        <input
          id="taskTitle"
          value={taskTitle}
          onChange={(e) => setTaskTitle(e.target.value)}
          placeholder="e.g. Build login page"
          required
        />

        <label htmlFor="taskDescription">Description</label>
        <textarea
          id="taskDescription"
          value={taskDescription}
          onChange={(e) => setTaskDescription(e.target.value)}
          placeholder="Describe the task"
          rows="3"
        />

        <label htmlFor="taskPriority">Priority</label>
        <select
          id="taskPriority"
          value={taskPriority}
          onChange={(e) => setTaskPriority(e.target.value)}
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>

        {taskError && <p role="alert">{taskError}</p>}

        <div className="form-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => setShowTaskForm(false)}
          >
            Cancel
          </button>

          <button
            type="submit"
            className="form-submit"
            disabled={taskSaving}
          >
            {taskSaving ? 'Creating...' : 'Create Task'}
          </button>
        </div>
      </form>
    )}

    {tasksLoading ? (
      <p>Loading tasks...</p>
    ) : tasks.length === 0 ? (
      <div className="empty-state">
        <h3>No tasks yet</h3>
        <p>Your project tasks will appear here.</p>
      </div>
    ) : (
      <div className="project-list">
        {tasks.map((task) => (
          <article className="project-card" key={task.id}>

            {editingTaskId === task.id ? (
              <div className="project-form">
                <label>Task title</label>
                <input
                  value={editTaskTitle}
                  onChange={(e) => setEditTaskTitle(e.target.value)}
                  required
                />

                <label>Description</label>
                <textarea
                  value={editTaskDescription}
                  onChange={(e) => setEditTaskDescription(e.target.value)}
                  rows="3"
                />

                <label>Priority</label>
                <select
                  value={editTaskPriority}
                  onChange={(e) => setEditTaskPriority(e.target.value)}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>

                <button
                  type="button"
                  className="primary-button"
                  disabled={!editTaskTitle.trim()}
                  onClick={() => saveTaskEdit(task)}
                >
                  Save Changes
                </button>

                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setEditingTaskId(null)}
                >
                  Cancel
                </button>
              </div>
            ) : (
              <h3>{task.title}</h3>
            )}
            {editingTaskId !== task.id && (
              <p>{task.description || 'No description added.'}</p>
            )}
            <p>Project: {task.project_name}</p>

            <div className="task-status-row">
              <span className="task-status-label">Status</span>

              <select
                id={`status-${task.id}`}
                className={`status-badge status-${task.status}`}
                value={task.status}
                onChange={(e) =>
                  updateTaskStatus(task, e.target.value)
                }
              >
                <option value="todo">To Do</option>
                <option value="in_progress">In Progress</option>
                <option value="done">Done</option>
              </select>
            </div>

            <span className={`priority-badge priority-${task.priority}`}>
              {task.priority.charAt(0).toUpperCase() +
                task.priority.slice(1)} Priority
            </span>

            <button
              type="button"
              className="primary-button"
              onClick={() => {
                setEditingTaskId(task.id)
                setEditTaskTitle(task.title)
                setEditTaskDescription(task.description || '')
                setEditTaskPriority(task.priority)
              }}
            >
              Edit Task
            </button>

            <button
              type="button"
              className="secondary-button"
              onClick={() => deleteTask(task)}
            >
              Delete Task
            </button>
          </article>
        ))}
      </div>
    )}
  </section>
)}


{activePage === 'Team Members' && (
  <section className="projects-section">
    <div className="section-heading">
      <div>
        <h2>Team Members</h2>
        <p>People collaborating across your projects.</p>
      </div>

      <button
        type="button"
        className="primary-button"
        onClick={() => {
          setMemberError('')
          setShowMemberForm((current) => !current)
        }}
      >
        {showMemberForm ? 'Cancel' : '+ Add Member'}
      </button>
    </div>


    {showMemberForm && (
      <form className="project-form" onSubmit={addTeamMember}>
        <h3>Add a Team Member</h3>

        <label htmlFor="memberProject">Select project</label>
        <select
          id="memberProject"
          value={memberProjectId}
          onChange={(e) => setMemberProjectId(e.target.value)}
          required
        >
          <option value="">Choose a project</option>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>

        <label htmlFor="memberUserId">User ID</label>
        <input
          id="memberUserId"
          type="number"
          min="1"
          value={memberUserId}
          onChange={(e) => setMemberUserId(e.target.value)}
          placeholder="Enter the registered user's ID"
          required
        />

        <p>
          Enter the ID of an existing registered TeamCollab user.
        </p>

        {memberError && <p role="alert">{memberError}</p>}

        <button
          type="submit"
          className="primary-button"
          disabled={memberSaving}
        >
          {memberSaving ? 'Adding Member...' : 'Add Member'}
        </button>
      </form>
    )}

    {membersLoading ? (
      <p>Loading team members...</p>
    ) : teamMembers.length === 0 ? (
      <div className="empty-state">
        <h3>No team members yet</h3>
        <p>
          Add members to your projects to see them here.
        </p>
      </div>
    ) : (
      <div className="project-list">
        {teamMembers.map((member) => (
          <article
            className="project-card"
            key={`${member.project_id}-${member.user_id}`}
          >
            <h3>{member.name}</h3>
            <p>{member.email}</p>
            <p>Project: {member.project_name}</p>
            <span className="priority-badge priority-medium">
              {member.role}
            </span>
          </article>
        ))}
      </div>
    )}
  </section>
)}
      </main>
    </div>
  )
}

export default App
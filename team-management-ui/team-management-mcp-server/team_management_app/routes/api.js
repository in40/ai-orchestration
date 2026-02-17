const express = require('express');
const router = express.Router();

// Mock data for team members
let teamMembers = [
  {
    id: 'member-1',
    name: 'John Doe',
    email: 'john.doe@example.com',
    role: 'Frontend Developer',
    skills: ['React', 'JavaScript', 'CSS'],
    availability: 'full_time'
  },
  {
    id: 'member-2',
    name: 'Jane Smith',
    email: 'jane.smith@example.com',
    role: 'Backend Developer',
    skills: ['Python', 'Django', 'PostgreSQL'],
    availability: 'full_time'
  }
];

// Mock data for tasks
let tasks = [
  {
    id: 'task-1',
    title: 'Implement login feature',
    description: 'Create user login functionality',
    assignee_id: 'member-1',
    due_date: '2024-12-15',
    status: 'in_progress',
    priority: 'high',
    tags: ['frontend', 'auth']
  },
  {
    id: 'task-2',
    title: 'Fix database connection issue',
    description: 'Resolve intermittent database connection problems',
    assignee_id: 'member-2',
    due_date: '2024-12-10',
    status: 'todo',
    priority: 'critical',
    tags: ['backend', 'database']
  }
];

// Get all team members
router.get('/team-members', (req, res) => {
  res.json(teamMembers);
});

// Get a specific team member
router.get('/team-members/:id', (req, res) => {
  const member = teamMembers.find(m => m.id === req.params.id);
  if (!member) {
    return res.status(404).json({ error: 'Member not found' });
  }
  res.json(member);
});

// Create a new team member
router.post('/team-members', (req, res) => {
  const newMember = {
    id: `member-${Date.now()}`,
    ...req.body
  };
  teamMembers.push(newMember);
  res.status(201).json(newMember);
});

// Update a team member
router.put('/team-members/:id', (req, res) => {
  const index = teamMembers.findIndex(m => m.id === req.params.id);
  if (index === -1) {
    return res.status(404).json({ error: 'Member not found' });
  }
  
  teamMembers[index] = { ...teamMembers[index], ...req.body };
  res.json(teamMembers[index]);
});

// Delete a team member
router.delete('/team-members/:id', (req, res) => {
  const index = teamMembers.findIndex(m => m.id === req.params.id);
  if (index === -1) {
    return res.status(404).json({ error: 'Member not found' });
  }
  
  teamMembers.splice(index, 1);
  res.status(204).send();
});

// Get all tasks
router.get('/tasks', (req, res) => {
  const { assignee_id, status, priority } = req.query;
  let filteredTasks = tasks;
  
  if (assignee_id) {
    filteredTasks = filteredTasks.filter(t => t.assignee_id === assignee_id);
  }
  
  if (status) {
    filteredTasks = filteredTasks.filter(t => t.status === status);
  }
  
  if (priority) {
    filteredTasks = filteredTasks.filter(t => t.priority === priority);
  }
  
  res.json(filteredTasks);
});

// Get a specific task
router.get('/tasks/:id', (req, res) => {
  const task = tasks.find(t => t.id === req.params.id);
  if (!task) {
    return res.status(404).json({ error: 'Task not found' });
  }
  res.json(task);
});

// Create a new task
router.post('/tasks', (req, res) => {
  const newTask = {
    id: `task-${Date.now()}`,
    status: 'todo',
    ...req.body
  };
  tasks.push(newTask);
  res.status(201).json(newTask);
});

// Update a task
router.put('/tasks/:id', (req, res) => {
  const index = tasks.findIndex(t => t.id === req.params.id);
  if (index === -1) {
    return res.status(404).json({ error: 'Task not found' });
  }
  
  tasks[index] = { ...tasks[index], ...req.body };
  res.json(tasks[index]);
});

// Delete a task
router.delete('/tasks/:id', (req, res) => {
  const index = tasks.findIndex(t => t.id === req.params.id);
  if (index === -1) {
    return res.status(404).json({ error: 'Task not found' });
  }
  
  tasks.splice(index, 1);
  res.status(204).send();
});

module.exports = router;
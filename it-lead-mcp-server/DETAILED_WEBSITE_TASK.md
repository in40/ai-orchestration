# Detailed Website Development Task for NexusTech

## Original Task Submission (via IT Lead UI)

```json
{
  "task_id": "website-dev-cool-demo",
  "title": "Build a Modern Cool Website - Tech Showcase Portfolio",
  "description": "Create a stunning, modern portfolio website for NexusTech. Show services, team members, and projects with interactive elements.",
  "assignee": "IT Lead",
  "priority": "high",
  "due_date": "",
  "context": {
    "code_diff": "",
    "programming_language": "React, TypeScript, Node.js, Python",
    "framework": "Vite, Express.js, SQLAlchemy",
    "acceptance_criteria": [
      "Responsive design that works on mobile, tablet, and desktop screens",
      "Modern UI with glassmorphism effects and smooth transitions",
      "Interactive hero section with animated gradient background",
      "Services showcase grid with hover animations and icons"
    ],
    "business_context": "NexusTech is a boutique tech consultancy looking to establish their online presence."
  },
  "tags": ["feature", "frontend", "backend"],
  "dependencies": [],
  "attachments": []
}
```

---

## IT Lead Analysis & Decomposition

When you submit this task, IT Lead analyzes it using the **Task Routing Engine** and creates a comprehensive plan:

### Step 1: Content Analysis
IT Lead's LLM evaluates your description:
- ✅ Keywords detected: "modern", "portfolio website", "services", "team members", "projects"
- ✅ Technology stack identified: React, TypeScript, Node.js, Python, Vite, Express.js
- ✅ Design requirements: glassmorphism, animated gradients, interactive elements

### Step 2: Routing Decision
Based on routing rules, IT Lead determines:

| Component | Assigned To | Tool Used |
|-----------|-------------|-----------|
| Requirements gathering | Requirements Engineer | `analyze_requirements` |
| Technical specification | Implementation Engineer | `generate_code_from_spec` |
| Frontend implementation | Implementation Engineer | `implement_feature` |
| Backend API development | Implementation Engineer | `vibe_code_async` |

### Step 3: Task Sequence

```
PHASE 1: REQUIREMENTS ENGINEERING
├── Analyze business requirements (NexusTech consultancy)
├── Define technical specifications
└── Create acceptance criteria documentation

PHASE 2: FRONTEND DEVELOPMENT  
├── Setup React + TypeScript project with Vite
├── Implement responsive layout structure
├── Build hero section with animated gradient background
├── Create services showcase grid component
├── Add team member profiles cards
├── Build project portfolio gallery with lightbox
├── Implement dark mode toggle functionality

PHASE 3: BACKEND DEVELOPMENT
├── Setup Express.js server
├── Configure SQLAlchemy database models
├── Create API endpoints for:
│   ├── GET /api/services - List all services
│   ├── GET /api/team - Get team members
│   ├── GET /api/projects - Fetch portfolio items
│   └── POST /api/contact - Handle contact form submissions

PHASE 4: INTEGRATION & TESTING
├── Connect frontend to backend APIs
├── Implement email sending functionality (contact form)
└── Run end-to-end tests

PHASE 5: FINAL REVIEW
├── Code review by code-reviewer agent
├── QA testing for responsiveness
└── SEO optimization check
```

---

## Expected Website Features

### Visual Design
- **Color Scheme**: Modern gradient with glassmorphism effects
- **Typography**: Clean, modern sans-serif fonts
- **Animations**: Smooth transitions on hover/focus states

### Pages & Components
1. **Hero Section** - Animated background with call-to-action
2. **Services Showcase** - Grid of service cards (development, consulting, etc.)
3. **Team Members** - Profile cards with social links
4. **Portfolio Gallery** - Filterable project showcase with lightbox view
5. **Contact Form** - With validation and email notification

### Technical Stack
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS
- Backend: Node.js + Express.js + SQLAlchemy (PostgreSQL)
- Styling: Modern CSS with glassmorphism effects
- Deployment-ready structure

---

## How to Submit This Task in the Web UI

1. Open `http://localhost:5173/tasks`
2. Click **"Add Task"** button
3. Fill in:
   - **Task Title**: "Build NexusTech Website"
   - **Description**: Paste your detailed requirements (like above)
   - **Assign To**: Keep as "IT Lead" 
   - **Priority**: High/Medium/Low
4. In the **Routing & Assignment** section, you can optionally specify:
   - Tags: `frontend`, `backend`, `full-stack`
5. In **Additional Context**, include:
   - Programming Language: React, TypeScript, Node.js, Python
   - Framework: Vite, Express.js, SQLAlchemy
6. Click **"Submit Task"**

IT Lead will then analyze your requirements and start the workflow automatically!

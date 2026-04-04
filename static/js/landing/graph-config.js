// Graph configuration and data for hero and how-it-works visualizations
// D3.js force-directed graph setup

// Desktop graph: 18 nodes representing technology stack
export const heroGraphData = {
  nodes: [
    { id: "Python", group: 1, x: null, y: null },
    { id: "Django", group: 1 },
    { id: "PostgreSQL", group: 2 },
    { id: "Neo4j", group: 2 },
    { id: "Redis", group: 2 },
    { id: "React", group: 1 },
    { id: "JavaScript", group: 1 },
    { id: "AWS", group: 3 },
    { id: "Docker", group: 3 },
    { id: "API", group: 1 },
    { id: "GraphQL", group: 1 },
    { id: "Celery", group: 3 },
    { id: "HTMX", group: 1 },
    { id: "Bootstrap", group: 1 },
    { id: "REST", group: 1 },
    { id: "Git", group: 3 },
    { id: "OpenAI", group: 3 },
    { id: "Matching", group: 1 }
  ],
  links: [
    { source: "Python", target: "Django", distance: 80 },
    { source: "Django", target: "PostgreSQL", distance: 80 },
    { source: "Django", target: "Redis", distance: 80 },
    { source: "Django", target: "Celery", distance: 80 },
    { source: "Neo4j", target: "Matching", distance: 80 },
    { source: "Matching", target: "Python", distance: 80 },
    { source: "React", target: "JavaScript", distance: 60 },
    { source: "JavaScript", target: "HTMX", distance: 70 },
    { source: "HTMX", target: "Bootstrap", distance: 70 },
    { source: "API", target: "Django", distance: 80 },
    { source: "API", target: "REST", distance: 60 },
    { source: "GraphQL", target: "API", distance: 70 },
    { source: "AWS", target: "Docker", distance: 80 },
    { source: "Docker", target: "Python", distance: 80 },
    { source: "OpenAI", target: "Matching", distance: 80 },
    { source: "Redis", target: "Celery", distance: 60 },
    { source: "Bootstrap", target: "React", distance: 70 },
    { source: "Git", target: "Docker", distance: 70 },
    { source: "PostgreSQL", target: "REST", distance: 70 },
    { source: "Neo4j", target: "GraphQL", distance: 80 }
  ]
};

// Mobile graph: 10 nodes (subset of desktop data)
export const mobileGraphData = {
  nodes: [
    { id: "Python", group: 1 },
    { id: "Django", group: 1 },
    { id: "PostgreSQL", group: 2 },
    { id: "Neo4j", group: 2 },
    { id: "React", group: 1 },
    { id: "JavaScript", group: 1 },
    { id: "API", group: 1 },
    { id: "AWS", group: 3 },
    { id: "OpenAI", group: 3 },
    { id: "Matching", group: 1 }
  ],
  links: [
    { source: "Python", target: "Django", distance: 80 },
    { source: "Django", target: "PostgreSQL", distance: 80 },
    { source: "Neo4j", target: "Matching", distance: 80 },
    { source: "Matching", target: "Python", distance: 80 },
    { source: "React", target: "JavaScript", distance: 60 },
    { source: "API", target: "Django", distance: 80 },
    { source: "AWS", target: "Python", distance: 80 },
    { source: "OpenAI", target: "Matching", distance: 80 },
    { source: "JavaScript", target: "React", distance: 70 },
    { source: "PostgreSQL", target: "API", distance: 70 }
  ]
};

// Node colors by group
export const nodeColors = {
  1: "#0066FF",  // Blue - Frontend/API
  2: "#00D4AA",  // Cyan - Database
  3: "#0099FF"   // Light Blue - Infrastructure
};

// "How It Works" graph: 8 nodes showing the matching pipeline
export const howItWorksGraphData = {
  nodes: [
    { id: "Candidate", group: 1 },
    { id: "Python", group: 1 },
    { id: "Django", group: 1 },
    { id: "PostgreSQL", group: 2 },
    { id: "Neo4j", group: 2 },
    { id: "Match", group: 3 },
    { id: "Job", group: 3 },
    { id: "Skills", group: 2 }
  ],
  links: [
    { source: "Candidate", target: "Python", distance: 80 },
    { source: "Python", target: "Django", distance: 80 },
    { source: "Django", target: "PostgreSQL", distance: 80 },
    { source: "Neo4j", target: "Skills", distance: 80 },
    { source: "Skills", target: "Match", distance: 80 },
    { source: "Match", target: "Job", distance: 80 },
    { source: "Python", target: "Skills", distance: 70 }
  ]
};
